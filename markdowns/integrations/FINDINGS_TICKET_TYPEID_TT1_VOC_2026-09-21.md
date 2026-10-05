# Findings: tiket review VoC kembali TT1 (temuan Agung, dev 18 September)

Tanggal: 21 September 2026
Gejala: `Ticket.TypeId = 'TT1'` pada tiket review Google, seharusnya `TT3`.
Data: dev, ±20 baris LANUD (MessageId 139468–139523), `MediaId = GBUSINESS`.

---

## Ringkasan

Kode pembentuk tiket **tidak** kehilangan perbaikannya — itu sudah gua
pastikan, bukan diasumsikan. Yang terbukti rusak adalah **migrasi
penambal TT1 → TT3**: ia dipatok ke provider `PVD97`, padahal provider VoC
sudah `PVD99` sejak 5 Agustus. Migrasi itu berjalan, memproses nol baris,
lalu melaporkan sukses.

Untuk tiket **baru** masih ada dua kemungkinan yang belum bisa dipisahkan
tanpa data dev. SQL pembedanya ada di bagian 4.

---

## 1. Petunjuk yang paling menentukan ada di layar Agung

Dua kolom rusak **bersamaan**, dan itu bukan kebetulan:

| Kolom | Nilai | Seharusnya |
|---|---|---|
| `TypeId` | `TT1` | `TT3` |
| `LocationId` | `NULL` | id lokasi |

Keduanya diisi oleh jalur yang sama. Tiket yang lahir lewat jalur VoC
mendapat dua-duanya; tiket yang lahir di luar jalur itu tidak mendapat
satu pun. Jadi pertanyaannya bukan "kenapa TypeId salah" melainkan
**"kenapa tiket ini tidak dikenali sebagai tiket VoC"**.

Ini juga menyambung ke to-do yang masih terbuka: *"Lokasi review tidak
dipetakan sejak gerbang tiket ditutup"*. Kemungkinan besar itu gejala yang
sama, bukan dua bug terpisah.

---

## 2. Yang sudah gua PASTIKAN (bukan dugaan)

**Kode perbaikannya ada, di semua branch yang relevan.**
`Ticketing::tiketVoc()` lahir 10 Agustus (`5e7054ae49`). Gua periksa 11
branch: seluruh branch VoC (`feature/voc`, `release/1.123.0`, 3385, 3387,
3392, 3420, 3511, 3513, 3529, 3549) memilikinya. Yang **tidak** punya hanya
`origin/develop` dan `origin/development`.

> Kalau dev ternyata menayangkan build dari `develop`, seluruh teka-teki
> selesai di sini. Ini yang pertama harus dipastikan.

**Provider di seed sudah benar.** Dugaan awal gua: koneksi LANUD ditulis
dengan provider lama sehingga `tiketVoc()` gagal. Gua cek
`VOC_SEED_LOKASI_TNIAU_DEV.sql` — seed itu memakai `PVD99` di seluruh
INSERT dan bahkan menyalin kredensial dari koneksi `PVD99` yang sudah
berjalan. **Dugaan ini gugur.** Tetap perlu diverifikasi di DB (BLOK A),
karena seed bukan satu-satunya cara koneksi lahir.

**Aturan TT3 di `Ticketing::build()`:**

```php
if ($this->tiketVoc($message)) {          // → TT3
} elseif ($this->common->getSetting('messaging') == 'Media') {  // → TT3
} else {                                   // → TT1
}
```

`tiketVoc()` mensyaratkan **tiga** hal sekaligus:
1. `$message->ConnectionId` tidak kosong
2. `$message->MediaId === 'GBUSINESS'` ✅ (terlihat di layar Agung)
3. `Connection.ProviderId === 'PVD99'`

Gagal salah satu → TT1.

---

## 3. Yang TERBUKTI rusak: migrasi penambal tidak menambal apa pun

`app/migrations/1786200000000000_1_123_0/Ticket.php`:

```php
private const PROVIDER_1785900000000000 = 'PVD97';   // ← provider lama

UPDATE Ticket t
  JOIN Message m ON m.ObjectId = t.Id AND m.ObjectName = 'Ticket'
  JOIN Connection c ON c.Id = m.ConnectionId AND c.ProviderId = ?   -- 'PVD97'
   SET t.TypeId = 'TT3'
 WHERE t.TypeId <> 'TT3'
```

Riwayat nilai provider:

| Tanggal | Perubahan |
|---|---|
| 18 Jun | VoC memakai `PVD97` (slot milik IKS) |
| 5 Agu | `PVD97` → `PVD98` |
| 5 Agu | `PVD98` → `PVD99` (hari yang sama) |
| 10 Agu | `tiketVoc()` lahir |

Koneksi VoC hari ini `PVD99`. `JOIN ... c.ProviderId = 'PVD97'`
menghasilkan **nol baris**. Migrasinya tetap `commit`, mencetak
`dipanggil … selesai — TT3: 0 dari 0`, dan keluar sukses.

**Konsekuensi:** tiket TT1 lama tidak akan pernah diperbaiki oleh migrasi,
di environment mana pun — dev, staging, maupun produksi. Dan karena
laporannya sukses, tidak ada yang curiga.

Diperparah satu hal lagi: ada rencana menandai versi `1786200000000000`
sebagai *sudah diterapkan* di dev **tanpa menjalankannya**. Kalau itu sudah
dilakukan, penambalnya memang tidak pernah jalan sama sekali.

`Reference.php` di folder migrasi yang sama juga masih membuat Reference
`PVD97` bernama "Voc" — folder itu secara keseluruhan tertinggal di era
sebelum 5 Agustus.

---

## 4. Yang belum bisa dipisahkan tanpa data dev

Untuk tiket **baru** tersisa dua kemungkinan. Keduanya menghasilkan gejala
yang identik, jadi harus dipisahkan dengan data, bukan dengan argumen.

**H1 — tiketnya lama.** Dibuat sebelum 10 Agustus (atau sebelum build
ber-`tiketVoc` tayang di dev). Wajar TT1, dan memang tugas migrasilah
memperbaikinya — yang ternyata no-op (bagian 3).

**H2 — `tiketVoc()` gagal saat tiket lahir.** Entah `ConnectionId` belum
terisi pada objek Message saat `build()` dipanggil, atau `ProviderId`
koneksinya bukan `PVD99`.

### SQL pembeda — jalankan di DB dev

```sql
-- BLOK A — apakah koneksi LANUD benar PVD99?
SELECT c.Id, c.ProviderId, c.MediaId, c.SiteId,
       JSON_UNQUOTE(JSON_EXTRACT(c.Options,'$.location.branch_name')) AS lokasi,
       COUNT(m.Id) AS jml_message
  FROM Connection c
  LEFT JOIN Message m ON m.ConnectionId = c.Id
 WHERE c.MediaId = 'GBUSINESS'
   AND JSON_UNQUOTE(JSON_EXTRACT(c.Options,'$.location.branch_name')) LIKE '%LANUD%'
 GROUP BY c.Id, c.ProviderId, c.MediaId, c.SiteId, lokasi
 ORDER BY c.Id;
-- ProviderId selain PVD99 -> H2 terbukti, dan itu akar masalahnya.
```

```sql
-- BLOK B — tiket TT1 itu lahir kapan, dan koneksinya apa?
SELECT t.Id AS TicketId, t.TypeId, t.LocationId, t.CreateDate,
       m.Id AS MessageId, m.ConnectionId, m.MediaId,
       c.ProviderId
  FROM Ticket t
  JOIN Message m ON m.ObjectId = t.Id AND m.ObjectName = 'Ticket'
  LEFT JOIN Connection c ON c.Id = m.ConnectionId
 WHERE m.Id BETWEEN 139468 AND 139523
 ORDER BY t.CreateDate;
-- CreateDate sebelum 2026-08-10  -> H1 (tiket lama)
-- CreateDate sesudah, ProviderId = PVD99, ConnectionId terisi -> H2 varian
--   "ConnectionId kosong saat build", perlu ditelusuri di pipeline processing.
-- ConnectionId NULL di baris Message -> H2 terbukti langsung.
```

```sql
-- BLOK C — seberapa luas, dan apakah ada yang TT3 (pembanding sehat)
SELECT c.ProviderId, t.TypeId,
       SUM(t.LocationId IS NULL) AS lokasi_kosong,
       COUNT(*) AS jml,
       MIN(t.CreateDate) AS paling_awal,
       MAX(t.CreateDate) AS paling_akhir
  FROM Ticket t
  JOIN Message m ON m.ObjectId = t.Id AND m.ObjectName = 'Ticket'
  JOIN Connection c ON c.Id = m.ConnectionId
 WHERE m.MediaId = 'GBUSINESS'
 GROUP BY c.ProviderId, t.TypeId
 ORDER BY c.ProviderId, t.TypeId;
-- Kalau ada baris PVD99/TT3 berdampingan dengan PVD99/TT1, bandingkan
-- rentang tanggalnya: itu memisahkan H1 dari H2 tanpa perlu menebak.
```

```sql
-- BLOK D — apakah migrasi penambal tercatat pernah jalan?
SELECT * FROM Migration
 WHERE Version LIKE '1786200000000000%' OR Version LIKE '%1_123_0%';
-- Nama tabelnya mungkin berbeda; sesuaikan dengan tabel pencatat migrasi.
```

---

## 5. Saran solusi

### 5.1 Perbaiki migrasi penambal — wajib, tidak bergantung hasil SQL

Ini sudah terbukti rusak. Dua pilihan:

**(a) Tidak mematok provider sama sekali** — lebih tahan banting. Kenali
tiket review dari `MediaId` Message plus keberadaan kunci VoC di
`MessageContent.Meta`, bukan dari angka provider yang ternyata bisa
berpindah tiga kali dalam dua bulan.

**(b) Patok ke `\Provider::VOC`** alih-alih string literal, supaya
perpindahan berikutnya ikut terbawa otomatis.

Gua condong ke **(a)**: nilai provider sudah membuktikan dirinya tidak
stabil, dan migrasi yang memeriksa sifat data lebih jujur daripada migrasi
yang memeriksa nomor slot. Tapi (b) jauh lebih kecil risikonya kalau mau
cepat.

Apa pun yang dipilih: migrasinya harus **berteriak, bukan diam**, kalau
menyentuh nol baris. Yang membuat bug ini hidup lama persis karena ia
melaporkan sukses.

### 5.2 Tambal data yang sudah terlanjur (perlu persetujuan owner)

Setelah BLOK A–C menjelaskan cakupannya, satu `UPDATE` terbatas pada
tiket yang terbukti berasal dari koneksi VoC. **Jangan** dijalankan sebelum
BLOK C dibaca — kalau ada tiket kanal lain ikut terjaring, kita memindahkan
tiket orang lain ke layar Media Monitoring.

### 5.3 Kalau H2 yang terbukti

Perbaiki di `Ticketing::tiketVoc()` atau pada pemanggilnya, **bukan** dengan
menambah pengoreksi baru. Saat ini sudah ada dua mekanisme untuk satu
keputusan:

1. `Ticketing::tiketVoc()` — berlaku untuk semua jalur
2. `VocController::pastikanTipeMediaMonitoring()` — hanya jalur eskalasi HTTP

Yang kedua tidak menolong tiket yang lahir dari worker. Menambah yang
ketiga hanya akan memperbanyak tempat yang harus benar bersamaan.

### 5.4 Pastikan dulu branch yang tayang di dev

Paling murah dan paling mungkin menyelesaikan semuanya: `origin/develop`
tidak punya `tiketVoc` sama sekali. Kalau dev menayangkan build dari sana,
tidak ada yang perlu didebug lebih jauh — tinggal tayangkan branch VoC.

---

## 6. Yang perlu gua minta

- Hasil BLOK A–D dari DB dev.
- Nama branch/tag image yang sedang tayang di dev.

Dengan dua itu, H1 vs H2 selesai tanpa tebakan, dan gua bisa langsung
tulis perbaikannya.

---

## Catatan kejujuran

Bagian 3 (migrasi no-op) **terbukti dari kode**, tidak perlu DB.
Bagian 4 **belum terbukti** — MySQL tidak hidup di stack lokal gua hari ini
(`.env` tertimpa merge `hotfix/1.122.1` sehingga menunjuk host `xtradb`
yang tidak ada), jadi gua tidak bisa memeriksa data dev sendiri. Semua yang
gua sebut "terbukti" di atas berasal dari kode dan riwayat git, dan gua
sudah menyebutkan dugaan mana yang gugur setelah diperiksa.
