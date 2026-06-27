"""第二轮：排除.NET/Unity框架，专门搜索游戏业务代码中的反篡改/校验逻辑"""
import re

dump_path = r"e:\Crack\soul-knight-4-2-0\crack\dump.cs"

# 排除的命名空间（.NET/Mono/Unity框架代码）
framework_ns = re.compile(
    r'System\.|Mono\.|UnityEngine\.|Unity\.|Microsoft\.|Google\.|Facebook\.|'
    r'Locale\.|I18N\.|Newtonsoft\.|JetBrains\.|LitJson\.|okhttp|'
    r'com\.google\.|com\.facebook\.|com\.unity\.|TMPro\.|TextMeshPro',
    re.IGNORECASE
)

with open(dump_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"dump.cs 共 {len(lines)} 行\n")

# ====== 1. 搜索游戏自定义的 Verify/Validate/Check 类或方法 ======
print("=" * 70)
print("1. 游戏业务代码中的 Verify/Validate/Check（排除框架）")
print("=" * 70)

# 先收集当前命名空间上下文
current_ns = ""
current_class = ""
verify_pattern = re.compile(r'Verify|Validate|Check(?!Box|Mark|Point|ed\b|Out\b|In\b)', re.IGNORECASE)

game_verify_hits = []
for i, line in enumerate(lines, 1):
    if '// Namespace: ' in line:
        current_ns = line.split('// Namespace: ')[-1].strip()
    if 'class ' in line and '//' in line:
        m = re.search(r'class\s+(\w+)', line)
        if m:
            current_class = m.group(1)
    if verify_pattern.search(line) and not framework_ns.search(current_ns):
        # 仅关注方法声明或重要的字段
        if any(kw in line for kw in ['void ', 'bool ', 'int ', 'string ', 'static ', 'private ', 'public ', 'internal ']):
            game_verify_hits.append((i, current_ns, current_class, line.rstrip()[:200]))

print(f"  找到 {len(game_verify_hits)} 处")
for lineno, ns, cls, text in game_verify_hits[:80]:
    print(f"  L{lineno} [{ns}::{cls}]: {text}")

# ====== 2. 专门搜索反作弊/安全SDK类 ======
print("\n" + "=" * 70)
print("2. 反作弊/安全保护SDK")
print("=" * 70)

security_pattern = re.compile(
    r'AntiCheat|GameGuard|HackShield|SecureValue|ObscuredInt|ObscuredFloat|'
    r'ObscuredString|ACTk|CodeStage|Obscured|SecurePrefs|SecurePlayerPrefs|'
    r'EncryptedPrefs|TamperDetect|SpeedHack|WallHack|AimBot|CheatDetect',
    re.IGNORECASE
)
for i, line in enumerate(lines, 1):
    if security_pattern.search(line):
        print(f"  L{i}: {line.rstrip()[:200]}")

# ====== 3. root检测/模拟器检测/调试检测 ======
print("\n" + "=" * 70)
print("3. Root/模拟器/调试检测")
print("=" * 70)

detect_pattern = re.compile(
    r'root.?detect|isRooted|jailbreak|Superuser|su\s+binary|'
    r'isEmulator|emulator.?detect|BlueStacks|NoxPlayer|'
    r'isDebug|debugger.?detect|anti.?debug|ptrace|TracerPid|'
    r'Frida|Xposed|MagiskHide|GameGuardian|Lucky.?Patcher|'
    r'SB.?Game.?Hack|iGG|CreeHack',
    re.IGNORECASE
)
for i, line in enumerate(lines, 1):
    if detect_pattern.search(line):
        print(f"  L{i}: {line.rstrip()[:200]}")

# ====== 4. PlayerPrefs 相关的校验逻辑 ======
print("\n" + "=" * 70)
print("4. PlayerPrefs 相关校验/保护")
print("=" * 70)

prefs_check_pattern = re.compile(
    r'PlayerPrefs.*(?:Check|Verify|Validate|Hash|Encrypt|Sign|Integrity)|'
    r'(?:Check|Verify|Validate|Hash|Encrypt|Sign|Integrity).*PlayerPrefs|'
    r'SaveCheck|SaveVerify|SaveHash|SaveIntegrity|DataHash|DataSign',
    re.IGNORECASE
)
for i, line in enumerate(lines, 1):
    if prefs_check_pattern.search(line):
        print(f"  L{i}: {line.rstrip()[:200]}")

# ====== 5. nms相关（native保护） ======
print("\n" + "=" * 70)
print("5. NMS / native保护库")
print("=" * 70)

nms_pattern = re.compile(r'libnms|nms_|NMS|native.?lib|native.?protect', re.IGNORECASE)
for i, line in enumerate(lines, 1):
    if nms_pattern.search(line):
        # 排除太常见的
        if 'nms' in line.lower() or 'native-lib' in line.lower() or 'NMS' in line:
            print(f"  L{i}: {line.rstrip()[:200]}")

# ====== 6. IFix 热修复校验 ======
print("\n" + "=" * 70)
print("6. IFix热修复 校验/补丁")
print("=" * 70)

ifix_pattern = re.compile(r'IsPatched|GetPatch|PatchFrom|WrappersManager|IFixManager', re.IGNORECASE)
for i, line in enumerate(lines, 1):
    if ifix_pattern.search(line):
        print(f"  L{i}: {line.rstrip()[:200]}")

# ====== 7. 搜索含有 "receipt" "purchase" "server" 验证 ======
print("\n" + "=" * 70)
print("7. 购买/服务器端验证")
print("=" * 70)

purchase_pattern = re.compile(
    r'receipt.?verif|purchase.?verif|server.?verif|server.?valid|'
    r'validatePurchase|verifyReceipt|verifyPurchase',
    re.IGNORECASE
)
for i, line in enumerate(lines, 1):
    if purchase_pattern.search(line):
        print(f"  L{i}: {line.rstrip()[:200]}")

# ====== 8. 搜索 abo.bytes / cmjax / rnjax 配置文件加载 ======
print("\n" + "=" * 70)
print("8. 加密配置文件(abo/cmjax/rnjax)")
print("=" * 70)

config_pattern = re.compile(r'abo\.bytes|cmjax|rnjax|abo_|game_config', re.IGNORECASE)
for i, line in enumerate(lines, 1):
    if config_pattern.search(line):
        print(f"  L{i}: {line.rstrip()[:200]}")

print("\n\n===== 搜索完成 =====")
