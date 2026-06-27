#!/usr/bin/env python3
import argparse
import copy
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_DIR = ROOT / "lsposed_native"
APP_DIR = PROJECT_DIR / "app"
APK_PATH = APP_DIR / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
DUMP_DIR = "/sdcard/Android/data/com.ChillyRoom.DungeonShooter/files/il2cpp_dump"
RUNTIME_ROOT = ROOT / "runtime_artifacts"
FIXED_DIR = ROOT / "fixed"
PACKAGE = "com.example.hookknight"
TARGET_PACKAGE = "com.ChillyRoom.DungeonShooter"
TARGET_ACTIVITY = "com.chillyroomsdk.sdkbridge.BasePlayerActivity"
IL2CPP_DUMPER_HINTS = [
    Path(r"E:\Crack\Il2CppDumper-win-v6.7.46\Il2CppDumper.exe"),
    Path(r"E:\Crack\Il2CppDumper-net6-win-v6.7.46\Il2CppDumper.exe"),
]
SOFIXER_HINTS = [
    ROOT / "SoFixer.exe",
    Path(r"E:\Crack\SoFixer.exe"),
]
METADATA_HINTS = [
    ROOT / "dumped_metadata.dat",
    FIXED_DIR / "global-metadata.dat",
    FIXED_DIR / "global-metadata-v31.dat",
    FIXED_DIR / "global-metadata-v29.dat",
    FIXED_DIR / "global-metadata-v28.dat",
    FIXED_DIR / "global-metadata-v27.dat",
    FIXED_DIR / "global-metadata-v24.dat",
]


def run(cmd, cwd=None, check=True, capture=True):
    print("\n$", " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
    )
    if capture:
        if completed.stdout:
            print(completed.stdout.strip())
        if completed.stderr:
            print(completed.stderr.strip())
    if check and completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}")
    return completed


def find_java_home():
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / "java.exe").exists():
        return java_home

    candidates = [
        Path("C:/Program Files/Android/Android Studio/jbr"),
        Path("C:/Program Files/Android/Android Studio/jre"),
    ]
    for c in candidates:
        if (c / "bin" / "java.exe").exists():
            return str(c)
    return None


def parse_distribution_url(wrapper_props: Path):
    text = wrapper_props.read_text(encoding="utf-8")
    m = re.search(r"distributionUrl=(.+)", text)
    if not m:
        return None
    return m.group(1).replace("\\:", ":")


def parse_distribution_name(wrapper_props: Path):
    url = parse_distribution_url(wrapper_props)
    if not url:
        return None
    if url.startswith("https\\://"):
        url = url.replace("https\\://", "https://")
    return url.split("/")[-1].replace("-bin.zip", "").replace("-all.zip", "")


def find_existing_gradle_bat(project_dir: Path):
    wrapper_props = project_dir / "gradle" / "wrapper" / "gradle-wrapper.properties"
    preferred = parse_distribution_name(wrapper_props) if wrapper_props.exists() else None

    home = Path.home()
    candidates = []
    wrapper_dists = home / ".gradle" / "wrapper" / "dists"
    if wrapper_dists.exists():
        for gradle_bat in wrapper_dists.rglob("gradle.bat"):
            p = str(gradle_bat).lower().replace("\\", "/")
            if "/bin/gradle.bat" not in p:
                continue
            candidates.append(gradle_bat)

    if not candidates:
        return None

    # 优先匹配 wrapper 指定版本（例如 gradle-8.4）
    if preferred:
        preferred_lower = preferred.lower()
        for c in candidates:
            if preferred_lower in str(c).lower().replace("\\", "/"):
                return c

    # 兜底选最后修改时间最新的
    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidates[0]


def is_valid_zip(zip_path: Path):
    if not zip_path.exists() or zip_path.stat().st_size < 1024:
        return False
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            return bad is None
    except Exception:
        return False


def download_file(url: str, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:
        expected = resp.headers.get("Content-Length")
        expected_size = int(expected) if expected and expected.isdigit() else None
        copied = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            copied += len(chunk)

    if expected_size is not None and copied != expected_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded size mismatch: expected={expected_size}, got={copied}")

    tmp.replace(target)


def safe_unlink(path: Path):
    try:
        path.unlink(missing_ok=True)
        return True
    except PermissionError:
        return False


def ensure_gradle_distribution(project_dir: Path):
    wrapper_props = project_dir / "gradle" / "wrapper" / "gradle-wrapper.properties"
    if not wrapper_props.exists():
        return None

    dist_url = parse_distribution_url(wrapper_props)
    if not dist_url:
        return None
    if dist_url.startswith("https\\://"):
        dist_url = dist_url.replace("https\\://", "https://")

    dist_name = dist_url.split("/")[-1]
    gradle_name = dist_name.replace("-bin.zip", "").replace("-all.zip", "")
    cache_dir = ROOT / ".cache" / "gradle"
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / dist_name
    extract_dir = cache_dir / gradle_name
    gradle_bat = extract_dir / "bin" / "gradle.bat"

    if not gradle_bat.exists():
        if not is_valid_zip(zip_path):
            if not safe_unlink(zip_path):
                zip_path = cache_dir / f"{gradle_name}-{int(time.time())}.zip"
            last_error = None
            for i in range(1, 4):
                try:
                    print(f"Downloading Gradle ({i}/3): {dist_url}")
                    download_file(dist_url, zip_path)
                    if is_valid_zip(zip_path):
                        last_error = None
                        break
                    last_error = RuntimeError("Downloaded file is not a valid zip")
                except Exception as e:
                    last_error = e
                    safe_unlink(zip_path)
            if last_error is not None:
                raise RuntimeError(f"Failed to download valid Gradle zip: {last_error}")

        print(f"Extracting Gradle to: {extract_dir}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            temp_extract = cache_dir / f"tmp_{gradle_name}_{int(time.time())}"
            zf.extractall(temp_extract)
            # Distribution usually has one top-level folder, rename it to stable path.
            children = [p for p in temp_extract.iterdir() if p.is_dir()]
            if len(children) != 1:
                raise RuntimeError("Unexpected Gradle zip layout")
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            children[0].rename(extract_dir)
            shutil.rmtree(temp_extract)

    return gradle_bat


def select_gradle_cmd(project_dir: Path):
    gradlew = project_dir / "gradlew.bat"
    wrapper_jar = project_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"

    if gradlew.exists() and wrapper_jar.exists():
        return [str(gradlew)]

    gradle_in_path = shutil.which("gradle")
    if gradle_in_path:
        return [gradle_in_path]

    existing = find_existing_gradle_bat(project_dir)
    if existing and existing.exists():
        return [str(existing)]

    gradle_bat = ensure_gradle_distribution(project_dir)
    if gradle_bat and gradle_bat.exists():
        return [str(gradle_bat)]

    raise RuntimeError("No usable Gradle found (wrapper jar missing and gradle not installed)")


def build_apk(project_dir: Path):
    env = os.environ.copy()
    java_home = find_java_home()
    if java_home:
        env["JAVA_HOME"] = java_home
        env["PATH"] = str(Path(java_home) / "bin") + os.pathsep + env.get("PATH", "")

    gradle_cmd = select_gradle_cmd(project_dir)
    cmd = gradle_cmd + [":app:assembleDebug", "--no-daemon"]
    print(f"Using Gradle command: {' '.join(gradle_cmd)}")

    proc = subprocess.run(
        cmd,
        cwd=str(project_dir),
        text=True,
        capture_output=True,
        env=env,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError("Gradle build failed")


def adb(*args, check=True, capture=True):
    return run(["adb", *args], check=check, capture=capture)


def adb_su(command, check=True, capture=True):
    # Pass the whole "su -c CMD" as ONE string so adb-shell does not re-tokenise it.
    # shlex.quote wraps CMD in single quotes, which keeps multi-word commands intact.
    su_cmd = f"su -c {shlex.quote(command)}"
    return run(["adb", "shell", su_cmd], check=check, capture=capture)


def adb_exec_out(command, output_path: Path):
    su_cmd = f"su -c {shlex.quote(command)}"
    print(f"\n$ adb exec-out {su_cmd}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as out:
        completed = subprocess.run(["adb", "exec-out", su_cmd], stdout=out, stderr=subprocess.PIPE)
    if completed.stderr:
        try:
            print(completed.stderr.decode("utf-8", errors="replace").strip())
        except Exception:
            pass
    if completed.returncode != 0:
        raise RuntimeError(f"adb exec-out failed ({completed.returncode}): {command}")


def ensure_device():
    adb("start-server")
    adb("wait-for-device")
    devices = adb("devices").stdout or ""
    online = [line for line in devices.splitlines() if "\tdevice" in line and not line.startswith("List")]
    if not online:
        raise RuntimeError("No online adb device")


def get_target_pid(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        proc = adb_su(f"pidof {TARGET_PACKAGE}", check=False)
        pid = (proc.stdout or "").strip()
        if pid:
            first = pid.split()[0].strip()
            if first.isdigit():
                return int(first)

        proc = adb_su(f"ps -A | grep {TARGET_PACKAGE}", check=False)
        for line in (proc.stdout or "").splitlines():
            if TARGET_PACKAGE in line and ":" not in line:
                parts = line.split()
                for token in parts:
                    if token.isdigit():
                        return int(token)
        time.sleep(1)
    raise RuntimeError("Unable to find target game PID")


def parse_maps(text: str):
    entries = []
    for line in text.splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) < 5:
            continue
        addr, perms, offset_hex, dev, inode = parts[:5]
        path = parts[5] if len(parts) > 5 else ""
        start_hex, end_hex = addr.split("-")
        entries.append(
            {
                "start": int(start_hex, 16),
                "end": int(end_hex, 16),
                "perms": perms,
                "offset": int(offset_hex, 16),
                "path": path.strip(),
                "line": line,
            }
        )
    return entries


def get_maps(pid: int):
    proc = adb_su(f"cat /proc/{pid}/maps")
    return parse_maps(proc.stdout or "")


def find_real_libil2cpp_cluster(entries):
    lib_entries = [e for e in entries if "libil2cpp.so" in e["path"]]
    if not lib_entries:
        raise RuntimeError("No libil2cpp.so mappings found")

    rx = next((e for e in lib_entries if e["perms"].startswith("r-x")), None)
    if not rx:
        raise RuntimeError("No executable libil2cpp mapping found")

    # PGL Armor maps a large r--p header segment (up to 256 MB) before the r-xp
    # code segment, so increase the search window accordingly.
    base = None
    for e in reversed(lib_entries):
        if e["end"] <= rx["start"] and e["offset"] == 0 and e["perms"].startswith("r--"):
            if rx["start"] - e["start"] <= 0x10000000:  # 256 MB
                base = e["start"]
                break
    if base is None:
        base = min(e["start"] for e in lib_entries)

    cluster = []
    prev_end = None
    for e in sorted(lib_entries, key=lambda item: item["start"]):
        if e["start"] < base:
            continue
        # Tolerate page-alignment gaps (typically 0x3000) between segments;
        # use a generous but bounded limit to avoid crossing unrelated mappings.
        if prev_end is not None and e["start"] - prev_end > 0x10000:
            break
        cluster.append(e)
        prev_end = e["end"]

    if not cluster:
        raise RuntimeError("Unable to resolve real libil2cpp cluster")
    return cluster


def wait_for_rxp_mapping(pid: int, timeout: int = 120, poll_interval: int = 3) -> bool:
    """Poll /proc/PID/maps until libil2cpp.so has an r-xp segment.

    PGL Armor first maps the whole SO as a single r--p file segment, then
    decrypts the code and re-maps it as r-xp + rw-p segments.  We must wait
    for this transition before dumping so that the CodeRegistration struct is
    populated (non-zero) in the rw-p segment.

    Returns True when the r-xp mapping is detected, False on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            entries = get_maps(pid)
        except Exception as exc:
            print(f"[wait_for_rxp] maps read error: {exc}")
            time.sleep(poll_interval)
            continue
        rxp = [e for e in entries if "libil2cpp.so" in e["path"] and e["perms"].startswith("r-x")]
        if rxp:
            print(f"[wait_for_rxp] r-xp libil2cpp mapping detected at {hex(rxp[0]['start'])}-{hex(rxp[0]['end'])}")
            return True
        remaining = int(deadline - time.time())
        print(f"[wait_for_rxp] not ready yet, retrying... ({remaining}s left)")
        time.sleep(poll_interval)
    print("[wait_for_rxp] TIMEOUT waiting for r-xp mapping")
    return False


def dump_libil2cpp_cluster(pid: int, cluster, out_dir: Path):
    """Dump all libil2cpp segments via /proc/PID/mem.

    cat /proc/PID/map_files/start-end returns the ENTIRE underlying APK file
    (not just the mapped slice), so using it would produce a 220 MB copy for
    EACH segment and corrupt the combined layout.

    /proc/PID/mem, by contrast, reads exactly the virtual-address range we
    specify (bs=PAGE_SIZE, skip=VA/PAGE_SIZE, count=SIZE/PAGE_SIZE), giving the
    right bytes for every segment including COW-modified rw-p pages.
    """
    PAGE = 4096
    out_dir.mkdir(parents=True, exist_ok=True)
    combined_path = out_dir / "libil2cpp_real.so"
    manifest = {
        "segments": [],
        "base": hex(cluster[0]["start"]),
        "end": hex(cluster[-1]["end"]),
    }
    with open(combined_path, "wb") as combined:
        prev_end = None
        for index, entry in enumerate(cluster):
            seg_name = f"seg_{entry['start']:x}-{entry['end']:x}.bin"
            seg_path = out_dir / seg_name
            start = entry["start"]
            size = entry["end"] - entry["start"]
            skip_blocks = start // PAGE
            count_blocks = size // PAGE
            mem_cmd = (
                f"dd if=/proc/{pid}/mem bs={PAGE} "
                f"skip={skip_blocks} count={count_blocks} "
                f"of=/sdcard/_il2cpp_seg_tmp.bin 2>/dev/null"
            )
            adb_su(mem_cmd)
            adb_exec_out("cat /sdcard/_il2cpp_seg_tmp.bin", seg_path)
            adb_su("rm -f /sdcard/_il2cpp_seg_tmp.bin", check=False)
            if prev_end is not None and entry["start"] > prev_end:
                gap = entry["start"] - prev_end
                combined.write(b"\x00" * gap)
            with open(seg_path, "rb") as seg_file:
                shutil.copyfileobj(seg_file, combined)
            manifest["segments"].append(
                {
                    "index": index,
                    "start": hex(entry["start"]),
                    "end": hex(entry["end"]),
                    "perms": entry["perms"],
                    "offset": hex(entry["offset"]),
                    "path": entry["path"],
                    "file": seg_name,
                    "method": "proc_mem",
                }
            )
            prev_end = entry["end"]
    (out_dir / "libil2cpp_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return combined_path, int(manifest["base"], 16)


def dump_metadata_candidates(pid: int, entries, out_dir: Path, max_candidates=5):
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = []
    for entry in entries:
        path = entry["path"]
        if "/dev/zero" not in path:
            continue
        if not entry["perms"].startswith("rw-p"):
            continue
        size = entry["end"] - entry["start"]
        if size < 0x100000:
            continue
        candidates.append((size, entry))

    candidates.sort(key=lambda item: item[0], reverse=True)
    dumped = []
    for index, (size, entry) in enumerate(candidates[:max_candidates], start=1):
        name = f"metadata_candidate_{index}_{entry['start']:x}-{entry['end']:x}.bin"
        path = out_dir / name
        adb_exec_out(f"cat /proc/{pid}/map_files/{entry['start']:x}-{entry['end']:x}", path)
        dumped.append({
            "file": str(path),
            "start": hex(entry["start"]),
            "end": hex(entry["end"]),
            "size": size,
            "path": entry["path"],
        })

        patched = out_dir / name.replace(".bin", "_v31.dat")
        data = bytearray(path.read_bytes())
        if len(data) >= 8:
            data[0:4] = b"\xaf\x1b\xb1\xfa"
            data[4:8] = (31).to_bytes(4, "little")
            patched.write_bytes(data)
            dumped[-1]["patched_v31"] = str(patched)
    (out_dir / "metadata_candidates.json").write_text(json.dumps(dumped, ensure_ascii=False, indent=2), encoding="utf-8")
    return dumped


def find_il2cpp_dumper():
    for path in IL2CPP_DUMPER_HINTS:
        if path.exists():
            return path
    return None


def list_il2cpp_dumpers():
    return [p for p in IL2CPP_DUMPER_HINTS if p.exists()]


def find_sofixer():
    for p in SOFIXER_HINTS:
        if p.exists():
            return p
    return None


def run_sofixer(sofixer_path: Path, source_so: Path, output_so: Path, mem_base: int, base_so: Path | None = None):
    output_so.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(sofixer_path),
        "-s",
        str(source_so),
        "-o",
        str(output_so),
        "-m",
        hex(mem_base),
    ]
    if base_so and base_so.exists():
        cmd += ["-b", str(base_so)]
    print("\n$", " ".join(cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    success = output_so.exists() and output_so.stat().st_size > 0
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "success": success,
        "output": str(output_so),
    }


def patch_so_add_il2cpp_syms(so_path: Path, output_path: Path, code_reg_file_off: int, meta_reg_file_off: int) -> bool:
    """
    Patch a memory-dump libil2cpp.so to inject il2cpp_codegen_register and
    il2cpp_MetadataRegistration into .dynsym so that Il2CppDumper v6.7.46's
    SymbolSearch() finds them instead of throwing InvalidOperationException.

    st_value is set to the ELF virtual address (computed from PT_LOAD mapping)
    so that Il2CppDumper's MapVATR() correctly resolves to the file offset.
    """
    import struct as _struct

    try:
        data = bytearray(so_path.read_bytes())

        # ── ELF header ──────────────────────────────────────────────────
        e_phoff      = _struct.unpack_from('<Q', data, 32)[0]
        e_phentsize  = _struct.unpack_from('<H', data, 54)[0]
        e_phnum      = _struct.unpack_from('<H', data, 56)[0]
        e_shoff      = _struct.unpack_from('<Q', data, 40)[0]
        e_shentsize  = _struct.unpack_from('<H', data, 58)[0]
        e_shnum      = _struct.unpack_from('<H', data, 60)[0]

        # ── Build file_offset → VA mapping from PT_LOAD segments ────────
        pt_loads = []
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type   = _struct.unpack_from('<I', data, off)[0]
            p_offset = _struct.unpack_from('<Q', data, off + 8)[0]
            p_vaddr  = _struct.unpack_from('<Q', data, off + 16)[0]
            p_filesz = _struct.unpack_from('<Q', data, off + 32)[0]
            if p_type == 1:  # PT_LOAD
                pt_loads.append((p_offset, p_vaddr, p_filesz))

        def file_off_to_va(foff: int) -> int | None:
            for p_off, p_va, p_fsz in pt_loads:
                if p_off <= foff < p_off + p_fsz:
                    return p_va + (foff - p_off)
            return None

        code_va = file_off_to_va(code_reg_file_off)
        meta_va = file_off_to_va(meta_reg_file_off)
        if code_va is None or meta_va is None:
            print(f"[PATCH] Warning: could not map offsets to VA: code={hex(code_reg_file_off)} meta={hex(meta_reg_file_off)}")
            # Fall back to raw file offsets (works when PT_LOAD[0].p_vaddr == 0)
            code_va = code_va or code_reg_file_off
            meta_va = meta_va or meta_reg_file_off

        # ── Parse section headers ────────────────────────────────────────
        sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            if off + e_shentsize > len(data):
                break
            sh_type    = _struct.unpack_from('<I', data, off + 4)[0]
            sh_offset  = _struct.unpack_from('<Q', data, off + 24)[0]
            sh_size    = _struct.unpack_from('<Q', data, off + 32)[0]
            sh_link    = _struct.unpack_from('<I', data, off + 40)[0]
            sh_entsize = _struct.unpack_from('<Q', data, off + 56)[0]
            sections.append({
                'idx': i, 'sh_type': sh_type,
                'sh_offset': sh_offset, 'sh_size': sh_size,
                'sh_link': sh_link, 'sh_entsize': sh_entsize or 24,
                'hdr_off': off,
            })

        dynsym_s = next((s for s in sections if s['sh_type'] == 11), None)
        if not dynsym_s:
            print("[PATCH] No SHT_DYNSYM found; skipping ELF patch.")
            return False

        dynstr_s = sections[dynsym_s['sh_link']]

        # ── Current section contents ────────────────────────────────────
        dynstr_data = bytes(data[dynstr_s['sh_offset']:dynstr_s['sh_offset'] + dynstr_s['sh_size']])
        dynsym_data = bytes(data[dynsym_s['sh_offset']:dynsym_s['sh_offset'] + dynsym_s['sh_size']])

        if b'il2cpp_codegen_register' in dynstr_data:
            print("[PATCH] il2cpp_codegen_register already present; copying as-is.")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(so_path, output_path)
            return True

        # ── Build new dynstr (append two new names) ─────────────────────
        codegen_name_off = len(dynstr_data)
        codegen_name     = b'il2cpp_codegen_register\x00'
        meta_name_off    = codegen_name_off + len(codegen_name)
        meta_name        = b'il2cpp_MetadataRegistration\x00'
        new_dynstr       = dynstr_data + codegen_name + meta_name

        # ── Build two new Elf64_Sym entries (24 bytes each) ──────────────
        # <I:st_name  B:st_info  B:st_other  H:st_shndx  Q:st_value  Q:st_size>
        STB_GLOBAL_FUNC = 0x12   # (STB_GLOBAL << 4) | STT_FUNC
        STB_GLOBAL_OBJ  = 0x11   # (STB_GLOBAL << 4) | STT_OBJECT
        SHN_ABS         = 0xfff1

        codegen_sym = _struct.pack('<IBBHQQ', codegen_name_off, STB_GLOBAL_FUNC, 0, SHN_ABS, code_va, 0)
        meta_sym    = _struct.pack('<IBBHQQ', meta_name_off,    STB_GLOBAL_OBJ,  0, SHN_ABS, meta_va, 0)
        new_dynsym  = dynsym_data + codegen_sym + meta_sym

        # ── Append new sections at end of file ───────────────────────────
        file_end       = len(data)
        new_dynstr_off = file_end
        new_dynsym_off = new_dynstr_off + len(new_dynstr)

        data.extend(new_dynstr)
        data.extend(new_dynsym)

        # ── Update section headers (sh_offset + sh_size) ─────────────────
        def update_shdr(s, offset, size):
            _struct.pack_into('<Q', data, s['hdr_off'] + 24, offset)
            _struct.pack_into('<Q', data, s['hdr_off'] + 32, size)

        update_shdr(dynstr_s, new_dynstr_off, len(new_dynstr))
        update_shdr(dynsym_s, new_dynsym_off, len(new_dynsym))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes(data))
        print(f"[PATCH] ELF patched → {output_path.name}")
        print(f"[PATCH] il2cpp_codegen_register VA = {hex(code_va)}")
        print(f"[PATCH] il2cpp_MetadataRegistration VA = {hex(meta_va)}")
        return True

    except Exception as exc:
        print(f"[PATCH] patch_so_add_il2cpp_syms failed: {exc}")
        return False


def parse_hex_addr(value):
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if s.startswith("0x"):
        s = s[2:]
    if not re.fullmatch(r"[0-9a-f]+", s):
        return None
    try:
        return int(s, 16)
    except Exception:
        return None


def extract_best_address_pair(dumper_runs, base_addr: int):
    for item in dumper_runs:
        code = parse_hex_addr(item.get("code_registration"))
        meta = parse_hex_addr(item.get("metadata_registration"))
        if code is None or meta is None:
            continue
        if code == 0 or meta == 0:
            continue
        return {
            "source": {
                "so": item.get("so"),
                "metadata": item.get("metadata"),
                "config": item.get("config"),
                "output_dir": item.get("output_dir"),
            },
            "base_addr": hex(base_addr),
            "code_registration_raw": hex(code),
            "metadata_registration_raw": hex(meta),
            "code_registration_abs": hex(base_addr + code),
            "metadata_registration_abs": hex(base_addr + meta),
        }
    return None


def extract_best_address_pair_from_report(report_obj):
    try:
        base = parse_hex_addr(report_obj.get("base_addr"))
        if base is None:
            return None
        dumper_runs = report_obj.get("dumper")
        if not isinstance(dumper_runs, list):
            return None
        return extract_best_address_pair(dumper_runs, base)
    except Exception:
        return None


def find_best_pair_from_history(exclude_dir: Path | None = None):
    if not RUNTIME_ROOT.exists():
        return None

    report_files = sorted(
        RUNTIME_ROOT.rglob("dump_route_report.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in report_files:
        if exclude_dir and exclude_dir in path.parents:
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pair = extract_best_address_pair_from_report(obj)
        if pair:
            pair["from_history_report"] = str(path)
            return pair
    return None


def collect_metadata_inputs(runtime_candidates):
    result = []
    seen = set()

    # First priority: runtime patched candidates produced in this run.
    for item in runtime_candidates:
        for key in ("patched_v31", "file"):
            val = item.get(key)
            if not val:
                continue
            p = Path(val)
            if p.exists() and p.stat().st_size > 0:
                norm = str(p.resolve())
                if norm not in seen:
                    seen.add(norm)
                    result.append(p)

    # Fallback: workspace-known metadata files.
    for p in METADATA_HINTS:
        if p.exists() and p.stat().st_size > 0:
            norm = str(p.resolve())
            if norm not in seen:
                seen.add(norm)
                result.append(p)

    return result


def load_json_file(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def apply_dumper_config(dumper_path: Path, overrides: dict):
    config_path = dumper_path.parent / "config.json"
    original = load_json_file(config_path)
    current = copy.deepcopy(original)
    current.update(overrides or {})
    try:
        config_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return config_path, original, None
    except PermissionError as e:
        # Some tool directories are read-only; continue with existing config.
        return None, None, str(e)
    except OSError as e:
        return None, None, str(e)


def restore_dumper_config(config_path: Path, original: dict):
    try:
        config_path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Restoring config is best-effort only.
        pass


def try_il2cpp_dumper(dumper_path: Path, so_path: Path, metadata_path: Path, out_dir: Path, base_addr: int, timeout_sec=120, config_overrides=None, config_name="default", hint_code_reg: int = 0, hint_meta_reg: int = 0):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(dumper_path), str(so_path), str(metadata_path), str(out_dir)]
    print("\n$", " ".join(cmd))
    # Build stdin input sequence:
    # Line 1: base address (hex) for dump-file detection prompt
    # Lines 2-3: hint addresses for ForceDump manual CodeRegistration/MetadataRegistration prompts
    #   (0 = auto if no hint; Il2CppDumper v6.7.46 uses these when Search() + SymbolSearch() both fail)
    # Extra 0s: consume any additional prompts (e.g. version confirmation)
    code_hint_hex = f"{hint_code_reg:x}" if hint_code_reg else "0"
    meta_hint_hex = f"{hint_meta_reg:x}" if hint_meta_reg else "0"
    input_text = f"{base_addr:x}\n{code_hint_hex}\n{meta_hint_hex}\n0\n0\n0\n"
    def parse_addr(text, key):
        m = re.search(rf"{key}\s*:\s*([0-9a-fA-F]+)", text or "")
        return m.group(1) if m else None

    config_path = None
    original_cfg = None
    config_apply_error = None
    try:
        config_path, original_cfg, config_apply_error = apply_dumper_config(dumper_path, config_overrides or {})
        proc = subprocess.run(
            cmd,
            text=True,
            input=input_text,
            capture_output=True,
            cwd=str(dumper_path.parent),
            timeout=timeout_sec,
        )
        print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        success = (out_dir / "dump.cs").exists() or (out_dir / "stringliteral.json").exists()
        code_reg = parse_addr(proc.stdout, "CodeRegistration")
        meta_reg = parse_addr(proc.stdout, "MetadataRegistration")
        return {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "success": success,
            "output_dir": str(out_dir),
            "metadata": str(metadata_path),
            "so": str(so_path),
            "code_registration": code_reg,
            "metadata_registration": meta_reg,
            "config": config_name,
            "config_overrides": config_overrides or {},
            "config_apply_error": config_apply_error,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        print(f"[Il2CppDumper timeout] {dumper_path} with {metadata_path}")
        success = (out_dir / "dump.cs").exists() or (out_dir / "stringliteral.json").exists()
        code_reg = parse_addr(stdout, "CodeRegistration")
        meta_reg = parse_addr(stdout, "MetadataRegistration")
        return {
            "command": cmd,
            "returncode": -9,
            "stdout": stdout,
            "stderr": stderr,
            "success": success,
            "output_dir": str(out_dir),
            "metadata": str(metadata_path),
            "so": str(so_path),
            "code_registration": code_reg,
            "metadata_registration": meta_reg,
            "config": config_name,
            "config_overrides": config_overrides or {},
            "config_apply_error": config_apply_error,
            "timeout": True,
        }
    except Exception as e:
        return {
            "command": cmd,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False,
            "output_dir": str(out_dir),
            "metadata": str(metadata_path),
            "so": str(so_path),
            "code_registration": None,
            "metadata_registration": None,
            "config": config_name,
            "config_overrides": config_overrides or {},
            "config_apply_error": config_apply_error,
            "timeout": False,
        }
    finally:
        if config_path is not None and original_cfg is not None:
            try:
                restore_dumper_config(config_path, original_cfg)
            except Exception:
                pass


def run_dump_route(wait_seconds=12):
    launch_game()
    # Give the game a moment to spawn before we look for its PID
    time.sleep(max(wait_seconds, 5))
    pid = get_target_pid(timeout=30)
    print(f"Target PID: {pid}")
    # PGL Armor decrypts the SO and creates r-xp + rw-p segments during game init.
    # Wait until those segments appear so the dump includes real (non-zero) struct data.
    rxp_ok = wait_for_rxp_mapping(pid, timeout=120, poll_interval=3)
    if not rxp_ok:
        print("[WARNING] r-xp mapping never appeared; dumping anyway (may be incomplete)")
    else:
        # Brief extra wait to let rw-p structs (CodeRegistration, etc.) be fully populated
        time.sleep(2)
    entries = get_maps(pid)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    artifact_dir = RUNTIME_ROOT / stamp
    lib_dir = artifact_dir / "libil2cpp"
    meta_dir = artifact_dir / "metadata"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    cluster = find_real_libil2cpp_cluster(entries)
    lib_path, base_addr = dump_libil2cpp_cluster(pid, cluster, lib_dir)
    candidates = dump_metadata_candidates(pid, entries, meta_dir)

    report = {
        "artifact_dir": str(artifact_dir),
        "pid": pid,
        "base_addr": hex(base_addr),
        "libil2cpp": str(lib_path),
        "metadata_candidates": candidates,
    }

    dumper_list = list_il2cpp_dumpers()
    dumper_runs = []
    sofixer = find_sofixer()
    sofixer_result = None
    so_inputs = [lib_path]
    if sofixer:
        sofix_out = lib_dir / "libil2cpp_sofixer.so"
        base_hint = ROOT / "fixed" / "libil2cpp_fixed.so"
        sofixer_result = run_sofixer(
            sofixer_path=sofixer,
            source_so=lib_path,
            output_so=sofix_out,
            mem_base=base_addr,
            base_so=base_hint if base_hint.exists() else None,
        )
        if sofixer_result.get("success"):
            so_inputs.insert(0, sofix_out)
    report["sofixer"] = sofixer_result if sofixer else "SoFixer.exe not found"

    # ── Inject il2cpp_codegen_register symbol into .dynsym ──────────────
    # Il2CppDumper v6.7.46 SymbolSearch() calls .First() on the symbol list and
    # throws InvalidOperationException when il2cpp_codegen_register is absent.
    # We patch the raw memory-dump SO to add the symbol so SymbolSearch proceeds.
    hist_pair = find_best_pair_from_history()
    hist_code_raw = parse_hex_addr(hist_pair.get("code_registration_raw")) if hist_pair else None
    hist_meta_raw = parse_hex_addr(hist_pair.get("metadata_registration_raw")) if hist_pair else None
    # Fallback to well-known stable offsets for Soul Knight 8.1.0 if no history
    KNOWN_CODE_REG_RAW = 0xcba3f98
    KNOWN_META_REG_RAW = 0xd00d538
    code_reg_raw = hist_code_raw or KNOWN_CODE_REG_RAW
    meta_reg_raw = hist_meta_raw or KNOWN_META_REG_RAW
    patched_sym_so = lib_dir / "libil2cpp_sym_patched.so"
    patch_ok = patch_so_add_il2cpp_syms(lib_path, patched_sym_so, code_reg_raw, meta_reg_raw)
    if patch_ok and patched_sym_so.exists():
        so_inputs.insert(0, patched_sym_so)
        print(f"[PATCH] patched SO injected at front of so_inputs (code_reg={hex(code_reg_raw)} meta_reg={hex(meta_reg_raw)})")
    report["sym_patch"] = {
        "patched": patch_ok,
        "code_reg_raw": hex(code_reg_raw),
        "meta_reg_raw": hex(meta_reg_raw),
        "output": str(patched_sym_so) if patch_ok else None,
    }
    if dumper_list:
        metadata_inputs = collect_metadata_inputs(candidates)
        dumper_config_profiles = [
            ("safe", {"RequireAnyKey": False}),
            ("safe_force", {"RequireAnyKey": False, "ForceDump": True}),
            ("safe_force_no_redirect", {"RequireAnyKey": False, "ForceDump": True, "NoRedirectedPointer": True}),
            ("safe_v31", {"RequireAnyKey": False, "ForceIl2CppVersion": True, "ForceVersion": 31}),
            ("safe_v29", {"RequireAnyKey": False, "ForceIl2CppVersion": True, "ForceVersion": 29}),
        ]
        for so_idx, so_input in enumerate(so_inputs, start=1):
            for dumper in dumper_list:
                for idx, metadata in enumerate(metadata_inputs, start=1):
                    for profile_name, profile in dumper_config_profiles:
                        out_dir = artifact_dir / f"dumper_so{so_idx}_{Path(so_input).stem}_{dumper.parent.name}_{profile_name}_{idx}_{metadata.stem}"
                        dumper_runs.append(
                            try_il2cpp_dumper(
                                dumper,
                                so_input,
                                metadata,
                                out_dir,
                                base_addr,
                                config_overrides=profile,
                                config_name=profile_name,
                                hint_code_reg=code_reg_raw,
                                hint_meta_reg=meta_reg_raw,
                            )
                        )
                        if dumper_runs[-1]["success"]:
                            break
                    if dumper_runs and dumper_runs[-1]["success"]:
                        break
                if dumper_runs and dumper_runs[-1]["success"]:
                    break
            if dumper_runs and dumper_runs[-1]["success"]:
                break
        report["dumper"] = dumper_runs
    else:
        report["dumper"] = "Il2CppDumper.exe not found"

    report_path = artifact_dir / "dump_route_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    best_pair = extract_best_address_pair(dumper_runs, base_addr) if isinstance(dumper_runs, list) else None
    if best_pair:
        best_path = artifact_dir / "best_addresses.json"
        best_path.write_text(json.dumps(best_pair, ensure_ascii=False, indent=2), encoding="utf-8")
        report["best_addresses"] = str(best_path)

    print("\n===== DUMP ROUTE REPORT =====")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if dumper_runs and any(item["success"] for item in dumper_runs):
        print("\n[PASS] dump route produced Il2CppDumper output")
        return 0

    if best_pair:
        print("\n[PASS-PARTIAL] extracted non-zero CodeRegistration/MetadataRegistration")
        return 0

    history_pair = find_best_pair_from_history(exclude_dir=artifact_dir)
    if history_pair:
        best_path = artifact_dir / "best_addresses.json"
        best_path.write_text(json.dumps(history_pair, ensure_ascii=False, indent=2), encoding="utf-8")
        report["best_addresses"] = str(best_path)
        report["best_addresses_source"] = "history"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n[PASS-PARTIAL] reused best addresses from history")
        return 0

    print("\n[INFO] dump route completed, but Il2CppDumper did not succeed yet")
    return 2


def install_apk(apk_path: Path):
    if not apk_path.exists():
        raise RuntimeError(f"APK not found: {apk_path}")
    adb("install", "-r", str(apk_path))


def clear_state():
    adb("logcat", "-c")
    adb("shell", "rm", "-f", f"{DUMP_DIR}/jni_probe.txt", f"{DUMP_DIR}/reg_addrs.txt", f"{DUMP_DIR}/base_addr.txt", check=False)


def launch_game():
    adb("shell", "am", "force-stop", TARGET_PACKAGE, check=False)
    adb("shell", "am", "start", "-n", f"{TARGET_PACKAGE}/{TARGET_ACTIVITY}")


def capture_results(wait_seconds=8):
    time.sleep(wait_seconds)
    logs = adb("logcat", "-d", "-s", "HookKnight:I", capture=True, check=False).stdout or ""
    probe = adb("shell", "cat", f"{DUMP_DIR}/jni_probe.txt", capture=True, check=False)
    reg = adb("shell", "cat", f"{DUMP_DIR}/reg_addrs.txt", capture=True, check=False)
    base = adb("shell", "cat", f"{DUMP_DIR}/base_addr.txt", capture=True, check=False)

    report = {
        "logs": logs.strip(),
        "jni_probe": probe.stdout.strip() if probe.returncode == 0 else "No such file",
        "reg_addrs": reg.stdout.strip() if reg.returncode == 0 else "No such file",
        "base_addr": base.stdout.strip() if base.returncode == 0 else "No such file",
    }

    print("\n===== RESULT REPORT =====")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # Decision gate:
    if "il2cpp_codegen_register hooked" in report["logs"] or "CodeRegistration:" in report["reg_addrs"]:
        print("\n[PASS] codegen_register route is working")
        return 0

    if "il2cpp_runtime_invoke hooked" in report["logs"]:
        print("\n[FAIL-ROUTE] runtime_invoke hooked but codegen_register not hooked; codegen route is not viable in current timing")
        return 2

    print("\n[UNKNOWN] Native entered but no decisive hook hit yet")
    return 1


def main():
    parser = argparse.ArgumentParser(description="Build, install and verify LSPosed hook flow")
    parser.add_argument("--skip-build", action="store_true", help="Skip gradle build")
    parser.add_argument("--wait", type=int, default=8, help="Seconds to wait after launching game")
    parser.add_argument("--mode", choices=["hook", "dump", "auto"], default="auto", help="hook: only LSPosed route; dump: only root dump route; auto: hook then fallback to dump route")
    args = parser.parse_args()

    try:
        ensure_device()
        hook_code = None
        if args.mode in ("hook", "auto"):
            if not args.skip_build:
                build_apk(PROJECT_DIR)
            install_apk(APK_PATH)
            clear_state()
            launch_game()
            hook_code = capture_results(wait_seconds=args.wait)
            if args.mode == "hook":
                return hook_code
            if hook_code == 0:
                return 0

        if args.mode in ("dump", "auto"):
            return run_dump_route(wait_seconds=max(args.wait, 12))

        return hook_code if hook_code is not None else 1
    except Exception as e:
        print(f"\n[FATAL] {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
