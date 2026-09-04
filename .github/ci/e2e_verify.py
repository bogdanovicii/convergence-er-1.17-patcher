"""CI only: verify what the exe did to the stand-in install (see e2e_setup.py). Exit code 1 on any failure."""
import filecmp, os, re, sys
sys.path.insert(0, "tools"); import regtool as R
root = os.path.join(sys.argv[1] if len(sys.argv) > 1 else "e2e", "ELDEN RING")
conv, game = os.path.join(root, "ConvergenceER"), os.path.join(root, "Game")
ex = os.path.join(conv, "mod", "action", "script", "modules", "exposer"); bk = os.path.join(conv, "_backup_pre_1.17")
checks = {}
b, _, raw = R.read_regulation(os.path.join(conv, "mod", "regulation.bin")); g, _, graw = R.read_regulation(os.path.join(game, "regulation.bin"))
checks["regulation rebuilt at 11701000, payload identical to the 1.17 stand-in (same rows -> same bytes)"] = b.version == "11701000" and raw == graw
gb = open(os.path.join(ex, "GameBasePointers.hks")).read(); ci = open(os.path.join(ex, "ChrInsPointers.hks")).read()
checks["GameBasePointers: 12 lines carry 1.17 addresses"] = len(re.findall(r"^local _[A-Z_]+ = 0x[0-9A-F]+ -- 1\.17 \(eldenring\.exe 2\.7\.0\.0", gb, re.M)) == 12
checks["ChrInsPointers: 0x538 x3, 0x539, 0x53A, no 0x530-0x532 entries"] = ci.count("0x538 }") == 3 and ci.count("0x539 }") == 1 and ci.count("0x53A }") == 1 and not re.search(r"0x53[012] \}", ci)
checks["me3 0.13.0 installed"] = os.path.isfile(os.path.join(conv, "me3", "Windows", "me3.exe")) and os.path.isfile(os.path.join(conv, "me3", "convergence.me3"))
checks["music DLL replaced with the 1.17 build"] = filecmp.cmp(os.path.join(conv, "mod", "dll", "unlock_wwise_states_er.dll"), os.path.join("payload", "dll", "unlock_wwise_states_er.dll"), shallow=False)
checks["launcher + README installed"] = all(os.path.isfile(os.path.join(conv, f)) for f in ("Start_Convergence.bat", "Diagnose_Convergence.bat", "Start_Convergence.sh", "README.md"))
checks["version.txt removed"] = not os.path.exists(os.path.join(conv, "version.txt"))
checks["backup: original regulation"] = filecmp.cmp(os.path.join(bk, "mod", "regulation.bin"), os.path.join("tools", "vanilla-regulation-1.16.1-11611000.bin"), shallow=False)
checks["backup: original pointer tables (1.16 values)"] = "-- 1.16\n" in open(os.path.join(bk, "mod/action/script/modules/exposer/GameBasePointers.hks")).read() and "0x530 }" in open(os.path.join(bk, "mod/action/script/modules/exposer/ChrInsPointers.hks")).read()
checks["backup: original me3 folder and version.txt (not overwritten by the 2nd run)"] = os.path.isfile(os.path.join(bk, "me3", "marker.txt")) and not os.path.isfile(os.path.join(bk, "me3", "Windows", "me3.exe")) and os.path.isfile(os.path.join(bk, "version.txt"))
checks["backup: original DLL"] = open(os.path.join(bk, "mod", "dll", "unlock_wwise_states_er.dll"), "rb").read() == b"old dll"
r1 = open(os.path.join(conv, "run1.txt"), errors="replace").read(); r2 = open(os.path.join(conv, "run2.txt"), errors="replace").read()
checks["run 1: found the folder next to the exe, rebuilt, finished with Done"] = "regulation.bin rebuilt for 1.17" in r1 and "Done. Run Start_Convergence.bat" in r1 and "ERROR" not in r1
checks["run 2: clean no-op"] = "already at 11701000" in r2 and "GameBasePointers.hks already patched" in r2 and "ChrInsPointers.hks already patched" in r2 and "Done." in r2 and "ERROR" not in r2
ok = True
for k, v in checks.items():
    print(("  PASS  " if v else "  FAIL  ") + k); ok &= bool(v)
print("E2E OK" if ok else "E2E FAILED"); sys.exit(0 if ok else 1)
