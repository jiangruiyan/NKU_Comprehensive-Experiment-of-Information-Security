# Soul Knight 8.1.0 IL2CPP Dump —— 实际可用方法(已验证)

> 本文是**唯一权威**的 dump 方法说明。结论由 `build.py` 源码 + 产物文件时间戳 +
> `dump_route_report.json` / `libil2cpp_manifest.json` 交叉验证得出(2026-06-13 复核)。
> 旧的探索性 / 错误结论文档已移入 [`archive/`](archive/),仅作历史参考。

---

## 0. 环境

| 项 | 值 |
|----|----|
| 游戏 | 元气骑士 Soul Knight 8.1.0 (`com.ChillyRoom.DungeonShooter`) |
| 引擎 | Unity 2022.3.57f1 · IL2CPP · metadata **v31.1** · ARM64 (arm64-v8a) |
| 加固 | **PGL Armor(腾讯)**:仅加密 `libil2cpp.so`,运行时在内存解密;metadata 未加密 |
| 设备 | ROOT 真机 + Magisk(+ LSPosed),ADB 可用且不触发闪退 |

**两个输入文件,来源不同:**
- `global-metadata.dat` —— **未加密**,标准 v31(magic `0xFAB11BAF`、版本 `31`,45,973,504 字节),直接可用。
- `libil2cpp.so` —— 磁盘上是 PGL 加密态,**必须从运行时内存 dump**(见下)。

---

## 1. 全流程(按实际执行顺序)

```
游戏运行(内存中已解密)
   │  ① build.py: dd /proc/PID/mem 按段读取(等 r-xp 重映射后)
   ▼
libil2cpp_real.so  (4 段拼接, 230,879,232 B, base=0x7012181000)
   │  ② SoFixer.exe -m 0x7012181000   (运行时 VA 指针 → 文件偏移)
   ▼
libil2cpp_sofixer.so
   │  ③ fix_elf_sym.py   (修 SoFixer 损坏的 .dynsym st_name)
   ▼
libil2cpp_sofixer_fixsym.so   ← 最终可用 SO
   │  ④ Il2CppDumper(+ config.json + 管道喂 EOF)  + global-metadata.dat
   ▼
dump.cs (96.5MB) / script.json (256MB) / stringliteral.json / DummyDll
```

产物全部位于 `runtime_artifacts/20260422-193513/`,权威 `dump.cs` 另复制到
`crack/ill2cppDumperContent/dump.cs`(所有 RVA / 偏移的来源)。

---

## 2. 步骤①:内存 dump(核心,`build.py`)

PGL 的关键行为:磁盘 so 加密,**运行时先把整个 so 映射成一段 `r--p`(仍加密),
再把代码解密、重映射为 `r-xp` + `rw-p`**。所以 dump 有两个必须做对的点:

### 2.1 等待解密重映射 —— `wait_for_rxp_mapping` (build.py:388)
轮询 `/proc/PID/maps`,**直到 `libil2cpp.so` 出现 `r-xp` 段才开始 dump**。
> 这是 4 月一直拿到"不可用结果"的真正原因:dump 早了,读到的是还没解密的 `r--p`
> 加密段 / 全 0 的 `rw-p`(CodeRegistration 尚未填充)。**与 config.json 无关。**

### 2.2 定位真实基址 —— `find_real_libil2cpp_cluster` (build.py:351)
PGL 会在 `r-xp` 前面映射一段最大 **256MB** 的 `r--p` 头段(加密缓冲)。
从 `r-xp` 往前找 **`offset==0` 且 `r--p`** 的段作为真实 base,容忍 ≤0x10000 的页对齐间隙
把相邻段聚成一簇(本次共 4 段)。

### 2.3 用 /proc/PID/mem 读,不要用 map_files —— `dump_libil2cpp_cluster` (build.py:417)
```sh
dd if=/proc/PID/mem bs=4096 skip=<VA/4096> count=<SIZE/4096> of=/sdcard/_il2cpp_seg_tmp.bin
```
- `/proc/PID/map_files/start-end` 的符号链接会返回**整个 220MB 的 APK 加密文件**(且每段都返回整文件),不可用。
- `/proc/PID/mem` 按虚拟地址范围**精确读出已解密内存**(含 COW 改过的 `rw-p` 页)。
- 每段先 `dd` 到 `/sdcard` 临时文件,再 `adb exec-out cat` 拉回 PC,按段拼接(段间空隙补 0)。
- 同时写 `libil2cpp_manifest.json`(记录 4 段地址 / perms / `method:proc_mem` / base)。

本次实际 4 段:
```
r--p 0x7012181000-0x7016c75000  (文件头, offset 0)
r-xp 0x7016c78000-0x701ed21000  (代码段, offset 0x4af3000)
rw-p 0x701ed24000-0x701f5cf000  (offset 0xcb9b000)
rw-p 0x701f5d2000-0x701fdb0000  (offset 0xd445000)
base = 0x7012181000
```

---

## 3. 步骤②:SoFixer

```
SoFixer.exe -s libil2cpp_real.so -o libil2cpp_sofixer.so -m 0x7012181000 -b fixed/libil2cpp_fixed.so
```
把运行时 VA 指针重写为文件相对偏移,重建可被 Il2CppDumper 识别的 ELF 结构。
(命令与 returncode=0 记录在 `dump_route_report.json` 的 `sofixer` 段。)

---

## 4. 步骤③:修符号(`fix_elf_sym.py`)

SoFixer 有时把 `.dynsym` 的 `st_name` 当成 VA 指针重写,导致它指向 `.dynstr` 之外
→ Il2CppDumper 的 `StructGenerator` / Cpp2IL 读符号名时 `EndOfStreamException` 崩溃。
本脚本把越界的 `st_name` 复位 → `libil2cpp_sofixer_fixsym.so`(**最终用于 dump 的 SO**)。

> 注意:`build.py` 内置的 `sym_patch` 当时 `patched:false`(没成功),`fixsym.so` 是
> **次日(04-23)单独运行 `fix_elf_sym.py` 产生的**。

---

## 5. 步骤④:Il2CppDumper(06-11 的突破)

输入:`libil2cpp_sofixer_fixsym.so` + `global-metadata.dat`。两个操作要点:

1. **补回 config.json**:Il2CppDumper 目录缺 `config.json`(`RequireAnyKey:false`)会
   `FileNotFoundException` 直接闪退。(此文件 6 月被误删过,与 4 月失败无关。)
2. **喂 EOF 跳过交互**:内存 dump 出来的 so 会触发
   `Detected this may be a dump file. Input il2cpp dump address or input 0 to force continue:`
   并**阻塞等 stdin**。管道喂 EOF(或输入 `0`)即强制继续。

之后 Il2CppDumper **自动搜索**到:
```
CodeRegistration     = 0xcba3f98
MetadataRegistration = 0xd00d538
```
(`dump_route_report.json` stdout 里 `Searching... CodeRegistration : cba3f98` 为证。)
产出完整 `dump.cs`(~2.6M 行) / `script.json`(561,853 方法) / `stringliteral.json` / DummyDll。

> **lsposed_native 的定位**:它(`crack/lsposed_native/hook_il2cpp.cpp`)是教程 B 的备用方案——
> hook `il2cpp_codegen_register` 在运行时截获这两个寄存器地址,供 Il2CppDumper 手动模式填入。
> 但因为修好的 fixsym.so 上**自动搜索就成功了**,这条路**最终没用上**,保留作 fallback。

---

## 6. 常见误解纠正

| 误解 | 事实 |
|------|------|
| "4 月失败是因为缺 config.json" | ❌ 真因是 **dump 早于 PGL 解密重映射** + dumper stdin 卡死;config.json 是 6 月才误删 |
| "SO 是 PADumper 拿的" | ❌ 是 `build.py` 自写的 `dd /proc/PID/mem` 流程 |
| "metadata 加密,要从 /dev/zero dump" | ❌ metadata 是标准 v31 未加密,直接用;`fixed/global-metadata-v24/27/28/29.dat` 是当时的版本号试错产物,没用上 |
| "Il2CppDumper 处理不了这版 metadata,得手写 Python 解析器" | ❌ 这是 `archive/dump排查过程.md` 的旧错误结论;给对 fixsym.so + config.json + EOF 后它跑得很好 |
| "用 map_files 读 so 就行" | ❌ map_files 返回整个加密 APK 文件,必须用 `/proc/PID/mem` |

---

## 7. 迁移到新版本(8.x 更新后)

RVA 每次重编译都会变,字段偏移相对稳定。最小流程:
1. 新版上重跑 `build.py`(proc_mem dump,注意仍要等 r-xp 重映射) → `real.so` → SoFixer。
2. `fix_elf_sym.py` 修符号 → `fixsym.so`。
3. Il2CppDumper(config.json + EOF)→ 新 `dump.cs`。
4. grep `C19Controller.SetUpChar` / `C31Controller.SetUpChar` 等取新 RVA,更新 hook 常量。

---

## 8. 权威产物清单

| 文件 | 路径 | 状态 |
|------|------|------|
| `libil2cpp_sofixer_fixsym.so` | `runtime_artifacts/20260422-193513/libil2cpp/` | ✅ 最终可用 SO(220MB) |
| `global-metadata.dat` | `crack/global-metadata.dat` | ✅ 标准 v31(45MB) |
| `dump.cs` | `il2cppdumper_test/` 及 `ill2cppDumperContent/` | ✅ 96.5MB,所有偏移来源 |
| `script.json` | `il2cppdumper_test/` | ✅ 256MB,561,853 方法 |
| `stringliteral.json` | `il2cppdumper_test/` | ✅ 5.5MB |
| `libil2cpp_manifest.json` / `dump_route_report.json` | `runtime_artifacts/20260422-193513/` | ✅ dump 过程记录 |

**已废弃产物**(同目录下,可删):`dumper_acs/`(手写 Python 路线,类型不全)、
`dumper_so1_.../`(38k 行桩)、`dumper_patched_meta/`、`dumper_no_attr/`(metadata 试错失败品)。
