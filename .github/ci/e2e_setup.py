"""CI only: build a stand-in ConvergenceER install from public data, so the built exe can be run end to end on Windows.
The bundled vanilla 1.16.1 regulation plays the mod's regulation; a copy re-labelled 11701000 plays the game's 1.17
regulation; the pointer tables are synthetic lines in the exact 3.0.1.x format. No Convergence files involved."""
import importlib.util, os, shutil, sys
out = sys.argv[1] if len(sys.argv) > 1 else "e2e"
sys.path.insert(0, "tools"); import regtool as R
spec = importlib.util.spec_from_file_location("ap", "apply_1.17_patch.py"); ap = importlib.util.module_from_spec(spec)
sys.argv = ["ap", "--selftest"]; spec.loader.exec_module(ap)   # import only (the flag keeps the module non-interactive)
root = os.path.join(out, "ELDEN RING")
conv, game = os.path.join(root, "ConvergenceER"), os.path.join(root, "Game")
ex = os.path.join(conv, "mod", "action", "script", "modules", "exposer")
for d in (ex, game, os.path.join(conv, "mod", "dll"), os.path.join(conv, "me3")): os.makedirs(d, exist_ok=True)
van = os.path.join("tools", "vanilla-regulation-1.16.1-11611000.bin")
shutil.copy(van, os.path.join(conv, "mod", "regulation.bin"))
GAME_VER = os.environ.get("E2E_GAME_VERSION", "11701000")   # 11701000 = ER 1.17, 11711000 = ER 1.17.1
bnd, level, _ = R.read_regulation(van); bnd.version = GAME_VER; R.write_regulation(os.path.join(game, "regulation.bin"), bnd, level)
open(os.path.join(game, "eldenring.exe"), "wb").close()
open(os.path.join(ex, "GameBasePointers.hks"), "w").write("-- synthetic\n" + "".join(f"local {n} = 0x{o:X} -- 1.16\n" for n, (o, _) in ap.RVAS.items()))
open(os.path.join(ex, "ChrInsPointers.hks"), "w").write("    CHR_FLAGS = { -- 0x530 / 0x533\n" + "".join(
    f"        {{ _CHR_INS_BASE, BIT, {b}, 0x{v:X} }},\n" for b, v in ((3, 0x530), (4, 0x530), (5, 0x530), (0, 0x531), (0, 0x532))) + "    }\n")
open(os.path.join(conv, "mod", "dll", "unlock_wwise_states_er.dll"), "wb").write(b"old dll")
open(os.path.join(conv, "me3", "marker.txt"), "w").write("stock me3 0.11.0")
open(os.path.join(conv, "version.txt"), "w").write("3.0.1.2")
print("stand-in install ready:", conv)
