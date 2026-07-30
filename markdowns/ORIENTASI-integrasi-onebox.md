# Orientasi — Integrasi Crawler System × OneBox

> **Untuk siapa:** kamu, saat bingung harus mulai dari mana di antara ~90 file MD.
> **Dibuat:** 2026-07-29 · berdasarkan pembacaan langsung ke kode, bukan hanya ke dokumen.
> **Yang dokumen ini lakukan:** menjelaskan kondisi project *sekarang*, memberi tahu dokumen mana yang benar-benar perlu dibaca, lalu menjabarkan apa yang harus dikerjakan terkait `SPEC-multi-tenant-opsi-c`.
> **Yang dokumen ini TIDAK lakukan:** menggantikan ADR. Kalau isi di sini bentrok dengan ADR, ADR yang menang.

Penanda yang dipakai:
**[terverifikasi]** = saya buka kodenya · **[dokumen]** = klaim dari MD lain, belum saya cek ke kode · **[gap]** = temuan yang belum tercatat di dokumen mana pun.

---

## Bagian 1 — Peta besar: ini sebenarnya project apa

Ada **dua sistem terpisah** yang harus bekerja sama.

| | **OneBox** | **Crawler System** (repo ini) |
|---|---|---|
| Bahasa | PHP / Phalcon | Python / FastAPI |
| Lokasi | **repo lain, tidak ada di laptop ini** [terverifikasi] | `~/…/PROJECT/herminaCrawler` |
| Perannya | Otak & etalase | Tangan & kaki |
| Isinya | Master data lokasi, dashboard, review management, jadwal crawl, kuota/benefit, UI | Scraping Google Maps pakai Selenium, analisa AI, simpan hasil |

Satu kalimat yang menjelaskan seluruh arsitektur:

> **OneBox tahu APA yang harus di-crawl dan KAPAN. Crawler System yang MENGEKSEKUSI.**

Kalau kamu cuma ingat satu hal dari dokumen ini, ingat kalimat itu. Semua keputusan lain adalah turunannya.

### Kenapa pembagiannya begitu

Dulu Crawler System dirancang sebagai produk berdiri sendiri — punya frontend Next.js sendiri, punya tabel `Company`, `User`, `Location` sendiri, punya login sendiri. Lalu keputusan bisnis berubah: **VoC jadi fitur di dalam OneBox**, bukan produk terpisah.

Masalahnya, kepemilikan data tidak ikut ditinjau ulang. Akibatnya sempat ada kondisi aneh: menambah satu lokasi rumah sakit berarti kerja manual di dua sistem, dan OneBox mereferensi ID milik sistem lain. `ADR-0001` yang membereskan ini — dan konsekuensinya besar: **frontend Next.js di `herminaCrawler-fe/` resmi jadi dead code untuk alur produksi**, dipertahankan hanya sebagai benchmark visual.

---

## Bagian 2 — Tiga ADR: satu-satunya yang wajib kamu pahami

ADR (*Architecture Decision Record*) adalah otoritas tertinggi di project ini. Ada tiga, semuanya di `markdowns/decisions/`. **Kalau kamu cuma punya waktu 1 jam, baca tiga ini saja dan abaikan sisanya.**

### ADR-0001 — OneBox jadi System of Record
Semua modul (dashboard, review management, location, competitor, reports, insights, benefit) dikelola di OneBox. Crawler System direduksi jadi **mesin crawler headless** — tanpa UI, tanpa kepemilikan master data.

Konsekuensi yang perlu kamu cerna: tabel `locations` dan `competitors` di repo ini **bukan master data**. Itu "crawl target registry" — turunan, seperti index pencarian. Yang boleh mengubahnya hanya OneBox. Sedangkan `reviews` disimpan sebagai **cache** supaya tidak perlu re-scrape dan re-analisa (hemat token AI).

### ADR-0002 — AI: kendali di OneBox, eksekusi di Crawler
Parameter AI (model mana, prompt versi berapa, threshold, on/off) diputuskan OneBox dan **dikirim di dalam request**. Crawler yang benar-benar memanggil LLM, lalu **wajib mengembalikan `tokens_used`** supaya OneBox bisa mencatat pemakaian ke kuota.

### ADR-0003 — Pull worklist + antrean job
Ini yang paling banyak mengubah kode. Dua keputusan:

1. **Provisioning: push → pull.** Dulu OneBox memanggil Crawler saat user menyimpan lokasi (sinkron, di jalur yang dilihat user — kalau Crawler lambat, tombol Simpan ikut lambat). Sekarang dibalik: **Crawler yang menarik daftar target** dari OneBox lewat `GET /api/VocWorklist`. Simpan lokasi di OneBox jadi commit lokal instan.

2. **Eksekusi: blocking → antrean durable.** Crawl tidak lagi dijalankan di dalam request HTTP yang menunggu Selenium selesai. OneBox cuma bilang "enqueue crawl untuk target-target ini", dijawab `batch_id` dalam hitungan milidetik. Worker terpisah yang menguras antreannya.

Prinsipnya: **semua kerja berat terjadi di background berjadwal; user hanya membaca hasil yang sudah jadi.**

---

## Bagian 3 — Kondisi nyata kode sekarang

Ini hasil pembacaan langsung ke kode hari ini (2026-07-29), bukan salinan dari tasklist.

### ✅ Yang sudah jalan

| Bagian | Bukti di kode |
|---|---|
| **Lapisan data sudah multi-tenant** | `app/db/models.py` — `users`, `api_clients`, `locations`, `reviews`, `fetch_logs`, `competitors`, `worklist_sync_states`, `crawl_batches`, `crawl_jobs` semuanya punya `company_id` + index [terverifikasi] |
| **Consumer worklist** | `app/integrations/onebox_worklist_client.py` (login JWT + retry/backoff + token caching) → `app/services/worklist_sync_service.py` (validasi payload, upsert, rekonsiliasi target yang hilang jadi nonaktif) → `scripts/refresh_worklist.py` [terverifikasi] |
| **Antrean crawl durable** | Tabel `crawl_batches` + `crawl_jobs`, klaim atomik pakai `SELECT … FOR UPDATE SKIP LOCKED` (`app/services/crawl_job_service.py:228`), lease + retry + backoff, endpoint enqueue & status batch di `apps/api/app_api/routers/integration_crawl_jobs.py`, worker `scripts/run_crawl_worker.py` [terverifikasi] |
| **Isolasi tenant diuji** | `tests/test_tenant_isolation.py` — 5 test: location, review, competitor, fetch_log, entitlement flags [terverifikasi] |
| **Test suite hijau** | `69 passed` (di luar `test_real_integrations` & `test_selenium_scraping` yang butuh jaringan/browser) [terverifikasi] |

### ⚠️ Yang perlu kamu tahu sebelum percaya dokumen lain

**`VOC_DEV_TASKLIST.md` sudah basi.** Dokumen itu menandai M2-01 sampai M2-07 (antrean + worker) sebagai `todo`, padahal sebagian besar sudah ada di kode sejak commit `b1ead26`. Kondisi sebenarnya:

| Task | Kata tasklist | Kondisi kode sebenarnya |
|---|---|---|
| M2-01 tabel antrean | `todo` | **sudah ada** |
| M2-02 worker + SKIP LOCKED | `todo` | **sudah ada** |
| M2-03 endpoint enqueue | `todo` | **sudah ada** |
| M2-04 retry sadar-jenis-error | `todo` | **separuh** — retry & backoff ada, tapi semua error diperlakukan sama; belum ada beda antara 429 (backoff panjang) vs 404 (jangan retry) |
| M2-05 rate limit + stagger | `todo` | **memang belum ada** |
| M2-06 backpressure CPU/RAM | `todo` | **memang belum ada** |
| M2-07 status batch | `todo` | **sudah ada** |

Pelajaran praktisnya: **verifikasi ke kode sebelum percaya status di MD mana pun.** Ini bukan kelalaian siapa-siapa — dokumen memang selalu tertinggal dari kode. Tapi artinya kamu tidak boleh merencanakan kerja berdasarkan tasklist saja.

### 🔴 Yang masih single-tenant — inilah pokok masalahnya

Seluruh lapisan data sudah siap melayani banyak penyewa. Yang mengunci sistem ke satu penyewa cuma **dua baris konfigurasi**:

```python
# app/config.py:94-95
onebox_site_id: int | None = None      # satu, tetap
onebox_company_id: int | None = None   # satu, tetap
```

Dua nilai itu merembet ke tiga tempat [terverifikasi]:
- `onebox_worklist_client.py:112` — `siteId` saat login dikunci ke satu site
- `onebox_worklist_client.py:188` — dianggap config wajib
- `worklist_sync_service.py:120, 132, 163` — company & site dikunci dari settings

Jadi: **sistemnya sudah bisa menampung banyak penyewa; yang belum bisa adalah menemukan siapa saja penyewanya.**

---

## Bagian 4 — Peta dokumen: mana yang perlu dibaca, mana yang boleh diabaikan

Ada 90+ file MD di repo ini. Kamu tidak perlu membaca semuanya. Kelompoknya begini:

### Wajib (baca berurutan, sekali duduk)
1. `markdowns/decisions/ADR-0001-ownership-inversion.md`
2. `markdowns/decisions/ADR-0002-ai-execution-split.md`
3. `markdowns/decisions/ADR-0003-crawl-execution-pull-queue.md`
4. `markdowns/decisions/SPEC-multi-tenant-opsi-c.md` ← ini yang mau dikerjakan
5. `markdowns/integrations/MUST_READ.md` — aturan kerja & daftar dokumen basi

### Detail teknis — buka **hanya saat mengerjakan task terkait**, jangan dibaca borongan
- `markdowns/integrations/implementation-plan-crawler-system/VOC-CS-*.md` — detail sisi Crawler (repo ini)
- `markdowns/integrations/implementation-plan-onebox/RI-*.md` — detail sisi OneBox (repo lain)
- `markdowns/integrations/VOC_DEV_TASKLIST.md` — urutan kerja, tapi **statusnya jangan dipercaya**, lihat Bagian 3

### Sudah TIDAK berlaku — jangan jadikan acuan [dokumen]
Semua ini ditulis sebelum ADR-0001, waktu Crawler masih diposisikan punya UI dan master data sendiri:
- `markdowns/crawler_system/erd.md` dan `dfd.md`
- `markdowns/integrations/architecture_diagram.md`
- `markdowns/integrations/implementation-plan-onebox/RI-06_tenant-mapping.md` (arah mapping terbalik)
- `RI-02_keputusan-arsitektur.md` — sebagian: D2 & D6 batal, D10 direvisi

### Konteks lama — arsip, bukan acuan
Seluruh folder `markdowns/markdown-hc/` adalah dokumentasi era "Hermina Crawler sebagai produk standalone". Berguna kalau kamu mau paham cara kerja Selenium atau setup Docker, tapi keputusan arsitekturnya sudah lewat.

---

## Bagian 5 — SPEC-multi-tenant-opsi-c: apa isinya, kenapa begitu

### Masalah yang diselesaikan

Sekarang satu deployment Crawler = satu penyewa. Kalau ada klien kedua, harus deploy instance kedua dengan `.env` berbeda. Tidak berkelanjutan.

### Solusinya

Satu deployment melayani semua penyewa. **Crawler tidak menyimpan daftar penyewa — ia menanyakannya ke OneBox.**

Kenapa ke OneBox? Karena ADR-0003 sudah menetapkan OneBox pemilik "APA". Daftar penyewa adalah "APA". Jadi ini bukan pola baru — pola yang sama, diterapkan satu tingkat lebih tinggi.

Dokumen itu memakai contoh **Five Coffee** (kedai kopi) sebagai penyewa kedua. Pemilihan itu disengaja: kalau kedai kopi bisa masuk dengan alur yang persis sama seperti rumah sakit **tanpa satu baris kode pun diubah**, barulah klaim "multi-tenant" terbukti. Kalau harus ada `if` khusus, berarti belum multi-tenant.

### Bentuk akhirnya

```
Tingkat 0   Kredensial awal      env, satu akun layanan     [perlu di-scope]
Tingkat 1   Daftar penyewa       ditarik dari OneBox        ← YANG BARU
Tingkat 2   Daftar target crawl  worklist per site          [sudah jalan]
Tingkat 3   Hasil crawl          disimpan per company_id    [sudah jalan]
```

Tingkat 2 dan 3 sudah terbukti bekerja. Yang ditambahkan **hanya Tingkat 1** — dan bentuknya sama persis dengan worklist yang sudah ada. Tidak ada mekanisme baru untuk dipelajari, cuma satu endpoint tambahan dengan pola yang sudah kamu kenal.

### Dua gerbang pengaman

Endpoint `/api/VocTenants` hanya boleh mengembalikan site yang:

1. **Benar-benar bisa diakses akun layanan itu** — diturunkan dari keanggotaan user di JWT (`sub`), **bukan dari parameter request**. Akun layanan tidak boleh bisa "menebak" site milik orang lain dengan mengirim angka sembarangan.
2. **Benefit VoC-nya aktif** — ini gerbang komersialnya. Admin OneBox menyalakan benefit dulu, baru Crawler bisa dipakai untuk site itu.

Crawler sendiri **tidak perlu tahu apa pun** soal benefit, kuota, atau tagihan. Kalau benefit dimatikan, site itu hilang dari daftar, dan crawl berhenti dengan sendirinya. Tidak ada logika billing yang bocor ke sisi Crawler.

### Risiko yang sudah disadari dan diterima

Satu akun layanan mengakses semua penyewa = **satu kebocoran berdampak ke semua**. Ini konsekuensi sadar dari memilih Opsi C, bukan kelalaian. Mitigasinya: akun read-only, token ber-scope sempit (`worklist:read`, bukan admin), rotasi berkala, keanggotaan site diberikan satu per satu.

Jalan mundurnya sudah disiapkan: kalau nanti dinilai terlalu berisiko, pindah ke satu kredensial per penyewa yang disimpan terenkripsi. **Bentuk endpoint dan alur sinkronisasi tidak perlu berubah** — hanya sumber kredensialnya. Ini yang bikin keputusan ini murah untuk dibatalkan.

---

## Bagian 6 — Apa yang harus kamu lakukan

### Pahami dulu batasnya: mana yang bisa kamu kerjakan

Spec §10 memberi 6 langkah. Tapi **tidak semuanya di repo ini**:

| # | Langkah | Di mana | Bisa kamu kerjakan? |
|---|---|---|---|
| 1 | Kolom `onebox_site_id` di `companies` | Crawler (repo ini) | ✅ Ya, sekarang juga |
| 2 | Gerbang benefit di `/api/VocWorklist` | OneBox (PHP) | ❌ Repo lain |
| 3 | Bangun `/api/VocTenants` | OneBox (PHP) | ❌ Repo lain |
| 4 | Siklus `refresh_all_tenants` + isolasi kegagalan | Crawler (repo ini) | ⚠️ Bisa ditulis, tapi belum bisa diuji end-to-end sebelum #3 jadi |
| 5 | Buang `ONEBOX_SITE_ID` & `ONEBOX_COMPANY_ID` | Crawler (repo ini) | ⚠️ Terakhir, setelah #4 terbukti |
| 6 | Uji dengan Five Coffee | Dua-duanya | ❌ Butuh #2 & #3 |

Artinya: **kamu bisa mulai langkah 1 hari ini tanpa menunggu siapa pun.** Langkah 2 dan 3 perlu dikoordinasikan dengan yang pegang OneBox.

### Langkah 1 — kerjakan ini duluan

Tambah kolom di `app/db/models.py` class `Company`, lalu buat migration Alembic baru dengan `down_revision = "20260729_0002"` (itu head sekarang [terverifikasi]).

**Yang spec sebut:**
```python
onebox_site_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
```

**[gap] Yang spec TIDAK sebut tapi kamu butuh:**

Spec §4.4 bilang *"Tandai company nonaktif dan hentikan crawl"* saat penyewa hilang dari daftar. Tapi **tabel `companies` sekarang tidak punya kolom `is_active`** [terverifikasi — `Company` cuma punya `id`, `name`, `ai_enable_flag`, `total_enable_review`, `analyze_competitor_flag`, `created_at`, `updated_at`; sementara `users`, `api_clients`, `locations`, `competitors` semuanya punya `is_active`].

Jadi §4.4 **tidak bisa dijalankan** tanpa kolom tambahan. Tambahkan sekalian di migration yang sama:
```python
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

Ini temuan yang layak kamu sampaikan ke penulis spec — bukan sekadar kamu tambal diam-diam.

### Langkah 4 — struktur yang harus ditulis

```
refresh_all_tenants():
    daftar = GET /api/VocTenants
    untuk tiap penyewa:
        company = cari_atau_buat(onebox_site_id = penyewa.site_id)
        try:
            login(siteId = penyewa.site_id)
            worklist = GET /api/VocWorklist
            sinkronkan(worklist, company_id = company.id)
        except:
            catat kegagalan, LANJUT ke penyewa berikutnya   ← ini yang paling penting
```

Baris `except` itu bukan penyempurnaan, itu **syarat mutlak**. Kalau Five Coffee bermasalah, Hermina harus tetap jalan.

Yang perlu disentuh:
- `app/integrations/onebox_worklist_client.py` — sekarang `site_id` diambil dari settings (baris 112 & 188). Harus bisa menerima `site_id` per pemanggilan.
- `app/services/worklist_sync_service.py` — `is_configured()` (baris 124-135) masih mensyaratkan `onebox_site_id` & `onebox_company_id`; `_require_site_id()` (163-165) baca dari settings. Keduanya harus jadi parameter.
- File baru `scripts/refresh_all_tenants.py`, polanya contek `scripts/refresh_worklist.py` yang sudah ada.

### Sebelum semua itu — hal praktis yang menghalangi

**[gap] `.env` di laptop kamu belum punya satu pun variabel `ONEBOX_*`** [terverifikasi — 0 baris]. Artinya consumer worklist yang sudah jadi itu **belum pernah dijalankan di mesin ini**.

Kerjakan ini dulu, karena tanpanya kamu tidak bisa memverifikasi apa pun:
1. Isi `ONEBOX_BASE_URL`, `ONEBOX_SVC_EMAIL`, `ONEBOX_SVC_PASSWORD`, `ONEBOX_SITE_ID`, `ONEBOX_COMPANY_ID` di `.env` (jangan di-commit)
2. Jalankan `python -m scripts.refresh_worklist --json`
3. Pastikan alur satu-penyewa berhasil **sebelum** menyentuh multi-tenant

Alasannya sederhana: kalau nanti `refresh_all_tenants` gagal, kamu harus bisa tahu apakah yang rusak itu kode barumu atau koneksi ke OneBox yang memang belum pernah dites. Kalau alur lama belum pernah kamu buktikan jalan, kamu tidak punya baseline.

**Prasyarat P5 di tasklist masih `todo` [dokumen]:** jaringan Crawler → OneBox dua arah. Selama ini yang terbukti cuma arah OneBox → Crawler. Kalau `refresh_worklist` gagal timeout, kemungkinan besar itu penyebabnya, bukan kodenya. Ini perlu dikonfirmasi ke yang pegang infra.

### Urutan yang saya sarankan

1. Konfigurasi `.env` + buktikan `refresh_worklist` jalan satu penyewa ← **mulai di sini**
2. Migration: `onebox_site_id` + `is_active` di `companies` (langkah 1 + gap)
3. Laporkan temuan `is_active` ke penulis spec
4. Koordinasi dengan pemegang OneBox untuk langkah 2 & 3 — ini yang paling lama, mulai obrolannya sekarang
5. Sambil menunggu: tulis `refresh_all_tenants` + testnya pakai client palsu (pola `tests/test_worklist_sync.py` sudah menunjukkan caranya)
6. Baru buang config lama, setelah semua terbukti

### Cara tahu kamu sudah selesai

Spec §8 memberi 7 tes. Dua yang paling penting:

- **Tes 4 — isolasi data:** token Hermina tidak bisa melihat data Five Coffee.
- **Tes 6 — isolasi kegagalan:** Five Coffee sengaja dirusak, Hermina tetap tersinkron.

Kutipan spec-nya layak diingat: *"Keduanya yang membedakan sistem multi-tenant sungguhan dari sistem satu-penyewa yang kebetulan menampung dua."*

---

## Bagian 7 — Ringkasan yang bisa kamu bawa ke standup

- Repo ini = **mesin crawler**, bukan produk. Otaknya di OneBox (repo lain, tidak ada di laptop kamu).
- Otoritasnya **tiga ADR**, bukan 90 MD. Sisanya detail atau arsip.
- Lapisan data **sudah multi-tenant**. Yang single-tenant cuma **dua baris config**.
- Kerjaan multi-tenant = menambah **satu tingkat** (daftar penyewa) di atas alur yang sudah terbukti jalan. Bukan bongkar arsitektur.
- **Separuh langkahnya ada di repo OneBox**, bukan di sini — koordinasi harus dimulai lebih awal daripada coding.
- Yang menghalangi kamu sekarang bukan pemahaman, tapi **`.env` yang belum diisi**. Beresin itu dulu.

### Dua hal yang saya temukan dan belum ada di dokumen mana pun

1. **`companies` tidak punya kolom `is_active`** — spec §4.4 tidak bisa dijalankan tanpa menambahnya.
2. **`VOC_DEV_TASKLIST.md` menandai M2-01/02/03/07 sebagai `todo` padahal sudah ada di kode.** Kalau kamu merencanakan sprint dari tasklist itu, kamu akan mengerjakan ulang yang sudah jadi.
