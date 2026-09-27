# Custom portrait icons in Baldur's Gate: Enhanced Edition

### …that appear on **both** the sidebar **and** the character‑record "Affects" list.

Turkish version: [`README.tr.md`](README.tr.md)

---

## The problem

Adding a custom portrait icon the "usual" way (a BAM in `STATDESC.2DA`, column 3)
makes the icon show up **next to the portrait / on the sidebar**, but the
**character‑record screen** keeps drawing a generic icon (Haste). Many mods —
including large ones — live with this limitation. This repository documents the
mechanism and a small recipe that makes custom icons work in **both** places.

## How the engine resolves a portrait icon

A portrait icon is requested by an effect with **opcode `142`**, where
`parameter2 = N` is the icon index. The engine resolves `N` from two sources:

| index `N`      | drawn from |
|----------------|------------|
| `0 … 190`      | `STATES.BAM`, **sequence `N + 65`** |
| `191 …`        | the BAM named in `STATDESC.2DA`, column 3 (`BAM_FILE`) |

The **character‑record "Affects" list** (`ui.menu`, Lua) always uses the
`STATES.BAM` path: for every active effect it takes the icon index and draws
`STATES.BAM` sequence `index + 65`:

```lua
for k, v in pairs(characters[currentID].statusEffects) do
    if v.current == 0 then -- haste exception
        table.insert(listItems, {103, ...})
    else
        table.insert(listItems, {v.current, ...})
    end
end
```

If `STATDESC.2DA` holds a BAM in column 3 for that index, the record screen still
tries that BAM and, when it cannot render it there, falls back to the generic
Haste icon. That is exactly why a `STATDESC` BAM alone shows on the sidebar but
not in the record.

## The working recipe

1. **Pick an unused index `N` in the range `0 … 190`.**
   In BG:EE the rows `160 … 187` of `STATDESC.2DA` are unused (`-1 ****`), so
   `N = 160 … 187` is safe. (These are single‑frame status icons, so overwriting
   their `STATES.BAM` sequence does not affect any real state.)

2. **Put your art inside `STATES.BAM` at sequence `N + 65`.**
   Append a new 13×13 frame and repoint that sequence to it. The helper
   `example/lib/states_icon_add.py` does this automatically.

3. **In `STATDESC.2DA` set row `N`:** column 2 = your text strref,
   column 3 = **`****`** — it **must stay empty**. (This is the crucial step.)

4. **Point the effect at the icon:** opcode `142`, `parameter2 = N`.

The icon is then drawn from `STATES.BAM` on the sidebar **and** in the record.

## Tooling

`example/lib/states_icon_add.py` appends 13×13 frames to a vanilla `STATES.BAM`
and repoints the chosen sequences:

```bash
weidu --biff-get states.bam                 # extract the vanilla STATES.BAM
python3 example/lib/states_icon_add.py states.bam override/states.bam \
        179:icons/shield.png:3aa0ff  180:icons/spider.png:b400dc
```

* The PNGs must be 8‑bit grayscale (`colortype 0`); they are downscaled to 13×13.
* The optional `RRGGBB` suffix tints the icon.
* Only the produced `states.bam` (plus the `STATDESC.2DA` rows and the opcode 142
  assignments) is needed at runtime.

## Minimal, formal WeiDU example

See [`example/setup-portrait_icon.tp2`](example/setup-portrait_icon.tp2).

## Limits and experimental findings

Everything below is the result of tests that probe the engine's actual limits
(BG:EE v2.7.3.2).

### 1) Index resolution and limit table

| Path | Format | Max index | Sidebar (portrait) | Record ("Affects") |
|------|--------|-----------|--------------------|--------------------|
| `STATES.BAM` | V1 (inline pixels) | **189** | ✅ | ✅ |
| `STATDESC.2DA` col-3 BAM | any | high (tested to 600) | ✅ | ❌ falls back to Haste |
| `STATES.BAM` | V2 (PVRZ texture) | ~600+ (theoretical) | ? | ? (untested) |

### 2) Why `STATES.BAM` stops at 189

- In a **BAM V1** header the cycle (sequence) count is a **single byte** at `0x0A`
  → at most **255 sequences**.
- Since icons map to sequence `N + 65`, `N + 65 ≤ 254` → **`N ≤ 189`**.
- The vanilla `ui.menu` (see `PATCH20.BIF`) always asks the record screen for
  `states.bam` sequence `index + 65`; for `N ≥ 190` that sequence does not exist
  → generic Haste icon.

### 3) The `STATDESC` BAM path (sidebar only)

- `opcode 142, parameter2 = N` with `N ≥ 191` makes the **sidebar** draw the BAM
  named in `STATDESC.2DA` column 3.
- **Test:** distinct icons at indices 160…600 all rendered **without issues** on
  the sidebar; `STATDESC.2DA` was extended to 600 rows with **no crash**. The
  record screen does not use this path (shows Haste instead).
- Adding rows to `STATDESC.2DA` alone (without icons) is also safe (tested to 601 rows).

### 4) Why BAM V2 is not a solution yet

- A **BAM V2** header stores the cycle count as a **dword** → >255 sequences are
  possible in principle.
- However V2 frames reference **PVRZ** textures (`MOSxxxx.PVRZ`); there are no
  inline pixels. Producing a V2 `STATES.BAM` therefore needs a **PVR
  (PVRTC/ETC) encoder**. Not tested here.

### 5) Practical conclusion

- To make an icon appear in **both** the sidebar and the record screen: put the
  art in `STATES.BAM` at sequence `N+65` and keep `STATDESC.2DA` row `N` column 3
  **empty (`****`)**.
- Safe usable range: **`160 … 189`** (recommended: `164 … 189`, since `160…163`
  and `188…189` may be occupied in some setups) → **~26 icons**.

### 6) Related notes

- **Resrefs are limited to 8 characters** (SPL/BAM/…); longer names crash the engine.
- The `states_icon_add.py` here can be extended to support **multi-tone (ramp)**
  icons instead of a single colour; a ramp allocates a few palette slots per icon
  (the vanilla `STATES.BAM` has ~179 free slots).

## Files

```
example/
  setup-portrait_icon.tp2   minimal WeiDU component demonstrating the method
  lib/states_icon_add.py    STATES.BAM frame/sequence helper
  icons/                    example 13x13 source art (grayscale PNG)
```

## License

MIT — see [`LICENSE`](LICENSE). Example icons in `example/icons/` are from
[game‑icons.net](https://game-icons.net) (CC BY 3.0); see `example/icons/CREDITS.txt`.
