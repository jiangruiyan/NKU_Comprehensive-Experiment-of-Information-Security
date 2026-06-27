"""分析 libil2cpp.so 函数入口字节，判断 ARM/Thumb-2 指令模式"""
import struct

so_path = r'e:\Crack\soul-knight-4-2-0\crack\soul-knight-4-2-0\lib\armeabi-v7a\libil2cpp.so'

rvas = {
    'C19_SetUpChar':       0x2583758,
    'C19_RoleSkill':       0x2583BE0,
    'Stele_Start':         0x12B5DB0,
    'Stele_GetHurt':       0x12B6F74,
    'Stele_AtkWithTarget': 0x12B7C70,
    'ElemAtk_Start':       0xEAA708,
    'ElemAtk_OnHitEnemy':  0xEAAD6C,
    'SteleManager_Add':    0xEAB8AC,
}

with open(so_path, 'rb') as f:
    # Check ELF header
    f.seek(0)
    elf_magic = f.read(4)
    print(f"ELF magic: {elf_magic}")
    f.seek(0x24)  # e_flags
    e_flags = struct.unpack('<I', f.read(4))[0]
    print(f"e_flags: 0x{e_flags:08X}")
    # EF_ARM_ABI_VER5 = 0x05000000
    # EF_ARM_BE8 = 0x00800000
    print(f"  ABI version: {(e_flags >> 24) & 0xFF}")
    print()
    
    for name, rva in rvas.items():
        f.seek(rva)
        data = f.read(20)
        hex_bytes = ' '.join(f'{b:02X}' for b in data)
        
        # Detect mode
        hw = struct.unpack_from('<H', data, 0)[0]
        w = struct.unpack_from('<I', data, 0)[0]
        
        # Thumb-2 32-bit instructions: bits[15:11] >= 0x1D (29)
        prefix = hw >> 11
        is_thumb32_start = prefix >= 29  # 11101, 11110, 11111
        is_thumb16_push = (hw & 0xFF00) == 0xB500
        
        # ARM mode: condition field in bits[31:28], usually 0xE
        is_arm = (w >> 28) == 0xE
        
        if is_thumb32_start or is_thumb16_push:
            mode = 'Thumb-2'
        elif is_arm:
            mode = 'ARM'
        else:
            mode = 'UNKNOWN'
        
        print(f'{name} @ 0x{rva:08X}:')
        print(f'  Bytes: {hex_bytes}')
        print(f'  Mode:  {mode}')
        
        # Decode instructions
        if mode == 'Thumb-2':
            offset = 0
            while offset < 16:
                ihw = struct.unpack_from('<H', data, offset)[0]
                p = ihw >> 11
                if p >= 29:  # 32-bit Thumb-2
                    ihw2 = struct.unpack_from('<H', data, offset + 2)[0]
                    print(f'  +{offset:2d}: T32  {ihw:04X} {ihw2:04X}', end='')
                    # Decode common instructions
                    if ihw == 0xE92D:
                        regs = ihw2
                        reg_names = []
                        for i in range(16):
                            if regs & (1 << i):
                                reg_names.append(f'r{i}' if i < 13 else ['sp','lr','pc'][i-13])
                        print(f'  PUSH.W {{{", ".join(reg_names)}}}', end='')
                    elif (ihw & 0xFBF0) == 0xF1A0 and (ihw & 0xF) == 0xD:
                        imm8 = ihw2 & 0xFF
                        imm3 = (ihw2 >> 12) & 0x7
                        i = (ihw >> 10) & 0x1
                        imm = (i << 11) | (imm3 << 8) | imm8
                        print(f'  SUB SP, SP, #{imm}', end='')
                    print()
                    offset += 4
                else:
                    print(f'  +{offset:2d}: T16  {ihw:04X}', end='')
                    if (ihw & 0xFF00) == 0xB500:
                        regs = ihw & 0xFF
                        reg_names = []
                        for i in range(8):
                            if regs & (1 << i):
                                reg_names.append(f'r{i}')
                        if ihw & 0x0100:
                            reg_names.append('lr')
                        print(f'  PUSH {{{", ".join(reg_names)}}}', end='')
                    elif ihw == 0x4770:
                        print(f'  BX LR', end='')
                    elif (ihw & 0xFF00) == 0xBD00:
                        regs = ihw & 0xFF
                        reg_names = []
                        for i in range(8):
                            if regs & (1 << i):
                                reg_names.append(f'r{i}')
                        if ihw & 0x0100:
                            reg_names.append('pc')
                        print(f'  POP {{{", ".join(reg_names)}}}', end='')
                    elif (ihw & 0xF800) == 0x4800:
                        print(f'  LDR r{(ihw>>8)&7}, [PC, #...]', end='')
                    elif (ihw & 0xFF00) == 0xB000:
                        if ihw & 0x80:
                            print(f'  SUB SP, #{(ihw&0x7F)*4}', end='')
                        else:
                            print(f'  ADD SP, #{(ihw&0x7F)*4}', end='')
                    print()
                    offset += 2
        elif mode == 'ARM':
            for i in range(0, 16, 4):
                instr = struct.unpack_from('<I', data, i)[0]
                print(f'  +{i:2d}: ARM  {instr:08X}', end='')
                if (instr & 0x0FFF0000) == 0x092D0000 or (instr & 0xFFFF0000) == 0xE92D0000:
                    regs = instr & 0xFFFF
                    reg_names = []
                    for j in range(16):
                        if regs & (1 << j):
                            reg_names.append(f'r{j}' if j < 13 else ['sp','lr','pc'][j-13])
                    print(f'  STMDB SP!, {{{", ".join(reg_names)}}}', end='')
                print()
        print()

# Also get file size
import os
size = os.path.getsize(so_path)
print(f"libil2cpp.so size: {size:,} bytes ({size/1024/1024:.1f} MB)")
