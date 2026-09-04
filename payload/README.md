# The Convergence: Elden Ring 3.0.1.2 — Elden Ring 1.17 build (unofficial)

This is The Convergence mod, version 3.0.1.2, made to run on **Elden Ring patch 1.17** (the update that
shipped with the Tarnished Pack DLC, 2026-08-27). Every part of the mod is active, including the custom
boss and area music. It has been played through boot, character creation and gameplay on 1.17.

This is an unofficial compatibility build. All credit for the mod belongs to The Convergence team. If the
team releases an official 1.17 version, prefer that.

**No co-op.** Seamless Co-op is not part of this package and its profile has been removed.

## Requirements

* Elden Ring on **patch 1.17** (`Game\eldenring.exe` file version 2.7.0.0). It will not work on 1.16.
* Shadow of the Erdtree is required by the mod itself, as before.
* Works with the normal Steam install (Steam must be running) and with a game folder that is not registered
  in Steam (set `GAME_EXE` in the launcher). Windows, or Linux / Steam Deck through Proton.

## Install

1. Unzip. Put the `ConvergenceER` folder **next to the game's `Game` folder**, i.e. inside your
   `ELDEN RING` folder, not inside `Game`:

   ```
   ELDEN RING\
     Game\eldenring.exe
     ConvergenceER\Start_Convergence.bat
   ```

   Any other location also works: for a Steam install the launcher asks Steam where the game is; for any
   other copy set `GAME_EXE` at the top of `Start_Convergence.bat`.
2. **Back up your save** (`%APPDATA%\EldenRing\<steam id>\ER0000.cnv`). A save opened on 1.17 will not
   open on 1.16 again.
3. Run `Start_Convergence.bat`. Keep its window open while you play.
4. On the title screen the bottom-right corner must read **App Ver. 1.17** and **Regulation Ver. 1.17**.

Do **not** run the official Convergence Launcher on this folder. It would "update" the files back to the
1.16 versions and undo the 1.17 changes. There is deliberately no `version.txt` in this package.

### Steam Deck / Linux

Add `Start_Convergence.bat` to Steam as a non-Steam game, set it to run with Proton, and launch it from
there. The launcher finds `eldenring.exe` on its own. Run the mod from internal storage, not from an
external exFAT drive. `Start_Convergence.sh` is an alternative that uses me3's native Linux binary; the
`.bat` route is the recommended one.

### If it does not start

Run `Diagnose_Convergence.bat` the same way you run the launcher. It writes `me3-diagnostic.txt` next to
itself with the actual error from the mod loader. The normal launcher also keeps its output in
`me3-launch.log`.

## What was changed for 1.17

| Component | Change |
|---|---|
| `mod/regulation.bin` | Rebased onto 1.17 params with a three-way merge (mod, vanilla 1.16.1, vanilla 1.17): 357 new 1.17 rows added (Tarnished Pack items, Spectral Steed rows for Torrent, new classes, spells, weapons), 100 untouched rows updated, the mod's own balance kept everywhere it differs, the mod's deliberate deletions respected, and the new EquipParamProtector flags applied. Regulation version 11701000. |
| `mod/action/script/modules/exposer/GameBasePointers.hks` | 12 game-singleton addresses updated to 1.17 (the executable's globals moved). |
| `mod/action/script/modules/exposer/ChrInsPointers.hks` | 3 character-struct offsets updated (the character struct gained a field in 1.17). |
| `mod/dll/unlock_wwise_states_er.dll` | Rebuilt from source for 1.17 (custom boss/area music). |
| `me3/` | Mod Engine 3 updated to 0.13.0. Profile: dev-only DLL entries removed, cosmetic DLLs marked optional. |
| `Start_Convergence.bat` | Passes the game path to me3, runs it in the foreground with a log, and no longer contains the checks that misfire under Proton. |
| 3.0.1.1 / 3.0.1.2 hotfixes | Included (from the team's public repository). |

Unchanged and working as-is on 1.17: Scripts-Data-Exposer-FS, ErdTools, erdyes (dyes), ertransmogrify
(transmog), and all of the mod's assets.

## Known limitations

* The mod ships its own text files, so if you own the Tarnished Pack its new item names may show blank.
  Cosmetic only.
* Not tested with Seamless Co-op (removed from this package).

## Credits

* The Convergence team — the mod. https://www.convergencemod.com
* garyttierney — Mod Engine 3 (me3). https://github.com/garyttierney/me3
* ndahn — the Wwise state unlocker the music DLL is built from. https://github.com/ndahn/yonder
* ElaDiDu, Nordgaren, ThomasJClark — Scripts-Data-Exposer-FS, ErdTools, dyes / transmog.
* vswarte — fromsoftware-rs (1.17 bindings used for the music DLL).
* vawser — Smithbox, whose bundled vanilla regulations and paramdefs made the param merge possible.
