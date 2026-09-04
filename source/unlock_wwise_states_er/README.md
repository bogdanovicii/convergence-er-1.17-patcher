# unlock_wwise_states_er.dll rebuilt for Elden Ring 1.17 (eldenring.exe 2.7.0.0)

Source: https://github.com/ndahn/yonder, `unlock_wwise_states/eldenring/` (upstream HEAD 5d85f12, 2026-07-09,
no 1.17 support). Only `src/lib.rs` was changed (see `lib.rs` vs `lib.rs.upstream-2026-06-27`).
fromsoftware-rs resolved to e0948c8d (2026-09-02), which accepts exe version 2.7.0.0 and carries the 1.17 RVAs.

## Values re-derived for 1.17 (all verified against the 1.17 executable on disk)

| constant | 1.16.2 | 1.17 | evidence |
|---|---|---|---|
| SETBOSSBGM_RVA | 0xdb2ec0 | 0xdb4c20 | aobs_er.toml pattern (minus its changed cmp immediate) hits once; .pdata function start; same +0x1D60 shift as the other two; prologue keeps (rcx=controller, edx=param id, r8d=state) |
| SETAREABGM_RVA | 0xdadfe0 | 0xdafd40 | aobs_er.toml pattern hits once; .pdata start; this is the area-BGM resolver itself (rcx=CSSound, xmm1=dt) |
| GLOBAL_FIELDAREA_RVA | 0x3d691d8 | 0x3d6d248 | fromsoftware-rs rva_ww `field_area_ptr`; 248 RIP-relative refs; read by the resolver |
| GLOBAL_WORLDSOUNDMAN_RVA | 0x3d6f708 | 0x3d73778 | 84 RIP-relative refs (+0x4070 region shift; neighbours 2 and 4); read by the resolver |
| FieldArea +0x2c / +0xb6 / +0xf8 | same | same | resolver reads [rsi+0xb6], [rsi+0xf8]; +0x2c via a 2-instruction getter, compared on its top byte (area) == 61 -> lib.rs now does `(map_id >> 24) == 61` |
| WorldSoundMan +0x5c28 -> +0x364 | same | same | resolver: `mov rax,[rcx+0x5c28]; movzx eax,[rax+0x364]` |
| CSSound +0x435/+0x436/+0x2f0/+0x328 | same | same | resolver reads 0x435/0x436/0x2f0; +0x328 is passed to the controller Update (0xdb5f70) by the caller |
| BOSS_BGM_OFFSET 0x238 (105 x 32) | same | same | init: `lea rcx,[rbx+0x238]; mov r8d,0xD20; memset` (0xD20 = 105*32); object size 0x1658 |
| PLACE_TYPE_OFFSET 0xf58 (53 x 32) | same | same | init: `lea rcx,[rbx+0xf58]; mov r8d,0x6A0; memset` (0x6A0 = 53*32) |

The controller constructor (0xdb4630) is Arxan-obfuscated on disk; the two memsets above are relocated
fragments that are in the clear. Residual risk: a hook site or field only reached inside an encrypted region.

## Rebuild
```
source ~/.cargo/env
export PATH="<scratch>/wwise-build/bin:$PATH"   # llvm-lib shim (symlink to rustup's llvm-ar)
export CFLAGS="/FIstring.h"                     # libudis86-sys needs memset declared under clang-cl
cd yonder/unlock_wwise_states/eldenring && cargo +nightly xwin build --release --locked --target x86_64-pc-windows-msvc
```
Toolchain: rustc 1.100.0-nightly (2026-09-02), cargo-xwin 0.23.1, MSVC CRT 14.44 + Windows SDK 10.0.26100.
