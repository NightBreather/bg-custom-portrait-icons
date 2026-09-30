# PPUI and custom portrait icons — "wrong / all-the-same icon" in the character record

This document records the cause, the measurements and three possible fixes for a specific
bug: **custom portrait icons (`STATDESC.2DA` / `STATES.BAM`) appearing wrong — usually all
showing the same (Haste) icon — in the character record ("Affects") list** when a UI
replacement mod is installed, in particular **Pocket Play UI++ (PPUI)**.

General method and recipes: [`README.md`](../README.md). This document is a
**case study / issue report**.

- **Measured on:** Baldur's Gate: Enhanced Edition **v2.7.3.0** (GOG), `lang/tr_TR`, Wine/Linux.
- **UI mod examined:** PPUI **v2.31** (`Renegade0/PocketPlayUI`), `UI.MENU` = 618,941 bytes.
- **Reference (vanilla) `UI.MENU`:** 474,758 bytes (extracted from the game BIF with `COPY_EXISTING ~ui.menu~`).

---

## 1. Symptom

A custom portrait icon (your own 13×13 BAM + `STATDESC.2DA` column 3 + `opcode 142`) installs correctly:

- **Sidebar (next to the portrait):** icon shows **correctly**.
- **Character record ("Affects") list, vanilla UI:** icon shows **correctly**.
- **Same install, PPUI:** the record list shows the **wrong** icon; with several custom icons,
  **all of them show the same** icon (Haste).

So the problem is not on the game's side (`STATDESC` / `STATES.BAM`) — it is in **how the UI
draws that list**.

---

## 2. How the engine resolves a portrait icon

The icon request is `opcode 142`; `parameter2 = N` is the icon index. The engine resolves `N` as:

| Condition | Source |
|-----------|--------|
| `STATDESC.2DA` row `N`, **column 3 contains a BAM name** | **that BAM**, used verbatim (resref ≤ 8 chars, no last-letter substitution) |
| column 3 is **empty (`****`)** | `STATES.BAM`, **cycle `N + 65`** |

- The BAM V1 header stores the cycle count in a **single byte** → at most 255 cycles →
  `N + 65 ≤ 254` → **`N ≤ 189`**.
- When column 3 is set, `STATES.BAM` is never consulted (this path has no index ceiling).

The record the engine hands to Lua (`characters[id].statusEffects[k]`) carries:

```
bam       → the resolved BAM (the col-3 name, or 'STATES')
current   → the cycle/frame to display inside that BAM
strRef    → the state text
helpStrRef
```

**Key point:** the record-list icon is **not drawn by the UI** — the engine resolves it and the
UI merely binds the values. Vanilla `ui.menu` (2.7) does exactly that:

```lua
-- vanilla ui.menu, lines ~780-810 (statusEffects list)
bam       lua "statusEffects[rowNumber].bam"       -- resolved BAM (col-3 name or 'STATES')
sequence  lua "statusEffects[rowNumber].current"   -- cycle inside that BAM
text      lua "Infinity_FetchString(statusEffects[rowNumber].strRef)"
```

That is why custom `STATDESC` icons and `N ≥ 190` indices do work in the record screen on
**vanilla**.

---

## 3. What PPUI actually does (code evidence, v2.31)

PPUI does not patch the game UI; it ships its **own complete `UI.MENU`** (based on a pre-2.6
revision). It **comments out** vanilla's list above (`ppui.UI.MENU` ~1132-1164) and moves the
state icons into one combined list. There:

```lua
-- ppui.UI.MENU, lines 1285-1286
bam      'STATES'                              -- HARD-CODED! the per-effect bam is never used
sequence lua "listItems[rowNumber][1]"
```

State rows are built like this (lines 595-606):

```lua
for k, v in pairs(characters[currentID].statusEffects) do
    if v.current == 0 then --haste exception
        table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef)})
    else
        table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef)})
    end
end
```

The resulting chain:

1. Because `bam 'STATES'` is **hard-coded**, the BAM in `STATDESC` column 3 is **never read**;
   the icon is drawn from `STATES.BAM` instead.
2. For single-frame custom BAMs the engine reports `current = 0`, which hits PPUI's
   `v.current == 0 → 103` ("haste exception") branch → **every icon is drawn as STATES cycle 103
   (Haste)**. That is the "always the same icon" symptom.
3. The very same code exists in PPUI's own `UI-backup2.6.MENU`, so this comes from **PPUI's
   design**, not from the 2.6→2.7 port.

> Note: because of this, PPUI also loses `N ≥ 190` vanilla indices and vanilla col-3 icons
> (e.g. `BOOT01D`) in the record list — not just custom ones.

---

## 4. Measured data (v2.7.3.0)

### 4.1 `STATDESC.2DA` (vanilla + the rows we added)

**211 rows** total (id 0..210). Columns: `<id>  DESCRIPTION(strref)  BAM_FILE`.

- **id 0..187** → `BAM_FILE = ****` (empty) → `STATES.BAM`, cycle `id + 65`.
- **id 188..206** → named BAMs; most are **multi-frame icon sheets**:

| id | BAM | frames |
|----|-----|--------|
| 188 | `SPWI417D` | 1206 |
| 189 | `SPPR150D` | 1206 |
| 190 | `SPPR750D` | 1206 |
| 191 | `SPSH004D` | 1161 |
| 192 | `OHTMPS2D` | 1206 |
| 193 | `BDMAREK`  | **1** |
| 194 | `SPWM101D` | 1174 |
| 195 | `BOOT01D`  | **1** |
| 196-203 | `spwi510d` | 1193 (8 rows share one sheet) |
| 204 | `SPCL238D` | 1212 |
| 205 | `SPDM105D` | 1212 |
| 206 | `SPPR111D` | 1187 |
| 207-210 | `nbmoon1`..`nbmoon4` | 1 (our test mod) |

This table proves column 3 overrides `STATES.BAM` for **every** index, not only `N ≥ 191`
(ids 188-190 are `< 191` yet carry a custom BAM).

### 4.2 `STATES.BAM`

| Field | Value |
|-------|-------|
| `frames` | **179** |
| `cycles` | **255** (BAM V1: `0x0A`, one byte) |
| lookup table | **257 u16** (cycle → frame mapping) |
| format | BAM V1, `13×13`, `cx=0 cy=13` (STATES standard) |

Structure is "**cycle = icon, frame = animation step**"; for `****` rows the icon is cycle
`N + 65`. The cycle ceiling (`≤ 254`) is what produces the `N ≤ 189` limit.

### 4.3 There is **no** `states.2da`

`COPY_EXISTING ~states.2da~` was tried → `resource not found`. So "adding a row to STATES"
means **adding a frame/cycle to `STATES.BAM`**; there is no separate 2DA.

---

## 5. Fix options

| Option | What it does | Vanilla | PPUI | Shared-file risk | Index ceiling |
|--------|--------------|:-------:|:----:|:----------------:|:-------------:|
| **A** | `STATDESC` col-3 + own BAM | ✅ | ❌ | none | none |
| **B** | Put the icon in `STATES.BAM`, col-3 `****` | ✅ | ✅ | **yes** (`STATES.BAM`) | `N ≤ 189` |
| **C** | Patch PPUI's `UI.MENU` | ✅ | ✅ | none (UI file) | none |

- **A:** the preferred general method (see `README.md`). Breaks in "STATES-hard-coding" UIs like PPUI.
- **B:** fixes it with **no UI code change**; because the icon really lives in `STATES.BAM`,
  *every* UI draws it correctly. Cost: overwriting the shared `STATES.BAM`.
- **C:** fixes the code; patches that UI's file (install order matters).

---

## 6. Option B — step by step (no code change)

1. **Pick a free index** (`N ≤ 189`; on BG:EE roughly `179…187` are free).
2. Add a **13×13 frame** to `STATES.BAM` and point **cycle `N + 65`** at it.
   (`example/lib/states_icon_add.py` does this.)
3. Leave `STATDESC.2DA` row `N`'s **column 3 empty (`****`)** (column 2 = text strref).
4. Apply `opcode 142, parameter2 = N` to the effect.

Then:

- **Vanilla:** `bam = 'STATES'`, `sequence = N + 65` → our icon ✅
- **PPUI:** `bam 'STATES'` (hard-coded) + `sequence = N + 65` (≠ 0, so it does not fall into 103) → our icon ✅

> This is exactly what `example/setup-portrait_icon.tp2` does (indices 179..182).

---

## 7. Option C — patching PPUI's `UI.MENU` (3 changes)

For people who want to keep PPUI as-is (no index ceiling, no shared-file edit) and only fix the
record list:

```weidu
COPY_EXISTING ~UI.MENU~ ~override~
  // 1-2) put the engine-provided BAM into the row data (status rows only)
  REPLACE_TEXTUALLY ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef), 'STATES'})~
  REPLACE_TEXTUALLY ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef), v.bam})~
  // 3) use it in the icon column (icon-less rows fall back to STATES)
  REPLACE_TEXTUALLY ~bam            'STATES'~
                    ~bam lua "listItems[rowNumber][3] or 'STATES'"~
  BUT_ONLY
```

Notes:

- The patch must be installed **after** PPUI (WeiDU order).
- It modifies a game (UI) file, so keep backups/install log.
- You do not need to remove the `v.current == 0` branch; the col-3 path uses `v.bam` directly.
- Better still: report the fix to the mod author — the engine already provides the data
  (`statusEffects[k].bam`) the fix needs.

---

## 8. Verification

1. **Identify the active UI:** inside `override/UI.MENU`
   - contains `bam lua "statusEffects[rowNumber].bam"` → fine,
   - contains hard-coded `bam 'STATES'` → this document's bug applies.
2. **In-game observation:** grant several custom-icon effects at once, open the character record
   → "Affects". If they all show the same (Haste) icon, the `v.current == 0 → 103` branch is firing.
3. **Log check:** no `Demanded resource but failed to find anything!` in the game log.
4. **Optional deep diagnosis:** add a temporary
   `Infinity_Log("bam=" .. tostring(v.bam) .. " cur=" .. tostring(v.current))`, run it from a
   temporary tp2 *outside* the install directory (using `--game`), open the record screen and read
   the engine's **actual** `bam`/`current` values.

---

## 9. Open points / limitations

- For the **col-3 (named BAM) path**, the exact value of `current` (row id `N` vs `N + 65`) was
  not measured. What is certain: for **single-frame** col-3 BAMs `current = 0` (the Haste symptom
  proves it). For the `STATES` path `current = N + 65`.
- Measurements are for **v2.7.3.0**; other patches may change `STATES.BAM` / `STATDESC`.
- **Option B** overwrites the shared `STATES.BAM` → if another mod overwrites it too, cycles may
  be lost depending on install order. It has a hard `N ≤ 189` ceiling.
- A BAM V2 header stores the cycle count as a dword (theoretically >255) but its frames reference
  **PVRZ** textures; not tried here (see `README.md` §Limitations).

---

## 10. Appendix: read a `STATES.BAM` header (Python, quick diagnosis)

```python
import struct
d = open('states.bam', 'rb').read()
frames, cycles, comp = struct.unpack_from('<HBB', d, 8)
frameoff, paloff, lookoff = struct.unpack_from('<III', d, 0x0c)
print(f"frames={frames} cycles={cycles} compidx={comp}")
print(f"frameoff={frameoff} paloff={paloff} lookoff={lookoff} size={len(d)}")
# frame entry (12 B): w h cx cy dataoff
for i in (0, frames - 1):
    w, h, cx, cy, off = struct.unpack_from('<HHhhI', d, frameoff + i * 12)
    print(f"frame[{i}] {w}x{h} cx={cx} cy={cy} dataoff=0x{off:x}")
```

---

## License

MIT — see [`LICENSE`](../LICENSE).
