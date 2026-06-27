"""搜索 dump.cs 中的完整性校验/反篡改相关代码"""
import re
import sys

dump_path = r"e:\Crack\soul-knight-4-2-0\crack\dump.cs"

# 定义搜索模式分组
patterns = {
    "哈希/摘要算法": re.compile(r'MD5|SHA1|SHA256|SHA512|HashAlgorithm|ComputeHash|HMAC|digest', re.IGNORECASE),
    "校验和/CRC": re.compile(r'checksum|CRC32|CRC16|Adler', re.IGNORECASE),
    "完整性/篡改检测": re.compile(r'integrity|tamper|anti.?cheat|anti.?hack|anti.?tamper', re.IGNORECASE),
    "签名验证": re.compile(r'SignatureVerif|APKVerif|VerifySign|PackageInfo|certificates|getPackageInfo', re.IGNORECASE),
    "数据验证": re.compile(r'ValidateData|ValidateSave|VerifyData|DataIntegrity|SaveIntegrity', re.IGNORECASE),
    "Verify/Validate方法": re.compile(r'(?:void|bool|int|string)\s+(?:Verify|Validate)\w*\s*\(', re.IGNORECASE),
    "Check方法(非UI)": re.compile(r'(?:void|bool|int)\s+Check(?!Box|Mark|Point|ed|Out|In|er)\w*\s*\(', re.IGNORECASE),
    "安全/保护SDK": re.compile(r'AntiCheat|GameGuard|HackShield|SecureValue|ObscuredInt|ObscuredFloat|ObscuredString|ACTk|CodeStage', re.IGNORECASE),
    "root/越狱检测": re.compile(r'root.?detect|jailbreak|isRooted|su\s+binary|Superuser', re.IGNORECASE),
    "调试检测": re.compile(r'isDebug|debugger|anti.?debug|ptrace|TracerPid', re.IGNORECASE),
    "模拟器检测": re.compile(r'emulator|isEmulator|BlueStacks|NoxPlayer|LDPlayer|generic.*goldfish', re.IGNORECASE),
    "PlayerPrefs保护": re.compile(r'SecurePlayerPrefs|EncryptedPrefs|PrefsEncrypt|PlayerPrefsEncrypt', re.IGNORECASE),
    "内存保护/加密值": re.compile(r'SecureInt|SecureFloat|SecureString|ObscuredValue|ProtectedValue|EncryptedValue', re.IGNORECASE),
    "网络校验": re.compile(r'ServerVerif|ServerValidat|server.?check|receipt.?verif|purchase.?verif', re.IGNORECASE),
    "nms保护(native)": re.compile(r'libnms|nms_init|nms_protect|NMSProtect', re.IGNORECASE),
    "IFix热修复相关校验": re.compile(r'IsPatched|GetPatch|PatchFrom|patch.*verify', re.IGNORECASE),
}

print(f"正在读取 dump.cs ...")
with open(dump_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f"dump.cs 共 {len(lines)} 行\n")

total_hits = 0
for category, pattern in patterns.items():
    hits = []
    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            hits.append((i, line.rstrip()))
    if hits:
        total_hits += len(hits)
        print(f"=== {category} ({len(hits)} 处匹配) ===")
        for lineno, text in hits[:30]:  # 每类最多显示30条
            print(f"  L{lineno}: {text[:200]}")
        if len(hits) > 30:
            print(f"  ... 还有 {len(hits)-30} 处匹配")
        print()

if total_hits == 0:
    print("*** 未找到任何完整性校验/反篡改相关代码 ***")
else:
    print(f"\n总计找到 {total_hits} 处匹配")
