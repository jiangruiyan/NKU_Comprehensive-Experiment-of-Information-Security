"""
批量重新加密脚本
从 decryptFiles/ 读取已修改的 JSON 文件，
根据 cracked_keys.txt 中记录的加密方式重新加密，
输出到 encryptedFiles/ 目录，保持与原始加密文件相同的格式。
"""
import os
import sys
import json

# 复用 batch_crack 中的加解密函数
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from batch_crack import crypt_data, des_encrypt

# ============================================================
# 路径配置
# ============================================================
WORKSPACE    = r"E:\Crack\soul-knight-4-2-0\crack"
DECRYPT_DIR  = os.path.join(WORKSPACE, "datafile", "decryptFiles")   # 已解密(可能已修改)的 JSON 文件
ENCRYPT_DIR  = os.path.join(WORKSPACE, "datafile", "encryptedFiles") # 重新加密后的输出目录
KEY_LOG_FILE = os.path.join(WORKSPACE, "datafile", "cracked_keys.txt")


def load_cracked_keys(key_log_file: str) -> dict:
    """加载 cracked_keys.txt → { 相对路径: 加密方式 }"""
    cache = {}
    if not os.path.exists(key_log_file):
        return cache
    with open(key_log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ": " in line:
                path, key = line.split(": ", 1)
                cache[path] = key
    return cache


def encrypt_file(json_str: str, method: str) -> bytes:
    """
    根据加密方式将 JSON 字符串加密为原始字节。

    method 取值:
      - "plaintext"       → 不加密，直接输出 UTF-8 字节
      - "DES(key=iambo)"  → DES-CBC 加密 + Base64 编码，输出 ASCII 字节
      - 其他字符串 (如 "smg") → 视为 XOR 密钥，输出加密后的原始字节
    """
    if method == "plaintext":
        return json_str.encode("utf-8")

    if method.startswith("DES("):
        # 提取密钥名 (目前只有 iambo)
        b64_str = des_encrypt(json_str)
        return b64_str.encode("ascii")

    # XOR 加密 (crypt_data 是对称的，加密 = 解密)
    plaintext_bytes = json_str.encode("utf-8")
    return crypt_data(plaintext_bytes, method)


if __name__ == "__main__":
    if not os.path.exists(DECRYPT_DIR):
        print(f"[-] 解密文件目录不存在: {DECRYPT_DIR}")
        sys.exit(1)

    if not os.path.exists(KEY_LOG_FILE):
        print(f"[-] 密钥记录文件不存在: {KEY_LOG_FILE}")
        sys.exit(1)

    cracked_keys = load_cracked_keys(KEY_LOG_FILE)
    if not cracked_keys:
        print("[-] cracked_keys.txt 为空，无法确定加密方式")
        sys.exit(1)

    print(f"[*] 已加载 {len(cracked_keys)} 条加密记录")
    print(f"[*] 输入目录: {DECRYPT_DIR}")
    print(f"[*] 输出目录: {ENCRYPT_DIR}")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for root, dirs, files in os.walk(DECRYPT_DIR):
        rel_dir = os.path.relpath(root, DECRYPT_DIR)
        target_dir = os.path.join(ENCRYPT_DIR, rel_dir) if rel_dir != "." else ENCRYPT_DIR

        for file in files:
            json_path = os.path.join(root, file)

            # 解密时在原文件名后追加了 .json, 这里还原
            if file.endswith(".json"):
                original_name = file[:-5]          # 去掉 .json → 原文件名
            else:
                original_name = file               # 非 .json 文件原样保留名字

            # 构建与 cracked_keys.txt 中一致的相对路径
            rel_file = os.path.join(rel_dir, original_name) if rel_dir != "." else original_name

            # 查找加密方式
            method = cracked_keys.get(rel_file)
            if method is None:
                print(f"[~] 跳过 (无加密记录): {rel_file}")
                skip_count += 1
                continue

            # 读取并解析 JSON
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"[-] 读取失败 ({type(e).__name__}): {json_path}")
                fail_count += 1
                continue

            # 序列化为紧凑 JSON (与游戏原始格式一致，无多余空白)
            compact_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

            # 加密
            try:
                encrypted_bytes = encrypt_file(compact_json, method)
            except Exception as e:
                print(f"[-] 加密失败 ({type(e).__name__}: {e}): {rel_file}")
                fail_count += 1
                continue

            # 写入输出目录，文件名恢复为原始名称
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            out_path = os.path.join(target_dir, original_name)
            with open(out_path, "wb") as f:
                f.write(encrypted_bytes)

            print(f"[+] 成功: {rel_file} (方式: {method}, {len(encrypted_bytes)} bytes)")
            success_count += 1

    print("=" * 50)
    print(f"批量加密完成！成功 {success_count} 个，跳过 {skip_count} 个，失败 {fail_count} 个。")
    print(f"输出目录: {ENCRYPT_DIR}")
