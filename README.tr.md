# Baldur's Gate: Enhanced Edition'da özel portre ikonları

### …hem **sidebar'da** hem de **karakter kayıt penceresinin "Etkiler" listesinde** görünen.

İngilizce sürüm: [`README.md`](README.md)

---

## Sorun

Özel bir portre ikonunu "alışıldık" yolla eklemek (`STATDESC.2DA` 3. sütuna bir BAM
koymak) ikonu **portrenin yanında / sidebar'da** gösterir; ancak **karakter kayıt
penceresi** jenerik bir ikon (Haste) çizmeye devam eder. Büyük modlar dahil birçok
mod bu sınırlamayla yaşar. Bu depo, mekanizmayı ve özel ikonları **iki yerde de**
çalıştıran küçük bir tarifi belgeler.

## Motor bir portre ikonunu nasıl çözer

Bir portre ikonu, **opcode `142`** kullanan bir efektle istenir; burada
`parameter2 = N` ikon indeksidir. Motor `N`'i iki kaynaktan çözer:

| indeks `N`     | çizildiği kaynak |
|----------------|------------------|
| `0 … 190`      | `STATES.BAM`, **sequence `N + 65`** |
| `191 …`        | `STATDESC.2DA` 3. sütununda (`BAM_FILE`) adı geçen BAM |

**Karakter kayıt penceresinin "Etkiler" listesi** (`ui.menu`, Lua) her zaman
`STATES.BAM` yolunu kullanır: her aktif efekt için ikon indeksini alıp
`STATES.BAM` sequence `indeks + 65`'i çizer:

```lua
for k, v in pairs(characters[currentID].statusEffects) do
    if v.current == 0 then -- haste exception
        table.insert(listItems, {103, ...})
    else
        table.insert(listItems, {v.current, ...})
    end
end
```

Eğer `STATDESC.2DA` o indeks için 3. sütunda bir BAM taşıyorsa, kayıt ekranı yine
o BAM'ı çizmeye çalışır ve orada çizemeyince jenerik Haste ikonuna düşer. Bu
yüzden yalnızca `STATDESC` BAM'ı eklemek sidebar'da görünür ama kayıt penceresinde
görünmez.

## Çalışan tarif

1. **`0 … 190` aralığında kullanılmayan bir indeks `N` seç.**
   BG:EE'de `STATDESC.2DA`'nın `160 … 187` satırları kullanılmıyor (`-1 ****`),
   bu yüzden `N = 160 … 187` güvenlidir. (Bunlar tek çerçeveli durum ikonlarıdır;
   `STATES.BAM` sequence'lerini değiştirmek gerçek bir durumu etkilemez.)

2. **Art'ını `STATES.BAM` içine, sequence `N + 65`'e koy.**
   Yeni bir 13×13 çerçeve ekle ve o sequence'i ona yönlendir. `example/lib/states_icon_add.py`
   yardımcı script'i bunu otomatik yapar.

3. **`STATDESC.2DA`'da `N` satırını ayarla:** 2. sütun = metin strref'in,
   3. sütun = **`****`** — **boş kalmalı**. (Kritik adım budur.)

4. **Efekti ikona yönlendir:** opcode `142`, `parameter2 = N`.

Böylece ikon hem sidebar'da hem kayıt penceresinde `STATES.BAM`'dan çizilir.

## Araç

`example/lib/states_icon_add.py`, vanilla `STATES.BAM`'a 13×13 çerçeveler ekler ve
seçilen sequence'leri bunlara yönlendirir:

```bash
weidu --biff-get states.bam                 # vanilla STATES.BAM'i çıkar
python3 example/lib/states_icon_add.py states.bam override/states.bam \
        179:icons/shield.png:3aa0ff  180:icons/spider.png:b400dc
```

* PNG'ler 8-bit gri tonlamalı (`colortype 0`) olmalı; 13×13'e indirgenir.
* İsteğe bağlı `RRGGBB` soneki ikonu renklendirir.
* Çalışma anında yalnızca üretilen `states.bam` (artı `STATDESC.2DA` satırları ve
  opcode 142 atamaları) gerekir.

## Basit, formal WeiDU örneği

Bkz. [`example/setup-portrait_icon.tp2`](example/setup-portrait_icon.tp2).

## Sınırlar ve deneysel bulgular

Aşağıdakiler, motorun gerçek sınırlarını ölçen testlerin sonucudur (BG:EE v2.7.3.2).

### 1) İndeks çözümü ve sınır tablosu

| Yol | Biçim | Max indeks | Sidebar (portre) | Kayıt ekranı ("Etkiler") |
|-----|-------|-----------|------------------|--------------------------|
| `STATES.BAM` | V1 (inline piksel) | **189** | ✅ | ✅ |
| `STATDESC.2DA` 3. kolon BAM | herhangi | yüksek (600 test edildi) | ✅ | ❌ Haste'e düşer |
| `STATES.BAM` | V2 (PVRZ doku) | ~600+ (teorik) | ? | ? (test edilemedi) |

### 2) `STATES.BAM` neden 189'da bitiyor

- BAM **V1** başlığında dizi (cycle) sayısı `0x0A` offsetinde **1 byte**'tır → en çok **255 dizi**.
- İkon eşlemesi `dizi = N + 65` olduğundan `N + 65 ≤ 254` → **`N ≤ 189`**.
- Vanilla `ui.menu` (bkz. `PATCH20.BIF`) kayıt ekranında **her zaman** `states.bam` dizi
  `index + 65`'i ister; `N ≥ 190` için o dizi yok → jenerik Haste ikonu.

### 3) `STATDESC` BAM yolu (yalnız sidebar)

- `opcode 142, parameter2 = N` ve `N ≥ 191` → sidebar `STATDESC.2DA` 3. kolondaki BAM'ı çizer.
- **Test:** 160…600 arası ayrı ikonlar sidebar'da **sorunsuz göründü**; `STATDESC.2DA`
  600 satıra kadar uzatıldı, **çökme olmadı**. Kayıt ekranı bu yolu kullanmaz (Haste).
- `STATDESC.2DA`'ya yalnızca satır eklemek (ikon olmadan) da güvenlidir (601 satır test edildi).

### 4) BAM V2 neden şimdilik çözüm değil

- BAM **V2** başlığında dizi sayısı **dword**'dür → 255 üstü diziler mümkündür.
- Ancak V2 çerçeveleri **PVRZ** dokularına (`MOSxxxx.PVRZ`) başvurur; inline piksel yoktur.
  Bu yüzden V2 bir `STATES.BAM` üretmek **PVR (PVRTC/ETC) encoder** gerektirir. Test edilmedi.

### 5) Pratik sonuç

- İkonun **hem sidebar hem kayıt ekranında** görünmesi için: ikonu `STATES.BAM`'e
  `dizi N+65` olarak koy ve `STATDESC.2DA` satır `N`'in 3. sütununu **`****` bırak**.
- Kullanılabilir güvenli aralık: **`160 … 189`** (önerilen: `164 … 189`, çünkü
  `160…163` ve `188…189` belirli kurulumlarda dolu olabilir) → **~26 ikon**.

### 6) İlgili notlar

- **Resref'ler en fazla 8 karakterdir** (SPL/BAM/…). Daha uzun adlar motoru çökertir.
- Bu depodaki `states_icon_add.py`, tek renk yerine **çok tonlu (ramp)** ikonları da
  destekleyecek şekilde genişletilebilir; ramp için ikon başına birkaç palet slotu
  ayrılır (vanilla `STATES.BAM`'de ~179 boş slot vardır).

## Dosyalar

```
example/
  setup-portrait_icon.tp2   yöntemi gösteren minimal WeiDU bileşeni
  lib/states_icon_add.py    STATES.BAM çerçeve/sequence yardımcısı
  icons/                    örnek 13x13 kaynak art (gri tonlamalı PNG)
```

## Lisans

MIT — bkz. [`LICENSE`](LICENSE). `example/icons/` içindeki örnek ikonlar
[game‑icons.net](https://game-icons.net) kaynaklıdır (CC BY 3.0); bkz.
`example/icons/CREDITS.txt`.
