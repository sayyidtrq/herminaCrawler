# Rencana: Membuktikan Key Process End-to-End di Dev

> Dibuat 2026-07-28 · Otoritas: [ADR-0001](../decisions/ADR-0001-ownership-inversion.md) · [ADR-0002](../decisions/ADR-0002-ai-execution-split.md) · [ADR-0003](../decisions/ADR-0003-crawl-execution-pull-queue.md)
> Tandai setiap klaim **[verified] / [assumption] / [blocked]**.

**Sasaran:** menunjukkan satu alur utuh yang bisa didemokan —
**tambah lokasi di OneBox → review Google ter-crawl → dianalisa AI → muncul sebagai tiket yang bisa ditindaklanjuti.**

Ini bukan membangun fitur baru. Sebagian besar kodenya sudah ada; yang belum ada adalah **bukti bahwa rantainya nyambung**.

---

## 1. Peta status tiap tahap

| # | Tahap | Status | Pemilik |
|---|---|---|---|
| 1 | Tambah lokasi di OneBox (tersimpan ke DB) | ✅ **[verified]** 28 Jul | OneBox |
| 2 | Crawler menarik worklist dari OneBox | ✅ **[verified]** `fetched:1, upserted:1` | VoC |
| 3 | **Crawl review Google untuk target itu** | ❓ **belum pernah dibuktikan** | **VoC** |
| 4 | Review tersimpan + dianalisa AI di VoC | ⚠️ kode ada, belum diuji untuk target baru | VoC |
| 5 | OneBox menarik review (delta) dari VoC | ⚠️ kode ada, **konfigurasi di dev belum benar** | OneBox |
| 6 | Review → Ticket + kategori + prioritas | ⚠️ kode ada **[verified di lokal]**, belum di dev | OneBox |
| 7 | Tampil di Dashboard / Reviews | ✅ **[verified]** | OneBox |

**Jalur kritis: tahap 3 → 5 → 6.** Tahap 3 adalah risiko terbesar dan harus diuji lebih dulu.

---

## 2. Analisis blocker

### B1 — Selenium & login Google di container *(KRITIS, tahap 3)*
Catatan lama: *"Selenium mode tidak jalan di container (butuh manual Google login GUI)"* **[assumption — perlu diverifikasi ulang]**.

Kalau masih berlaku, seluruh rencana otomatisasi (antrean M2, penjadwalan M4) berdiri di atas sesuatu yang belum tentu bisa dieksekusi tanpa manusia.

**Karena itu ini diuji PALING AWAL.** Gagal sekarang murah; gagal setelah scheduler jadi, mahal.

Kemungkinan hasil & konsekuensinya:
- **Bisa crawl tanpa login** → lanjut sesuai rencana.
- **Butuh sesi login yang bisa disimpan** → simpan profil browser/cookie, perpanjang masa berlaku, jadikan bagian runbook.
- **Wajib GUI tiap kali** → arsitektur berubah: crawl tidak bisa sepenuhnya otomatis. Perlu dibawa ke Pak Agung, dan ADR-0003 (penjadwalan otomatis) harus ditinjau.

### B2 — Connection VoC di dev menunjuk ke alamat yang salah *(tahap 5)*
Baris `977` (Hermina depok) mewarisi kredensial dari koneksi lama `959`, yang `Options`-nya berisi `{"Host":"space.datakelola.com","Url":"https://sp..."}` **[verified dari phpMyAdmin]**.

Itu **bukan** alamat API VoC. Tanpa `Url`, `api_mode`, dan `service_token` yang benar, OneBox tidak akan bisa menarik review — sekalipun crawling berhasil.

### B3 — Jaringan dev ⇄ crawler *(tahap 5)*
OneBox **lokal tidak bisa** menjangkau server crawler (`10.13.13.90` tertutup) **[verified]**. Jadi pengujian tahap 5–6 **harus dilakukan di dev**, bukan di laptop.

Dev (`10.13.13.42`) dan crawler (`10.13.13.90`) sama-sama di WireGuard — menurut Infra semestinya tersambung **[assumption — belum diuji dua arah]**.

### B4 — Letak eksekusi AI
ADR-0002: **parameter & kuota di OneBox, eksekusi AI di VoC**. Yang didemokan di OneBox adalah **hasil** analisa (sentimen, urgensi, kategori, ringkasan), bukan pemanggilan LLM-nya.

Perlu disepakati sebelum demo supaya narasinya tidak salah.

### B5 — Kuota/Benefit belum aktif
Kode `VOC_*` belum diregistrasi. Untuk demo tidak menghalangi, tapi artinya **pemakaian token AI belum dibatasi**.

---

## 3. Alur kerja & deployment

Pertanyaan yang sering muncul: *"apakah setiap uji coba harus push ke `feature/voc`?"* — **tergantung tahapnya.**

| Tahap diuji | Perlu deploy OneBox? | Alasan |
|---|---|---|
| 3 — crawl Google | **Tidak** | murni di server crawler, OneBox tidak terlibat |
| 4 — simpan + analisa di VoC | **Tidak** | idem |
| 2, 5, 6 — melibatkan OneBox | **Ya, di dev** | crawler & OneBox harus saling menjangkau; laptop tidak masuk jaringan itu |

**Alur perubahan kode OneBox** (aturan Pak Agung, 28 Jul):
```
koding di feature/DNGO19-3346  →  push  →  merge ke feature/voc  →  Jenkins auto-build + auto-migration  →  dev.onebox.co.id/feature/voc/
```
Tidak ada koding langsung di `feature/voc` — branch itu hanya untuk merge. PR mengikuti kebiasaan tim; yang wajib adalah **koding di branch DNGO**, karena itu yang naik ke release.

---

## 4. Pembagian kerja dua agen

### Agen VoC (Codex) — **jalan duluan, memblokir yang lain**

| ID | Tugas | Selesai bila |
|---|---|---|
| **X1** | **Buktikan crawl 1 target** (`Hermina depok`, place id dari worklist) di server. Catat: butuh login Google atau tidak, berapa lama, berapa review didapat. | Ada review baru tersimpan untuk target itu, atau kegagalan terdokumentasi dengan sebabnya |
| X2 | Pastikan review tersimpan dengan **`location_id` target hasil worklist** (bukan target lama) | Query DB menunjukkan review terikat ke lokasi yang benar |
| X3 | Jalankan analisa AI untuk review baru; laporkan `tokens_used` | Tiap review punya sentimen, urgensi, kategori |
| X4 | Pastikan `GET /api/integration/v1/reviews` mengembalikan review baru itu, cursor maju dengan benar | OneBox bisa menariknya secara delta |
| X5 | Sediakan pemicu crawl yang bisa dipanggil dari luar (CLI/endpoint), **non-blocking** | OneBox bisa memicu tanpa menunggu Selenium |

> X1 adalah **gerbang**. Kalau gagal, hentikan X2–X5 dan laporkan — arsitekturnya yang harus ditinjau, bukan dipaksakan.

### Agen OneBox (Claude)

| ID | Tugas | Selesai bila |
|---|---|---|
| **C1** | **Perbaiki Connection VoC di dev** — `Url`, `api_mode`, `service_token`, `company_id` (blocker B2). Kredensial **tidak lewat git** | `whoami` dari dev mengembalikan company yang benar |
| C2 | Jalankan ingest di dev: `voice_of_customer_system receive <connId>` | Review VoC masuk jadi Message/Ticket |
| C3 | Verifikasi `Options.location_map` memetakan lokasi VoC → `Location` OneBox | `Ticket.LocationId` terisi, bukan "Unknown" |
| C4 | Verifikasi hasil analisa mendarat di Ticket (sentimen, kategori, prioritas) | Dashboard menampilkan angka nyata, bukan 0/Netral semua |
| C5 | Halaman **Fetch Jobs** memicu crawl lewat X5 + menampilkan riwayat | Demo bisa dijalankan dari UI, bukan terminal |

### Urutan & titik temu
```
X1 (gerbang) ─┬─> X2 ─> X3 ─> X4 ─┐
              │                    ├─> C2 ─> C3 ─> C4 ─> demo
C1 (paralel) ─┴────────────────────┘
C5 menyusul (memoles demo)
```
C1 bisa dikerjakan **paralel** dengan X1 — tidak saling menunggu.

---

## 5. Skenario demo & kriteria sukses

**Yang ditunjukkan (dari UI, bukan terminal):**
1. Tambah cabang di OneBox → hanya butuh Nama + Google Place ID
2. Crawler menariknya sendiri (tunjukkan `refresh_worklist`)
3. Crawl berjalan → review Google masuk
4. Review muncul di **Reviews** lengkap dengan sentimen & urgensi
5. Review negatif menjadi **Tiket** yang bisa ditugaskan
6. Dashboard memperlihatkan cabang mana yang berisiko

**Kriteria sukses (harus terukur, bukan "kelihatan jalan"):**
- Minimal 1 cabang baru menempuh seluruh rantai tanpa langkah manual di sisi crawler
- Review tidak dobel saat proses diulang (idempotent)
- `Ticket.LocationId` terisi benar — bukan "Unknown"
- Minimal 1 review negatif menjadi tiket berstatus terbuka

**Yang jujur disebut sebagai belum jalan:** penjadwalan otomatis 3 window, antrean crawl, kuota AI, review kompetitor.

---

## 6. Rencana cadangan bila X1 gagal

Kalau Selenium tidak bisa jalan tanpa GUI:
1. **Jangan** memaksakan penjadwalan otomatis — itu menjanjikan sesuatu yang tidak bisa ditepati.
2. Demokan rantainya memakai review yang **sudah ada** di cache VoC (tahap 4–6 tetap nyata dan bernilai).
3. Angkat ke Pak Agung sebagai keputusan: crawl semi-otomatis dengan sesi yang diperbarui berkala, atau cari sumber data alternatif.
4. ADR-0003 bagian penjadwalan ditinjau ulang — bukan dibatalkan, tapi diberi prasyarat.

---

## 7. Yang dikerjakan lebih dulu

1. **X1** — uji crawl di server *(Codex, hari ini)*
2. **C1** — benahi Connection VoC di dev *(OneBox, paralel)*
3. Baru lanjut sesuai bagan di §4
