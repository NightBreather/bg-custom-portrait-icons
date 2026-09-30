# Custom portrait icons in Baldur's Gate: Enhanced Edition

### …that appear on **both** the sidebar **and** the character‑record "Affects" list — *without* touching `STATES.BAM`.

Turkish version: [`README.tr.md`](README.tr.md)

Deep dive (case study: the PPUI record-list icon bug, measurements and every fix): [`docs/ppui-record-icons.md`](docs/ppui-record-icons.md)

---

## Summary

A custom portrait/state icon can be added with **`STATDESC.2DA` alone**: put your own
BAM in the row's 3rd column and point an effect's `opcode 142` at that row. In the
**vanilla UI** the icon then shows **both** next to the portrait (sidebar) **and** in
the character‑record "Affects" list. No `STATES.BAM` editing is required — so there is
no 255‑sequence ceiling and no risk of overwriting a file other mods also patch.

The widely‑repeated claim *"a custom icon shows on the sidebar but not in the record
screen"* is **not a vanilla limitation**. It is caused by **UI‑replacement mods** that
ship their own, older `UI.MENU` and hardcode `STATES.BAM` for that list. One such mod
is documented below, together with a 3‑line fix.

## How the engine resolves a portrait icon

A portrait icon is requested by an effect with **opcode `142`**, where
`parameter2 = N` is the icon index. For a given index `N`:

| Condition | Icon drawn from |
|-----------|-----------------|
| `STATDESC.2DA` row `N`, column 3 names a BAM | **that BAM** — used **as‑is** (no character rewriting). Works for **any** `N`. |
| column 3 is empty (`****`) | `STATES.BAM`, **cycle `N + 65`** (BAM V1: 1‑byte cycle count → 255 cycles → `N ≤ 189`) |

**The 3rd column overrides `STATES.BAM` for any index, not only for `N ≥ 191`.** Vanilla
itself does this: `STATDESC` rows 188‑190 (`SPWI417D`, `SPPR150D`, `SPPR750D`) carry
custom BAMs even though they are below 191.

The icon in the **record list** is resolved by the **engine, not the UI**: for every
active state the engine exposes a record with the *already resolved* BAM and cycle,
and the vanilla `ui.menu` simply binds them:

```lua
-- character record: "statusEffects" list (vanilla 2.7)
bam       lua "statusEffects[rowNumber].bam"      -- the col-3 BAM, or 'STATES'
sequence  lua "statusEffects[rowNumber].current"  -- the cycle inside that BAM
text      lua "Infinity_FetchString(statusEffects[rowNumber].strRef)"
```

That is the whole "fix": the UI asks the engine *which* BAM and *which* cycle to use
instead of computing `index + 65` itself. Because of this, custom `STATDESC` icons and
indices above 189 work in the record screen too, in vanilla.

## Recommended recipe (`STATDESC` column 3 only)

1. **Ship a 13×13 BAM.** State/portrait icons are small single‑cycle BAMs. Vanilla's
   own `STATDESC` BAMs are shipped as **BAMC** (compressed BAM); a plain
   `BAM V1` file with one 13×13 frame also loads. Do **not** reuse a hotbar spell
   icon (those are much larger — e.g. 90×90 — and will be drawn huge).
2. **Add one row to `STATDESC.2DA`** (or reuse an unused one):
   * column 2 = your text strref,
   * column 3 = **your BAM resref** (≤ 8 chars, used exactly as written).
3. **Point the effect at it:** `opcode 142`, `parameter2 = N`.

```weidu
// minimal: one custom state icon via STATDESC column 3
COPY ~mymod/icons/MYICON.bam~ ~override/MYICON.bam~

OUTER_SET my_ref = RESOLVE_STR_REF (@100)   // e.g. "My Custom State"
COPY_EXISTING ~statdesc.2da~ ~override~
  COUNT_2DA_ROWS 3 rows
  FOR (i = 0; i < rows; i += 1) BEGIN
    READ_2DA_ENTRY i 0 3 key
    PATCH_IF (~%key%~ STRING_EQUAL ~186~) BEGIN
      SET_2DA_ENTRY i 1 3 my_ref
      SET_2DA_ENTRY i 2 3 ~MYICON~
    END
  END
  PRETTY_PRINT_2DA
BUT_ONLY
```

Result with the vanilla UI: sidebar ✅ + record list ✅.

## Alternative recipe (`STATES.BAM`, only needed for older UI mods)

If you must support a UI that hardcodes `STATES.BAM` (see below):

* pick an unused index `N ≤ 189` (in BG:EE the rows around `160…187` are unused),
* append a 13×13 frame to `STATES.BAM` and repoint sequence `N + 65`
  (`example/lib/states_icon_add.py` does this),
* keep `STATDESC` row `N` column 3 **empty (`****`)**,
* `opcode 142, parameter2 = N`.

Caveats: hard ceiling at `N ≤ 189`; you are rewriting a **shared** file (other mods'
sequences can be lost, and a mod installed after you can erase yours); it breaks if
the install order changes. The `STATDESC` col‑3 route has none of these problems.

## UI mods that break the record icon (and the fix)

**Pocket‑play UI++ (PPUI, by Pecca)** — a *total conversion* UI for phones/tablets
(first release ~March 2020; it inherits from Pecca's older *Dragonspear UI++*). It does
not patch the game's UI: it **ships its own complete `UI.MENU`**, built on a
**pre‑patch‑2.6** base. Consequences:

* its record list **hardcodes** `bam 'STATES'` and passes the engine's cycle as the
  sequence, so any `STATDESC` col‑3 icon (and any index ≥ 190) loses its icon there;
* it also contains a `v.current == 0 → draw sequence 103` special case, which is why
  affected icons show the **Haste** icon in the record screen;
* the newer `.bam`‑based list still exists in that file, but **commented out**.

Evidence: the vanilla 2.7 `ui.menu` is 474,758 bytes and uses
`bam lua "statusEffects[rowNumber].bam"`; PPUI's is 619,334 bytes, uses
`bam 'STATES'`, and lacks newer APIs present in vanilla (`Infinity_ClipboardCopy`,
`Infinity_GetFileExists`).

**Fix (3 replacements in PPUI's `UI.MENU`)** — route the merged list through the
engine's `bam` field:

```weidu
COPY_EXISTING ~UI.MENU~ ~override~
  // push the per-effect BAM into the row data (status rows only)
  REPLACE_TEXTUALLY ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef), v.bam})~
  REPLACE_TEXTUALLY ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef), v.bam})~
  // use it for the icon column (fall back to STATES for non-icon rows)
  REPLACE_TEXTUALLY ~bam            'STATES'~
                    ~bam lua "listItems[rowNumber][3] or 'STATES'"~
  BUT_ONLY
```

(Keep a backup; the patch must be installed **after** PPUI. Better still: report it to
the mod author — the data the fix needs is already exposed by the engine.)

## Limits and experimental findings

Tested on BG:EE v2.7.3.2 with the **vanilla** UI unless noted.

### 1) Index resolution

| Path | Format | Max index | Sidebar | Record ("Affects") |
|------|--------|-----------|---------|--------------------|
| `STATES.BAM` (no col‑3 BAM) | V1 (inline pixels) | **189** | ✅ | ✅ |
| `STATDESC` col‑3 BAM | BAMC or BAM V1 | no practical limit | ✅ | ✅ **in vanilla**; ❌ with UIs that hardcode `STATES` (see above) |
| `STATES.BAM` | V2 (PVRZ texture) | ~600+ (theoretical) | ? | ? (untested) |

### 2) Why `STATES.BAM` stops at 189

* A BAM **V1** header stores the cycle (sequence) count in a **single byte** at `0x0A`
  → at most **255 cycles**.
* Since icons map to cycle `N + 65`, `N + 65 ≤ 254` → **`N ≤ 189`** (verified: index 78
  draws cycle 143).
* With a `STATDESC` col‑3 BAM the index is irrelevant — `STATES.BAM` is not consulted.

### 3) The `STATDESC` BAM path

* The col‑3 name is used **verbatim** — unlike SPL icons, the engine does **not**
  rewrite the last character (no `B`/`C` variants needed).
* `STATDESC` row `N` must **exist** for the text/icon to be meaningful (row number = index).
* Vanilla uses this path for spell‑specific states (e.g. `SPWI417D`, `SPPR150D`,
  `SPPR750D`, `BOOT01D`, `dwicon1`) and for Shaman‑specific icons.

### 4) Why BAM V2 is not a solution yet

* A **BAM V2** header stores the cycle count as a **dword** → >255 cycles are possible
  in principle, but V2 frames reference **PVRZ** textures and need a PVR
  (PVRTC/ETC) encoder. Not tested here.

### 5) Practical conclusion

* **Preferred:** `STATDESC` col‑3 + your own 13×13 BAM → sidebar ✅ record ✅, no shared
  file touched, no index ceiling.
* **Only if a UI mod forces it:** `STATES.BAM` at `N + 65` with col‑3 empty, `N ≤ 189`.
* Diagnosing a missing record icon: check whether the active `UI.MENU` uses
  `statusEffects[rowNumber].bam` (fine) or hardcodes `bam 'STATES'` (broken).

### 6) Related notes

* **Resrefs are limited to 8 characters** (SPL/BAM/…); longer names crash the engine.
* The `states_icon_add.py` here can be extended to **multi‑tone (ramp)** icons; a ramp
  allocates a few palette slots per icon (the vanilla `STATES.BAM` has ~179 free slots).

## Files

```
example/
  setup-portrait_icon.tp2   minimal WeiDU component demonstrating the STATES.BAM method
  lib/states_icon_add.py    STATES.BAM frame/sequence helper
  icons/                    example 13x13 source art (grayscale PNG)
```

## License

MIT — see [`LICENSE`](LICENSE). Example icons in `example/icons/` are from
[game‑icons.net](https://game-icons.net) (CC BY 3.0); see `example/icons/CREDITS.txt`.
