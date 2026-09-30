# PPUI ve özel portre ikonları — karakter kaydında "yanlış/aynı ikon" sorunu

Bu belge; BG:EE'de **`STATDESC.2DA` / `STATES.BAM` tabanlı özel portre ikonlarının**, kendi
`UI.MENU`'sunu getiren arayüz modlarında (özellikle **Pocket Play UI++ / PPUI**) **karakter
kaydı "Etkiler" listesinde yanlış — çoğu zaman hep aynı (Haste) — görünmesi** sorununun
nedenini, ölçümlerini ve üç ayrı çözüm yolunu kaydeder.

Genel yöntem ve tarifler için: [`README.tr.md`](../README.tr.md). Bu belge bir **vaka
incelemesi / sorun kaydıdır**.

- **Ölçüm ortamı:** Baldur's Gate: Enhanced Edition **v2.7.3.0** (GOG), `lang/tr_TR`, Wine/Linux.
- **İncelenen UI modu:** PPUI **v2.31** (`Renegade0/PocketPlayUI`), `UI.MENU` = 618.941 bayt.
- **Referans (vanilla) `UI.MENU`:** 474.758 bayt (oyunun BIF'inden `COPY_EXISTING ~ui.menu~` ile çıkarıldı).

---

## 1. Semptom

Özel bir portre ikonu (kendi 13×13 BAM'in + `STATDESC.2DA` 3. kolon + `opcode 142`) doğru kurulur:

- **Sidebar (portre yanı):** ikon **doğru** görünür.
- **Karakter kaydı ("Etkiler") listesi, vanilla UI:** ikon **doğru** görünür.
- **Aynı kurulum, PPUI ile:** kayıt listesinde ikon **yanlış** görünür; birden çok özel ikon
  varsa **hepsi aynı** ikonu (Haste) gösterir.

Yani sorun oyunun (`STATDESC`/`STATES.BAM`) tarafında değil, **UI'nin o listeyi nasıl çizdiğinde**.

---

## 2. Motor bir portre ikonunu nasıl çözer

İkon isteği `opcode 142`'dir; `parameter2 = N` ikon indeksidir. Motor `N`'i şöyle çözer:

| Koşul | Kaynak |
|-------|--------|
| `STATDESC.2DA` satır `N`, **3. kolon bir BAM adı** içeriyor | **o BAM** birebir kullanılır (resref ≤ 8 karakter, son harf değiştirilmez) |
| 3. kolon **boş (`****`)** | `STATES.BAM`, **dizi (cycle) `N + 65`** |

- BAM V1 başlığında dizi sayısı **1 bayttır** → en fazla 255 dizi → `N + 65 ≤ 254` → **`N ≤ 189`**.
- 3. kolon doluysa `STATES.BAM`'e hiç bakılmaz (bu yol indeks tavanından bağımsızdır).

Motordan Lua'ya gelen kayıt (`characters[id].statusEffects[k]`) şu alanları taşır:

```
bam       → çözülen BAM (col-3 adı ya da 'STATES')
current   → o BAM içinde gösterilecek dizi/frame
strRef    → durumun metni
helpStrRef
```

**Kritik nokta:** karakter kaydı listesindeki ikonu **UI çizmez** — motor çözer, UI yalnızca
bağlar. Vanilla `ui.menu` (2.7) tam olarak bunu yapar:

```lua
-- vanilla ui.menu, satır ~780-810 (statusEffects listesi)
bam       lua "statusEffects[rowNumber].bam"       -- çözülmüş BAM (col-3 ya da 'STATES')
sequence  lua "statusEffects[rowNumber].current"   -- o BAM içindeki dizi
text      lua "Infinity_FetchString(statusEffects[rowNumber].strRef)"
```

Bu yüzden custom `STATDESC` ikonları ve `N ≥ 190` indeksler **vanilla'da** kayıt ekranında çalışır.

---

## 3. PPUI'de tam olarak ne oluyor (kod kanıtı, v2.31)

PPUI oyunun UI'sini patch'lemez; **kendi komple `UI.MENU`'sunu** getirir (tabanı 2.6 öncesi).
Vanilla'nın yukarıdaki listesini **yorum satırına almıştır** (`ppui.UI.MENU` ~1132-1164) ve
durum ikonlarını ana birleşik listeye taşımıştır. Orada:

```lua
-- ppui.UI.MENU, satır 1285-1286
bam      'STATES'                              -- SABİT! efekte özel bam hiç kullanılmaz
sequence lua "listItems[rowNumber][1]"
```

Durum satırları da `listItems`e şöyle eklenir (satır 595-606):

```lua
for k, v in pairs(characters[currentID].statusEffects) do
    if v.current == 0 then --haste exception
        table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef)})
    else
        table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef)})
    end
end
```

Sonuç zinciri:

1. **`bam 'STATES'` sabit** olduğu için `STATDESC` 3. kolonundaki BAM **hiç okunmaz**;
   ikon STATES.BAM'den çizilmeye çalışılır.
2. Tek frame'li custom BAM'lerde motor `current = 0` verir → PPUI'nin
   `v.current == 0 → 103` ("haste exception") dalına düşer → **her ikon STATES dizi 103
   (Haste)** olarak çizilir. Gözlenen "hep aynı ikon" bundan ibarettir.
3. Aynı dosya PPUI'nin kendi `UI-backup2.6.MENU` dosyasında da birebir aynıdır → bu
   **2.6→2.7 portundan değil, PPUI'nin tasarımından** gelir.

> Not: PPUI bu davranışı nedeniyle yalnız custom ikonları değil, `N ≥ 190` vanilla indekslerini
> ve `STATDESC` col-3 taşıyan *vanilla* ikonlarını (ör. `BOOT01D`) da kayıt listesinde kaybeder.

---

## 4. Ölçülen veri (v2.7.3.0)

### 4.1 `STATDESC.2DA` (vanilla + bizim eklediğimiz satırlar)

Toplam **211 satır** (id 0..210). Kolonlar: `<id>  DESCRIPTION(strref)  BAM_FILE`.

- **id 0..187** → `BAM_FILE = ****` (boş) → `STATES.BAM` (dizi `id + 65`).
- **id 188..206** → isimli BAM'ler; çoğu **çok frame'li ikon sayfasıdır**:

| id | BAM | frame sayısı |
|----|-----|--------------|
| 188 | `SPWI417D` | 1206 |
| 189 | `SPPR150D` | 1206 |
| 190 | `SPPR750D` | 1206 |
| 191 | `SPSH004D` | 1161 |
| 192 | `OHTMPS2D` | 1206 |
| 193 | `BDMAREK`  | **1** |
| 194 | `SPWM101D` | 1174 |
| 195 | `BOOT01D`  | **1** |
| 196-203 | `spwi510d` | 1193 (8 satır aynı sayfayı paylaşır) |
| 204 | `SPCL238D` | 1212 |
| 205 | `SPDM105D` | 1212 |
| 206 | `SPPR111D` | 1187 |
| 207-210 | `nbmoon1`..`nbmoon4` | 1 (bizim test modumuz) |

Bu tablo, 3. kolonun **`N ≥ 191` için değil, her indekste** `STATES.BAM`'i geçersiz kıldığını
kanıtlar (id 188-190 `< 191` olmasına rağmen özel BAM taşır).

### 4.2 `STATES.BAM`

| Alan | Değer |
|------|-------|
| `frames` | **179** |
| `cycles` | **255** (BAM V1: `0x0A`, 1 bayt) |
| lookup tablosu | **257 u16** (cycle → frame eşlemesi) |
| format | BAM V1, `13×13`, `cx=0 cy=13` (STATES standardı) |

"**cycle = ikon, frame = animasyon karesi**" yapısındadır; `****` satırlar için ikon,
cycle `N + 65`'tir. Cycle tavanı (`≤ 254`) `N ≤ 189` sınırını doğurur.

### 4.3 `states.2da` **yoktur**

`COPY_EXISTING ~states.2da~` denenmiştir → `resource not found`. Yani "STATES'e yeni satır
eklemek" = **`STATES.BAM`'e yeni frame/cycle eklemek** demektir; ayrı bir 2DA yoktur.

---

## 5. Çözüm yolları

| Yol | Ne yapar | Vanilla | PPUI | Paylaşılan dosya riski | İndeks tavanı |
|-----|----------|:------:|:----:|:----------------------:|:-------------:|
| **A** | `STATDESC` col-3 + kendi BAM | ✅ | ❌ | yok | yok |
| **B** | İkonu `STATES.BAM`'e koy, col-3 `****` | ✅ | ✅ | **var** (STATES.BAM) | `N ≤ 189` |
| **C** | PPUI'nin `UI.MENU`'sunu yamala | ✅ | ✅ | yok (UI dosyası) | yok |

- **A:** Tercih edilen genel yöntem (bkz. `README.tr.md`). PPUI gibi "STATES sabitleyen" UI'larda
  kayıt listesi bozulur.
- **B:** UI **kodu değişmeden** çözer; ikon gerçekten STATES.BAM'de olduğu için *her* UI doğru
  çizer. Bedeli: paylaşılan `STATES.BAM`'i ezmek.
- **C:** Kodu düzeltir; ilgili UI'nin dosyasını yamalar (kurulum sırası önemli).

---

## 6. Yol B — adım adım (kod değişmeden)

1. **Boş bir indeks seç** (`N ≤ 189`; BG:EE'de `179…187` civarı boştur).
2. `STATES.BAM`'e **13×13 frame** ekle ve **dizi `N + 65`**'i ona yönlendir.
   (`example/lib/states_icon_add.py` bu işi yapar.)
3. `STATDESC.2DA` satır `N`'in **3. kolonunu boş (`****`)** bırak (2. kolon = metin strref).
4. Efekte `opcode 142, parameter2 = N` ver.

Böylece:

- **Vanilla:** `bam = 'STATES'`, `sequence = N + 65` → bizim ikon ✅
- **PPUI:** `bam 'STATES'` (sabit) + `sequence = N + 65` (≠ 0, dolayısıyla 103'e düşmez) → bizim ikon ✅

> Bu yol `example/setup-portrait_icon.tp2` bileşeninin yaptığı şeydir (indeksler 179..182).

---

## 7. Yol C — PPUI'nin `UI.MENU`'sunu yamalama (3 değişiklik)

PPUI'yi olduğu gibi kullanmak isteyip (indeks tavanı/paylaşılan dosya istemeyip) yalnız
kayıt listesini düzeltmek isteyenler için:

```weidu
COPY_EXISTING ~UI.MENU~ ~override~
  // 1-2) durum satırlarına, motorun verdiği BAM'i 3. eleman olarak koy
  REPLACE_TEXTUALLY ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef), 'STATES'})~
  REPLACE_TEXTUALLY ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef), v.bam})~
  // 3) ikon kolonunda onu kullan (ikonsuz satırlar STATES'e düşsün)
  REPLACE_TEXTUALLY ~bam            'STATES'~
                    ~bam lua "listItems[rowNumber][3] or 'STATES'"~
  BUT_ONLY
```

Notlar:

- Yama **PPUI'den sonra** kurulmalıdır (WeiDU sırası).
- Oyun dosyasını (UI dosyasını) değiştirdiği için yedek/log takibi gerekir.
- `v.current == 0` özel durumunun kaldırılması gerekmez; col-3 yolu zaten `v.bam`i kullanır.
- Daha temizi: düzeltmeyi mod yazarına bildirmek — ihtiyaç duyulan veriyi (`statusEffects[k].bam`)
  motor zaten sağlıyor.

---

## 8. Doğrulama

1. **Aktif UI'yi tespit et:** `override/UI.MENU` içinde
   - `bam lua "statusEffects[rowNumber].bam"` geçiyorsa → sorun yok,
   - `bam 'STATES'` (sabit) geçiyorsa → bu belgedeki sorun var.
2. **Oyun içi gözlem:** aynı anda birkaç custom ikonlu efekt ver, karakter kaydı → "Etkiler"
   listesini aç. Hepsi aynı ikonu (Haste) gösteriyorsa → `v.current == 0 → 103` dalı tetikleniyor.
3. **Log kontrolü:** oyun log'unda `Demanded resource but failed to find anything!` olmamalı.
4. **İsteğe bağlı derin teşhis:** geçici bir `Infinity_Log("bam=" .. tostring(v.bam) .. " cur=" .. tostring(v.current))`
   satırı ekleyip (kurulum dizininin dışında, `--game` ile çalıştırılan geçici bir tp2 ile) kayıt
   ekranını açarak motordan gelen **gerçek** `bam`/`current` değerlerini oku.

---

## 9. Açık noktalar / sınırlar

- **Col-3 (isimli BAM) yolunda `current`'ın tam değeri** (satır id `N` mi, `N + 65` mi)
  ölçülmedi. Kesin gözlem: **tek frame'li** col-3 BAM'lerde `current = 0`'dır (Haste semptomu
  bunu kanıtlar). `STATES` yolu için `current = N + 65`'tir.
- Ölçümler **v2.7.3.0** içindir; farklı yamalarda `STATES.BAM`/`STATDESC` değişebilir.
- **Yol B** paylaşılan `STATES.BAM`'i ezer → başka bir mod da eziyorsa kurulum sırasına göre
  diziler kaybolabilir. `N ≤ 189` sert tavanı vardır.
- BAM V2 dizi sayısını dword tutar (teorik olarak >255) ancak frame'leri **PVRZ** dokudur;
  burada denenmedi (bkz. `README.tr.md` §Sınırlar).

---

## 10. Ek: `STATES.BAM` başlığını okuma (Python, hızlı teşhis)

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

## Lisans

MIT — bkz. [`LICENSE`](../LICENSE).
