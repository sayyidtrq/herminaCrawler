# PLAN — Dashboard KPI, Isolasi Kelompok, dan Sentimen Ingest

- **Tanggal:** 2026-09-21
- **Base branch:** `feature/voc` (dev). Branch `3511` dan `3529` saat ini **persis di commit yang sama** dengan `feature/voc` (0 ahead / 0 behind) — titik start bersih, tidak ada risiko urutan merge seperti kasus 3385/3387.
- **Pembagian branch (sesuai instruksi):**
  - `feature/DNGO19-3511_Workspace-Branch-Manager` → dashboard + seeding kelompok + isolasi data
  - `feature/DNGO19-3529_Fetch-Review-Improvement` → perbaikan sentimen saat ingest

---

## Temuan yang mengubah urutan kerja

**1. KPI periode saat ini ikut terfilter — jadi "KPI bisa dipencet sebagai filter" tidak bisa langsung dikerjakan.**
`review_today` / `review_week` / `review_month` dihitung **di dalam loop hasil yang sudah difilter** (`app/controllers/VocController.php:7558-7571`). Akibatnya begitu filter tanggal aktif, ketiga angka itu jadi subset dari window filter — pilih "Hari Ini", maka "Minggu Ini" dan "Bulan Ini" ikut menampilkan angka hari ini juga. Kalau KPI-nya dijadikan tombol filter tanpa memperbaiki ini dulu, hasilnya: begitu diklik, dua KPI sebelahnya langsung berbohong. Jadi **T1 wajib sebelum T2**.

**2. Skema kelompok sudah ada, yang belum ada itu datanya dan penegakannya.**
`VocKelompok` (`app/migrations/1788842363644923_1_123_0/VocKelompok.php:18`) dan `VocLocationKelompok` (`app/migrations/1788842373644923_1_123_0/VocLocationKelompok.php:18`) sudah termigrasi, CRUD master + assign per-lokasi sudah jalan (`VocController.php:13295`, `:13499`), dropdown di layar Lokasi sudah ada (`locations.volt:813`). Yang belum: **tidak ada seed** (beda dengan wilayah yang punya `VocWilayahSeed.php`), dan filter kelompok di layar Lokasi **cuma client-side** (`locations.volt:1351-1379, 1857`) — artinya seluruh lokasi site tetap dikirim ke browser. Untuk tujuan "hide lokasi company lain", filter client-side itu **bukan isolasi**, cuma penyembunyian visual.

**3. `hospital_name` tidak bisa dipakai sebagai dasar pengelompokan.**
Di JSON dev, `hospital_name` terkontaminasi nilai default `"Hermina"`: semua `UPTD Puskesmas *`, semua `LANUD *`, semua `MyRepublic *`, bahkan sebagian besar `Asuransi Astra *` tercatat `hospital_name: "Hermina"`. Seeding harus berbasis **pola `branch_name` + pengecualian eksplisit**, bukan `hospital_name`.

**4. Ada assignment kelompok yang salah di data dev sekarang.**
Lokasi id `1104` **LANUD HUSEIN SASTRANEGARA** saat ini `kelompok_id: 2` (`Asuransi Astra`). Itu salah — harusnya masuk kelompok TNI AU. Seed harus mengoreksi, bukan cuma mengisi yang null.

**5. Badge "belum diklasifikasi" ≠ sentimen kosong.**
Angka `1.367 belum diklasifikasi` di layar review itu counter **kategori** (`uncategorized`, `VocController.php:4555`), sedangkan sentimen kosong counter-nya lain (`unanalyzed`, `:4546`). Kategori hanya diisi jalur AI/Crawler, tidak pernah oleh pelabel native. Jadi memperbaiki sentimen native **tidak akan menurunkan angka 1.367 itu** — perlu diukur dulu supaya tidak salah klaim.

**6. Filter navbar global sebenarnya mati di tab VoC.**
Filter tanggal navbar (`#searchdateglobal`) cuma ada di shell berita (`app/views/layouts/templates_news.volt:558-578`), state-nya murni client-side di instance daterangepicker, dan cara kerjanya memicu ulang `$('div.tab-pane.active').find('[id^=searchdata]').trigger('click')` (`layouts/Mediamonitoring/filter.volt:603`). Layar VoC **tidak punya elemen ber-id `searchdata*`**, jadi tombol Filter global itu no-op diam di tab VoC. Jadi masalahnya bukan "dua filter bertabrakan", tapi "satu filter kelihatan tapi mati".

---

## Urutan kerja (dependency order)

### Branch 3511

| # | Task | Kenapa urutannya di sini |
|---|---|---|
| **T1** | KPI periode (Hari/Minggu/Bulan Ini) dibuat **independen dari filter tanggal** — dihitung terpisah, tetap ikut scope site/lokasi/wilayah/kelompok | Prasyarat T2. Tanpa ini, KPI yang diklik bikin dua KPI lain salah |
| **T2** | KPI jadi **tombol filter**: klik = set periode, klik lagi = lepas, ada state aktif + chip. Semua perubahan periode lewat satu fungsi `setPeriode()` | Butuh T1. Sekaligus menciptakan seam tunggal yang dipakai T5 |
| **T3** | **Seed kelompok**: bikin master kelompok + map semua 222 lokasi, idempotent, sekaligus koreksi id 1104 | Prasyarat T4 — tanpa data kelompok, isolasi tidak bisa diuji apalagi didemokan |
| **T4** | **Isolasi data**: setting kelompok aktif per-site di Setup Parameter, ditegakkan **server-side** di `locationsDataAction` (`VocController.php:10449`), lalu dirambatkan ke dashboard/profile/review | Butuh T3 |
| **T5** | **Dua filter tanggal**: navbar global jadi default yang diwarisi, filter VoC jadi override eksplisit + chip "override" + reset | Terakhir: paling besar, menyentuh layout bersama `templates_news.volt` yang dipakai Mediamonitoring — dikerjakan saat API filter VoC sudah stabil (sesudah T2) |

### Branch 3529

| # | Task | Kenapa urutannya di sini |
|---|---|---|
| **T6** | **Ukur dulu**: hitung baris yang benar-benar tidak punya sentimen (`unanalyzed`) vs tidak punya kategori (`uncategorized`) | Supaya tidak memperbaiki angka yang salah (lihat temuan 5) |
| **T7** | **Label saat ingest**: pelabelan dipindah/diduplikasi ke jalur ingest (`app/services/Provider/VocProvider.php:1252 buildMeta`) supaya tidak ada jalur masuk yang bisa menghasilkan baris tanpa label | Ini inti permintaan "saat ulasan masuk langsung dilabeli" |
| **T8** | **Tutup celah sisa**: cap `LIMIT 500` per panggilan (`VocController.php:16188`), null-guard yang membuang baris tanpa bintang + teks tak dikenal (`:16206`), dan jalur terjadwal `VocTask` yang tidak pernah melabeli sama sekali | Butuh T7 sebagai fondasi |
| **T9** | **Backfill** baris lama yang belum berlabel | Terakhir, setelah jalur baru terbukti benar |

---

## Rekomendasi desain untuk T5 (pertanyaan "solusi terbaiknya bagaimana")

**Global = default yang diwarisi, lokal = override eksplisit.** Saat tab VoC dibuka, baca picker global sekali lalu pakai sebagai periode awal VoC; begitu user menyentuh filter VoC sendiri, tampilkan chip "override" dan berhenti mengikuti global sampai di-reset. Presedennya sudah ada di modul berita — override per-tab lewat hidden input `#localStartDate…`/`#localEndDate…` (`app/views/Mediamonitoring/filter.volt:474-478`).

Alasan tidak sekadar membuang filter VoC dan ikut global saja: VoC butuh preset yang tidak dimiliki global — "Semua waktu" (default dashboard) dan 365 hari (default dashboard profile) — dan global itu datetime-presisi + POST + `CONVERT_TZ`, sedangkan VoC date-only + GET. Menyatukannya paksa akan menghilangkan komponen jam dan mengubah cache key modul berita (`$keyListParam`, `MediamonitoringController.php:1939`). Trade-off yang diterima: user melihat dua kontrol, jadi chip override wajib ada supaya jelas mana yang sedang berlaku.
