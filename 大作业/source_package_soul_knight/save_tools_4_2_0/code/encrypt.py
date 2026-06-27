import os
import json

# ----------------- 核心算法区 ----------------- #
def get_t(i: int) -> int:
    """计算随着位置变化的干扰项"""
    return ((i % 15) * (i % 5)) % 92

def crypt_data(data: bytes, password: str) -> bytes:
    """加密和解密用的是同一个函数 (XOR 的对称性)"""
    result = bytearray(data)
    pwd_len = len(password)
    
    for i in range(len(result)):
        pc = ord(password[i % pwd_len])
        result[i] = result[i] ^ pc ^ get_t(i)
        
    return bytes(result)

# ----------------- 执行流程 ----------------- #
if __name__ == "__main__":
    # 配置路径与密钥
    input_json_file = r"E:\Crack\soul-knight-4-2-0\crack\code\decrypted_game.json"
    output_data_file = r"E:\Crack\soul-knight-4-2-0\crack\code\modded_game.data"
    
    # ⚠️ 请将这里的字符串替换为您在 cracked_keys.txt 中得到的真实密钥
    key = "smg"  
    
    if key == "YOUR_CRACKED_KEY_HERE":
        print("[-] 错误：请先在代码中填入你爆破出来的正确密钥 (key)！")
        exit(1)

    if not os.path.exists(input_json_file):
        print(f"[-] 找不到文件 {input_json_file}")
        exit(1)
        
    print(f"[*] 正在读取修改后的 JSON: {input_json_file}")
    with open(input_json_file, "r", encoding="utf-8") as f:
        # 先读取并解析 JSON，为了抹除换行和缩紧，让它变回原本紧凑的一行
        parsed_json = json.load(f)
        
    # 游戏往往只认最紧凑的 JSON 格式（无空格无换行）
    compact_json_str = json.dumps(parsed_json, separators=(',', ':'), ensure_ascii=False)
    plain_bytes = compact_json_str.encode('utf-8')
    
    print(f"[*] 开始加密，密钥: '{key}'，数据大小: {len(plain_bytes)} 字节...")
    encrypted_bytes = crypt_data(plain_bytes, key)
    
    with open(output_data_file, "wb") as f:
        f.write(encrypted_bytes)
        
    print(f"✅ 加密成功！")
    print(f"[+] 重新打包的存档已保存为: {output_data_file}")
    print(f"[*] 您现在可以将其重命名为原名并放回游戏中测试了。")
