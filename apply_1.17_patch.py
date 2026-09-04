#!/usr/bin/env python3
"""
apply_1.17_patch.py - make an existing The Convergence 3.0.1.x install run on Elden Ring 1.17.

This kit contains NO Convergence files. It edits YOUR copy of the mod in place:
  1. rebuilds mod/regulation.bin from your mod's regulation + your game's 1.17 regulation (3-way merge)
  2. updates the two exposer pointer tables (12 addresses + 3 struct offsets) for eldenring.exe 2.7.0.0
  3. installs Mod Engine 3 0.13.0, a 1.17 build of the custom-music DLL, and the 1.17 launcher/README

Usage:
  python apply_1.17_patch.py "<path to ConvergenceER>" ["<path to ELDEN RING\\Game>"]
  python apply_1.17_patch.py                 (no arguments: finds ConvergenceER on its own, or asks)
  python apply_1.17_patch.py --selftest      (checks the bundled merge tool and payload; no files touched)

  Windows exe (Convergence-1.17-patcher.exe): put it inside your ConvergenceER folder and double-click it,
  or run it from anywhere - it looks next to itself, in your Steam libraries, then asks with a folder dialog.

The Game folder is found automatically: next to ConvergenceER, or through your Steam libraries.
Requires Python 3.9+ and either `pip install zstandard cryptography` or the `zstd` + `openssl` command-line
tools (SteamOS has both). The Windows exe needs nothing.
Backups of every replaced file go to <ConvergenceER>/_backup_pre_1.17/
"""
import os, re, shutil, sys

FROZEN = bool(getattr(sys, "frozen", False))                                   # running as the PyInstaller exe
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))    # where tools/ and payload/ live
EXE_DIR = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
FLAGS = {a for a in sys.argv[1:] if a.startswith("-")}
INTERACTIVE = (FROZEN or not ARGS) and not FLAGS   # double-clicked / no arguments: ask when needed, keep the window open at the end
sys.path.insert(0, os.path.join(HERE, "tools"))

RVAS = {  # GameBasePointers.hks singletons: 1.16 -> 1.17 (verified against eldenring.exe 2.7.0.0)
    "_GAME_DATA_MAN": (0x3D5DF38, 0x3D61F98), "_CS_NOW_LOADING_HELPER": (0x3D60EC8, 0x3D64F28),
    "_CS_BULLET_MANAGER": (0x3D62748, 0x3D667A8), "_WORLD_CHR_MAN": (0x3D65F88, 0x3D69FF8),
    "_DMG_MAN": (0x3D66378, 0x3D6A3E8), "_CS_GA_ITEM": (0x3D69890, 0x3D6D900),
    "_GAME_MAN": (0x3D69918, 0x3D6D988), "_LOCK_TGT_MAN": (0x3D6A208, 0x3D6E278),
    "_WORLD_MAP_MAN": (0x3D6A320, 0x3D6E390), "_CS_FE_MAN": (0x3D6B880, 0x3D6F8F0),
    "_CS_SESSION_MANAGER": (0x3D7A4D0, 0x3D7E540), "_CS_WINDOW": (0x458B890, 0x458F910),
}
PAYLOAD_FILES = ("me3/Windows/me3.exe", "me3/Windows/me3-launcher.exe", "me3/Windows/me3_mod_host.dll", "me3/Linux/me3",
                 "me3/convergence.me3", "me3/LICENSE-MIT", "dll/unlock_wwise_states_er.dll",
                 "Start_Convergence.bat", "Start_Convergence.sh", "Diagnose_Convergence.bat", "README.md")

def pause():
    if INTERACTIVE:
        try: input("\nPress Enter to close this window.")
        except EOFError: pass

def die(msg):
    print("\nERROR:", msg); pause(); sys.exit(1)

def is_conv(p): return bool(p) and os.path.isfile(os.path.join(p, "mod", "regulation.bin"))

def steam_library_roots():
    """Steam library folders on Windows (registry + libraryfolders.vdf) and Linux/Steam Deck defaults."""
    roots = []
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                roots.append(winreg.QueryValueEx(k, "SteamPath")[0])
        except Exception: pass
    for d in (os.path.expanduser("~/.steam/steam"), os.path.expanduser("~/.local/share/Steam"),
              os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam"), "C:\\Program Files (x86)\\Steam"):
        if os.path.isdir(d): roots.append(d)
    libs = []
    for r in roots:
        libs.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="replace").read()):
                libs.append(m.group(1).replace("\\\\", "\\"))
    seen, out = set(), []
    for l in libs:
        if l not in seen: seen.add(l); out.append(l)
    return out

def ask_folder(title):
    """Interactive fallback: a folder dialog when a display is available, otherwise a typed path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        try: root.attributes("-topmost", True)
        except Exception: pass
        p = filedialog.askdirectory(title=title, mustexist=True)
        root.destroy()
        if p: return os.path.abspath(p)
    except Exception: pass
    try: p = input(f"{title}\nType or paste the path and press Enter: ").strip().strip('"').strip("'")
    except EOFError: p = ""
    return os.path.abspath(p) if p else None

def find_conv():
    """No path given: the exe's own folder (drop it into ConvergenceER), a ConvergenceER next to it, the current folder, Steam libraries, then ask."""
    for c in (EXE_DIR, os.path.join(EXE_DIR, "ConvergenceER"), os.path.join(EXE_DIR, "..", "ConvergenceER"), os.getcwd()):
        if is_conv(c): return os.path.abspath(c)
    for lib in steam_library_roots():
        c = os.path.join(lib, "steamapps", "common", "ELDEN RING", "ConvergenceER")
        if is_conv(c): return os.path.abspath(c)
    print("Could not find your ConvergenceER folder automatically.")
    return ask_folder("Select your ConvergenceER folder (the one that contains Start_Convergence.bat)")

def find_game(conv):
    for cand in (os.path.join(conv, "..", "Game", "eldenring.exe"), os.path.join(conv, "..", "ELDEN RING", "Game", "eldenring.exe")):
        if os.path.isfile(cand): return os.path.dirname(os.path.abspath(cand))
    for lib in steam_library_roots():   # normal Steam install, anywhere
        cand = os.path.join(lib, "steamapps", "common", "ELDEN RING", "Game", "eldenring.exe")
        if os.path.isfile(cand): return os.path.dirname(os.path.abspath(cand))
    if INTERACTIVE:
        print("Could not find the game's Game folder automatically.")
        return ask_folder("Select your ELDEN RING\\Game folder (the one that contains eldenring.exe)")
    return None

def backup(conv, rel):
    """Copy <conv>/<rel> to _backup_pre_1.17/ once. A backup taken by an earlier run is never overwritten, so re-running
    the patcher keeps the original 3.0.1.x files rather than replacing them with already-patched copies."""
    src = os.path.join(conv, rel); dst = os.path.join(conv, "_backup_pre_1.17", rel)
    if os.path.exists(src) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src): shutil.copytree(src, dst)
        else: shutil.copy2(src, dst)

def patch_hks(conv):
    ex = os.path.join(conv, "mod", "action", "script", "modules", "exposer")
    gb = os.path.join(ex, "GameBasePointers.hks"); ci = os.path.join(ex, "ChrInsPointers.hks")
    for p in (gb, ci):
        if not os.path.isfile(p): die(f"missing {p} - is this a Convergence 3.0.1.x install?")
    s = open(gb, encoding="utf-8").read()
    if "eldenring.exe 2.7.0.0" in s: print("  GameBasePointers.hks already patched")
    else:
        for name, (old, new) in RVAS.items():
            s, n = re.subn(rf"^(local {name}\s*=\s*)0x{old:X}(\s*--\s*)1\.16\s*$", lambda m: f"{m.group(1)}0x{new:X}{m.group(2)}1.17 (eldenring.exe 2.7.0.0; was 0x{old:X} in 1.16)", s, flags=re.M)
            if n != 1: die(f"GameBasePointers.hks: expected exactly one line for {name} = 0x{old:X}, found {n}. Is this an unmodified 3.0.1.x file?")
        open(gb, "w", encoding="utf-8").write(s); print("  GameBasePointers.hks: 12 addresses updated")
    s = open(ci, encoding="utf-8").read()
    if re.search(r"0x538 \}", s) and not re.search(r"0x53[012] \}", s): print("  ChrInsPointers.hks already patched")
    else:
        n1 = len(re.findall(r"\{ _CHR_INS_BASE, BIT, \d+, 0x530 \}", s)); n2 = s.count("0x531 }"); n3 = s.count("0x532 }")
        if (n1, n2, n3) != (3, 1, 1): die(f"ChrInsPointers.hks: unexpected flag entries {n1},{n2},{n3}; expected 3,1,1")
        s = re.sub(r"(\{ _CHR_INS_BASE, BIT, \d+, )0x530( \})", r"\g<1>0x538\g<2>", s)
        s = re.sub(r"(\{ _CHR_INS_BASE, BIT, \d+, )0x531( \})", r"\g<1>0x539\g<2>", s)
        s = re.sub(r"(\{ _CHR_INS_BASE, BIT, \d+, )0x532( \})", r"\g<1>0x53A\g<2>", s)
        s = s.replace("    CHR_FLAGS = { -- 0x530 / 0x533", "    CHR_FLAGS = { -- 0x538 / 0x53B  (1.17; was 0x530 / 0x533 in 1.16)")
        open(ci, "w", encoding="utf-8").write(s); print("  ChrInsPointers.hks: 3 flag offsets updated (PLAYER_GAME_DATA 0x580 unchanged in 1.17)")

def selftest():
    """Prove this copy works without touching any install: merge tool round-trips the bundled vanilla regulation
    through every layer (AES, DCX/zstd, BND4, PARAM), the pointer-table patcher rewrites a synthetic table, and
    every payload file is present. Used by the Windows exe build on a real Windows machine."""
    import tempfile
    import regtool as R
    print(f"backends: zstd={'python module' if R.zstandard else 'zstd CLI'}, aes={'python module' if R.Cipher else 'openssl CLI'}")
    van = os.path.join(HERE, "tools", "vanilla-regulation-1.16.1-11611000.bin")
    bnd, level, raw = R.read_regulation(van)
    if bnd.version != "11611000": die(f"selftest: unexpected version {bnd.version}")
    if R.Bnd4.parse(raw).write() != raw: die("selftest: BND4 container round-trip mismatch")
    ident = 0
    for f in bnd.files:   # rows/names/data must survive parse+write exactly. The raw FromSoftware file may differ only in the
        p = R.Param.parse(f.data); w = p.write(); p2 = R.Param.parse(w)   # strings-offset header field and the zero padding
        pt = p.param_type.encode(); io, iw = f.data.rfind(pt), w.rfind(pt)   # around the trailing param-type string (the
        if io < 0 or iw < 0 or w[4:iw] != f.data[4:io] or any(f.data[io + len(pt):]) or any(w[iw + len(pt):]) \
                or p2.write() != w or len(p2.rows) != len(p.rows) or any(tuple(a) != tuple(b) for a, b in zip(p.rows, p2.rows)) \
                or (p2.param_type, p2.fmt2d, p2.fmt2e) != (p.param_type, p.fmt2d, p.fmt2e):   # layout Smithbox and the mod's own file use)
            die(f"selftest: param round-trip mismatch in {R.short_name(f.name)}")
        ident += w == f.data
    print(f"  read + parse + rewrite: {len(bnd.files)} params equal ({ident} byte-identical, the rest differ only in the raw file's strings-offset field / tail padding)")
    tmp = os.path.join(tempfile.mkdtemp(prefix="convergence-selftest-"), "regulation.bin")
    R.write_regulation(tmp, bnd, level)
    dcx = R.aes_decrypt(open(tmp, "rb").read())
    zi = dcx.find(b"\x28\xb5\x2f\xfd")
    if dcx[:4] != b"DCX\0" or zi < 0 or dcx[zi + 4] != 0x00: die("selftest: written DCX/zstd header is not what the game accepts")
    raw2, level2 = R.dcx_unwrap(dcx)
    if raw2 != raw or level2 != level: die("selftest: encrypt/compress/decrypt/decompress round-trip mismatch")
    shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    print("  encrypt + compress + decrypt + decompress: byte-identical, zstd frame header as the game expects")
    conv = tempfile.mkdtemp(prefix="convergence-selftest-")
    ex = os.path.join(conv, "mod", "action", "script", "modules", "exposer"); os.makedirs(ex)
    open(os.path.join(ex, "GameBasePointers.hks"), "w").write("".join(f"local {n} = 0x{o:X} -- 1.16\n" for n, (o, _) in RVAS.items()))
    open(os.path.join(ex, "ChrInsPointers.hks"), "w").write("    CHR_FLAGS = { -- 0x530 / 0x533\n" + "".join(
        f"        {{ _CHR_INS_BASE, BIT, {b}, 0x{v:X} }},\n" for b, v in ((0, 0x530), (1, 0x530), (2, 0x530), (0, 0x531), (0, 0x532))))
    patch_hks(conv)
    g = open(os.path.join(ex, "GameBasePointers.hks")).read(); c = open(os.path.join(ex, "ChrInsPointers.hks")).read()
    if any(f"0x{n:X}" not in g for _, n in RVAS.values()) or re.search(r"0x53[012] \}", c) or c.count("0x538 }") != 3 or c.count("0x539 }") != 1 or c.count("0x53A }") != 1:
        die("selftest: pointer-table patch produced unexpected output")
    patch_hks(conv)   # second run must be a no-op
    if (open(os.path.join(ex, "GameBasePointers.hks")).read(), open(os.path.join(ex, "ChrInsPointers.hks")).read()) != (g, c): die("selftest: pointer-table patch is not idempotent")
    shutil.rmtree(conv, ignore_errors=True)
    missing = [rel for rel in PAYLOAD_FILES if not os.path.isfile(os.path.join(HERE, "payload", rel))]
    if missing: die(f"selftest: payload files missing: {missing}")
    print(f"  payload: all {len(PAYLOAD_FILES)} files present")
    print("SELFTEST OK")

def main():
    if FLAGS & {"-h", "--help"}: print(__doc__); return
    if "--selftest" in FLAGS: selftest(); return
    conv = os.path.abspath(ARGS[0]) if ARGS else find_conv()
    if not is_conv(conv): die(f"{conv or '(none)'} does not look like a ConvergenceER folder (no mod/regulation.bin)")
    game = os.path.abspath(ARGS[1]) if len(ARGS) > 1 else find_game(conv)
    if not game or not os.path.isfile(os.path.join(game, "regulation.bin")): die("could not find the game's Game folder (needs regulation.bin + eldenring.exe); pass it as the 2nd argument")
    try:
        import regtool as R
    except ImportError as e: die(f"cannot import the merge tool ({e})")
    print(f"Convergence: {conv}\nGame:        {game}")
    # 1) regulation
    van_new = os.path.join(game, "regulation.bin"); van_old = os.path.join(HERE, "tools", "vanilla-regulation-1.16.1-11611000.bin")
    modreg = os.path.join(conv, "mod", "regulation.bin")
    b, _, _ = R.read_regulation(modreg)
    if b.version == "11701000": print("  regulation.bin already at 11701000 - skipping merge")
    else:
        if b.version != "11611000": die(f"mod regulation version is {b.version}; this patch expects the 3.0.1.x file (11611000)")
        v, _, _ = R.read_regulation(van_new)
        if v.version != "11701000": die(f"game regulation version is {v.version}; the game must be on patch 1.17")
        backup(conv, os.path.join("mod", "regulation.bin"))
        R.cmd_upgrade(modreg, van_old, van_new, modreg + ".new", os.path.join(conv, "regulation-upgrade-report.json"))
        os.replace(modreg + ".new", modreg); print("  regulation.bin rebuilt for 1.17")
    # 2) pointer tables
    for rel in ("mod/action/script/modules/exposer/GameBasePointers.hks", "mod/action/script/modules/exposer/ChrInsPointers.hks"): backup(conv, rel)
    patch_hks(conv)
    # 3) payload: me3, music DLL, launcher, README
    pay = os.path.join(HERE, "payload")
    for rel in ("me3", "Start_Convergence.bat", "Start_Convergence.sh", "Diagnose_Convergence.bat", "README.md"): backup(conv, rel)
    backup(conv, os.path.join("mod", "dll", "unlock_wwise_states_er.dll"))
    shutil.copytree(os.path.join(pay, "me3"), os.path.join(conv, "me3"), dirs_exist_ok=True)
    for f in ("Start_Convergence.bat", "Start_Convergence.sh", "Diagnose_Convergence.bat", "README.md"): shutil.copy2(os.path.join(pay, f), os.path.join(conv, f))
    shutil.copy2(os.path.join(pay, "dll", "unlock_wwise_states_er.dll"), os.path.join(conv, "mod", "dll", "unlock_wwise_states_er.dll"))
    for stale in ("version.txt",):  # stops the official launcher from reverting the files
        p = os.path.join(conv, stale)
        if os.path.exists(p): backup(conv, stale); os.remove(p); print(f"  removed {stale} (prevents the official Launcher from undoing this patch)")
    print("\nDone. Run Start_Convergence.bat. The title screen must show App Ver. 1.17 / Regulation Ver. 1.17.")
    print(f"Backups of replaced files: {os.path.join(conv, '_backup_pre_1.17')}")
    pause()

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception as e:
        import traceback; traceback.print_exc(); die(f"{type(e).__name__}: {e}")
