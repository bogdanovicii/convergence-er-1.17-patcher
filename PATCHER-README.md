# The Convergence 3.0.1.x -> Elden Ring 1.17 patcher (unofficial)

This kit makes an EXISTING install of The Convergence 3.0.1 / 3.0.1.2 run on Elden Ring patch 1.17.
It contains none of the mod's files. The Convergence team's Nexus permissions do not allow re-uploading or
modifying their files, so instead of shipping modified copies this kit edits YOUR copy on your machine, using
your own game's 1.17 data. What it does ship is only redistributable work: Mod Engine 3 (MIT/Apache-2.0), a
1.17 rebuild of the custom-music DLL (GPL, source included under `source/`), the launcher scripts, and the
merge tool.

## You need

* The Convergence 3.0.1 or 3.0.1.2 already installed (official download or the official Launcher).
* Elden Ring on patch 1.17 (`Game\eldenring.exe` file version 2.7.0.0).
* Python 3.9 or newer. On Windows also `pip install zstandard cryptography`. On Steam Deck / Linux nothing
  else: the helper script uses the `zstd` and `openssl` tools that are already on the system, so no pip and no
  packages are needed (the Python modules are used only if they happen to be installed).

## Run

Windows:
```
python apply_1.17_patch.py "D:\Games\ELDEN RING\ConvergenceER"
```
Steam Deck / Linux (Konsole; nothing to install, no root needed):
```
bash run_patcher_linux.sh "$HOME/.steam/steam/steamapps/common/ELDEN RING/ConvergenceER"
```
The game's `Game` folder is found next to ConvergenceER or through your Steam libraries; pass it as a second
argument only for a copy of the game that is neither. The script:

1. rebuilds `mod/regulation.bin` by merging your mod's params with the 1.17 params from your game
   (357 new rows added, the mod's own balance and deletions kept, new armor flags applied, version 11701000);
2. updates the two address tables the mod's scripts use (`GameBasePointers.hks`, `ChrInsPointers.hks`);
3. installs Mod Engine 3 0.13.0 and its profile, the rebuilt music DLL, the launcher and the README;
4. removes `version.txt` so the official Launcher cannot revert the files;
5. keeps a copy of everything it replaced in `ConvergenceER/_backup_pre_1.17/`.

Then run `Start_Convergence.bat`. The title screen must show **App Ver. 1.17 / Regulation Ver. 1.17**.

It refuses to run on anything other than an unmodified 3.0.1.x install and a 1.17 game, and it is safe to
re-run (already-patched files are skipped).

No co-op in this version. Back up your save first; a save opened on 1.17 will not open on 1.16 again.

The result is byte-for-byte the same data as the hand-built package that was tested in play on 1.17
(boot, character creation, gameplay, custom boss/area music). Credit for the mod belongs to The Convergence
team; if they release an official 1.17 build, use that.
