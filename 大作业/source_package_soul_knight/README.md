# Soul Knight Security Analysis Source Package

本目录是《信息安全综合实验》大作业的源码提交包, 对应实验报告中“元气骑士本地存档与运行时逻辑安全分析”的代码部分。

## 目录结构

```text
source_package_soul_knight/
  save_tools_4_2_0/
    code/                 4.2.0 存档解密、密钥爆破、DES/XOR 复现和重新加密脚本
    examples/             批量解密识别结果示例, 不包含完整存档数据
  zygisk_hook_4_2_0/      4.2.0 古代元素使技能修改的 Zygisk 模块源码
  il2cpp_dump_8_1_0/      8.1.0 运行时 libil2cpp dump、SoFixer、fixsym、Il2CppDumper 流程脚本
  docs/                   提交要求摘录和源码清单
```

## 1. save_tools_4_2_0

对应报告中的“存档加密算法分析: XOR 与 DES”和“存档修改”部分。

主要脚本:

- `crack.py`: 针对 `game.data` 的 XOR 已知明文密钥爆破脚本。
- `gamedataDecrypt.py`: 早期 `game.data` 解密脚本。
- `encrypt.py`: 早期 `game.data` 重新加密脚本。
- `batch_crack.py`: 批量识别明文 JSON、DES-CBC、XOR 加密文件, 并输出解密结果。
- `batch_encrypt.py`: 根据 `cracked_keys.txt` 记录, 将修改后的 JSON 按原方式重新加密。
- `test_des.py`: 独立验证 DES Key、IV 和 DES-CBC 解密/加密逻辑。
- `search_integrity.py`, `search_integrity2.py`: 存档完整性或校验相关搜索脚本。
- `analyze_so.py`: 辅助分析 so/符号的脚本。

关键结论:

- `game.data` 使用自定义 XOR, 密钥为 `smg`。
- `item_data.data`、`setting.data`、`task.data` 等使用 `DES(key=iambo)`。
- DES Key 来自 `Abo.JsonUtil.LoadJsonWithCrypt<ItemData>` 的 `secret` 参数。
- DES IV 由 `"\x11(55(#"` 通过 XOR 密钥 `"PASSWORD"` 解出 `Ahbool` 后补零得到。

运行依赖:

- Python 3
- `pycryptodome` (`Crypto.Cipher.DES`)

## 2. zygisk_hook_4_2_0

对应报告中的“hook 游戏逻辑并修改古代元素使技能”部分。

主要文件:

- `jni/main.cpp`: Zygisk 模块核心逻辑, 包含目标进程判断、`libil2cpp.so` 基址解析、ARM32 inline hook 和技能字段修改。
- `jni/zygisk.hpp`: Zygisk API 头文件。
- `jni/Android.mk`, `jni/Application.mk`: Android NDK 构建配置。
- `build.py`: 自动查找 NDK、编译 `.so` 并打包为 Magisk 模块的脚本。
- `module.prop`: Magisk 模块元数据。

运行依赖:

- Android NDK r21+
- Magisk + Zygisk 环境
- 已 root 的 Android 设备

源码包中未包含 `libs/`、`obj/` 和 `zygisk_envoy_mod.zip`, 因为它们是编译产物, 可由 `build.py` 重新生成。

## 3. il2cpp_dump_8_1_0

对应报告中的“8.1 源码再次尝试获得和分析”部分。

主要流程:

```text
运行游戏并等待 PGL Armor 完成 libil2cpp.so 解密
  -> build.py 通过 /proc/PID/mem 分段读取运行时内存
  -> 拼接得到 libil2cpp_real.so
  -> SoFixer 修复运行时 ELF
  -> fix_elf_sym.py 修复 .dynsym st_name
  -> libil2cpp_sofixer_fixsym.so + 未加密 global-metadata.dat
  -> Il2CppDumper 生成 dump.cs / script.json / stringliteral.json / DummyDll
```

主要文件:

- `README.md`: 8.1.0 IL2CPP dump 的已验证流程说明。
- `scripts/build.py`: 运行时 dump 和 SoFixer 编排脚本。
- `scripts/fix_elf_sym.py`: 修复 SoFixer 输出中异常动态符号名字段。
- `scripts/Il2CppDumper_config.json`: Il2CppDumper v6.7.46 配置。
- `scripts/README.md`: 实际所需脚本说明。

运行依赖:

- Root 真机
- ADB
- SoFixer
- Il2CppDumper v6.7.46

源码包中未包含 `libil2cpp_real.so`、`libil2cpp_sofixer*.so`、`dump.cs`、`script.json`、`DummyDll` 等产物, 因为它们体积较大且属于运行结果, 不是源码。

## 未包含内容

为保持源码包可提交、可审阅, 以下内容没有放入压缩包:

- 游戏 APK 文件。
- 第三方工具目录, 如 Il2CppDumper、Cpp2IL、dnSpy、Ghidra、Frida、SoFixer 可执行文件等。
- 大型 dump 产物, 如修复后的 `libil2cpp.so`、`dump.cs`、`script.json`、`DummyDll`。
- 编译中间产物, 如 Zygisk 模块的 `obj/`、`libs/` 和 zip 安装包。
- 完整个人存档数据文件。

这些内容可根据实验报告中的路径在本地工程目录中重新定位, 或由本源码包中的脚本重新生成。
