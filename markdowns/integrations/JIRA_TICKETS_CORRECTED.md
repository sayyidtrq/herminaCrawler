  ## VoC OneBox — Daftar Ticket Jira (Final, sesuai board asli)

> **Update:** nomor ticket di bawah adalah **nomor asli dari Jira** (dikonfirmasi via screenshot board), menggantikan placeholder `DNGO19-XXXX` di draft sebelumnya.
> **Keputusan baru:**
> - Restrukturisasi menu navigasi VoC (3 grup: Transaksi/Output/Setting) **TIDAK jadi ticket terpisah** — dikerjakan di `feature/DNGO19-3346_Media-Crawler-Google-Business-Review`.
> - **Delta Sync** (`M3-03`, `M3-04`, `M3-05`) **juga dikerjakan di branch 3346** — bukan ticket terpisah.
> - **Review Detail** (`M8-02`) **digabung ke dalam `DNGO19-3387` (Review Manage Actions)** — satu ticket untuk seluruh alur "Ulasan" (detail + aksi kelola).
>
> Konvensi tetap: maks 5 MD/ticket (aturan Agung), 1 screen = 1 ticket, branch 1:1 dengan ticket, jangan campur scope OneBox (PHP, repo `onecloud`) dengan Crawler (Python, repo `hermina_crawler`).

---

## Daftar Ticket (per board, dikonfirmasi dari screenshot)

| Ticket          | Nama                          | Status board         | Branch                                                     |
| --------------- | ----------------------------- | -------------------- | ---------------------------------------------------------- |
| **DNGO19-3385** | VOC : Master-Data-Locations   | IN DEV SPEC REVIEW   | `feature/DNGO19-3385_VOC-Master-Data-Locations`            |
| **DNGO19-3386** | VOC : Master-Data-Competitors | IN DEV SPEC REVIEW   | `feature/DNGO19-3386_VOC-Master-Data-Competitors`          |
| **DNGO19-3387** | VOC : Review Manage Actions   | IN DEV SPEC REVIEW   | `feature/DNGO19-3387_VOC-Review-Manage-Actions`            |
| **DNGO19-3388** | VOC : AI Analysis Setup       | READY TO DEV         | `feature/DNGO19-3388_VOC-AI-Analysis-Setup`                |
| **DNGO19-3389** | VOC : AI Insights             | TODO                 | `feature/DNGO19-3389_VOC-AI-Insights`                      |
| **DNGO19-3390** | VOC : Crawl Scheduler         | TODO                 | `feature/DNGO19-3390_VOC-Crawl-Scheduler`                  |
| **DNGO19-3391** | VOC : Config Setup            | READY TO DEV         | `feature/DNGO19-3391_VOC-Config-Setup`                     |
| **DNGO19-3392** | VOC : Generate Reports        | READY TO DEV         | `feature/DNGO19-3392_VOC-Generate-Reports`                 |
| **DNGO19-3396** | VOC : Competitor Analysis     | TODO                 | `feature/DNGO19-3396_VOC-Competitor-Analysis`              |
| DNGO19-3346     | Menu Restructure + Delta Sync | *dikerjakan di 3346* | `feature/DNGO19-3346_Media-Crawler-Google-Business-Review` |

---

## Detail per Ticket

### DNGO19-3385 — Master-Data-Locations
- **Owner:** Sayyid · **Status:** IN DEV SPEC REVIEW · **MD:** ~1.6 MD
- **Description (siap paste ke Jira — sudah dipakai, cocok dengan screenshot board):**
  > CRUD Lokasi sudah selesai. Sisa scope ticket ini:
  > (1) hapus jembatan transisi push-sync di tombol resync/toggle setelah worklist consumer VoC terbukti stabil (`M1-06`);
  > (2) perbaiki bug `StatusId` Connection dev 1039/Hermina Depok yang salah sampai ikut tersapu penjadwal (`M1-08`);
  > (3) tambah field PIC/penanggung jawab lokasi (nama, WA, email, ID OneBox) sesuai revisi klien — sudah ada implementasi awal di `VocController::locationSaveAction`, perlu diselesaikan sisi frontend (`locations.volt` form + wiring save).

### DNGO19-3386 — Master-Data-Competitors
- **Owner:** OneBox (OB) · **Status:** IN DEV SPEC REVIEW
- **Description (siap paste ke Jira):**
  > CRUD Kompetitor (`M1-02`) sudah selesai — pola sama seperti Location (`VocController::competitorSaveAction`, `competitorToggleAction`, `competitorDeleteAction`). Sisa scope ticket ini:
  > (1) verifikasi `StatusId=CNS3` kompetitor tidak ikut tersapu penjadwal (mirror bug `M1-08` di Location — cek apakah kompetitor punya kerentanan yang sama);
  > (2) konfirmasi ke Product/Agung: apakah kompetitor perlu field PIC seperti Location (DNGO19-3385), atau field itu memang khusus lokasi milik sendiri.
  > **Di luar scope** (tanggung jawab tim Crawler/VC, repo `hermina_crawler`): endpoint tulis Competitor lama yang perlu dijadikan read-only bagi manusia (`M1-07`) — jangan dikerjakan di sini.
  > **Catatan:** setelah adanya DNGO19-3396 (Competitor Analysis), pastikan scope ticket ini murni CRUD/registrasi (setup), bukan komparasi/output data — supaya tidak overlap.

### DNGO19-3387 — Review Manage Actions (kini termasuk Review Detail)
- **Owner:** OneBox (OB) · **Status:** IN DEV SPEC REVIEW · **MD:** 3 + 4 = **7 MD** ⚠️ melebihi cap 5MD (exception disengaja, lihat catatan)
- **Description (siap paste ke Jira):**
  > Ticket ini mencakup DUA bagian alur "Ulasan" yang sengaja digabung jadi satu (lihat catatan MD di bawah):
  >
  > **Bagian 1 — Detail Review:** halaman detail menampilkan teks lengkap review, rating, sentiment, urgency, kategori, summary, recommended action, dan link ke Ticket OneBox terkait. Data ini sudah tersedia dari `reviewsDataAction` (`id` yang dikembalikan = `Ticket.Id`). (`M8-02`)
  >
  > **Bagian 2 — Manage Actions:** dari halaman detail, sediakan aksi assign ke agent, ubah status resolve, dan tambah note internal — reuse mekanisme Ticket OneBox yang sudah ada (`TicketController::showTicketDetail`, `addTaskAssignTo`, `saveTicketUpdate`, `saveTicketMessage`), BUKAN membangun sistem assignment baru. Helper JS siap pakai: `openTabTicketDetail(Id, 'ticket-center', 'Case Detail', 'Ticket/showTicketDetail', 'POST')` di `public/js/navigation.js:588`. (`M8-06`)
  >
  > **Catatan estimasi:** kedua bagian ini totalnya 7 MD, melebihi standar 5MD/ticket. Rekomendasi: buat 2 sub-task di dalam ticket ini ("Detail" dan "Manage Actions") untuk pelacakan progress granular, sambil tetap 1 branch/1 ticket induk.

### DNGO19-3388 — AI Analysis Setup
- **Owner:** OneBox (OB) — **bukan Crawler** · **Status:** READY TO DEV · **MD:** 4 MD
- **Description (siap paste ke Jira):**
  > Layar/kontrak "Analisis" sisi OneBox — bagian TRANSAKSI (setup/trigger AI), berbeda dari hasil (itu di DNGO19-3389 Insights). Scope:
  > (1) kontrak parameter AI yang dikirim ke Crawler: `ai_enabled`, `model`, `prompt_version`, `threshold` (`M7-02`);
  > (2) simpan parameter tersebut di `Connection.Options`, dikirimkan lewat worklist ke Crawler (`M7-04`);
  > (3) klasifikasi rule-first memakai `Service\Ruling`, dijalankan SEBELUM AI untuk menghemat pemakaian token — rules ini otomatis ter-apply lewat `Ticketing.php:263` saat Ticket dibuat (`M7-05`).
  > **DI LUAR SCOPE** ticket ini (tanggung jawab tim Crawler/VC, repo `hermina_crawler` — JANGAN dikerjakan di sini): antrean analisa AI dan perhitungan `tokens_used` (`M7-01`, `M7-03`), serta perbaikan prompt kategori yang saat ini tidak diskriminatif (73 dari 75 review jatuh ke kategori yang sama).

### DNGO19-3389 — AI Insights
- **Owner:** OneBox (OB) · **Status:** TODO · **MD:** 3 MD
- **Description (siap paste ke Jira):**
  > Halaman Insight — menampilkan HASIL analisis AI yang sudah selesai diproses (bukan proses trigger-nya, itu di DNGO19-3388). User melihat output AI: sentiment, urgency, kategori, summary, recommended action per review, dalam bentuk yang mudah dibaca. (`M7-06`)
  > Cakupan detail tampilan masih perlu digali bersama Product — mulai dari kerangka dasar (list + filter) dulu, detail visualisasi menyusul.
  > **Dependency:** DNGO19-3388 selesai + data hasil analisa nyata mengalir dari Crawler. Saat ini terhambat 2 isu sisi Crawler (LLM lokal tidak reachable, bug kategori tidak diskriminatif) — di luar kendali ticket ini, jangan dianggap blocker ticket ini sendiri.

### DNGO19-3390 — Crawl Scheduler
- **Owner:** OneBox (OB) 
- **Status:** TODO · **MD:** hingga 8 MD (⚠️ lihat catatan cap)
- **Description :**
  > Penjadwalan crawl 3-window (pagi 05–07, siang 11–13, malam 21–23) + trigger otomatis + monitoring. Scope:
  > (1) tabel schedule occurrence, unique per `(site_id, local_date, slot)` (`M4-01`);
  > (2) waktu jalan (`planned_at`) diacak dalam rentang tiap slot, mengikuti timezone site, persisten (tidak berubah saat restart) (`M4-02`);
  > (3) ubah trigger fetch dari sinkron (menunggu) jadi "kick" non-blocking ke antrean crawl lalu delta pull — **ini bagian dari jalur kritis proyek** (`M4-03`);
  > (4) lock no-overlap + idempotency key `site:date:slot` supaya dua trigger bersamaan tidak menghasilkan crawl dobel (`M4-04`);
  > (5) UI histori run (planned/actual/status/counters) + tombol "Run now" (`M4-05`).
  > **Delta Sync (`M3-03/04/05`) TIDAK termasuk di ticket ini** — dikerjakan di branch DNGO19-3346.
  > **Owner scheduler tunggal = OneBox** — jangan bikin scheduler kedua di sisi Crawler.
  > **Catatan estimasi:** scope penuh di atas ≈ 8 MD, melebihi standar 5MD/ticket. Rekomendasi: pecah jadi 2 sub-task di dalam ticket ini ("Schedule Core" = item 1/2/4, "Trigger + UI" = item 3/5).
  > **Dependency:** Delta Sync (branch 3346) + `M2-02`/`M3-01` sisi Crawler harus jalan dulu.

### DNGO19-3391 — Config Setup
- **Owner:** OneBox (OB) ·
- **Status:** READY TO DEV · **MD:** 3 MD (menu/role dipisah, lihat catatan)
- **Description (siap paste ke Jira):**
  > Registrasi kode benefit `VOC_SCRAPE`, `VOC_AI`, `VOC_COMPETITOR` di sistem entitlement OneBox (`Benefit`/`SiteBenefit`) (`M6-02`), lalu pasang pemeriksaan kuota: `verifyBenefit()` untuk membatasi JUMLAH PANGGILAN di jalur crawl (`M6-03`), `addUsage()` untuk mencatat NILAI PEMAKAIAN (mis. token AI) di jalur analisa (`M6-04`).
  > ⚠️ **Jebakan terdokumentasi:** `verifyBenefit()` BUKAN pemeriksaan murni — ia ikut menaikkan `SiteBenefit.Quantity`. Jangan pasangkan `verifyBenefit()` dan `addUsage()` untuk satuan yang sama, itu akan menghitung dobel. Pisahkan sesuai fungsi masing-masing.
  > **DI LUAR SCOPE** ticket ini: menu + role/permission untuk VoC (`M8-07`) — item itu **blocked**, menunggu perbaikan bug `getUserAllRole` yang butuh izin senior dev. Jangan dianggap tanggung jawab diam-diam ticket ini.

### DNGO19-3392 — Generate Reports
- **Owner:** OneBox (OB)
- **Status:** READY TO DEV · **MD:** 4 MD
- **Description (siap paste ke Jira):**
  > Halaman Report — export data review ke format PDF/CSV. (`M8-05`) Judul dan struktur laporan disesuaikan kebutuhan stakeholder (mis. laporan bulanan per cabang, ringkasan sentiment) — detail template perlu dikonfirmasi ke Product sebelum development penuh dimulai.

### DNGO19-3396 — Competitor Analysis
- **Owner:** OneBox (OB) 
- **Status:** TODO
- **Description :**
  > Fitur komparasi/output data kompetitor terhadap performa cabang sendiri — user melihat perbandingan rating, sentiment, atau volume review antara cabang sendiri dan kompetitor terdaftar (lihat DNGO19-3386 untuk CRUD registrasi kompetitornya).
  > Detail metrik komparasi & tampilan **masih perlu dikonfirmasi ke Product** — scope ticket ini adalah asumsi awal berdasarkan notulen meeting Pak Agung (*"Competitor itu output juga ya? Iya bikin komparasi."*). Belum ada task ID resmi di `VOC_DEV_TASKLIST.md` — tambahkan setelah scope final disepakati.
  > ⚠️ **Pastikan tidak overlap dengan DNGO19-3386** — 3386 = CRUD/registrasi (setup), 3396 = tampilan komparasi (output).

---

## Branch 3346 — Cakupan yang Dikerjakan di Sana (bukan ticket terpisah)

`feature/DNGO19-3346_Media-Crawler-Google-Business-Review` menanggung 2 hal yang sengaja **tidak** dipecah jadi ticket sendiri:

**Description gabungan (siap paste ke Jira kalau branch ini butuh deskripsi formal):**
> Branch ini mencakup dua pekerjaan fondasi yang harus selesai sebelum ticket VoC lain (3388, 3389, 3390, 3396) menambah sub-menu/data baru:
>
> **(1) Menu Navigation Restructure:** ubah VoC dari submenu Mediamonitoring flat 9-item menjadi header menu tersendiri dengan 3 grup — Transaksi (Ulasan, Analisis, Insight), Output (Dashboard, Report), Setting (Setup Parameter, Master Data). Update seed `scriptdb/voc/voc_setup_all.sql` dari struktur flat ke hierarki 3-level (Header → Grup → Sub-menu), sesuai keputusan meeting Pak Agung.
>
> **(2) Delta Sync:** delta pull review dari Crawler memakai `checkpoint_cursor` — checkpoint hanya maju setelah SELURUH halaman sukses di-ingest (`M3-03`); backfill bertarget untuk lokasi baru yang sudah punya histori lama di Crawler, `?location_id&updated_since=<jauh>` dijalankan SEBELUM masuk aliran delta supaya review lama tidak terlewat (`M3-04`); rekonsiliasi lokasi lama yang sudah ter-crawl tapi belum punya Ticket, mis. kasus Bekasi (`M3-05`).

Ringkasan singkat:
1. **Menu Navigation Restructure** — header menu VoC + 3 grup (Transaksi/Output/Setting), update seed `scriptdb/voc/voc_setup_all.sql` dari flat 9-submenu jadi hierarki 3-level.
2. **Delta Sync** (`M3-03`, `M3-04`, `M3-05`) — delta pull pakai `checkpoint_cursor`, backfill lokasi baru, rekonsiliasi lokasi lama yang belum punya Ticket.

**Implikasi urutan kerja:**
- **Ticket yang nambah sub-menu baru (3388, 3389, 3390, 3396) sebaiknya menunggu restrukturisasi menu di 3346 selesai dulu**, supaya sub-menu baru langsung masuk ke grup yang benar.
- **`Crawl Scheduler` (3390) bergantung pada Delta Sync di 3346** — cek dependency ini sebelum mulai development 3390.

---

## 📋 Pending / Perlu Diklarifikasi (list terbuka, jangan diasumsikan selesai)

| # | Item | Kenapa masih terbuka |
|---|---|---|
| 1 | **Isi ticket 3393–3395** | **Hipotesis baru (perlu konfirmasi):** screenshot ticket 3385 menunjukkan subtask `DNGO19-3394 "Dev Specification : VOC : Master-Data-Locations"` — kemungkinan besar 3393/3394/3395 adalah subtask "Dev Specification" milik ticket-ticket induk (bagian dari alur spec-review sebelum status "in development"), **bukan** ticket fitur yang hilang. Kalau benar, Review-Detail dan Delta-Sync memang tidak butuh ticket sendiri (sudah sesuai keputusan digabung ke 3387 dan branch 3346). Tetap cek langsung di Jira untuk memastikan pola penomoran subtask ini konsisten di semua ticket induk. |
| 2 | **Scope persis `Crawl Scheduler` (3390)** | Perlu dikonfirmasi: apakah full M4-01..05 (8MD, exceeds cap) atau sudah dipangkas. Sub-task split direkomendasikan (lihat detail 3390 di atas). |
| 3 | **Scope persis `Competitor Analysis` (3396)** | Pastikan tidak overlap dengan `Master-Data-Competitors` (3386) — 3386 = CRUD/registrasi, 3396 = komparasi/output (asumsi dari notulen meeting, belum dikonfirmasi eksplisit). |
| 4 | **Exception 5MD di 3387 dan 3390** | Dua ticket ini disengaja melebihi cap karena penggabungan scope yang masuk akal secara alur kerja — perlu dikomunikasikan ke Agung sebagai exception yang disadari, bukan kelalaian. |

---

## Item yang Sudah Tidak Berlaku dari Draft Sebelumnya

- ~~T1a/T1b Review-Detail + Review-Manage-Actions terpisah~~ → **digabung jadi 3387**.
- ~~T5a Delta-Sync sebagai ticket sendiri~~ → **dikerjakan di branch 3346**.
- ~~T5b/T5c Scheduling-Core + Trigger-UI terpisah~~ → jadi **3390 (Crawl Scheduler)**, kemungkinan perlu sub-task internal karena cap 5MD.
- ~~T8 Menu Navigation Restructure sebagai ticket sendiri~~ → **dikerjakan di branch 3346**.
