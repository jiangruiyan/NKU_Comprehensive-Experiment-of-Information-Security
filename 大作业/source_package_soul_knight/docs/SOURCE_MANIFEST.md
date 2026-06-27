# 源码清单

## 提交依据

实验要求 PPT 中对结题提交的要求为:

- 中期汇报 PPT + 结题汇报 PPT + 完整代码文件, 小组任一人上传。
- 实验报告每人上传。

本目录对应“完整代码文件”。

## 已整理源码

### 4.2.0 存档分析脚本

路径: `save_tools_4_2_0/code/`

| 文件 | 说明 |
| --- | --- |
| `crack.py` | 针对 `game.data` 的 XOR 已知明文密钥爆破 |
| `gamedataDecrypt.py` | 早期单文件解密脚本 |
| `encrypt.py` | 早期单文件重新加密脚本 |
| `batch_crack.py` | 批量解密识别脚本, 支持明文 JSON、DES-CBC、XOR |
| `batch_encrypt.py` | 按 `cracked_keys.txt` 记录重新加密 JSON |
| `test_des.py` | DES Key/IV 复现验证 |
| `search_integrity.py` | 存档完整性/校验相关搜索脚本 |
| `search_integrity2.py` | 存档完整性/校验相关搜索脚本 |
| `analyze_so.py` | so/符号辅助分析脚本 |

示例记录:

- `save_tools_4_2_0/examples/cracked_keys.txt`

### 4.2.0 Zygisk Hook 模块源码

路径: `zygisk_hook_4_2_0/`

| 文件 | 说明 |
| --- | --- |
| `build.py` | 调用 Android NDK 编译并打包 Magisk 模块 |
| `module.prop` | Magisk 模块元数据 |
| `jni/main.cpp` | Hook 核心逻辑 |
| `jni/zygisk.hpp` | Zygisk API 头文件 |
| `jni/Android.mk` | NDK 构建脚本 |
| `jni/Application.mk` | NDK ABI/平台配置 |

### 8.1.0 IL2CPP runtime dump 脚本

路径: `il2cpp_dump_8_1_0/`

| 文件 | 说明 |
| --- | --- |
| `README.md` | 8.1.0 已验证 dump 流程 |
| `scripts/build.py` | `/proc/PID/mem` 分段读取、拼接、SoFixer 编排 |
| `scripts/fix_elf_sym.py` | 修复 SoFixer 输出的 `.dynsym st_name` |
| `scripts/Il2CppDumper_config.json` | Il2CppDumper 配置 |
| `scripts/README.md` | 实际所需脚本说明 |

## 排除内容

以下内容不是源码, 或体积过大, 没有纳入提交包:

- APK、第三方工具安装包、反编译工具目录。
- `libil2cpp_real.so`、`libil2cpp_sofixer*.so`、`dump.cs`、`script.json`、`DummyDll` 等运行结果。
- Zygisk 模块编译中间产物 `obj/`、`libs/` 和 zip 安装包。
- 完整个人游戏存档数据。
