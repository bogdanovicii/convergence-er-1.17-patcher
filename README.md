# The Convergence 3.0.1.x on Elden Ring 1.17 - unofficial patcher

**Download (Windows, no Python needed):** [Convergence-1.17-patcher.exe](https://github.com/bogdanovicii/convergence-er-1.17-patcher/releases/latest/download/Convergence-1.17-patcher.exe)
- put it in your `ConvergenceER` folder and double-click it.

**Download (Steam Deck / Linux, or Windows with Python):** [Convergence-1.17-patcher.zip](https://github.com/bogdanovicii/convergence-er-1.17-patcher/releases/latest/download/Convergence-1.17-patcher.zip)

Tested in play on Elden Ring 1.17 (Windows build under Proton on a Steam Deck): boot, character creation,
gameplay, custom boss/area music. No co-op. Bug reports: [Issues](https://github.com/bogdanovicii/convergence-er-1.17-patcher/issues).

This kit makes an EXISTING install of The Convergence 3.0.1 / 3.0.1.2 run on Elden Ring patch 1.17.
It contains none of the mod's files. The Convergence team's Nexus permissions do not allow re-uploading or
modifying their files, so instead of shipping modified copies this kit edits YOUR copy on your machine, using
your own game's 1.17 data. What it does ship is only redistributable work: Mod Engine 3 (MIT/Apache-2.0), a
1.17 rebuild of the custom-music DLL (GPL, source included under `source/`), the launcher scripts, and the
merge tool.

## You need

* The Convergence 3.0.1 or 3.0.1.2 already installed (official download or the official Launcher).
* Elden Ring on patch 1.17 (`Game\eldenring.exe` file version 2.7.0.0).
* Windows: nothing else if you use the exe. With the scripts instead: Python 3.9+ and `pip install zstandard cryptography`.
* Steam Deck / Linux: Python 3, which SteamOS has. No pip, no packages: the helper uses the `zstd` and `openssl` tools
  that are already on the system.

## Run

**Windows, no Python (easiest):** download `Convergence-1.17-patcher.exe` from the release page, put it inside your
`ConvergenceER` folder and double-click it. It finds the game (next to the mod or through Steam, otherwise it asks with a
folder dialog), does everything listed below, and waits for Enter before closing so you can read the result.
Windows SmartScreen warns about an unknown publisher the first time: click "More info", then "Run anyway". The exe is
built by GitHub Actions from this repository's own source and self-tested on the build machine; the build log is public.

**Windows with Python:**
```
python apply_1.17_patch.py "D:\Games\ELDEN RING\ConvergenceER"
```
**Steam Deck / Linux** (Konsole; nothing to install, no root needed):
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

## Licensing

* `apply_1.17_patch.py`, `run_patcher_linux.sh`, `tools/regtool.py`, the launcher scripts: MIT (see `LICENSE`).
* `payload/me3/`: Mod Engine 3 by garyttierney, MIT / Apache-2.0 (`payload/me3/LICENSE-MIT`).
* `payload/dll/unlock_wwise_states_er.dll`: built from ndahn/yonder, GPL. Full source of the 1.17 build is in
  `source/unlock_wwise_states_er/` together with the exact changes and the evidence for every 1.17 address.
* `tools/vanilla-regulation-1.16.1-11611000.bin`: the unmodified 1.16.1 game regulation used as the merge base,
  as bundled by Smithbox. No Convergence files are included anywhere in this repository.
