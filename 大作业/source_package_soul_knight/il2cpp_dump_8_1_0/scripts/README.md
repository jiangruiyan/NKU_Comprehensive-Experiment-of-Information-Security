# dump 实际所需脚本(副本)

这些是**实际产出可用 dump 的脚本**,从 `crack/` 根目录复制于此,方便集中保存。
原件仍在 `crack/`(`build.py` / `fix_elf_sym.py`),Il2CppDumper 的 config 原件在
`E:\Crack\Il2CppDumper-win-v6.7.46\config.json`。完整流程见 [`../README.md`](../README.md)。

| 文件 | 作用 | 对应流程步骤 |
|------|------|-------------|
| `build.py` | 编排器:adb 取 PID → 等 r-xp 重映射 → `dd /proc/PID/mem` 读 4 段 → 拼接 → SoFixer | ①② |
| `fix_elf_sym.py` | 修 SoFixer 损坏的 `.dynsym st_name`(否则 Il2CppDumper/Cpp2IL 读符号崩) → `fixsym.so` | ③ |
| `Il2CppDumper_config.json` | Il2CppDumper v6.7.46 配置(`RequireAnyKey:false` / `ForceVersion:31` 等),**缺它会闪退** | ④ |

> ⚠️ 这三个是关键路径。`crack/` 根目录下的 `gen_acs_dump.py` / `gen_full_dump.py` /
> `gen_il2cpp_h.py` / `gen_stringliteral*.py` / `merge_scripts.py` / `patch_metadata.py` /
> `gen_script_json.py` 都是**已废弃的手写 Python 解析路线**,不在这条可用流程里,故未复制。

## 步骤④ 的手动命令(突破口)

`build.py` 内置的 Il2CppDumper 调用当时产出的是桩(自动模式没喂 EOF)。最终可用 dump
是**手动**这样跑出来的:

```powershell
# config.json 必须在 Il2CppDumper.exe 同目录(本目录的 Il2CppDumper_config.json 即其内容)
# 内存 dump 的 so 会卡在 "Input il2cpp dump address or input 0..." -> 用管道喂 EOF/0
echo "" | .\Il2CppDumper.exe `
  ..\runtime_artifacts\20260422-193513\libil2cpp\libil2cpp_sofixer_fixsym.so `
  ..\global-metadata.dat `
  .\out
# 之后自动搜到 CodeRegistration=0xcba3f98 / MetadataRegistration=0xd00d538,完整 dump
```

外部二进制工具(非脚本,未复制):`crack/SoFixer.exe`、`E:\Crack\Il2CppDumper-win-v6.7.46\Il2CppDumper.exe`。
