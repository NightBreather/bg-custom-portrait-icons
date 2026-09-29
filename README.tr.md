# Baldur's Gate: Enhanced Edition'da özel portre ikonları

### …`STATES.BAM`'e hiç dokunmadan, hem **portre yanında** hem **karakter kaydı "Etkiler" listesinde** görünen ikonlar.

İngilizce sürüm: [`README.md`](README.md)

---

## Özet

Özel bir portre/durum ikonu **yalnız `STATDESC.2DA` ile** eklenebilir: satırın 3. kolonuna
kendi BAM'ini koy ve `opcode 142`'yi o satıra yönelt. **Vanilla UI**'da ikon hem portre
yanında (sidebar) hem de karakter kaydı "Etkiler" listesinde görünür. `STATES.BAM`'i
düzenlemek **gerekmez** — böylece 255 dizi tavanı ve başka modların da patch'lediği
paylaşılan bir dosyayı ezme riski ortadan kalkar.

Sık tekrarlanan *"özel ikon portrede görünür ama kayıt ekranında görünmez"* iddiası
**vanilla bir sınırlama değildir**. Sebep, kendi **eski `UI.MENU`'sunu** getirip o listede
`STATES.BAM`'i sabitleyen **UI değiştirme modlarıdır**. Aşağıda böyle bir mod ve 3 satırlık
düzeltmesi belgelenmiştir.

## Motor bir portre ikonunu nasıl çözer

Portre ikonunu isteyen şey `opcode 142`'dir; `parameter2 = N` ikon indeksidir. Bir `N` için:

| Koşul | İkonun kaynağı |
|-------|----------------|
| `STATDESC.2DA` satır `N`, 3. kolon bir BAM adı içeriyor | **o BAM** — **birebir** kullanılır (son harf değiştirilmez). **Her** `N` için geçerlidir. |
| 3. kolon boş (`****`) | `STATES.BAM`, **dizi `N + 65`** (BAM V1: dizi sayısı 1 bayt → 255 dizi → `N ≤ 189`) |

**3. kolon, yalnız `N ≥ 191` için değil, *her* indekste `STATES.BAM`'i geçersiz kılar.**
Vanilla da bunu yapar: `STATDESC` satır 188‑190 (`SPWI417D`, `SPPR150D`, `SPPR750D`) 191'in
altında olmalarına rağmen özel BAM taşır.

**Kayıt listesindeki** ikonu **UI değil, motor** çözer: her aktif durum için motor,
çözülmüş BAM ve diziyi içeren bir kayıt verir; vanilla `ui.menu` bunları sadece bağlar:

```lua
-- karakter kaydı: "statusEffects" listesi (vanilla 2.7)
bam       lua "statusEffects[rowNumber].bam"      -- col-3 BAM'i ya da 'STATES'
sequence  lua "statusEffects[rowNumber].current"  -- o BAM içindeki dizi
text      lua "Infinity_FetchString(statusEffects[rowNumber].strRef)"
```

Bütün "çözüm" bundan ibaret: UI, `index + 65`'i kendisi hesaplamak yerine motora
*hangi BAM, hangi dizi* diye sorar. Bu yüzden custom `STATDESC` ikonları ve 189 üstü
indeksler de vanilla'da kayıt ekranında çalışır.

## Önerilen tarif (yalnız `STATDESC` 3. kolon)

1. **13×13 bir BAM ship et.** Durum/portre ikonları küçük, tek dizili BAM'lerdir.
   Vanilla'nın kendi `STATDESC` BAM'leri **BAMC** (sıkıştırılmış) gelir; tek 13×13
   frame'li düz `BAM V1` de yüklenir. **Hotbar büyü ikonunu kullanma** (onlar çok daha
   büyüktür, ör. 90×90 → kocaman çizilir).
2. **`STATDESC.2DA`'ya bir satır ekle** (ya da boş bir satırı kullan):
   * 2. kolon = metin strref'in,
   * 3. kolon = **BAM resref'in** (≤ 8 karakter; birebir kullanılır).
3. **Efekti ona yönelt:** `opcode 142`, `parameter2 = N`.

```weidu
// asgari: STATDESC 3. kolon ile tek custom durum ikonu
COPY ~mymod/icons/MYICON.bam~ ~override/MYICON.bam~

OUTER_SET my_ref = RESOLVE_STR_REF (@100)   // ör. "Özel Durumum"
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

Vanilla UI ile sonuç: sidebar ✅ + kayıt listesi ✅.

## Alternatif tarif (`STATES.BAM`; yalnız eski UI modları için gerekir)

`STATES.BAM`'i sabitleyen bir UI'yi desteklemen gerekiyorsa (aşağıya bak):

* `N ≤ 189` olan boş bir indeks seç (BG:EE'de `160…187` civarı boştur),
* `STATES.BAM`'e 13×13 frame ekle ve `N + 65` dizisini ona yönelt
  (`example/lib/states_icon_add.py` bunu yapar),
* `STATDESC` satır `N` 3. kolonunu **boş (`****`)** bırak,
* `opcode 142, parameter2 = N`.

Sakıncalar: `N ≤ 189` sert tavanı; **paylaşılan** bir dosyayı ezmen (başka modların
dizileri kaybolabilir, senden sonra kurulan bir mod seninkini silebilir); kurulum sırası
bozulursa çalışmaz. `STATDESC` col‑3 yolunda bu sorunların hiçbiri yok.

## Kayıt ikonunu bozan UI modları (ve düzeltmesi)

**Pocket‑play UI++ (PPUI, Pecca)** — telefon/tablet için *total conversion* bir UI
(ilk sürüm ~Mart 2020; Pecca'nın daha eski *Dragonspear UI++*'ından miras alır). Oyunun
UI'sini patch'lemez: **kendi komple `UI.MENU`'sunu** getirir; tabanı **2.6 yaması
öncesi**dir. Sonuçlar:

* kayıt listesi `bam 'STATES'` diye **sabitler** ve motorun dizisini sequence olarak verir
  → her `STATDESC` col‑3 ikonu (ve `N ≥ 190`) kayıt ekranında ikonunu kaybeder;
* dosyada ayrıca `v.current == 0 → sequence 103 çiz` özel durumu vardır; etkilenen
  ikonların kayıt ekranında **Haste** ikonu göstermesinin sebebi budur;
* `.bam`'e dayalı yeni liste o dosyada hâlâ mevcuttur ama **yorum satırıdır**.

Kanıt: vanilla 2.7 `ui.menu` 474.758 bayt ve `bam lua "statusEffects[rowNumber].bam"`
kullanır; PPUI'ninki 619.334 bayt, `bam 'STATES'` kullanır ve vanilla'da olan yeni
API'lerden yoksundur (`Infinity_ClipboardCopy`, `Infinity_GetFileExists`).

**Düzeltme (PPUI'nin `UI.MENU`'sunda 3 değişiklik)** — birleşik listeyi motorun `bam`
alanına bağla:

```weidu
COPY_EXISTING ~UI.MENU~ ~override~
  // efekt başına BAM'i satır verisine koy (yalnız status satırları)
  REPLACE_TEXTUALLY ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {103, '    ' .. Infinity_FetchString(v.strRef), v.bam})~
  REPLACE_TEXTUALLY ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef)})~
                    ~table.insert(listItems, {v.current, '    ' .. Infinity_FetchString(v.strRef), v.bam})~
  // ikon kolonunda onu kullan (ikonsuz satırlar STATES'e düşsün)
  REPLACE_TEXTUALLY ~bam            'STATES'~
                    ~bam lua "listItems[rowNumber][3] or 'STATES'"~
  BUT_ONLY
```

(Yedek tut; yama **PPUI'den sonra** kurulmalıdır. Daha iyisi: mod yazarına bildir —
düzeltmenin ihtiyaç duyduğu veriyi motor zaten veriyor.)

## Sınırlar ve deneysel bulgular

Aksi belirtilmedikçe BG:EE v2.7.3.2 ve **vanilla** UI ile test edildi.

### 1) İndeks çözümü

| Yol | Format | Maks indeks | Sidebar | Kayıt ("Etkiler") |
|-----|--------|-------------|---------|-------------------|
| `STATES.BAM` (col‑3 BAM yok) | V1 (gömülü piksel) | **189** | ✅ | ✅ |
| `STATDESC` col‑3 BAM | BAMC veya BAM V1 | pratikte sınır yok | ✅ | ✅ **vanilla'da**; `STATES` sabitleyen UI'larda ❌ (yukarıya bak) |
| `STATES.BAM` | V2 (PVRZ doku) | ~600+ (teorik) | ? | ? (denenmedi) |

### 2) `STATES.BAM` neden 189'da duruyor

* BAM **V1** başlığında dizi sayısı `0x0A`'da **tek bayt**tır → en fazla **255 dizi**.
* İkonlar dizi `N + 65`'e eşlendiği için `N + 65 ≤ 254` → **`N ≤ 189`** (doğrulandı:
  indeks 78 → dizi 143).
* `STATDESC` col‑3 BAM varsa indeks önemsizdir — `STATES.BAM`'e hiç bakılmaz.

### 3) `STATDESC` BAM yolu

* 3. kolondaki ad **birebir** kullanılır — SPL ikonlarından farklı olarak motor son
  harfi **değiştirmez** (`B`/`C` varyantları gerekmez).
* Metin/ikonun anlamlı olması için `STATDESC` satırı `N` **var olmalıdır** (satır no = indeks).
* Vanilla bu yolu büyüye özel durumlar için kullanır (`SPWI417D`, `SPPR150D`,
  `SPPR750D`, `BOOT01D`, `dwicon1`) ve Shaman'a özel ikonlar için.

### 4) BAM V2 neden henüz çözüm değil

* **BAM V2** başlığı dizi sayısını **dword** tutar → teorik olarak >255 dizi mümkündür;
  ama V2 frame'leri **PVRZ** dokuya başvurur ve PVR (PVRTC/ETC) encoder gerekir. Burada
  denenmedi.

### 5) Pratik sonuç

* **Tercih edilen:** `STATDESC` col‑3 + kendi 13×13 BAM'in → sidebar ✅ kayıt ✅, paylaşılan
  dosyaya dokunulmaz, indeks tavanı yok.
* **Yalnız bir UI modu zorluyorsa:** `STATES.BAM` `N + 65`'e, col‑3 boş, `N ≤ 189`.
* Kayıt ikonu görünmüyorsa: aktif `UI.MENU` `statusEffects[rowNumber].bam` kullanıyor mu
  (sorun yok) yoksa `bam 'STATES'` sabitliyor mu (bozuk) — bunu kontrol et.

### 6) İlgili notlar

* **Resref'ler 8 karakterle sınırlıdır** (SPL/BAM/…); daha uzun adlar motoru çökertir.
* Buradaki `states_icon_add.py`, tek renk yerine **çok tonlu (ramp)** ikonları da
  destekleyecek şekilde genişletilebilir; ramp ikon başına birkaç palet slotu ayırır
  (vanilla `STATES.BAM`'de ~179 boş slot var).

## Dosyalar

```
example/
  setup-portrait_icon.tp2   STATES.BAM yöntemini gösteren asgari WeiDU bileşeni
  lib/states_icon_add.py    STATES.BAM frame/dizi yardımcısı
  icons/                    örnek 13x13 kaynak sanat (gri tonlu PNG)
```

## Lisans

MIT — bkz. [`LICENSE`](LICENSE). `example/icons/` içindeki örnek ikonlar
[game‑icons.net](https://game-icons.net) (CC BY 3.0); bkz. `example/icons/CREDITS.txt`.
