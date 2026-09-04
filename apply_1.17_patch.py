#!/usr/bin/env python3
"""
apply_1.17_patch.py - make an existing The Convergence 3.0.1.x install run on Elden Ring 1.17.

This kit contains NO Convergence files. It edits YOUR copy of the mod in place:
  1. rebuilds mod/regulation.bin from your mod's regulation + your game's 1.17 regulation (3-way merge)
  2. updates the two exposer pointer tables (12 addresses + 3 struct offsets) for eldenring.exe 2.7.0.0
  3. installs Mod Engine 3 0.13.0, a 1.17 build of the custom-music DLL, and the 1.17 launcher/README

Usage:
  python apply_1.17_patch.py "<path to ConvergenceER>" ["<path to ELDEN RING\\Game>"]
  (the Game folder is found automatically: next to ConvergenceER, or through your Steam libraries)

Requires Python 3.9+ and either `pip install zstandard cryptography` or the `zstd` + `openssl` command-line tools (SteamOS has both)
Backups of every replaced file go to <ConvergenceER>/_backup_pre_1.17/
"""
import os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))

RVAS = {  # GameBasePointers.hks singletons: 1.16 -> 1.17 (verified against eldenring.exe 2.7.0.0)
    "_GAME_DATA_MAN": (0x3D5DF38, 0x3D61F98), "_CS_NOW_LOADING_HELPER": (0x3D60EC8, 0x3D64F28),
    "_CS_BULLET_MANAGER": (0x3D62748, 0x3D667A8), "_WORLD_CHR_MAN": (0x3D65F88, 0x3D69FF8),
    "_DMG_MAN": (0x3D66378, 0x3D6A3E8), "_CS_GA_ITEM": (0x3D69890, 0x3D6D900),
    "_GAME_MAN": (0x3D69918, 0x3D6D988), "_LOCK_TGT_MAN": (0x3D6A208, 0x3D6E278),
    "_WORLD_MAP_MAN": (0x3D6A320, 0x3D6E390), "_CS_FE_MAN": (0x3D6B880, 0x3D6F8F0),
    "_CS_SESSION_MANAGER": (0x3D7A4D0, 0x3D7E540), "_CS_WINDOW": (0x458B890, 0x458F910),
}

def die(msg): print("ERROR:", msg); sys.exit(1)

def steam_library_roots():
    """Steam library folders on Windows (registry + libraryfolders.vdf) and Linux/Steam Deck defaults."""
    roots = []
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Valve\\Steam") as k:
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

def find_game(conv):
    for cand in (os.path.join(conv, "..", "Game", "eldenring.exe"), os.path.join(conv, "..", "ELDEN RING", "Game", "eldenring.exe")):
        if os.path.isfile(cand): return os.path.dirname(os.path.abspath(cand))
    for lib in steam_library_roots():   # normal Steam install, anywhere
        cand = os.path.join(lib, "steamapps", "common", "ELDEN RING", "Game", "eldenring.exe")
        if os.path.isfile(cand): return os.path.dirname(os.path.abspath(cand))
    return None

def backup(conv, rel):
    src = os.path.join(conv, rel)
    if os.path.exists(src):
        dst = os.path.join(conv, "_backup_pre_1.17", rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src): shutil.copytree(src, dst, dirs_exist_ok=True)
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
    if "0x538" in s and "0x530" not in s: print("  ChrInsPointers.hks already patched")
    else:
        n1 = len(re.findall(r"\{ _CHR_INS_BASE, BIT, \d+, 0x530 \}", s)); n2 = s.count("0x531 }"); n3 = s.count("0x532 }")
        if (n1, n2, n3) != (3, 1, 1): die(f"ChrInsPointers.hks: unexpected flag entries {n1},{n2},{n3}; expected 3,1,1")
        s = re.sub(r"(\{ _CHR_INS_BASE, BIT, \d+, )0x530( \})", r"\g<1>0x538\g<2>", s)
        s = re.sub(r"(\{ _CHR_INS_BASE, BIT, \d+, )0x531( \})", r"\g<1>0x539\g<2>", s)
        s = re.sub(r"(\{ _CHR_INS_BASE, BIT, \d+, )0x532( \})", r"\g<1>0x53A\g<2>", s)
        s = s.replace("    CHR_FLAGS = { -- 0x530 / 0x533", "    CHR_FLAGS = { -- 0x538 / 0x53B  (1.17; was 0x530 / 0x533 in 1.16)")
        open(ci, "w", encoding="utf-8").write(s); print("  ChrInsPointers.hks: 3 flag offsets updated (PLAYER_GAME_DATA 0x580 unchanged in 1.17)")

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    conv = os.path.abspath(sys.argv[1])
    if not os.path.isfile(os.path.join(conv, "mod", "regulation.bin")): die(f"{conv} does not look like a ConvergenceER folder (no mod/regulation.bin)")
    game = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else find_game(conv)
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

if __name__ == "__main__": main()
