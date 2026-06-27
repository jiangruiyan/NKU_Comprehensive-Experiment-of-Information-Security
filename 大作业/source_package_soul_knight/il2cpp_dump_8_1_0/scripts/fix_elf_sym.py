#!/usr/bin/env python3
"""
Fix bad st_name offsets in .dynsym that cause Cpp2IL to crash with
EndOfStreamException when reading symbol names.

SoFixer sometimes re-writes st_name (treating it as a VA pointer) instead
of leaving it as a plain .dynstr index, producing values that point beyond
the .dynstr section or beyond the file altogether.

Usage:
  python fix_elf_sym.py
"""
import struct
from pathlib import Path

SO_IN  = Path(r'E:\Crack\soul-knight-8-1-0\crack\runtime_artifacts\20260422-193513\libil2cpp\libil2cpp_sofixer.so')
SO_OUT = Path(r'E:\Crack\soul-knight-8-1-0\crack\runtime_artifacts\20260422-193513\libil2cpp\libil2cpp_sofixer_fixsym.so')

print(f'Reading {SO_IN} ({SO_IN.stat().st_size / 1024 / 1024:.1f} MB)...')
data = bytearray(SO_IN.read_bytes())
file_size = len(data)

# ── ELF64 header ─────────────────────────────────────────────────────────────
magic = data[0:4]
assert magic == b'\x7fELF', f'Not an ELF file: {magic}'
e_shoff     = struct.unpack_from('<Q', data, 40)[0]
e_shentsize = struct.unpack_from('<H', data, 58)[0]
e_shnum     = struct.unpack_from('<H', data, 60)[0]
e_shstrndx  = struct.unpack_from('<H', data, 62)[0]
print(f'ELF header: e_shoff={hex(e_shoff)}, e_shentsize={e_shentsize}, '
      f'e_shnum={e_shnum}, e_shstrndx={e_shstrndx}')

# ── Section name string table (.shstrtab) ─────────────────────────────────────
shstr_entry = e_shoff + e_shstrndx * e_shentsize
shstr_file_off = struct.unpack_from('<Q', data, shstr_entry + 24)[0]   # sh_offset
shstr_size     = struct.unpack_from('<Q', data, shstr_entry + 32)[0]   # sh_size

def section_name(idx: int) -> str:
    sh_entry = e_shoff + idx * e_shentsize
    name_idx = struct.unpack_from('<I', data, sh_entry)[0]
    start = shstr_file_off + name_idx
    end   = data.index(0, start)
    return data[start:end].decode('ascii', errors='replace')

# ── Find .dynstr and .dynsym sections ─────────────────────────────────────────
dynstr_off = dynstr_size = None
dynsym_off = dynsym_size = dynsym_entsize = None

for i in range(e_shnum):
    name = section_name(i)
    sh_entry  = e_shoff + i * e_shentsize
    sh_offset = struct.unpack_from('<Q', data, sh_entry + 24)[0]
    sh_size   = struct.unpack_from('<Q', data, sh_entry + 32)[0]
    sh_entsz  = struct.unpack_from('<Q', data, sh_entry + 56)[0]
    if name == '.dynstr':
        dynstr_off  = sh_offset
        dynstr_size = sh_size
        print(f'.dynstr : file_offset={hex(dynstr_off)}, size={hex(dynstr_size)} ({dynstr_size} bytes)')
    elif name == '.dynsym':
        dynsym_off     = sh_offset
        dynsym_size    = sh_size
        dynsym_entsize = sh_entsz if sh_entsz > 0 else 24  # Elf64_Sym is 24 bytes
        print(f'.dynsym : file_offset={hex(dynsym_off)}, size={hex(dynsym_size)}, '
              f'entsize={dynsym_entsize}')

if dynstr_off is None or dynsym_off is None:
    print('ERROR: could not locate .dynstr or .dynsym via section headers.')
    print('Trying DT_SYMTAB / DT_STRTAB via .dynamic segment...')
    # Fallback: scan for a PT_DYNAMIC segment
    e_phoff     = struct.unpack_from('<Q', data, 32)[0]
    e_phentsize = struct.unpack_from('<H', data, 54)[0]
    e_phnum     = struct.unpack_from('<H', data, 56)[0]
    PT_DYNAMIC  = 2
    dyn_off = dyn_size = None
    for i in range(e_phnum):
        ph_entry = e_phoff + i * e_phentsize
        p_type   = struct.unpack_from('<I', data, ph_entry)[0]
        if p_type == PT_DYNAMIC:
            dyn_off  = struct.unpack_from('<Q', data, ph_entry + 8)[0]   # p_offset
            dyn_size = struct.unpack_from('<Q', data, ph_entry + 32)[0]  # p_filesz
            break
    if dyn_off is None:
        print('ERROR: no PT_DYNAMIC segment found. Cannot fix.')
        raise SystemExit(1)
    # Parse .dynamic entries (Elf64_Dyn: d_tag 8B + d_val 8B = 16 bytes)
    DT_SYMTAB = 6; DT_STRTAB = 5; DT_STRSZ = 10
    dt_symtab = dt_strtab = dt_strsz = None
    pos = dyn_off
    while pos + 16 <= dyn_off + dyn_size:
        d_tag, d_val = struct.unpack_from('<qQ', data, pos)
        pos += 16
        if d_tag == DT_SYMTAB: dt_symtab = d_val
        elif d_tag == DT_STRTAB: dt_strtab = d_val
        elif d_tag == DT_STRSZ:  dt_strsz  = d_val
        elif d_tag == 0: break  # DT_NULL
    print(f'  DT_SYMTAB={hex(dt_symtab)}, DT_STRTAB={hex(dt_strtab)}, DT_STRSZ={hex(dt_strsz)}')
    dynsym_off     = dt_symtab
    dynsym_entsize = 24
    dynstr_off     = dt_strtab
    dynstr_size    = dt_strsz
    # We don't know dynsym_size from DT alone; we'll scan until st_name makes no sense
    dynsym_size    = 3560 * 24  # use count found by Cpp2IL

# ── Scan and fix .dynsym ───────────────────────────────────────────────────────
sym_count = dynsym_size // dynsym_entsize
print(f'\nScanning {sym_count} symbols in .dynsym...')

fixed = 0
bad_names = []
for i in range(sym_count):
    sym_file_off = dynsym_off + i * dynsym_entsize
    if sym_file_off + dynsym_entsize > file_size:
        print(f'  Symbol {i}: out of file range at {hex(sym_file_off)}, stopping')
        break
    st_name = struct.unpack_from('<I', data, sym_file_off)[0]
    # Valid st_name must be < dynstr_size AND dynstr_off + st_name < file_size
    bad = (st_name >= dynstr_size) or (dynstr_off + st_name >= file_size)
    if bad:
        bad_names.append((i, st_name))
        struct.pack_into('<I', data, sym_file_off, 0)
        fixed += 1

print(f'Fixed {fixed} / {sym_count} symbols with invalid st_name values.')
if bad_names[:10]:
    print('First bad entries (sym_idx, original_st_name):')
    for idx, val in bad_names[:10]:
        print(f'  [{idx}] st_name={hex(val)} (dynstr_size={hex(dynstr_size)})')

# ── Write output ───────────────────────────────────────────────────────────────
SO_OUT.write_bytes(data)
print(f'\nFixed SO written to: {SO_OUT}')
print(f'File size: {len(data) / 1024 / 1024:.1f} MB (unchanged)')
