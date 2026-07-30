# Onboarding — Crawler System (Voice of Customer) × OneBox

> **Untuk siapa:** anggota baru yang belum punya konteks apa pun tentang project ini.
> **Dibuat:** 2026-07-30 · disusun dengan membaca kode langsung, bukan hanya dokumen.
> **Cara pakai:** baca Bagian 1–2 dulu (30 menit). Bagian 5 (kamus) dipakai sebagai rujukan saat ketemu istilah asing, bukan dibaca berurutan.

**Penanda yang dipakai di seluruh dokumen:**

| Penanda | Artinya |
|---|---|
| **[terverifikasi]** | Saya buka file/kodenya langsung dan lihat sendiri |
| **[dokumen]** | Klaim dari file MD lain, belum saya cek ke kode |
| **[belum ada]** | Dicari di repo, tidak ketemu — bukan asumsi, memang tidak ada |
| **[analisis]** | Kesimpulan saya dari bukti di repo, bukan pernyataan yang tertulis di repo |

---

# 1. Ringkasan Eksekutif

## 1.1 Project ini apa

Ada **dua sistem terpisah** yang harus bekerja sama. Ini hal pertama yang harus jelas, karena hampir semua kebingungan berikutnya berakar di sini.

| | **OneBox** | **Crawler System** (repo yang kamu buka) |
|---|---|---|
| Nama lain di dokumen | OneBox, onecloud, Control Plane, System of Record | VoC System, Voice of Customer System, Hermina Crawler, "VC", crawler |
| Bahasa & framework | PHP / Phalcon / Swoole | Python / FastAPI |
| Lokasi kode | **Repo lain — TIDAK ada di laptop ini** [terverifikasi] | `~/…/PROJECT/herminaCrawler` |
| Peran | Otak, etalase, pemilik data | Tangan & kaki — tukang ambil data |
| Punya UI untuk user? | Ya | **Tidak** (ada FE Next.js, tapi sudah dipensiunkan — lihat §4.5) |

Satu kalimat yang menjelaskan seluruh arsitektur:

> **OneBox tahu APA yang harus di-crawl dan KAPAN. Crawler System yang MENGEKSEKUSI.**

Kalau kamu cuma ingat satu hal dari dokumen ini, ingat kalimat itu. Semua keputusan arsitektur lain adalah turunannya.

## 1.2 Masalah bisnis yang diselesaikan

RS Hermina punya banyak cabang. Tiap cabang punya halaman Google Maps, dan pasien menulis review di sana. Masalahnya [dokumen — `VOC_STAKEHOLDER_OVERVIEW.md` §2]:

- review baru terlambat diketahui;
- keluhan darurat tercampur dengan review biasa;
- manajemen sulit melihat pola masalah antar cabang;
- tindak lanjut tidak punya alur kerja yang konsisten;
- evaluasi kualitas layanan bergantung inspeksi manual.

Yang dibangun: sistem yang **otomatis mengambil review Google dari semua cabang**, **menganalisanya dengan AI** (sentimen, urgensi, kategori masalah, rekomendasi tindakan), lalu **menampilkannya di OneBox sebagai tiket yang bisa ditugaskan ke orang** — supaya manajemen tidak perlu baca review satu per satu.

## 1.3 Siapa aktornya

| Aktor | Perannya | Bukti di repo |
|---|---|---|
| **RS Hermina** | Klien pertama; cabang-cabangnya yang di-crawl. Di OneBox = `site_id 169` | `VOC_DEV_TASKLIST.md` P3 [dokumen] |
| **PT Ciptadra Softindo** | Pemilik & pengembang OneBox | Domain `ciptadrasoft.net`, image `ciptadra/onecloud` [terverifikasi di `local-dev-setup-guide.md`] |
| **OneBox** | Produk CRM milik Ciptadra. VoC jadi salah satu fiturnya | — |
| **Crawler System** | Repo ini. Awalnya produk standalone, sekarang jadi mesin pendukung OneBox | — |
| **Pak Agung Januar** | PM OneBox. Pemegang keputusan final. **Semua ADR belum diratifikasi beliau** | `information.md` header, `PROJECT_STATUS.md` §7 |
| **Sayyid** (`sayyidtrq`) | Dev yang menulis semua ADR & sebagian besar kode. 42 commit — kontributor terbesar | `git log` [terverifikasi] |
| **Nabil / Ridho** | Infra — pemegang kredensial server MySQL | `PROJECT_STATUS.md` §5 blocker 1 |
| **Cello** (`cellonada`), **Nisrina**, **zhofran** | Kontributor lain (10/4/3 commit) | `git log` [terverifikasi] |
| **Codex** & **Claude Code** | Dua AI agent dengan pembagian kerja resmi: Codex pegang Crawler System, Claude Code pegang OneBox | `two_agents_workflow.md`, `MUST_READ.md` §Agent Ownership |

> **Catatan tentang pembagian agent:** ini bukan sekadar preferensi tooling — `MUST_READ.md` menetapkannya sebagai aturan kerja. Kalau kamu memakai AI untuk bantu koding, ikuti pembagian itu supaya tidak ada dua agent mengubah sisi yang sama.

## 1.4 Sekarang fase apa

**Fase: merapikan agar demo Phase 1 solid** [dokumen — `PROJECT_STATUS.md` §1, update 2026-07-24].

Kondisinya menarik dan agak kontra-intuitif: **backend integrasi sudah jauh lebih matang daripada bukti bahwa rantainya nyambung.**

Artinya banyak komponen sudah jadi dan ada testnya, tapi **alur ujung-ke-ujung belum pernah dibuktikan sekali pun di lingkungan nyata**. Dokumen `PLAN_KEY_PROCESS_DEMO.md` (2026-07-28) memetakan 7 tahap, dan tahap 3 — **crawl review Google untuk target hasil worklist** — statusnya masih *"belum pernah dibuktikan"* [dokumen].

Itu tahap paling berisiko, dan sengaja dijadikan gerbang: kalau Selenium ternyata tidak bisa jalan tanpa GUI di server, rencana otomatisasi (antrean + penjadwalan) berdiri di atas sesuatu yang belum tentu bisa dieksekusi.

## 1.5 Lima hal yang harus kamu tahu sebelum menyentuh apa pun

**1. ADR adalah otoritas tertinggi.** Ada 3 ADR di `markdowns/decisions/`. Kalau dokumen lain bertentangan dengan ADR, **ADR yang menang** [dokumen — `MUST_READ.md`]. Banyak MD di repo ini ditulis sebelum ADR dan sudah tidak berlaku.

**2. Separuh pekerjaan integrasi ada di repo lain.** OneBox tidak ada di laptop ini. Kalau sebuah task menyentuh `VocController`, `Ticket`, `Benefit`, atau file `.volt` — itu bukan di sini.

**3. Status di dokumen sering tertinggal dari kode.** Saya menemukan `VOC_DEV_TASKLIST.md` menandai 4 task sebagai `todo` padahal kodenya sudah ada. Detail di §4.9. **Verifikasi ke kode sebelum percaya status di MD mana pun.**

**4. Data di Crawler diperlakukan sebagai cache, bukan sumber kebenaran.** Tabel `locations` & `competitors` di sini adalah *turunan* yang hanya boleh ditulis OneBox. Tapi ada ketegangan yang belum diselesaikan: review Google **tidak bisa diambil ulang** kalau dihapus, jadi menyebutnya "cache" secara teknis benar tapi operasional berbahaya. Ini pertanyaan terbuka yang diakui di dua dokumen [dokumen — `BRAINSTORM-multi-tenant-voc.md` §6.1, `SPEC-multi-tenant-opsi-c.md` §9.1].

**5. Semua ADR belum diratifikasi PM.** Kamu akan membangun di atas keputusan yang secara formal masih bisa berubah. Ini risiko yang sudah tercatat, bukan sesuatu yang kamu temukan sendiri [dokumen — `PROJECT_STATUS.md` §5 blocker 3].

---

# 2. Reading Path Lengkap

Repo ini punya **103 file Markdown** [terverifikasi]. Kamu **tidak perlu** membaca semuanya. Berikut urutan yang masuk akal.

## Hari 1 — Fondasi (±2 jam, wajib, baca berurutan)

### 1. `markdowns/PROJECT_STATUS.md` *(±5 menit)*
**Status: masih berlaku, tapi tanggalnya 2026-07-24 — cek ulang klaimnya.**

Dokumen terpendek dan paling padat. Isinya: di mana project sekarang dalam satu paragraf, apa yang sudah jadi, apa yang belum, 6 blocker berurut dampak, dan daftar keputusan yang menunggu Pak Agung.

**Kenapa dibaca duluan:** ini satu-satunya dokumen yang memberi gambaran menyeluruh dalam waktu singkat. Semua dokumen lain membahas satu potongan.

**Informasi kunci:** blocker nomor 1 adalah DB masih di Supabase free tier (lambat, tidur saat idle, 500 intermiten). Blocker nomor 2 adalah save frontend Location di OneBox masih mock — tidak persist ke backend.

⚠️ **Konflik yang saya temukan:** dokumen ini menyebut **"ADR-0001..0004 terdokumentasi"** dan merujuk **ADR-0004 (migrasi DB Postgres→MySQL)** beberapa kali. **File `ADR-0004-*.md` tidak ada di repo** [belum ada]. Entah belum di-commit, atau ada di repo OneBox. Tanyakan ke Sayyid.

### 2. `markdowns/decisions/ADR-0001-ownership-inversion.md` *(±20 menit)*
**Status: masih berlaku sebagai keputusan inti, tapi §"Mekanisme: auto-provisioning" SUDAH DIAMANDEMEN oleh ADR-0003.**

Ini ADR terpenting. Isinya keputusan yang membalik arah seluruh project.

Ceritanya: Crawler System awalnya dirancang sebagai **produk berdiri sendiri** — punya FE Next.js sendiri, punya tabel `Company`/`User`/`Location` sendiri, punya login sendiri. Lalu keputusan bisnis berubah: **VoC jadi fitur di dalam OneBox**, bukan produk terpisah. Masalahnya, kepemilikan data tidak ikut ditinjau ulang.

Akibatnya ada kondisi yang jelas salah: menambah satu lokasi = kerja manual di **dua** sistem, dan OneBox mereferensi ID milik sistem lain (`Connection.TargetId` = `location_id` milik Crawler). Ada satu lokasi (Hermina Bekasi) yang di-crawl Crawler tapi review-nya **tidak pernah masuk** ke OneBox karena Connection-nya tidak pernah dibuat.

**Keputusannya:** OneBox jadi System of Record untuk SELURUH modul VoC kecuali scraping. Crawler direduksi jadi mesin headless.

**Konsekuensi yang perlu kamu cerna:**
- Tabel `locations`/`competitors` di repo ini bukan master data — itu "crawl target registry", turunan seperti index pencarian
- `reviews` disimpan sebagai **cache** supaya tidak re-scrape & re-analisa (hemat token AI)
- **FE Next.js di `herminaCrawler-fe/` jadi dead code** untuk alur produksi
- `User`/`Company` di Crawler dipensiunkan jadi service account saja

Bagian §"Konsekuensi teknis yang ditemukan saat eksekusi" layak dibaca pelan-pelan — isinya tiga bug di `BenefitService` OneBox yang ditemukan saat implementasi, termasuk satu yang bikin `hasBenefit()` **selalu mengembalikan false secara senyap**.

### 3. `markdowns/decisions/ADR-0002-ai-execution-split.md` *(±10 menit)*
**Status: masih berlaku sepenuhnya. Belum diimplementasikan.**

ADR terpendek. Pertanyaannya sederhana: AI dieksekusi di mana? Dua-duanya punya kemampuan AI — Crawler punya `analysis_service` + client Gemini/OpenRouter/local LLM, OneBox punya `Library\OpenAi.php` yang sudah dipakai produksi.

**Keputusan: split.** Parameter & kuota AI dikendalikan OneBox dan dikirim di dalam request; Crawler yang memanggil LLM, lalu **wajib mengembalikan `tokens_used`** supaya OneBox bisa mencatat pemakaian ke kuota.

**Kenapa penting buat kamu:** ini menciptakan API gap yang belum ditutup. Endpoint crawl/analisa harus menerima `ai_enabled`, `model`, `prompt_version`, `threshold` dan mengembalikan `tokens_used`. Belum ada [terverifikasi — tidak ada field itu di `integration_crawl_schemas.py`].

### 4. `markdowns/decisions/ADR-0003-crawl-execution-pull-queue.md` *(±25 menit)*
**Status: masih berlaku sepenuhnya. Ini ADR yang paling banyak mengubah kode.**

Isinya dua keputusan besar:

**D1 — Provisioning: push → pull.** Dulu OneBox memanggil Crawler saat user menyimpan lokasi, **sinkron, di jalur yang dilihat user**. Kalau Crawler lambat, tombol Simpan ikut lambat; kalau Crawler mati, Simpan gagal. Seluruh kerumitan status `provisioning`, tombol retry, dan "batalkan delete kalau Crawler mati" ada **semata-mata karena** pola push itu.

Sekarang dibalik: **Crawler yang menarik daftar target** dari OneBox lewat `GET /api/VocWorklist`. Simpan lokasi di OneBox jadi commit lokal instan.

**D2 — Eksekusi: blocking → antrean durable.** Crawl tidak lagi dijalankan di dalam request HTTP yang menunggu Selenium. OneBox cuma bilang "enqueue crawl untuk target ini", dijawab `batch_id` dalam milidetik. Worker terpisah yang menguras antreannya, pakai tabel Postgres + `SELECT ... FOR UPDATE SKIP LOCKED` — **bukan** Redis/Celery, karena over-engineering untuk skala pilot.

**D3 — Crawl inkremental.** Scrape terbaru-dulu, berhenti begitu menyentuh review yang sudah dimiliki.

Prinsip tunggalnya: *"semua kerja crawl & analisa terjadi di background berjadwal; user hanya membaca hasil yang sudah jadi."*

Bagian §"Dua cursor yang berbeda (jangan dicampur)" wajib dibaca — ada dua hal berbeda yang sama-sama disebut "cursor" dan gampang tertukar. Lihat juga entri **crawl cursor** vs **ingestion checkpoint** di kamus (§5.4).

### 5. `markdowns/integrations/MUST_READ.md` *(±10 menit)*
**Status: masih berlaku sebagai aturan kerja. Satu butir bertentangan dengan SPEC baru — lihat §4.10.**

Aturan main tim. Isinya: ADR adalah otoritas tertinggi, daftar dokumen yang sudah tidak berlaku, konvensi penamaan ("Voice of Customer System", bukan nama lama), pembagian agent, dan aturan untuk kerja baru (jangan hardcode kredensial, jangan commit `.env`, handoff wajib ditandai verified/assumption/blocked).

## Hari 2 — Multi-tenant & rencana kerja (±1,5 jam)

### 6. `markdowns/decisions/BRAINSTORM-multi-tenant-voc.md` *(±15 menit)*
**Status: eksplorasi, sudah disimpulkan jadi SPEC. Baca untuk memahami *kenapa*, bukan *apa*.**

Dokumen yang membahas: kalau sistem ini mau dipakai perusahaan lain (bukan cuma RS Hermina), apa yang harus berubah?

Temuan utamanya mengubah bentuk seluruh diskusi: **lapisan data sudah multi-tenant** (semua tabel punya `company_id`), **yang single-tenant justru lapisan konfigurasinya** (`ONEBOX_SITE_ID` & `ONEBOX_COMPANY_ID` — masing-masing satu nilai).

Membandingkan tiga opsi:
- **Opsi A** — satu deployment per penyewa. Isolasi terkuat, tapi beban Selenium berlipat dan biaya server naik linear.
- **Opsi B** — satu deployment, daftar penyewa disimpan di tabel DB Crawler. Kredensial banyak penyewa jadi ada di DB Crawler, perlu enkripsi + rotasi.
- **Opsi C** — satu deployment, daftar penyewa **ditarik dari OneBox**. ← dipilih

### 7. `markdowns/decisions/SPEC-multi-tenant-opsi-c.md` *(±20 menit)*
**Status: disetujui untuk diimplementasikan, belum ada kode ditulis.**

Kelanjutan BRAINSTORM, sudah jadi spesifikasi konkret. Alasan Opsi C menang: ADR-0003 sudah menetapkan OneBox pemilik "APA"; daftar penyewa adalah "APA", jadi tempatnya di OneBox. Bukan pola baru — pola yang sama, satu tingkat lebih tinggi.

Dokumen ini memakai contoh **Five Coffee** (kedai kopi) sebagai penyewa kedua. Pemilihan itu disengaja: kalau kedai kopi bisa masuk dengan alur yang persis sama seperti rumah sakit **tanpa satu baris kode pun diubah**, barulah klaim "multi-tenant" terbukti.

**Kalau kamu ditugaskan mengerjakan ini**, sudah ada dokumen terpisah: `markdowns/ORIENTASI-integrasi-onebox.md` (lihat item 8).

### 8. `markdowns/ORIENTASI-integrasi-onebox.md` *(±15 menit)*
**Status: dibuat 2026-07-29, khusus membahas apa yang harus dikerjakan untuk SPEC multi-tenant.**

Melengkapi dokumen yang sedang kamu baca: yang ini fokus ke *langkah kerja* multi-tenant, dokumen yang kamu baca sekarang fokus ke *orientasi menyeluruh*. Berisi dua temuan yang tidak ada di dokumen lain (kolom `is_active` yang hilang, dan tasklist yang basi).

### 9. `markdowns/integrations/VOC_DEV_TASKLIST.md` *(±20 menit)*
**Status: ⚠️ struktur & urutannya berlaku, TAPI kolom Status-nya BASI. Jangan percaya kolom Status.**

Peta kerja utama, dibagi 10 modul (M0–M9). Tiap task punya ID, Owner (`OB`=OneBox / `VC`=Crawler / `OPS`=manusia), prasyarat, estimasi man-day, dan status.

Berguna untuk memahami **urutan dan ketergantungan** — ada diagram Mermaid peta dependensi dan jalur kritis `M1-05 → M2-02 → M3-01 → M4-03`.

Tapi kolom Status tidak akurat. Detailnya di §4.9.

### 10. `markdowns/integrations/PLAN_KEY_PROCESS_DEMO.md` *(±15 menit)*
**Status: masih berlaku — ini rencana kerja aktif per 2026-07-28.**

Rencana membuktikan alur ujung-ke-ujung di dev. Memetakan 7 tahap dengan status masing-masing, dan menandai **tahap 3 (crawl review Google) sebagai yang belum pernah dibuktikan**.

Bagian §2 (analisis blocker) sangat konkret: B1 Selenium mungkin butuh login Google GUI di container; B2 Connection VoC di dev menunjuk alamat yang salah (mewarisi kredensial koneksi lama); B3 laptop lokal tidak bisa menjangkau server crawler karena jaringan WireGuard.

Ada juga rencana cadangan kalau tahap 3 gagal — dan itu jujur: *"jangan memaksakan penjadwalan otomatis — itu menjanjikan sesuatu yang tidak bisa ditepati."*

## Hari 3 — Detail teknis sisi Crawler (baca saat butuh, bukan borongan)

### 11. `markdowns/integrations/implementation-plan-crawler-system/VOC-CS-08_consumer-worklist.md`
**Status: implemented di Crawler; endpoint OneBox harus tersedia di environment target.**

Detail teknis worklist consumer — yang paling relevan buat kamu karena ini kode yang aktif. Berisi contoh persis bentuk response `GET /api/VocWorklist`, arti tiap field (`kind`, `external_place_id`, `active`, `crawl_enabled`, `ingest_reviews`, `mock`), dan 7 aturan perilaku data.

### 12. `VOC-CS-01` … `VOC-CS-07` (folder yang sama)
Detail teknis per increment: contract fixture, delta sync/pagination, service auth, tenant/dedup integrity, reliability/observability, contract test, deployment runbook. **Buka satu saat mengerjakan task terkait.** Jangan dibaca borongan.

### 13. `markdowns/integrations/api-contract-v1.md`
Kontrak API v1 untuk OneBox. Rujuk saat menyentuh endpoint `/api/integration/v1/*`.

### 14. `markdowns/integrations/local-dev-setup-guide.md`
**Ini setup OneBox, bukan Crawler.** WSL + Docker Swarm + MySQL. Baca **hanya** kalau kamu perlu menjalankan OneBox lokal. Ditulis dari pengalaman nyata — bagian Troubleshooting-nya isinya error yang beneran kejadian.

## Referensi — buka saat butuh saja

| File | Kapan dibuka |
|---|---|
| `markdowns/integrations/implementation-plan-onebox/RI-01` … `RI-17` | Saat mengerjakan sisi OneBox (17 file, semuanya PHP/Volt) |
| `markdowns/integrations/VOC_SERVICE_AUTH_RUNBOOK.md` | Saat perlu menerbitkan/mencabut service token |
| `markdowns/integrations/NETWORK_WIREGUARD_CORS_ONEBOX.md` | Saat kena masalah jaringan Crawler ⇄ OneBox |
| `markdowns/integrations/VOC_DBEAVER_SEEDING.md` | Saat perlu isi data awal ke DB |
| `markdowns/markdown-hc/SELENIUM_CRAWLING.md` | Saat mengutak-atik scraping |
| `markdowns/markdown-hc/DOCKER_BACKEND_DEPLOYMENT_GUIDE.md` | Saat deploy ke server |
| `markdowns/onebox_system/erd.md`, `dfd.md` | Saat perlu paham struktur database OneBox |
| `apps.md` | Saat bingung beda folder `app/` vs `apps/` |

## Yang bisa kamu SKIP, beserta alasannya

### Sudah resmi tidak berlaku (ada banner SUPERSEDED) [dokumen — `MUST_READ.md` §⛔]

| File | Kenapa mati |
|---|---|
| `markdowns/crawler_system/erd.md` | ERD lama: Crawler digambar memiliki Location/Competitor/Company/User |
| `markdowns/crawler_system/dfd.md` | DFD lama: Crawler digambar punya aktor User/Admin + UI |
| `markdowns/integrations/architecture_diagram.md` | Crawler digambar punya FE sendiri |
| `implementation-plan-onebox/RI-06_tenant-mapping.md` | Arah mapping lokasi terbalik |
| `implementation-plan-onebox/RI-02_keputusan-arsitektur.md` | **Sebagian**: D2 & D6 batal, D10 direvisi. D1/D3/D4/D5/D7/D8/D9/D11 masih berlaku |

### Sebagian besar sudah usang

**`information.md`** (audit 2026-07-06) — ini snapshot audit kesiapan API sebelum integrasi dimulai. Nilainya historis: ia mendokumentasikan **kenapa** OneBox memilih pull, dan mencatat 3 gap yang saat itu wajib dibereskan. **Ketiganya sekarang sudah ditutup** [terverifikasi]:

| Gap di `information.md` | Kondisi sekarang |
|---|---|
| "Belum ada auth machine-to-machine" | Sudah ada — `service_auth.py` + tabel `api_clients` |
| "Belum ada delta sync `updated_since`" | Sudah ada — `/api/integration/v1/reviews` + kolom `sync_updated_at` |
| "Mayoritas endpoint tanpa `response_model`" | Sudah banyak yang punya `response_model` |

Jadi kalau kamu baca `information.md` tanpa konteks ini, kamu akan mengira sistemnya jauh lebih mentah daripada kenyataannya.

### Konteks era lama — arsip

Seluruh folder **`markdowns/markdown-hc/`** (26 file) adalah dokumentasi era "Hermina Crawler sebagai produk standalone". Berguna kalau kamu perlu paham cara kerja Selenium atau setup Docker, tapi keputusan arsitekturnya sudah lewat.

**`markdowns/integrations/superprompt.md`** & **`tasklist(draft).md`** — prompt/draft untuk AI agent dari Juli awal, sudah dilewati ADR. Skip kecuali kamu penasaran dengan sejarahnya.

**`markdowns/fe-profile-progress-report.md`** — progress FE Next.js yang sudah dipensiunkan.

---

# 3. Arsitektur Sistem

## 3.1 Diagram alur end-to-end

```mermaid
flowchart TB
    subgraph OB["OneBox — Control Plane (PHP/Phalcon) · repo lain"]
        USER["User RS Hermina<br/>(admin cabang, manajemen)"]
        MASTER["Master data:<br/>Location, Competitor"]
        SCHED["Scheduler 3 window<br/>05-07 / 11-13 / 21-23"]
        WLAPI["GET /api/VocWorklist<br/>(daftar target)"]
        TICKET["Ticket + Message<br/>+ Dashboard + Reviews UI"]
        BENEFIT["Benefit / SiteBenefit<br/>(kuota & entitlement)"]
    end

    subgraph CR["Crawler System — Worker (Python/FastAPI) · repo INI"]
        WLSYNC["WorklistSyncService<br/>tarik + rekonsiliasi"]
        CACHE[("locations / competitors<br/>= cache target crawl")]
        QUEUE[("crawl_batches / crawl_jobs<br/>= antrean durable")]
        WORKER["scripts.run_crawl_worker<br/>SKIP LOCKED + lease"]
        SELENIUM["Selenium + Chromium<br/>scrape Google Maps"]
        REVIEWS[("reviews /<br/>review_analysis")]
        AI["AnalysisService<br/>LLM: sentimen, urgensi"]
        INTAPI["GET /api/integration/v1/reviews<br/>POST .../crawl-jobs"]
    end

    GOOGLE[["Google Maps<br/>halaman review publik"]]

    USER -->|"simpan lokasi<br/>(instan, commit lokal)"| MASTER
    MASTER --> WLAPI
    WLAPI -->|"1 · pull worklist<br/>JWT akun layanan"| WLSYNC
    WLSYNC --> CACHE
    BENEFIT -.->|"gerbang:<br/>benefit mati = target hilang"| WLAPI

    SCHED -->|"2 · kick non-blocking<br/>service token"| INTAPI
    INTAPI --> QUEUE
    QUEUE --> WORKER
    CACHE --> WORKER
    WORKER --> SELENIUM
    SELENIUM <-->|scrape| GOOGLE
    SELENIUM --> REVIEWS
    REVIEWS --> AI
    AI --> REVIEWS

    REVIEWS --> INTAPI
    INTAPI -->|"3 · pull delta review<br/>cursor + service token"| TICKET
    TICKET --> USER
```

**Tiga panah bernomor itu adalah seluruh integrasinya.** Sisanya detail internal masing-masing sistem.

Perhatikan arah panah 1 dan 3: **keduanya pull, tapi berlawanan arah**. Ini bukan redundansi — panah 1 mengalirkan **konfigurasi turun** ke worker, panah 3 mengalirkan **hasil naik** ke pemilik data. Masing-masing membaca data otoritatif milik sisi lain [dokumen — ADR-0003 §Kontrak API].

## 3.2 Komponen sisi Crawler System, satu per satu

### Dua "muka" aplikasi

Repo ini punya **dua entrypoint berbeda** yang berbagi satu inti bisnis [terverifikasi, dijelaskan di `apps.md`]:

```
herminaCrawler/
├── app/          ← INTI: business logic, database, service, integrasi
├── main.py       ← Muka #1: aplikasi TERMINAL (menu CLI interaktif)
└── apps/api/     ← Muka #2: REST API (FastAPI) ← ini yang dipakai OneBox
```

Perbedaan `app/` (tanpa s) dan `apps/` (dengan s) membingungkan tapi disengaja. `apps/api` **tidak menduplikasi logika** — ia membungkus service di `app/services/*` jadi endpoint HTTP.

`main.py` menjalankan menu terminal [terverifikasi] — berguna untuk operasi manual, tidak dipakai integrasi.

### Komponen inti

| Komponen | File | Tanggung jawab | Data yang dipegang |
|---|---|---|---|
| **Config** | `app/config.py` | Baca `.env`, validasi, sediakan objek `Settings` immutable. Menolak boot kalau secret produksi belum diisi | — |
| **Models** | `app/db/models.py` | Definisi 11 tabel SQLAlchemy | — |
| **Worklist client** | `app/integrations/onebox_worklist_client.py` | Login ke OneBox (`POST /api/Authenticate`), simpan JWT di memori, retry + backoff eksponensial, panggil worklist | JWT di memori saja — tidak pernah ditulis ke disk/log |
| **Worklist sync** | `app/services/worklist_sync_service.py` | Validasi payload **sebelum** menyentuh DB, upsert location/competitor, rekonsiliasi (target hilang → nonaktif, bukan dihapus), fallback ke cache saat OneBox mati | `locations`, `competitors`, `worklist_sync_states` |
| **Crawl queue** | `app/services/crawl_job_service.py` | Enqueue batch (idempotent), klaim job atomik `SKIP LOCKED` (baris 228), lease + retry + backoff, eksekusi | `crawl_batches`, `crawl_jobs` |
| **Worker** | `scripts/run_crawl_worker.py` | Loop: klaim job → eksekusi → tidur `CRAWL_WORKER_POLL_SECONDS` → ulangi | — |
| **Fetch service** | `app/services/fetch_service.py` | Pilih client sesuai `REVIEW_SOURCE_MODE`, normalisasi review, hitung `review_hash`, dedup | `reviews`, `fetch_logs` |
| **Selenium client** | `app/integrations/selenium_google_maps_client.py` | Buka Chromium, scroll halaman review, ekstrak elemen | — |
| **Analysis** | `app/services/analysis_service.py` | Panggil LLM per batch, validasi hasil, simpan. Menggerakkan `sync_updated_at` di transaksi yang sama | `review_analysis` |
| **Service auth** | `apps/api/app_api/service_auth.py` | Verifikasi bearer token opaque → `ServicePrincipal`. **Tidak pernah menerima `company_id` dari request** | — |
| **API client mgmt** | `app/services/api_client_service.py` + `scripts/manage_api_client.py` | Terbitkan/cabut/rotasi service token | `api_clients` |

### Catatan penting tentang service auth

Baris ini di `service_auth.py` adalah inti keamanan multi-tenant [terverifikasi]:

```python
def require_service_principal(...) -> ServicePrincipal:
    """Verify a bearer token without ever accepting company_id from the request."""
```

`company_id` **selalu** diturunkan dari token, tidak pernah dari parameter. Kalau kamu menambah endpoint integrasi, jangan pernah menerima `company_id` sebagai query param — itu melubangi seluruh isolasi tenant.

## 3.3 Model data

11 tabel [terverifikasi — `app/db/models.py`]. Semua tabel inti punya `company_id`.

```mermaid
erDiagram
    companies ||--o{ users : "punya"
    companies ||--o{ api_clients : "punya"
    companies ||--o{ locations : "punya"
    companies ||--o{ competitors : "punya"
    companies ||--o{ reviews : "punya"
    companies ||--o{ fetch_logs : "punya"
    companies ||--o| worklist_sync_states : "punya (1:1)"
    companies ||--o{ crawl_batches : "punya"
    locations ||--o{ reviews : "menghasilkan"
    locations ||--o{ fetch_logs : "dicatat di"
    locations ||--o{ crawl_jobs : "jadi target"
    reviews ||--o{ review_analysis : "dianalisa jadi"
    competitors ||--o{ competitor_reviews : "menghasilkan"
    crawl_batches ||--o{ crawl_jobs : "berisi"
    api_clients ||--o{ crawl_batches : "meminta"
```

### Tabel per tabel

**`companies`** — tenant. Kolom: `id`, `name`, `ai_enable_flag`, `total_enable_review`, `analyze_competitor_flag`, `created_at`, `updated_at`.

> ⚠️ **Temuan:** `companies` **tidak punya kolom `is_active`** [terverifikasi], padahal `users`, `api_clients`, `locations`, `competitors` semuanya punya. Ini jadi masalah karena `SPEC-multi-tenant-opsi-c.md` §4.4 memerintahkan *"tandai company nonaktif"* saat penyewa hilang dari daftar — perintah yang tidak bisa dijalankan tanpa kolom itu. Juga tidak ada kolom `onebox_site_id` yang diminta SPEC §4.1.

**`users`** — akun login FE. `company_id`, `email` (unique), `password_hash` (bcrypt), `full_name`, `is_active`. Sesuai ADR-0001 #6, ini akan dipensiunkan jadi service account saja.

**`api_clients`** — kredensial service opaque untuk OneBox. `key_id` (unique), `secret_hash` (HMAC dengan `SERVICE_TOKEN_PEPPER`), `scopes` (JSON, default `["reviews:read"]`), `expires_at`, `last_used_at`, `revoked_at`. **Terikat ke tepat satu company.**

**`locations`** — cabang RS = target crawl. Kunci identitas: `external_place_id` (Google Place ID). Unique `(source, external_place_id)`. Field kontrol dari worklist: `crawl_enabled`, `ingest_reviews`, `is_mock`, `is_active`, `target_review_count`. Field jembatan ke OneBox: `onebox_connection_id`, `onebox_location_id`. Jejak sinkronisasi: `worklist_synced_at`.

**`reviews`** — review Google. Dedup pakai `review_hash` (**unique global**, bukan per company). Punya dua timestamp berbeda yang gampang tertukar:
- `updated_at` — kapan baris berubah, dengan `onupdate=func.now()`
- `sync_updated_at` — **watermark khusus untuk paging OneBox**, tanpa `onupdate` [terverifikasi]

Komentar di kode menjelaskan kenapa dipisah, dan alasannya bagus:

> *"analysis is append-only: a review analysed weeks after it was scraped never touches `updated_at`, but must still be resent."*

Ada index khusus `(company_id, sync_updated_at, id)` yang melayani keyset scan integrasi.

**`review_analysis`** — hasil AI, **append-only** (satu review bisa punya banyak analisa). `sentiment`, `sentiment_score`, `issue_category`, `urgency`, `summary`, `recommended_action`, `keywords` (JSON), `is_potential_viral`, `is_patient_safety_issue`, `model_name`, `prompt_version`, `raw_response`.

**`fetch_logs`** — riwayat tiap operasi crawl: `total_fetched`, `total_inserted`, `total_duplicate`, `total_failed`, `error_message`, `metadata`.

**`competitors`** & **`competitor_reviews`** — struktur mirip locations/reviews. Bedanya: `crawl_enabled` dan `ingest_reviews` default **false**, dan unique-nya `(source, external_place_id, company_id)` — jadi dua company boleh punya kompetitor yang sama. ⚠️ **Belum ada endpoint API yang mengekspos `competitor_reviews`** [terverifikasi] — ini API gap yang tercatat sebagai M3-06 `blocked`.

**`worklist_sync_states`** — hasil pull worklist terakhir, satu baris per company (unique). `site_id`, `last_attempt_at`, `last_success_at`, `last_error`, `item_count`.

**`crawl_batches`** — satu permintaan enqueue. `public_id` (UUID yang dilihat OneBox), `idempotency_key` + unique `(company_id, idempotency_key)` supaya retry tidak menggandakan, `request_fingerprint`, `slot`, `status`.

**`crawl_jobs`** — satu job per lokasi. `status`, `attempts`/`max_attempts`, `available_at`, `locked_by`/`locked_at`/`lease_expires_at` (mekanisme lease supaya worker yang mati tidak menyandera job), `result_json`, `last_error_code`. Index klaim: `(status, available_at, lease_expires_at)`.

## 3.4 Daftar endpoint yang benar-benar ada

Semua endpoint di-mount dengan prefix `/api`. Swagger: `/api/docs` · ReDoc: `/api/redoc` · OpenAPI JSON: **`/api/openapi.json`** (bukan `/openapi.json` — ini jebakan yang sudah tercatat di tasklist P4).

### A. Publik — tanpa auth

| Method | Path | Response |
|---|---|---|
| GET | `/api/health` | `HealthResponse` — status, app name, env, konektivitas DB |

### B. FE / user — auth JWT (OAuth2 Password Bearer, `tokenUrl=/api/auth/login`)

Token JWT HS256, payload hanya `{"sub": user_id, "exp": ...}`. `company_id` di-resolve dari DB, **tidak** ada di dalam token [dokumen — `information.md` §2, konsisten dengan kode].

| Method | Path | Response model |
|---|---|---|
| POST | `/api/auth/register` | `UserResponse` |
| POST | `/api/auth/login` | `TokenResponse` |
| GET | `/api/auth/me` | `UserResponse` |
| GET | `/api/places/resolve` | `PlaceResolveResponse` |
| GET | `/api/settings` | *(dict)* |
| GET | `/api/settings/database-check` | *(dict)* |
| GET | `/api/locations` | `LocationListResponse` |
| POST | `/api/locations` | `LocationResponse` |
| GET · PATCH · DELETE | `/api/locations/{location_id}` | `LocationResponse` / `DeleteResponse` |
| POST | `/api/locations/{location_id}/toggle-active` | `LocationResponse` |
| GET | `/api/competitors` | `CompetitorListResponse` |
| POST | `/api/competitors` | `CompetitorResponse` |
| GET · PATCH · DELETE | `/api/competitors/{competitor_id}` | `CompetitorResponse` / `DeleteResponse` |
| POST | `/api/competitors/{competitor_id}/toggle-active` | `CompetitorResponse` |
| GET | `/api/reviews` | `ReviewListResponse` |
| GET | `/api/reviews/{review_id}` | `ReviewResponse` |
| GET | `/api/dashboard/overview` | `DashboardOverviewResponse` |
| GET | `/api/dashboard/locations/{location_id}` | `LocationSummaryResponse` |
| GET | `/api/dashboard/critical-issues` | `IssueListResponse` |
| GET | `/api/dashboard/negative-reviews` | `IssueListResponse` |
| POST | `/api/fetch-jobs` | *(dict)* — crawl 1 lokasi, **sinkron/blocking** |
| POST | `/api/fetch-jobs/all-active` | *(dict)* |
| GET | `/api/fetch-logs` | `FetchLogListResponse` |
| GET | `/api/fetch-logs/latest` | `FetchLogLatestResponse` |
| POST | `/api/analysis/pending` | `AnalysisPendingResponse` |
| POST | `/api/analysis/locations/{location_id}/rerun` | *(dict)* |
| POST | `/api/analysis/reviews/{review_id}/rerun` | *(dict)* |
| POST | `/api/exports/reviews/all.csv` | `ExportResponse` |
| POST | `/api/exports/reviews/location/{location_id}.csv` | `ExportResponse` |
| POST | `/api/exports/analysis-summary.csv` | `ExportResponse` |
| POST | `/api/exports/raw-reviews.json` | `ExportResponse` |
| POST | `/api/pipeline/location` | *(dict)* |

> ⚠️ `POST /api/fetch-jobs` bersifat **sinkron/blocking** — ia menunggu Selenium selesai. Ini gaya lama yang justru dihindari ADR-0003. Endpoint integrasi `crawl-jobs` adalah penggantinya yang non-blocking.

### C. Integrasi OneBox — auth service token (`HTTPBearer`)

Berbeda dari blok B: token opaque (bukan JWT), diverifikasi ke tabel `api_clients`, dan tenant selalu dari token.

| Method | Path | Scope wajib | Catatan |
|---|---|---|---|
| GET | `/api/integration/v1/whoami` | *(hanya token valid)* | Balas `company_id`, `company_name`, `scopes` |
| GET | `/api/integration/v1/reviews` | `reviews:read` | Query: `limit` (1–200), `cursor`, `updated_since`, `location_id` |
| POST | `/api/integration/v1/crawl-jobs` | `crawl:enqueue` | **202 Accepted**. Header `Idempotency-Key` **wajib** |
| GET | `/api/integration/v1/crawl-jobs` | `crawl:read` | Daftar batch |
| GET | `/api/integration/v1/crawl-jobs/{batch_id}` | `crawl:read` | Status satu batch |

**Request `POST /api/integration/v1/crawl-jobs`** [terverifikasi — `integration_crawl_schemas.py`]:
```json
{
  "slot": "pagi",
  "targets": [ { "onebox_location_id": 12 } ]
}
```
`targets` minimal 1 maksimal 500; `extra="forbid"` (field tak dikenal ditolak).

**Response:**
```json
{
  "data": {
    "batch_id": "<uuid>", "status": "queued", "slot": "pagi",
    "job_count": 1, "counts": {}, "created_at": "...",
    "jobs": [ { "job_id": 1, "onebox_location_id": 12, "status": "queued",
                "attempts": 0, "max_attempts": 3, "result": {}, "error": null } ]
  },
  "meta": { "api_version": "v1", "request_id": "..." }
}
```

**Response `GET /api/integration/v1/reviews`** — field per item [terverifikasi — `integration_schemas.py`]: `id`, `location_id`, `location`, `source`, `external_place_id`, `external_review_id`, `review_hash`, `reviewer_name`, `reviewer_profile_url`, `rating`, `review_text`, `review_time`, `owner_response_text`, `owner_response_time`, `updated_at`, `sync_updated_at`, `analyzed`, lalu blok analisa (`sentiment`, `sentiment_score`, `issue_category`, `urgency`, `summary`, `recommended_action`, `keywords`, `is_potential_viral`, `is_patient_safety_issue`).

Blok `page`: `limit`, `has_more`, `next_cursor`, `checkpoint_cursor`, `snapshot_at`.

**Tiga jaminan kontrak v1** [terverifikasi dari docstring endpoint]:
1. Field hanya **bertambah** (additive) — tidak pernah dihapus atau berubah tipe
2. `raw_payload`/`raw_response` **tidak pernah** dikirim
3. `company_id` **tidak muncul** sebagai parameter maupun field response

**Error envelope** khusus jalur integrasi berbeda dari jalur FE [terverifikasi — `apps/api/main.py`]:
```json
{ "error": { "code": "INVALID_PARAMETER", "message": "...", "request_id": "..." } }
```
Dan validasi parameter dijawab **400**, bukan 422 seperti default FastAPI. Kode bahkan menghapus 422 dari OpenAPI untuk path integrasi supaya OneBox tidak menulis cabang yang tidak pernah aktif — detail yang jarang dipikirkan orang.

## 3.5 Arah panggilan & auth, ringkas

| # | Arah | Endpoint | Auth |
|---|---|---|---|
| 1 | Crawler → OneBox | `POST /api/Authenticate` lalu `GET /api/VocWorklist` | JWT akun layanan (email + password + siteId) |
| 2 | OneBox → Crawler | `POST /api/integration/v1/crawl-jobs` | Service token opaque, scope `crawl:enqueue` |
| 3 | OneBox → Crawler | `GET /api/integration/v1/reviews?cursor=…` | Service token opaque, scope `reviews:read` |

Perhatikan **dua model auth yang berbeda arah**: Crawler pakai JWT user saat memanggil OneBox; OneBox pakai token opaque saat memanggil Crawler. Ini bukan inkonsistensi — masing-masing memakai mekanisme yang tersedia di sisi lawan.

---

# 4. Status & Fase

## 4.1 Crawler engine (scraping)

| Item | Status | Bukti |
|---|---|---|
| Selenium + Chromium terpaket di image | ✅ DONE | `Dockerfile` install `chromium` + `chromium-driver` [terverifikasi] |
| Client Google Maps scraping | ✅ DONE | `app/integrations/selenium_google_maps_client.py` |
| 5 mode sumber review | ✅ DONE | `mock`, `google_places`, `google_business_profile`, `third_party`, `selenium` — `app/config.py` [terverifikasi] |
| Dedup review | ✅ DONE | `review_hash` unique + `generate_selenium_review_hash` |
| **Bukti crawl berhasil untuk target dari worklist** | ❌ **BELUM PERNAH** | `PLAN_KEY_PROCESS_DEMO.md` tahap 3 [dokumen] |
| Crawl inkremental (cursor per target) | ❌ TODO | M3-01; tidak ada kolom cursor di `locations` [terverifikasi] |

> **Ini risiko terbesar project.** Semua otomatisasi berdiri di atas asumsi bahwa Selenium bisa scrape Google tanpa campur tangan manusia — dan asumsi itu belum diuji.

## 4.2 API layer

| Item | Status | Bukti |
|---|---|---|
| REST API FastAPI, ~40 endpoint | ✅ DONE | `apps/api/` 15 router [terverifikasi] |
| Auth JWT user | ✅ DONE | `routers/auth.py` |
| **Auth service-to-service** | ✅ DONE | `service_auth.py` + `api_clients` |
| Scope-based authorization | ✅ DONE | `reviews:read`, `crawl:enqueue`, `crawl:read` [terverifikasi] |
| Delta sync + opaque cursor | ✅ DONE | `sync_updated_at` + `integration_cursor.py` |
| Error envelope + `request_id` | ✅ DONE | `apps/api/main.py` |
| Endpoint `competitor_reviews` | ❌ **TODO — API gap** | M3-06 `blocked` |
| Parameter AI di request | ❌ TODO | ADR-0002; tidak ada di schema [terverifikasi] |
| `tokens_used` di response | ❌ TODO | ADR-0002 §API Gap |

## 4.3 Database & migration

| Item | Status | Bukti |
|---|---|---|
| 11 tabel, semua tenant-scoped | ✅ DONE | `app/db/models.py` [terverifikasi] |
| 8 file migration Alembic | ✅ DONE | `alembic/versions/` [terverifikasi] |
| Migration head | ✅ | `20260729_0002_add_durable_crawl_queue` |
| Migration otomatis saat container start | ✅ DONE | `entrypoint.sh` [terverifikasi] |
| Test isolasi tenant | ✅ DONE | `tests/test_tenant_isolation.py` — 5 test |
| **DB produksi** | ⚠️ **BLOCKER** | Supabase free tier — lambat, tidur saat idle [dokumen] |
| Migrasi ke MySQL (ADR-0004) | ❌ TODO | Runbook siap, nunggu kredensial infra |
| Kolom `companies.is_active` | ❌ **belum ada** | Diperlukan SPEC §4.4 [terverifikasi] |
| Kolom `companies.onebox_site_id` | ❌ **belum ada** | Diperlukan SPEC §4.1 [terverifikasi] |

## 4.4 AI analysis

| Item | Status | Bukti |
|---|---|---|
| Service analisa + validasi hasil | ✅ DONE | `app/services/analysis_service.py` |
| Multi-provider (Gemini / OpenRouter / local LLM / mock) | ✅ DONE | `app/integrations/` [terverifikasi] |
| Simpan hasil append-only | ✅ DONE | `review_analysis` |
| Antrean analisa terpisah | ❌ TODO | M7-01 |
| Metering token | ❌ TODO | M7-03 + ADR-0002 |
| Parameter AI dari OneBox | ❌ TODO | M7-02/04 |

## 4.5 Frontend

| Item | Status | Bukti |
|---|---|---|
| FE Next.js 16 + React 19 + Tailwind 4 | ✅ ada & jalan | `herminaCrawler-fe/package.json` [terverifikasi] |
| 12 halaman (dashboard, reviews, locations, analysis, insights, reports, dll) | ✅ ada | `herminaCrawler-fe/app/` [terverifikasi] |
| **Status dalam arsitektur** | ⚠️ **DEAD CODE untuk produksi** | ADR-0001 §Consequences #3 |
| Pensiun resmi FE | ❌ TODO | `PROJECT_STATUS.md` §4 — "masih hidup" |

**Perlu ditekankan karena membingungkan:** FE ini masih ada, masih bisa dijalankan, punya git repo sendiri (`herminaCrawler-fe/.git`). Tapi menurut ADR-0001 ia **bukan** bagian alur produksi — UI produksi ada di OneBox. Jangan menghabiskan waktu memperbaiki FE ini kecuali diminta eksplisit.

## 4.6 Deployment & Docker

| Item | Status | Bukti |
|---|---|---|
| `Dockerfile` (python:3.11-slim + Chromium) | ✅ DONE | [terverifikasi] |
| `docker-compose.yml` 2 service: `api` + `crawl-worker` | ✅ DONE | [terverifikasi] |
| Healthcheck | ✅ DONE | `curl -f http://localhost:8000/api/health` tiap 15s |
| CI/CD GitHub Actions | ✅ DONE | `.github/workflows/deploy.yml`: test → build → push GHCR → deploy self-hosted |
| Volume persisten profil Selenium | ✅ DONE | `selenium-profile:/app/.selenium-profile` |
| Jaringan WireGuard Crawler ⇄ OneBox | ⚠️ **belum terbukti dua arah** | Prasyarat P5 `todo` [dokumen] |

## 4.7 Integrasi OneBox

| Item | Status | Bukti |
|---|---|---|
| Worklist consumer di Crawler | ✅ DONE | `worklist_sync_service.py` + `scripts/refresh_worklist.py` |
| Endpoint `GET /api/VocWorklist` di OneBox | ✅ DONE | M1-03 `done [verified]` [dokumen] |
| Antrean crawl durable | ✅ DONE (kode ada) | Commit `b1ead26` [terverifikasi] |
| CRUD Location & Competitor di OneBox | ✅ DONE backend | M1-01/02 |
| **Save frontend Location di OneBox** | ❌ **masih mock** | `locations.volt` cuma update array JS [dokumen] |
| Scheduler 3 window | ❌ TODO | M4 semua `todo` |
| Gerbang benefit | ❌ TODO | M6-02/03/04 |
| Multi-tenant (SPEC opsi C) | ❌ TODO | Belum ada kode [terverifikasi] |

## 4.8 Integration gap — untuk dikomunikasikan ke PM

Tiap gap: deskripsi, dampak, siapa yang memutuskan.

### GAP-1 · Selenium mungkin butuh login Google GUI di container
- **Deskripsi:** catatan lama menyebut Selenium tidak jalan di container tanpa login Google manual lewat GUI [dokumen — `PLAN_KEY_PROCESS_DEMO.md` B1, ditandai `[assumption]`, belum diverifikasi ulang]
- **Dampak:** kalau benar, **seluruh rencana otomatisasi runtuh**. Antrean (M2) dan penjadwalan (M4) mengasumsikan crawl bisa jalan tanpa manusia. Kalau butuh GUI tiap kali, ADR-0003 harus ditinjau ulang.
- **Yang memutuskan:** teknis dibuktikan dulu oleh dev (task X1); kalau gagal → **Pak Agung**, karena mengubah janji produk.

### GAP-2 · Endpoint `competitor_reviews` belum ada sama sekali
- **Deskripsi:** Crawler menyimpan review kompetitor di tabel `competitor_reviews`, tapi tidak ada satu pun endpoint yang mengeksposnya [terverifikasi]
- **Dampak:** fitur analisa kompetitor tidak bisa ditampilkan di OneBox. M3-07 `blocked` menunggu ini.
- **Yang memutuskan:** dev Crawler untuk implementasi; **PM** untuk prioritas (apakah kompetitor masuk Phase 1?)

### GAP-3 · Parameter AI & `tokens_used` belum ada di kontrak
- **Deskripsi:** ADR-0002 mensyaratkan request membawa `ai_enabled`/`model`/`prompt_version`/`threshold` dan response mengembalikan `tokens_used`. Belum ada [terverifikasi]
- **Dampak:** kuota AI tidak bisa ditegakkan. Pemakaian token **tidak terbatas dan tidak tercatat**. Risiko biaya.
- **Yang memutuskan:** nama parameter disepakati dev kedua sisi; **PM** untuk kebijakan kuota

### GAP-4 · Dua engine crawl belum diputuskan
- **Deskripsi:** OneBox punya `Gbusiness.php` (Google Business Profile API resmi, butuh kepemilikan lokasi); Crawler pakai scraping publik. Coverage, risiko ToS, dan cara dedup lintas-engine berbeda [dokumen — `developer_guide.md` §6.1, `PROJECT_STATUS.md` blocker 6]
- **Dampak:** kalau satu lokasi di-crawl dua engine, review bisa dobel dengan `review_hash` berbeda
- **Yang memutuskan:** **Pak Agung** — ini soal positioning produk

### GAP-5 · Semua ADR belum diratifikasi
- **Deskripsi:** ADR-0001/0002/0003 (dan 0004 yang filenya belum ada) semuanya "Pengambil keputusan: Sayyid (dev) — belum diratifikasi Pak Agung"
- **Dampak:** rework besar sudah dieksekusi di atas keputusan yang formalnya masih bisa dibatalkan
- **Yang memutuskan:** **Pak Agung**, satu paket

### GAP-6 · DB Supabase free tier
- **Deskripsi:** tidur saat idle → 500 intermiten [dokumen]
- **Dampak:** demo bisa gagal di momen yang salah
- **Yang memutuskan:** **infra (Nabil/Ridho)** untuk kredensial; **Pak Agung** untuk kapasitas server

### GAP-7 · Retensi cache review belum diputuskan
- **Deskripsi:** ADR-0001 menyebut review di Crawler sebagai "cache", padahal Google hanya menyimpan riwayat terbatas — kalau dihapus, **tidak bisa diambil ulang**
- **Dampak:** kalau ada yang menghapus data dengan alasan "ini cuma cache", data hilang permanen
- **Yang memutuskan:** **PM** — ini keputusan produk, bukan teknis

## 4.9 ⚠️ Konflik antar dokumen yang saya temukan

Ini bagian yang diminta eksplisit. Tiap konflik: apa yang bertentangan, mana yang kemungkinan berlaku, dan alasannya.

### K-1 · `VOC_DEV_TASKLIST.md` vs kode (M2)

| Task | Kata tasklist | Kondisi kode sebenarnya [terverifikasi] |
|---|---|---|
| M2-01 tabel antrean | `todo` | **ADA** — `crawl_batches` + `crawl_jobs` |
| M2-02 worker + SKIP LOCKED | `todo` | **ADA** — `crawl_job_service.py:228` |
| M2-03 endpoint enqueue | `todo` | **ADA** — `POST /api/integration/v1/crawl-jobs`, 202 |
| M2-04 retry sadar-jenis-error | `todo` | **SEPARUH** — retry & backoff ada, tapi semua error diperlakukan sama; tidak ada beda 429 vs 404 |
| M2-05 rate limit + stagger | `todo` | **memang belum ada** |
| M2-06 backpressure CPU/RAM | `todo` | **memang belum ada** |
| M2-07 status batch | `todo` | **ADA** |

**Yang berlaku: kode.** Tasklist ditulis 2026-07-24, kode masuk lewat commit `b1ead26` sesudahnya, dan tasklist tidak diperbarui.

### K-2 · `PROJECT_STATUS.md` merujuk ADR-0004 yang filenya tidak ada
Disebut 4 kali (§3, §4, §6, §7) sebagai keputusan migrasi DB Postgres→MySQL. **File `ADR-0004-*.md` tidak ada di repo** [belum ada].

**Kemungkinan:** ADR-nya ada di repo OneBox, atau belum di-commit. **Tanyakan** — jangan berasumsi keputusannya tidak ada, karena `PROJECT_STATUS.md` menyebutnya sudah "diputuskan, runbook siap".

### K-3 · `MUST_READ.md` vs `SPEC-multi-tenant-opsi-c.md`

`MUST_READ.md` §Rules For New Work menulis:
> *"Worklist consumer wajib memakai ONEBOX_COMPANY_ID yang eksplisit; tenant tidak boleh ditebak."*

`SPEC-multi-tenant-opsi-c.md` §4.2 menulis nilai yang **dihapus**:
> `ONEBOX_SITE_ID` ← tidak lagi dipakai · `ONEBOX_COMPANY_ID` ← tidak lagi dipakai

**Yang berlaku: SPEC**, tapi semangatnya tidak berubah. SPEC menghapus *sumber* nilainya (env → daftar penyewa dari OneBox), tapi mempertahankan *prinsipnya*: SPEC §6.2 tetap menegaskan *"tenant tidak pernah datang dari parameter request — selalu dari identitas"*. Jadi ini bukan pembatalan aturan, melainkan pemindahan sumber.

**Catatan:** SPEC statusnya "disetujui untuk diimplementasikan, belum ada kode". Jadi sampai kodenya ditulis, `MUST_READ` masih akurat untuk kondisi hari ini.

### K-4 · `CARA_JALANIN_DOCKER.md` vs `docker-compose.yml`

Dokumen menulis: *"Compose ini Supabase-only: hanya ada 1 service (`api`)"*. File aktualnya punya **2 service**: `api` dan `crawl-worker` [terverifikasi].

**Yang berlaku: file compose.** Dokumen ditulis sebelum worker ditambahkan.

### K-5 · `information.md` (2026-07-06) vs kondisi sekarang
Tiga gap yang ditandai wajib dibereskan sudah ditutup semua. Lihat §2 "Yang bisa kamu SKIP".

**Yang berlaku: kondisi sekarang.** `information.md` bernilai historis.

### K-6 · Nama aplikasi tidak konsisten
- `.env.example` → `APP_NAME=Voice of Customer Crawler System`
- `app/config.py` default → `"Review System"`
- Judul FastAPI → `"Review System API"`

[semua terverifikasi]. Tidak merusak apa pun, tapi bikin bingung saat `curl /api/health` mengembalikan nama yang berbeda dari dokumen. `MUST_READ.md` §Canonical Naming menetapkan **"Voice of Customer System"** sebagai nama resmi.

### K-7 · ADR-0001 vs ADR-0003 (sudah diselesaikan sendiri oleh dokumennya)
ADR-0001 §"Mekanisme: auto-provisioning" mendeskripsikan push sinkron; ADR-0003 menggantinya dengan pull. **Ini bukan konflik yang perlu kamu selesaikan** — ADR-0001 sudah memberi banner amandemen di bagian itu, dan blok lamanya sengaja dipertahankan sebagai histori. Contoh bagus dari konvensi dokumentasi yang benar (lihat §7).

## 4.10 Bukti test

```
69 passed, 2 warnings in 3.01s
```
[terverifikasi — dijalankan 2026-07-29, mengecualikan `test_real_integrations.py` dan `test_selenium_scraping.py` yang butuh jaringan/browser]

File test: `test_mvp`, `test_tenant_isolation`, `test_worklist_sync`, `test_service_auth`, `test_integration_api_contract`, `test_integration_delta_sync`, `test_integration_crawl_jobs`, `test_selenium_scraping`, `test_real_integrations`.

---

# 5. Kamus Terminologi

Bagian ini disusun dengan menyisir: seluruh MD di `markdowns/` (97 file), `information.md`, `apps.md`, nama file & folder, nama tabel & kolom, nama module/class di `app/` dan `apps/`, `.env.example`, `docker-compose.yml`, `requirements.txt`, `package.json`, dan `.github/workflows/`.

## 5.1 Domain bisnis & produk

| Istilah | Kepanjangan | Penjelasan awam (analogi) | Penjelasan teknis | Wujudnya di project | Muncul di |
|---|---|---|---|---|---|
| **VoC / VOC** | Voice of Customer | "Suara pelanggan" — semua yang pelanggan katakan tentang layananmu | Nama modul/produk untuk pengumpulan & analisa review publik | Nama resmi sistem ini | Semua dokumen |
| **Review** | — | Ulasan yang ditulis orang di Google Maps: bintang + tulisan | Baris di tabel `reviews` | `reviews` | Semua |
| **Rating** | — | Jumlah bintang, 1–5 | `reviews.rating`, dibatasi CHECK constraint 1–5 | `models.py:315` | ERD |
| **Cabang / Branch** | — | Satu lokasi fisik RS Hermina, mis. Hermina Depok | Baris di `locations`, field `branch_name` | `locations` | ADR, SPEC |
| **Location** | — | Sama dengan cabang, istilah teknisnya | Target crawl. Di OneBox = master data, di Crawler = cache | `locations` | Semua |
| **Competitor** | — | RS saingan yang juga dipantau reviewnya | Struktur mirip location, tapi `crawl_enabled` default false | `competitors` | ADR-0001 |
| **Worklist** | — | "Daftar tugas" — daftar tempat mana saja yang harus dicek hari ini | Response `GET /api/VocWorklist` berisi target crawl aktif per tenant | `worklist_sync_service.py` | ADR-0003, VOC-CS-08 |
| **Ticket** | — | Kartu tugas: "ada keluhan di cabang X, tolong ditangani" | Entitas OneBox. Review negatif → Ticket yang bisa di-assign | Tabel di OneBox | ADR-0001 |
| **Message / MessageContent** | — | Isi percakapan yang menempel di Ticket | Entitas OneBox | OneBox | RI-05 |
| **Insight** | — | Kesimpulan dari banyak review, bukan review satu-satu | Halaman OneBox, masih stub | OneBox | PROJECT_STATUS |
| **Sentiment** | — | Nada review: senang, netral, atau marah | `review_analysis.sentiment` + `sentiment_score` | `review_analysis` | ADR-0002 |
| **Urgency** | — | Seberapa cepat harus ditangani | `review_analysis.urgency` | `review_analysis` | ADR-0002 |
| **Issue category** | — | Jenis masalah: antrean lama, dokter judes, parkir penuh | `review_analysis.issue_category` | `review_analysis` | ADR-0002 |
| **PIC** | Person In Charge | Orang yang bertanggung jawab atas satu cabang | Field di OneBox (nama/WA/email) | OneBox | PROJECT_STATUS |
| **Benefit / SiteBenefit** | — | Paket langganan: fitur mana yang menyala untuk klien ini | Tabel OneBox + `BenefitService` | OneBox | ADR-0001, SPEC |
| **Entitlement** | — | Hak pakai — "kamu boleh pakai fitur ini karena sudah bayar" | Konsep; diimplementasi lewat Benefit | `entitlement_service.py` (sisi Crawler) | ADR-0001 |
| **Kuota** | — | Jatah pemakaian, mis. maksimal 10.000 token AI/bulan | `SiteBenefit.MaxQuantity`/`MaxAmount` | OneBox | ADR-0002 |
| **Site** | — | Satu klien/penyewa di OneBox. Hermina = site 169 | Tabel `Site` di OneBox; banyak baris satu DB | OneBox | BRAINSTORM |
| **Penyewa / Tenant** | — | Perusahaan yang menyewa sistem ini | `site_id` di OneBox ↔ `company_id` di Crawler | `companies` | SPEC |
| **Five Coffee** | — | Kedai kopi fiktif untuk menguji multi-tenant | Contoh di SPEC, bukan klien nyata | — | SPEC |
| **Kopi Kenangan** | — | Contoh penyewa hipotetis (dipakai di BRAINSTORM, diganti Five Coffee di SPEC) | — | — | BRAINSTORM |
| **Window / slot** | — | Jam-jam tertentu untuk crawl: pagi/siang/malam | 05–07, 11–13, 21–23 waktu site | `crawl_batches.slot` | ADR-0003, RI-08 |
| **Freshness** | — | Seberapa baru datanya | Badge "Terakhir di-crawl HH:MM" | OneBox | ADR-0003 |

## 5.2 Aktor, organisasi & peran

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **OneBox** | — | Produk CRM tempat semua orang bekerja | PHP/Phalcon/Swoole, repo terpisah | Repo lain | Semua |
| **onecloud** | — | Nama internal repo OneBox | Path `/var/www/html/onecloud` | — | local-dev-setup-guide |
| **Crawler System** | — | Mesin pengambil data, tanpa tampilan | Python/FastAPI, repo ini | Repo ini | Semua |
| **Hermina Crawler** | — | Nama lama repo ini | — | Nama repo GitHub | markdown-hc |
| **PT Ciptadra Softindo** | — | Perusahaan pemilik OneBox | Domain `ciptadrasoft.net` | — | local-dev-setup-guide |
| **RS Hermina** | — | Klien pertama, rumah sakit banyak cabang | site 169 | — | Semua |
| **Pak Agung Januar** | — | PM OneBox, pemegang keputusan final | — | — | information.md, ADR |
| **OB / VC / OPS** | OneBox / VoC Crawler / Operations | Kode owner task di tasklist | Kolom Owner | — | VOC_DEV_TASKLIST |
| **Codex** | — | AI agent yang ditugaskan pegang Crawler System | — | — | two_agents_workflow |
| **Claude Code** | — | AI agent yang ditugaskan pegang OneBox | — | — | MUST_READ |
| **Control Plane** | — | "Ruang kendali" — yang memutuskan apa & kapan | Peran OneBox | — | ADR-0003 |
| **System of Record** | SoR | Sumber kebenaran resmi — kalau beda, yang ini yang benar | Peran OneBox untuk seluruh master data | — | ADR-0001 |
| **Worker Service** | — | Tukang yang mengerjakan, bukan yang memutuskan | Peran Crawler System | — | ADR-0003 |
| **Headless** | — | "Tanpa kepala" = tanpa tampilan/UI | Service yang cuma punya API | Crawler System | ADR-0001 |

## 5.3 Proses & dokumentasi

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **ADR** | Architecture Decision Record | Catatan resmi "kami memutuskan X, alasannya Y" — supaya 6 bulan lagi tidak ada yang tanya "kenapa dulu begini?" | Dokumen bernomor, statusnya Accepted/Superseded | `markdowns/decisions/ADR-*.md` | Semua |
| **SPEC** | Specification | Rencana detail sebelum koding: apa persisnya yang dibangun | Turunan dari keputusan ADR | `SPEC-multi-tenant-opsi-c.md` | — |
| **BRAINSTORM** | — | Catatan mikir keras: opsi apa saja, plus-minusnya | Eksplorasi, belum keputusan | `BRAINSTORM-multi-tenant-voc.md` | — |
| **PROMPT** | — | Naskah instruksi yang di-paste ke AI agent | — | `PROMPT_execute-redesign.md` | — |
| **RUNBOOK** | — | Buku panduan langkah-per-langkah saat ada masalah | — | `VOC_SERVICE_AUTH_RUNBOOK.md` | — |
| **ERD** | Entity Relationship Diagram | Peta tabel database & hubungannya | — | `markdowns/*/erd.md` | — |
| **DFD** | Data Flow Diagram | Peta perjalanan data antar komponen | — | `markdowns/*/dfd.md` | — |
| **Superseded** | — | "Sudah digantikan" — dokumen mati | Banner di 5 baris pertama file | ADR-0001 header | MUST_READ |
| **Amandemen** | — | Sebagian isinya diubah, sisanya masih berlaku | ADR-0003 mengamandemen ADR-0001 | — | ADR-0001/0003 |
| **Ratifikasi** | — | Pengesahan resmi oleh atasan | Menunggu Pak Agung | — | Semua ADR |
| **DoD** | Definition of Done | Patokan "kapan ini boleh disebut selesai" | Ada di tiap modul tasklist | — | VOC_DEV_TASKLIST |
| **MD** | Man-Day | Estimasi 1 orang kerja 1 hari | Kolom di tasklist | — | VOC_DEV_TASKLIST |
| **[verified] / [assumption] / [blocked]** | — | Penanda kejujuran: sudah dibuktikan / masih dugaan / tertahan | Wajib di tiap klaim | — | MUST_READ, tasklist |
| **Handoff** | — | Serah terima pekerjaan antar orang/agent | — | — | MUST_READ |
| **API gap** | — | "OneBox butuh X, Crawler belum punya X" | Dicatat, bukan ditambal di sisi yang salah | — | ADR-0002 |
| **M0–M9** | Modul 0–9 | Pengelompokan task per tema | — | — | VOC_DEV_TASKLIST |
| **RI-xx / VOC-CS-xx** | — | Kode dokumen detail teknis: RI=sisi OneBox, CS=sisi Crawler | — | `implementation-plan-*/` | — |
| **P1–P7** | Prasyarat 1–7 | Hal yang harus benar sebelum task apa pun jalan | — | — | VOC_DEV_TASKLIST |
| **DNGO19-3346** | — | Nomor tiket Jira untuk branch OneBox | Nama branch `feature/DNGO19-3346_...` | — | PLAN_KEY_PROCESS_DEMO |

## 5.4 Arsitektur & pola

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **Multi-tenant** | — | Satu aplikasi melayani banyak perusahaan sekaligus, datanya tidak tercampur — seperti satu gedung apartemen, banyak penghuni, tiap unit terkunci sendiri | Pemisahan data per baris pakai `company_id` | Semua tabel inti | BRAINSTORM, SPEC |
| **Tenant isolation** | — | Jaminan penghuni A tidak bisa masuk unit B | Setiap query wajib ter-scope `company_id` | `tests/test_tenant_isolation.py` | SPEC §6 |
| **Blast radius** | — | Seberapa luas kerusakan kalau satu hal bocor | Satu akun layanan lintas penyewa = radius besar | — | BRAINSTORM §5 |
| **Pull** | — | "Aku yang datang ambil" | Penerima yang memanggil pengirim secara berkala | Crawler tarik worklist; OneBox tarik review | ADR-0003 |
| **Push** | — | "Aku yang antar ke rumahmu" | Pengirim memanggil penerima saat ada perubahan | Pola LAMA, sudah dibuang | ADR-0003 |
| **Queue / Antrean** | — | Antrean loket: tugas masuk, dikerjakan satu-satu | Tabel job dengan status pending→claimed→done | `crawl_jobs` | ADR-0003 |
| **Durable queue** | — | Antrean yang tidak hilang kalau listrik mati | Antrean disimpan di DB, bukan di memori | `crawl_batches`+`crawl_jobs` | ADR-0003 |
| **Worker** | — | Petugas yang menangani antrean | Proses terpisah yang loop ambil-kerjakan | `scripts/run_crawl_worker.py` | ADR-0003 |
| **Blocking / sinkron** | — | Nunggu sampai selesai baru lanjut | Request HTTP menunggu proses panjang | `POST /api/fetch-jobs` (gaya lama) | ADR-0003 |
| **Non-blocking / async** | — | Terima dulu, kerjakan belakangan, kasih nomor antrean | Balas 202 + `batch_id` seketika | `POST /api/integration/v1/crawl-jobs` | ADR-0003 |
| **Idempoten** | — | Dijalankan 1× atau 10× hasilnya sama — seperti tombol lift, ditekan berkali-kali tetap satu perintah | Operasi yang aman diulang | `Idempotency-Key`, unique constraint | ADR-0003 |
| **Idempotency key** | — | Nomor unik supaya permintaan yang sama tidak diproses dua kali | Header wajib di endpoint enqueue | `crawl_batches.idempotency_key` | integration_crawl_jobs.py |
| **Cursor** | — | Pembatas buku: "aku sudah baca sampai sini" | Penanda posisi untuk melanjutkan pengambilan data | Ada **dua** jenis — lihat bawah | ADR-0003 |
| **Crawl cursor** | — | Sampai mana Selenium sudah scrape | Di Crawler, per target. **Belum diimplementasi** | M3-01 `todo` | ADR-0003 |
| **Ingestion checkpoint** | — | Sampai mana OneBox sudah menarik review | Di OneBox, per SiteId | `checkpoint_cursor` | ADR-0003, RI-08 |
| **Opaque cursor** | — | Cursor yang isinya sengaja tidak bisa dibaca/ditebak klien | String ditandatangani HMAC | `integration_cursor.py` | VOC-CS-02 |
| **Watermark** | — | Garis batas air: penanda sampai mana data sudah diproses | `sync_updated_at` | `reviews` | models.py |
| **Delta sync** | — | Cuma ambil yang berubah sejak terakhir, bukan semuanya | `?updated_since=` atau `?cursor=` | `/integration/v1/reviews` | VOC-CS-02 |
| **Backfill** | — | Mengisi mundur data lama yang terlewat | Tarik dengan `updated_since` jauh ke belakang | M3-04 `todo` | VOC_DEV_TASKLIST |
| **Rekonsiliasi** | — | Mencocokkan dua daftar, membereskan yang beda | Target hilang dari worklist → ditandai nonaktif | `worklist_sync_service.py` | ADR-0003 |
| **Soft delete / nonaktif** | — | Dicoret, bukan dirobek — datanya masih ada | Set `is_active=False`, tidak `DELETE` | Semua entity worklist | SPEC §6.4 |
| **Cache** | — | Salinan sementara supaya tidak ambil ulang | `reviews` di Crawler diposisikan sebagai cache | — | ADR-0001 |
| **Crawl target registry** | — | Daftar alamat yang harus didatangi | Reframe untuk `locations`/`competitors` | — | ADR-0001 |
| **Dual-write** | — | Menulis hal yang sama ke dua tempat — sumber bug klasik | Pola lama yang dibuang ADR-0003 | — | ADR-0003 |
| **Eventual consistency** | — | Datanya akan sama, tapi tidak detik ini juga | Target baru muncul di window berikutnya | — | ADR-0003 |
| **Backpressure** | — | Rem otomatis saat kewalahan | Tolak job baru saat CPU/RAM tinggi | M2-06 `todo` | ADR-0003 |
| **Rate limit** | — | Batas "jangan panggil lebih dari N kali per menit" | Google membatasi per target | M2-05 `todo` | ADR-0003 |
| **Backoff** | — | Kalau gagal, tunggu makin lama tiap coba ulang | `delay = base * 5^(attempts-1)` | `crawl_job_service.py:319` | — |
| **Jitter** | — | Acak sedikit supaya tidak semua retry bersamaan | Disebut di M2-04, belum ada | — | VOC_DEV_TASKLIST |
| **Lease** | — | Sewa berjangka: kalau petugas hilang, tugasnya dilepas | `lease_expires_at` + `locked_by` | `crawl_jobs` | — |
| **Stagger** | — | Selang-seling, jangan serempak | M2-05 `todo` | — | ADR-0003 |
| **Single point of failure** | — | Satu titik yang kalau rusak semuanya mati | Satu deployment untuk semua penyewa | — | BRAINSTORM |
| **Ownership inversion** | — | Membalik siapa pemilik data | Judul ADR-0001 | — | ADR-0001 |
| **Provisioning** | — | Menyiapkan target baru supaya siap dipakai | Pola push lama, sudah dibuang | — | ADR-0001/0003 |
| **Microservice** | — | Aplikasi kecil berdiri sendiri yang bicara lewat API | Posisi Crawler System | — | superprompt |

## 5.5 Integrasi & API

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **REST** | REpresentational State Transfer | Gaya bikin API pakai alamat + kata kerja HTTP | GET/POST/PATCH/DELETE atas resource | Seluruh `apps/api/` | Semua |
| **Endpoint** | — | Satu alamat yang bisa dipanggil | Satu kombinasi method + path | `/api/reviews` | Semua |
| **Router** | — | Berkas yang mengelompokkan endpoint sejenis | `APIRouter` FastAPI | `apps/api/app_api/routers/` | apps.md |
| **Payload** | — | Isi kiriman | Body request/response | — | Semua |
| **Schema** | — | Cetakan: field apa saja, tipenya apa | Model Pydantic | `integration_schemas.py` | — |
| **Response model** | — | Cetakan untuk balasan | Parameter `response_model=` | Semua router | information.md |
| **Contract** | — | Perjanjian bentuk data antara dua sistem | v1 dibekukan: field hanya bertambah | `api-contract-v1.md` | — |
| **Additive** | — | Boleh nambah, tidak boleh mengurangi/mengubah | Jaminan kontrak v1 | — | integration_reviews.py |
| **Pagination** | — | Data dipecah per halaman | `limit` + cursor (keyset), bukan offset | `/integration/v1/reviews` | VOC-CS-02 |
| **Keyset pagination** | — | Lanjut dari "setelah item X" — lebih tahan data berubah daripada nomor halaman | ORDER BY `(sync_updated_at, id)` | Index `idx_reviews_company_sync_id` | VOC-CS-02 |
| **Offset pagination** | — | "Halaman 3" — gampang tapi bisa lompat/dobel kalau data berubah | `page`/`page_size` | `/api/reviews` (jalur FE) | information.md |
| **JWT** | JSON Web Token | Kartu identitas digital bertanda tangan, isinya bisa dibaca | HS256, payload `{sub, exp}`, kedaluwarsa 7 hari | `/api/auth/login` | information.md |
| **Bearer token** | — | "Siapa pun yang bawa kartu ini, saya layani" | Header `Authorization: Bearer <token>` | Semua endpoint ber-auth | — |
| **Service token** | — | Kartu untuk mesin, bukan manusia | Token opaque, hash disimpan di `api_clients` | `manage_api_client.py` | VOC-CS-03 |
| **Opaque token** | — | Token yang isinya tidak bisa dibaca — cuma server yang tahu artinya | Random string, diverifikasi lewat DB lookup | `api_clients.key_id`+`secret_hash` | VOC-CS-03 |
| **Service account** | — | Akun milik program, bukan orang | `ONEBOX_SVC_EMAIL` | `.env` | SPEC |
| **Scope** | — | Batas kewenangan kartu: boleh baca saja, atau boleh tulis juga | Daftar string di token | `reviews:read`, `crawl:enqueue`, `crawl:read` | service_auth.py |
| **Principal** | — | "Siapa yang sedang memanggil" | `ServicePrincipal` dataclass | `service_auth.py` | — |
| **M2M / service-to-service** | Machine to Machine | Program ngomong ke program, tanpa manusia login | Auth pakai service token | — | information.md |
| **CORS** | Cross-Origin Resource Sharing | Aturan browser: halaman dari domain A boleh manggil API domain B atau tidak | Middleware FastAPI, `CORS_ALLOWED_ORIGINS` | `apps/api/main.py` | MUST_READ |
| **Webhook** | — | Kebalikan polling: "kalau ada kabar, telepon aku" | **Tidak dipakai** di project ini | — | information.md |
| **Polling** | — | Menelepon berkala menanyakan kabar | Pola yang dipakai (pull) | — | — |
| **Request ID** | — | Nomor resi untuk melacak satu permintaan di log | Header `X-Request-ID`, ikut di error envelope | `apps/api/main.py` | — |
| **Error envelope** | — | Bentuk baku balasan error | `{"error":{"code","message","request_id"}}` | Jalur `/api/integration/` | — |
| **HTTP 202 Accepted** | — | "Diterima, dikerjakan nanti" — beda dari 200 "sudah selesai" | Status enqueue crawl | `integration_crawl_jobs.py:46` | — |
| **OpenAPI / Swagger** | — | Dokumentasi API yang bisa dicoba langsung dari browser | `/api/docs`, `/api/openapi.json` | `apps/api/main.py` | apps.md |
| **whoami** | — | "Saya ini siapa menurutmu?" — cek token berlaku untuk siapa | `GET /api/integration/v1/whoami` | — | VOC-CS-03 |
| **Contract test** | — | Test yang memastikan bentuk data tidak berubah diam-diam | Fixture deterministik | `test_integration_api_contract.py` | VOC-CS-06 |

## 5.6 Database & ORM

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **ORM** | Object Relational Mapping | Penerjemah: kamu nulis Python, dia yang nulis SQL | SQLAlchemy 2.x | `app/db/models.py` | apps.md |
| **Model** | — | Kelas Python yang mewakili satu tabel | `class Review(Base)` | `models.py` | — |
| **Migration** | — | Catatan perubahan bentuk database, berurutan — seperti riwayat renovasi rumah | Skrip Alembic naik/turun versi | `alembic/versions/*.py` | — |
| **Alembic** | — | Alat pencatat migration untuk SQLAlchemy | — | `alembic/`, `alembic.ini` | — |
| **Revision** | — | Satu langkah migration, punya ID | `revision`/`down_revision` | `20260729_0002` | — |
| **Head** | — | Migration paling baru | `alembic upgrade head` | — | entrypoint.sh |
| **Seeding** | — | Mengisi data awal supaya sistem bisa dipakai (menu, role, user) | Skrip INSERT terpisah dari migration | `voc_setup_all.sql` (OneBox) | VOC_DBEAVER_SEEDING |
| **Upsert** | — | "Kalau ada update, kalau belum ada insert" | Pola di worklist sync | `worklist_sync_service.py` | VOC-CS-08 |
| **Index** | — | Daftar isi buku — biar tidak baca dari halaman 1 | Struktur pencarian cepat | `idx_reviews_company_sync_id` | models.py |
| **FK** | Foreign Key | Kolom yang menunjuk baris di tabel lain | `ForeignKey("companies.id")` | Semua tabel anak | models.py |
| **PK** | Primary Key | Nomor identitas unik tiap baris | `id` integer | Semua tabel | models.py |
| **Unique constraint** | — | Aturan "nilai ini tidak boleh kembar" | `UniqueConstraint(...)` | `uq_locations_source_place` | models.py |
| **Check constraint** | — | Aturan isi kolom, mis. rating harus 1–5 | `CheckConstraint(...)` | `ck_reviews_rating` | models.py |
| **CASCADE** | — | Hapus induk → anak ikut terhapus | `ondelete="CASCADE"` | Semua FK ke `companies` | models.py |
| **JSONB** | — | Kolom yang isinya JSON, bisa dicari isinya (khas Postgres) | `JSON().with_variant(JSONB,"postgresql")` | `raw_payload`, `scopes` | models.py:27 |
| **SKIP LOCKED** | — | "Baris ini lagi dipegang orang lain, lewati saja" — supaya banyak worker tidak rebutan | `SELECT … FOR UPDATE SKIP LOCKED` | `crawl_job_service.py:228` | ADR-0003 |
| **Transaction** | — | Sekelompok perubahan: semua berhasil, atau semua batal | `session.commit()` | — | — |
| **Session / session factory** | — | Sesi percakapan dengan database | `sessionmaker` SQLAlchemy | `app/db/session.py` | — |
| **Watermark column** | — | Kolom penanda progres sinkronisasi | `sync_updated_at` (tanpa `onupdate`) | `reviews` | models.py:372 |
| **Append-only** | — | Cuma boleh nambah, tidak boleh ubah/hapus | Analisa baru = baris baru | `review_analysis` | ADR-0003 |
| **Dedup** | Deduplication | Buang yang kembar | `review_hash` unique global | `reviews.review_hash` | ADR-0003 |
| **Hash** | — | Sidik jari dari sepotong data | Kunci dedup dari author+tanggal+teks | `app/utils/hashing.py` | — |
| **Supabase** | — | Layanan hosting Postgres siap pakai | DB produksi saat ini (free tier) | `DATABASE_URL` | PROJECT_STATUS |
| **Pooler** | — | Penampung koneksi DB supaya tidak buka-tutup terus | Endpoint Supabase | `DATABASE_URL` | CARA_JALANIN_DOCKER |
| **PostgreSQL** | — | Database relasional yang dipakai sekarang | — | `psycopg2-binary` | — |
| **MySQL** | — | Database tujuan migrasi (ADR-0004) | Belum dieksekusi | — | PROJECT_STATUS |
| **SQLite** | — | Database file kecil, dipakai untuk test | — | tests | integration_schemas.py |

## 5.7 Crawling & scraping

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **Crawling** | — | Menjelajah halaman web secara otomatis | Proses mengunjungi + mengambil | Seluruh repo | Semua |
| **Scraping** | — | Mengambil isi halaman web dengan "membaca layar" | Ekstrak elemen HTML | `selenium_google_maps_client.py` | ADR-0001 |
| **Selenium** | — | Robot yang menyetir browser sungguhan | Library otomasi browser | `selenium>=4.27` | Semua |
| **Chromium** | — | Browser (versi open-source Chrome) | Dipasang di Docker image | `Dockerfile:12` | — |
| **chromium-driver** | — | Penerjemah antara Selenium dan Chromium | Versinya harus cocok dengan browsernya | `Dockerfile:13` | — |
| **Headless** | — | Browser jalan tanpa jendela terlihat | `SELENIUM_HEADLESS=true` | `.env.example:68` | — |
| **User data dir** | — | Folder profil browser (cookie, sesi login) | Disimpan di volume Docker | `SELENIUM_USER_DATA_DIR` | docker-compose.yml |
| **Google Place ID** | — | Kode unik satu tempat di Google, mis. `ChIJ...` | Kunci identitas target crawl | `external_place_id` | VOC-CS-08 |
| **Google Places API** | — | Cara resmi & berbayar ambil data tempat dari Google | Alternatif scraping, review terbatas | `google_places_client.py` | .env.example |
| **GBP** | Google Business Profile | API resmi untuk pemilik lokasi — butuh kepemilikan akun | Mode `google_business_profile` | `.env.example:45` | developer_guide |
| **Firecrawl** | — | Layanan scraping pihak ketiga | Ada di dependency | `firecrawl-py` | FIRECRAWL_SETUP_ANALYSIS |
| **Scroll** | — | Menggulir halaman supaya review berikutnya muncul | Google memuat review bertahap | `SELENIUM_MAX_SCROLL_ATTEMPTS=100` | .env.example |
| **Selector** | — | Alamat elemen di halaman, mis. "div dengan class X" | CSS/XPath | `google_maps_selectors.py` | — |
| **Mock** | — | Data palsu untuk latihan, tidak menyentuh Google | `REVIEW_SOURCE_MODE=mock` | `mock_review_client.py` | .env.example |
| **Fetch** | — | Sekali operasi ambil data | Satu `fetch_location()` | `fetch_service.py` | — |
| **Fetch job** | — | Satu tugas ambil data | Endpoint + tabel log | `/api/fetch-jobs`, `fetch_logs` | — |
| **ToS** | Terms of Service | Syarat & ketentuan — scraping bisa melanggar | Risiko yang dicatat, belum diputuskan | — | developer_guide §6.1 |

## 5.8 AI & analisis

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **LLM** | Large Language Model | Model AI yang paham & menulis bahasa manusia | Gemini/OpenAI-compatible | `app/integrations/*_client.py` | ADR-0002 |
| **Prompt** | — | Perintah yang dikirim ke AI | Template teks | `PROMPT_VERSION=v1` | .env.example |
| **Prompt version** | — | Nomor versi perintah — supaya tahu hasil ini dari perintah yang mana | Disimpan bersama hasil | `review_analysis.prompt_version` | ADR-0002 |
| **Token** | — | Potongan kata; AI dihitung biayanya per token | Satuan penagihan LLM | `tokens_used` (**belum ada**) | ADR-0002 |
| **Metering** | — | Meteran pemakaian, seperti meteran listrik | `BenefitService::addUsage()` | OneBox | ADR-0002 |
| **Gemini** | — | LLM buatan Google | `google-genai` | `gemini_client.py` | — |
| **OpenRouter** | — | Perantara ke banyak LLM sekaligus | `openrouter_client.py` | — | — |
| **Ollama** | — | Cara menjalankan LLM di komputer sendiri | `LOCAL_LLM_BASE_URL` port 11434 | `.env.example:57` | — |
| **qwen2.5:7b** | — | Nama model LLM lokal yang dipakai | `LOCAL_LLM_MODEL` | `.env.example:59` | — |
| **Batch** | — | Diproses berombongan, bukan satu-satu | `ANALYSIS_BATCH_SIZE=20` | .env.example | — |
| **Rule-first** | — | Pakai aturan sederhana dulu, AI cuma untuk yang sulit — hemat biaya | `Service\Ruling` di OneBox | OneBox | LABELING_rule-first, ADR-0002 |
| **Threshold** | — | Ambang: mis. hanya review ≤3 bintang yang dianalisa AI | Parameter dari OneBox (**belum ada**) | — | ADR-0002 |

## 5.9 Deployment & infrastruktur

| Istilah | Kepanjangan | Penjelasan awam | Penjelasan teknis | Wujudnya | Muncul di |
|---|---|---|---|---|---|
| **Docker** | — | Kotak berisi aplikasi + semua kebutuhannya, jalan sama di mana saja | Container runtime | `Dockerfile` | — |
| **Image** | — | Cetakan/blueprint kotak | Hasil `docker build` | `ghcr.io/sayyidtrq/herminacrawler` | docker-compose.yml |
| **Container** | — | Kotak yang sedang jalan | Instance dari image | `hermina-review-api` | docker-compose.yml |
| **Volume** | — | Lemari yang isinya tidak hilang saat kotak diganti | Storage persisten | `selenium-profile` | docker-compose.yml |
| **Compose** | — | Resep menjalankan beberapa container sekaligus | `docker compose up` | `docker-compose.yml` | CARA_JALANIN_DOCKER |
| **Healthcheck** | — | Pemeriksaan berkala "kamu masih hidup?" | `curl -f /api/health` tiap 15s | docker-compose.yml | — |
| **Entrypoint** | — | Perintah pertama saat container nyala | Jalankan migration lalu uvicorn | `entrypoint.sh` | — |
| **GHCR** | GitHub Container Registry | Gudang image milik GitHub | `ghcr.io/...` | deploy.yml | — |
| **CI/CD** | Continuous Integration / Deployment | Robot yang otomatis test + build + deploy tiap push | GitHub Actions | `.github/workflows/deploy.yml` | CI_CD_SETUP |
| **Self-hosted runner** | — | Robot CI yang jalan di server sendiri, bukan milik GitHub | `runs-on: self-hosted` | deploy.yml | — |
| **ARM64 / aarch64** | — | Jenis prosesor Mac M1/M2/M3 | Arsitektur CPU | — | **[belum ada di repo]** |
| **amd64 / x86_64** | — | Jenis prosesor Intel/AMD, umum di server | Arsitektur CPU | — | **[belum ada di repo]** |
| **OrbStack** | — | Alternatif Docker Desktop untuk Mac | — | — | **[belum ada di repo]** |
| **WireGuard** | — | Terowongan jaringan privat (VPN) antar server | Menghubungkan `10.13.13.x` | — | NETWORK_WIREGUARD_CORS |
| **Reverse proxy** | — | Resepsionis yang meneruskan tamu ke ruangan yang tepat | Traefik di sisi OneBox | — | VOC_DEV_TASKLIST P1 |
| **Traefik** | — | Merek reverse proxy yang dipakai OneBox | Publish :80/:443 | — | VOC_DEV_TASKLIST |
| **Swarm** | — | Cara Docker mengelola banyak server sekaligus | Dipakai OneBox, **bukan** Crawler | `docker stack` | local-dev-setup-guide |
| **Stack** | — | Sekelompok service yang dideploy bareng | `dev_DNGO19-3346` | — | local-dev-setup-guide |
| **WSL** | Windows Subsystem for Linux | Linux di dalam Windows | Environment dev OneBox | — | local-dev-setup-guide |
| **Swoole** | — | Mesin yang bikin PHP bisa jalan cepat & async | Runtime OneBox | — | developer_guide |
| **Phalcon** | — | Framework PHP yang dipakai OneBox | — | — | — |
| **Volt** | — | Bahasa template (HTML) milik Phalcon | `*.volt` | OneBox | RI-10 |
| **Gearman** | — | Sistem antrean job milik OneBox | — | OneBox | developer_guide |
| **Jenkins** | — | Robot CI/CD yang dipakai OneBox | Auto-build saat merge ke `feature/voc` | — | PLAN_KEY_PROCESS_DEMO |
| **uvicorn** | — | Server yang menjalankan aplikasi FastAPI | ASGI server | `entrypoint.sh:15` | — |

## 5.10 Bahasa, framework & library

| Istilah | Penjelasan awam | Wujudnya di project |
|---|---|---|
| **Python 3.11** | Bahasa utama Crawler System | `Dockerfile:1` |
| **FastAPI** | Framework bikin REST API di Python, otomatis bikin dokumentasi | `apps/api/` |
| **Pydantic v2** | Pengecek bentuk data — nolak kalau field salah tipe | Semua schema |
| **SQLAlchemy 2.x** | ORM | `app/db/` |
| **httpx** | Library untuk memanggil API lain | `onebox_worklist_client.py` |
| **PyJWT** | Bikin & verifikasi JWT | `auth.py` |
| **passlib[bcrypt]** | Mengacak password supaya aman disimpan | `auth.py` |
| **pytest** | Alat menjalankan test | `tests/` |
| **ruff** | Pemeriksa gaya penulisan kode Python | `requirements.txt` |
| **rich / tabulate** | Bikin tampilan terminal rapi | `app/terminal/` |
| **pandas** | Olah data tabel, dipakai untuk export | `export_service.py` |
| **beautifulsoup4** | Pembaca HTML | — |
| **Next.js 16** | Framework React untuk FE (sudah dipensiunkan) | `herminaCrawler-fe/` |
| **React 19** | Library UI | `herminaCrawler-fe/` |
| **Tailwind CSS 4** | Cara menulis style langsung di class HTML | `herminaCrawler-fe/` |
| **Zod** | Pengecek bentuk data versi TypeScript | `herminaCrawler-fe/` |
| **Leaflet** | Library peta | `herminaCrawler-fe/` |
| **Mermaid** | Cara menggambar diagram pakai teks | Blok ```mermaid di MD |

## 5.11 Struktur repo — apa isi tiap folder

| Path | Isinya |
|---|---|
| `app/` | **Inti bisnis** — dipakai bersama terminal & API |
| `app/config.py` | Baca & validasi `.env` |
| `app/db/` | Model, session, base SQLAlchemy |
| `app/integrations/` | Client ke dunia luar (Google, LLM, OneBox) |
| `app/services/` | Logika bisnis (15 file) |
| `app/terminal/` | Menu CLI |
| `app/utils/` | Helper: hashing, cursor, tanggal, logger |
| `apps/` | **Entrypoint produk** (perhatikan huruf "s") |
| `apps/api/` | REST API FastAPI |
| `apps/api/app_api/routers/` | 15 router endpoint |
| `alembic/versions/` | 8 file migration |
| `scripts/` | Utilitas CLI: refresh worklist, worker, kelola token, setup profil Selenium |
| `tests/` | 9 file test |
| `markdowns/` | 97 file dokumentasi |
| `markdowns/decisions/` | ADR, SPEC, BRAINSTORM — **otoritas tertinggi** |
| `markdowns/integrations/` | Rencana & runbook integrasi |
| `markdowns/markdown-hc/` | Arsip era standalone |
| `markdowns/crawler_system/`, `onebox_system/` | ERD & DFD (crawler_system sudah SUPERSEDED) |
| `herminaCrawler-fe/` | FE Next.js — punya git sendiri, dead code untuk produksi |
| `exports/` | Hasil export CSV/JSON |
| `main.py` | Entrypoint aplikasi terminal |

## 5.12 Environment variable (semua, dari `.env.example`)

| Variabel | Fungsi | Default |
|---|---|---|
| `APP_ENV` | `local`/`test`/lainnya — menentukan seberapa ketat validasi secret | `local` |
| `APP_NAME` | Nama aplikasi di response health | `Voice of Customer Crawler System` |
| `LOG_LEVEL` | Seberapa cerewet log | `INFO` |
| `EXPORT_DIR` | Folder hasil export | `exports` |
| `DATABASE_URL` | **Wajib.** Alamat database | — |
| `JWT_SECRET_KEY` | **Wajib di luar local.** Kunci tanda tangan JWT | — |
| `SERVICE_TOKEN_PEPPER` | **Wajib di luar local.** Bumbu rahasia hash service token | — |
| `INTEGRATION_CURSOR_SECRET` | **Wajib di luar local.** Tanda tangan cursor — kalau bocor, orang bisa memalsukan cursor tenant lain | — |
| `CORS_ALLOWED_ORIGINS` | Daftar domain browser yang boleh memanggil | `localhost:3000` |
| `ONEBOX_BASE_URL` | Alamat OneBox | kosong |
| `ONEBOX_SVC_EMAIL` / `_PASSWORD` | Kredensial akun layanan | kosong |
| `ONEBOX_SITE_ID` | Site OneBox yang dilayani | kosong |
| `ONEBOX_COMPANY_ID` | Company Crawler tujuan — **eksplisit, tidak boleh ditebak** | kosong |
| `ONEBOX_WORKLIST_PATH` | Path endpoint worklist | `/api/VocWorklist` |
| `ONEBOX_TIMEOUT_SECONDS` / `_MAX_RETRY` | Batas sabar & jumlah coba ulang | `30` / `3` |
| `ONEBOX_WORKLIST_CACHE_STALE_AFTER_SECONDS` | Umur cache sebelum dianggap basi | `86400` (1 hari) |
| `REVIEW_SOURCE_MODE` | Sumber review: `mock`/`google_places`/`google_business_profile`/`third_party`/`selenium` | `mock` |
| `GOOGLE_MAPS_API_KEY` | Kunci API Google | kosong |
| `GOOGLE_PLACES_LANGUAGE_CODE` / `_REGION_CODE` | Bahasa & wilayah | `id` / `ID` |
| `LOCAL_LLM_BASE_URL` / `_API_KEY` / `_MODEL` | Konfigurasi LLM lokal | Ollama, `qwen2.5:7b` |
| `FETCH_LIMIT_PER_LOCATION` | Maks review per lokasi per fetch | `50` |
| `FETCH_TIMEOUT_SECONDS` / `FETCH_MAX_RETRY` | Batas & retry fetch | `30` / `3` |
| `SELENIUM_HEADLESS` | Browser tanpa jendela | `false` |
| `SELENIUM_DEFAULT_TARGET_REVIEWS` / `_MAX_` | Target jumlah review | `100` / `300` |
| `SELENIUM_SCROLL_DELAY_SECONDS` | Jeda antar scroll (minimal dipaksa 2) | `2` |
| `SELENIUM_MAX_SCROLL_ATTEMPTS` | Maks scroll (dibatasi 100) | `100` |
| `SELENIUM_WAIT_TIMEOUT_SECONDS` | Sabar menunggu elemen muncul | `20` |
| `SELENIUM_USER_DATA_DIR` | Folder profil browser | `.selenium-profile` |
| `ANALYSIS_BATCH_SIZE` | Review per batch analisa | `20` |
| `PROMPT_VERSION` | Versi prompt AI | `v1` |
| `PAGE_SIZE` | Ukuran halaman default | `20` |
| `SHOW_RAW_PAYLOAD` | Tampilkan payload mentah — **jangan `true` di shared/prod** | `false` |
| `CRAWL_WORKER_LEASE_SECONDS` | Lama sewa job (min 60) | `900` |
| `CRAWL_WORKER_MAX_ATTEMPTS` | Maks percobaan | `3` |
| `CRAWL_WORKER_POLL_SECONDS` | Jeda cek antrean | `5` |
| `CRAWL_WORKER_RETRY_BASE_SECONDS` | Dasar hitungan backoff | `60` |
| `SKIP_MIGRATIONS` | Lewati migration saat start (dipakai worker) | `false` |

## 5.13 Sering tertukar — bacaan wajib

### `app/` vs `apps/`
`app/` (tanpa s) = **inti bisnis**. `apps/` (dengan s) = **entrypoint produk**. Beda satu huruf, beda peran total. Kalau kamu mau ubah logika, itu di `app/`. Kalau mau ubah bentuk endpoint, itu di `apps/`.

### Migration vs Seeding
**Migration** mengubah **bentuk** database (tambah tabel/kolom). **Seeding** mengisi **isi** database (data awal: menu, role, user). Migration wajib jalan di semua environment; seeding biasanya cuma di dev. Di project ini migration otomatis saat container start [terverifikasi], seeding manual.

### Push vs Pull
**Push** = pengirim yang memanggil ("kuantar ke rumahmu"). **Pull** = penerima yang memanggil ("kuambil sendiri"). Project ini **dulu push, sekarang pull**, dan itu perubahan besar yang jadi isi ADR-0003. Kalau kamu baca dokumen yang menyebut push, cek tanggalnya.

### Dua arah pull yang berbeda
Sama-sama pull, tapi **berlawanan arah dan beda isi**:
- **Crawler → OneBox**: menarik **worklist** (konfigurasi turun — "apa yang harus kucrawl?")
- **OneBox → Crawler**: menarik **review** (hasil naik — "apa yang sudah kamu dapat?")

Bukan redundansi. Masing-masing membaca data otoritatif milik sisi lain.

### Crawl cursor vs Ingestion checkpoint
Dua-duanya disebut "cursor" dan ADR-0003 secara khusus memperingatkan **jangan dicampur**:

| | Crawl cursor | Ingestion checkpoint |
|---|---|---|
| Ada di | Crawler | OneBox |
| Per | target/lokasi | SiteId |
| Artinya | sampai mana Selenium sudah scrape | sampai mana OneBox sudah tarik review jadi Ticket |
| Status | **belum diimplementasi** (M3-01) | ada di RI-08 |

### ADR vs SPEC vs BRAINSTORM
Urutan hidupnya: **BRAINSTORM** (eksplorasi, banyak opsi, belum keputusan) → **ADR** (keputusan arsitektur, "kami pilih X karena Y") → **SPEC** (rencana detail implementasi turunan ADR). Kalau ketiganya membahas topik sama, **ADR yang menang**; SPEC menjabarkan, BRAINSTORM cuma histori.

### OneBox vs Crawler System
| | OneBox | Crawler System |
|---|---|---|
| Punya UI? | Ya | Tidak |
| Punya master data? | Ya | Tidak (cuma cache) |
| Punya scheduler? | Ya (satu-satunya) | Tidak — **jangan bikin scheduler kedua** |
| Menjalankan Selenium? | **Tidak, dilarang** | Ya |
| Bahasa | PHP | Python |

### `updated_at` vs `sync_updated_at`
`updated_at` bergerak otomatis tiap baris berubah. `sync_updated_at` **hanya** digerakkan penulis secara eksplisit, dan itulah yang dipakai OneBox untuk paging. Kalau kamu menambah kolom yang perlu memicu re-sync ke OneBox, kamu harus menggerakkan `sync_updated_at` **secara sengaja** — kalau tidak, OneBox tidak akan pernah tahu ada perubahan.

### JWT vs Service token
**JWT** = kartu identitas yang isinya bisa dibaca siapa saja (tapi tanda tangannya tidak bisa dipalsu), dipakai user login, kedaluwarsa 7 hari. **Service token** = string acak yang tidak berarti apa-apa sampai dicek ke tabel `api_clients`, dipakai mesin, bisa dicabut kapan saja. Crawler memakai JWT saat memanggil OneBox; OneBox memakai service token saat memanggil Crawler.

### `locations` vs `competitors`
Struktur hampir sama, tapi: `competitors.crawl_enabled` dan `ingest_reviews` default **false** (kompetitor tidak otomatis di-crawl), dan unique constraint-nya menyertakan `company_id` (dua company boleh memantau kompetitor yang sama; dua company tidak boleh punya lokasi dengan place ID sama).

### Blocking vs Non-blocking
**Blocking**: `POST /api/fetch-jobs` — kamu tunggu sampai Selenium selesai, bisa menit-menit. **Non-blocking**: `POST /api/integration/v1/crawl-jobs` — dijawab 202 + `batch_id` dalam milidetik, kerjanya di belakang. ADR-0003 memindahkan semua ke pola kedua.

### Company vs Site
**`company_id`** = tenant di sisi **Crawler**. **`site_id`** = tenant di sisi **OneBox**. Dua nomor berbeda untuk penyewa yang sama. Jembatan antara keduanya adalah kolom `companies.onebox_site_id` yang **belum ada** — itulah persisnya yang dibangun SPEC multi-tenant.

## 5.14 Catatan penutup kamus

**Total istilah terdaftar: 233** — tersebar di 12 kategori (§5.1–5.12) plus 12 pasangan "sering tertukar" (§5.13).

**Istilah yang saya temukan tapi TIDAK bisa saya jelaskan karena konteksnya tidak ada di repo:**

| Istilah | Muncul di | Kenapa tidak bisa dijelaskan |
|---|---|---|
| **ADR-0004** | `PROJECT_STATUS.md` (4×) | Disebut sebagai keputusan migrasi DB Postgres→MySQL, tapi **filenya tidak ada** di repo. Isi lengkap keputusannya tidak bisa saya verifikasi |
| **`CNS2` / `CNS3`** | ADR-0001, ADR-0003, VOC_DEV_TASKLIST | Kode `StatusId` di tabel `Connection` OneBox. Efeknya diketahui ("`CNS3` supaya tidak disapu penjadwal"), tapi daftar lengkap kode status tidak ada di repo ini |
| **`Connection.Options`** | ADR-0001, PROMPT_execute-redesign | Kolom JSON di OneBox yang menyimpan konfigurasi per koneksi. Beberapa key disebut (`company_id`, `_sync_cursor`, `Url`, `api_mode`, `service_token`, `location_map`), tapi skema lengkapnya di repo OneBox |
| **`Service\Ruling`** | ADR-0002, LABELING_rule-first | Mesin aturan klasifikasi OneBox. Cara kerja & format `Rule.Conditions/Actions` tidak ada di repo ini |
| **`getUserAllRole`** | VOC_DEV_TASKLIST M0-07 | Fungsi OneBox dengan bug SQL `IN ()`. Kodenya di repo OneBox |
| **`voc_setup_all.sql`** | PROJECT_STATUS | Skrip seed menu & permission. Ada di repo OneBox |
| **`dev_DNGO19-3346`** | VOC_DEV_TASKLIST P1 | Nama Docker Swarm stack di environment dev OneBox. Cara pembuatannya ada di `local-dev-setup-guide.md`, tapi environment-nya bukan di repo ini |
| **`space.datakelola.com`** | PLAN_KEY_PROCESS_DEMO B2 | Host yang salah di konfigurasi Connection dev. Tidak dijelaskan ini layanan apa |
| **`10.13.13.42` / `10.13.13.90`** | PLAN_KEY_PROCESS_DEMO B3 | IP dev OneBox & server crawler di jaringan WireGuard. Topologi jaringan lengkapnya tidak ada di repo |
| **`CiptalifeApi.php`** | developer_guide §6.2 | Contoh pola client REST + JWT di OneBox yang jadi acuan. Kodenya di repo OneBox |

Semua yang tidak bisa saya jelaskan punya satu pola sama: **letaknya di repo OneBox.** Ini konsekuensi wajar dari repo ini cuma memegang separuh sistem. Untuk sepuluh istilah ini, orang yang bisa menjawab adalah yang punya akses OneBox.

---

# 6. Alur Kerja Developer

## 6.1 Setup dari nol — jalur lokal (tanpa Docker)

Semua perintah dijalankan dari root repo. Perintah di bawah **disesuaikan dengan isi repo ini**, bukan generik.

```bash
# 1. Clone
git clone https://github.com/sayyidtrq/herminaCrawler.git
cd herminaCrawler

# 2. Virtualenv (Python 3.11 — sesuai Dockerfile)
python3.11 -m venv venv
source venv/bin/activate            # macOS/Linux
# venv\Scripts\activate             # Windows

# 3. Dependency
#    apps/api/requirements.txt sudah include requirements.txt lewat "-r ../../requirements.txt"
#    jadi cukup satu perintah ini
pip install -r apps/api/requirements.txt

# 4. Environment
cp .env.example .env
```

Isi minimal `.env` supaya bisa jalan tanpa menyentuh Google atau OneBox:

```dotenv
APP_ENV=local
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/voc_crawler
REVIEW_SOURCE_MODE=mock
```

Untuk `APP_ENV=local`, `JWT_SECRET_KEY` / `SERVICE_TOKEN_PEPPER` / `INTEGRATION_CURSOR_SECRET` boleh kosong — `config.py` memakai fallback khusus lokal. **Di luar local, aplikasi menolak start tanpa ketiganya** [terverifikasi — `config.py:132-158`]. Ini disengaja.

```bash
# 5. Migration (bikin semua tabel)
python -m alembic upgrade head

# 6. Jalankan API
python -m uvicorn apps.api.main:app --reload --port 8000

# 7. Smoke test (terminal lain)
curl http://localhost:8000/api/health

# 8. Swagger — PERHATIKAN: /api/docs, bukan /docs
open http://localhost:8000/api/docs

# 9. Test
python -m pytest tests -q --ignore=tests/test_real_integrations.py --ignore=tests/test_selenium_scraping.py
# harusnya: 69 passed
```

### Seeding

**Tidak ada skrip seeding otomatis untuk Crawler System** [terverifikasi — tidak ada `seed.py`/`seeds/`]. Data awal dibuat lewat:

```bash
# Bikin company + user pertama lewat API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Test Co","email":"dev@local","password":"<password-kuat>","full_name":"Dev"}'
```

> Cek `apps/api/app_api/routers/auth.py` untuk field persisnya — ada validasi password policy di `validate_password_policy()`.

```bash
# Terbitkan service token untuk simulasi OneBox
python -m scripts.manage_api_client issue --company-id 1 --name "onebox-dev" \
  --scope reviews:read --scope crawl:enqueue --scope crawl:read

# Lihat token yang ada
python -m scripts.manage_api_client list --company-id 1
```

`voc_setup_all.sql` yang disebut di `PROJECT_STATUS.md` adalah seed **untuk OneBox**, bukan repo ini.

## 6.2 Setup via Docker

```bash
cp .env.example .env      # isi DATABASE_URL yang valid
docker compose up -d
docker compose ps         # api harus "healthy"
docker compose logs -f api
curl http://localhost:8000/api/health
```

Yang terjadi otomatis: image di-build (atau di-pull dari GHCR) → `entrypoint.sh` jalankan `alembic upgrade head` → uvicorn start di port 8000. Setelah `api` healthy, `crawl-worker` ikut nyala dengan `SKIP_MIGRATIONS=true` dan `SELENIUM_HEADLESS=true` [terverifikasi].

> ⚠️ **Peringatan yang ada di `CARA_JALANIN_DOCKER.md` dan layak diulang:** migration jalan terhadap DB di `DATABASE_URL` **tiap container start**. Kalau `.env`-mu menunjuk ke Supabase produksi, migration jalan di produksi. Pastikan `DATABASE_URL` menunjuk ke DB yang benar sebelum `docker compose up`.

## 6.3 Perintah operasional harian

```bash
# Tarik worklist dari OneBox (butuh ONEBOX_* di .env)
python -m scripts.refresh_worklist --json
python -m scripts.refresh_worklist --company-id 1 --json

# Jalankan worker antrean crawl
python -m scripts.run_crawl_worker                 # loop terus
python -m scripts.run_crawl_worker --once          # satu job lalu keluar
python -m scripts.run_crawl_worker --worker-id dev-1

# Siapkan profil browser Selenium (untuk sesi login Google)
python -m scripts.setup_selenium_profile

# Kelola service token
python -m scripts.manage_api_client issue --company-id 1 --name onebox
python -m scripts.manage_api_client list
python -m scripts.manage_api_client revoke --key-id <key> --yes
python -m scripts.manage_api_client rotate --key-id <key> --overlap-hours 24

# Menu terminal interaktif
python main.py

# Lint
ruff check .
```

## 6.4 Troubleshooting

### `DATABASE_URL is required in .env`
`config.py` menolak start tanpa `DATABASE_URL`. Cek `.env` **ada di root repo** — `config.py` memuat `BASE_DIR/.env` di mana `BASE_DIR` = root repo [terverifikasi `config.py:11-12`].

### `INTEGRATION_CURSOR_SECRET is required when APP_ENV is not local`
Kamu set `APP_ENV` selain `local`. Entah kembalikan ke `local`, atau isi ketiga secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### `JWT_SECRET_KEY ... must be set to a unique secret outside local/test`
Sama seperti di atas. Nilai yang diawali `change-me` **ditolak** — itu sengaja, supaya nilai contoh tidak pernah lolos ke produksi [terverifikasi `config.py:139`].

### Swagger 404 di `/docs`
Path-nya **`/api/docs`**. OpenAPI JSON di **`/api/openapi.json`**, bukan `/openapi.json`. Ini sudah tercatat sebagai jebakan di tasklist P4.

### `OneBox worklist integration is not configured: ONEBOX_BASE_URL, ...`
Variabel `ONEBOX_*` belum diisi. `refresh_worklist` butuh keempatnya: base URL, email, password, site ID — plus `ONEBOX_COMPANY_ID` di sisi service [terverifikasi].

### `OneBox authentication failed` / timeout
Tiga kemungkinan berurut:
1. Kredensial salah — akun dev yang valid tercatat `voc.dev@onebox.local` / siteId `169`; `test@gmail.com` **tidak valid** [dokumen — tasklist P3]
2. **Jaringan tidak tembus** — prasyarat P5 (Crawler → OneBox) masih `todo`. Laptop lokal **tidak bisa** menjangkau server crawler/OneBox karena WireGuard [dokumen — `PLAN_KEY_PROCESS_DEMO.md` B3]
3. OneBox dev mati

### Test gagal karena Selenium/jaringan
Kecualikan dua file yang butuh dunia luar:
```bash
python -m pytest tests -q --ignore=tests/test_real_integrations.py --ignore=tests/test_selenium_scraping.py
```
CI juga mengecualikan `test_real_integrations.py` [terverifikasi — `deploy.yml`].

### Selenium tidak jalan di container
Ini **blocker terbuka**, bukan salah setup kamu. Catatan lama menyebut butuh login Google manual lewat GUI [dokumen, ditandai `[assumption]`]. Kalau kamu kena ini, kamu sedang menyentuh GAP-1 (§4.8) — laporkan, jangan dipaksakan.

Profil browser disimpan di volume `selenium-profile` supaya sesi login bertahan antar restart [terverifikasi — `docker-compose.yml:39`].

### `alembic upgrade head` gagal / tabel sudah ada
Cek versi sekarang:
```bash
python -m alembic current
python -m alembic history
```
Head saat ini `20260729_0002`.

### Supabase lambat / error 500 acak
Ini **blocker nomor 1** yang sudah diketahui, bukan bug kamu. Supabase free tier tidur saat idle [dokumen]. Panggilan pertama setelah idle bisa lambat atau gagal — coba lagi.

## 6.5 Docker ARM64 (Mac) vs server x86_64

> **[belum ada]** — Tidak ada satu pun penyebutan ARM64, arm64, amd64, x86_64, atau OrbStack di seluruh repo [terverifikasi — grep ke semua `.md`, `.yml`, `.yaml`]. Jadi masalah ini **tidak terdokumentasi**. Yang berikut adalah **[analisis]** saya dari bukti di repo, bukan pernyataan yang tertulis di repo.

**Bukti di repo:**
1. `.github/workflows/deploy.yml` build pakai `docker/build-push-action@v6` **tanpa parameter `platforms:`** [terverifikasi]
2. Runner-nya `ubuntu-latest` = **amd64**
3. `docker-compose.yml` menunjuk `image: ghcr.io/sayyidtrq/herminacrawler:latest` [terverifikasi]

**Konsekuensinya [analisis]:** image yang dipublish ke GHCR kemungkinan besar **amd64-only**. Di Mac Apple Silicon (M1/M2/M3), `docker compose pull` akan mengambil image amd64 dan menjalankannya lewat emulasi QEMU — **jalan, tapi lambat**, dan Chromium di bawah emulasi bisa jauh lebih lambat atau tidak stabil.

**Cara mengecek arsitektur image:**
```bash
docker image inspect ghcr.io/sayyidtrq/herminacrawler:latest --format '{{.Architecture}}'
docker manifest inspect ghcr.io/sayyidtrq/herminacrawler:latest
```

**Kalau kamu di Mac Apple Silicon, tiga pilihan:**

**(a) Build lokal — paling sederhana.** `docker-compose.yml` masih punya blok `build:`, jadi:
```bash
docker compose build api
docker compose up -d
```
Image dibangun untuk arsitektur laptopmu.

**(b) Paksa platform** — kalau tetap mau pakai image dari registry:
```bash
docker compose pull --platform linux/amd64
# atau tambahkan "platform: linux/amd64" per service di compose
```
Jalan, tapi lambat karena emulasi.

**(c) Jangan pakai Docker untuk dev sehari-hari.** Jalur lokal (§6.1) tidak kena masalah ini sama sekali. Untuk mayoritas pekerjaan (API, migration, test), ini pilihan tercepat.

**Yang layak diusulkan ke tim [analisis]:** tambahkan `platforms: linux/amd64,linux/arm64` di step build-and-push `deploy.yml` supaya image jadi multi-arch. Biayanya waktu build lebih lama; untungnya dev Mac tidak perlu build sendiri. Ini keputusan tim, bukan sesuatu yang sebaiknya kamu ubah sendirian di minggu pertama.

---

# 7. Alur Kerja Tim & Konvensi Dokumentasi

## 7.1 Kenapa ada folder `decisions/`

Karena keputusan arsitektur punya sifat yang berbeda dari dokumentasi biasa: **ia harus bisa dilacak alasannya bertahun-tahun kemudian.**

Contoh nyata dari repo ini: kalau kamu buka `herminaCrawler-fe/` dan lihat ada FE Next.js lengkap 12 halaman, wajar kamu bertanya "kenapa ini tidak dipakai?". Tanpa ADR-0001, jawabannya hilang bersama orang yang memutuskan. Dengan ADR-0001, kamu bisa baca sendiri: keputusan bisnis berubah, VoC jadi fitur OneBox, UI produksi pindah, FE ini jadi dead code — lengkap dengan konsekuensi dan alternatif yang ditolak.

Itu yang membedakan `decisions/` dari `integrations/`: yang satu menyimpan **kenapa**, yang lain menyimpan **bagaimana**.

## 7.2 Empat jenis dokumen dan kapan dipakai

| Jenis | Isinya | Kapan dibuat | Statusnya |
|---|---|---|---|
| **BRAINSTORM** | Eksplorasi: pertanyaan, temuan, beberapa opsi dengan plus-minus, rekomendasi, pertanyaan yang belum terjawab | Saat menghadapi masalah yang belum jelas bentuknya | "eksplorasi, belum keputusan" |
| **ADR** | Satu keputusan arsitektur: Context → Decision → Consequences → Alternatif yang ditolak | Saat keputusan diambil dan sulit dibatalkan | Accepted / Superseded / Amandemen |
| **SPEC** | Rencana detail implementasi: apa yang dibangun, di mana, urutannya, cara mengujinya | Setelah ADR, sebelum koding | "disetujui untuk diimplementasikan" |
| **PROMPT** | Naskah instruksi untuk AI agent | Saat mendelegasikan eksekusi ke agent | — |

Urutan hidupnya terlihat jelas di kasus multi-tenant [terverifikasi dari isi ketiga file]:

```
BRAINSTORM-multi-tenant-voc.md   →   SPEC-multi-tenant-opsi-c.md   →   (kode)
"ada 3 opsi, saya rekomendasi C"      "opsi C, ini detailnya"          belum ditulis
2026-07-28                            2026-07-28+
```

Perhatikan: BRAINSTORM **tidak dihapus** setelah SPEC dibuat. Ia jadi jejak "kenapa bukan opsi A atau B" — dan itu pertanyaan yang pasti muncul lagi nanti.

## 7.3 Aturan yang sudah berlaku

Dari `MUST_READ.md` [dokumen]:

1. **ADR adalah otoritas tertinggi.** Kalau dokumen lain bertentangan, ADR yang menang.
2. **Keputusan arsitektur berubah → buat ADR baru**, jangan edit yang lama. Format `ADR-####-nama.md`.
3. **Dokumen yang tidak berlaku diberi banner SUPERSEDED di 5 baris pertama**, lalu didaftarkan di `MUST_READ.md`. **Jangan dihapus** — nilai historisnya nyata.
4. **Jangan hardcode kredensial.** Jangan commit `.env`, `.env.local`, atau config dev pribadi.
5. **Tandai tiap klaim** `[verified]` / `[assumption]` / `[blocked]`. Jangan tulis "sudah jalan" tanpa bukti.
6. **API gap → handoff**, jangan ditambal di sisi yang salah. OneBox tidak boleh menambal kekurangan Crawler, begitu juga sebaliknya.
7. **ID task tidak pernah dinomori ulang.** Task batal → status `superseded`, bukan dihapus.
8. **Selesai = observable.** Bukti minimum: commit/PR, perintah test, curl tersanitasi (tanpa token), hasil aktual.

## 7.4 Konvensi penamaan

`MUST_READ.md` §Canonical Naming menetapkan nama resmi **"Voice of Customer System"**. Nama lama hanya boleh muncul saat membahas dokumen historis, repo/deployment lama, atau path yang sudah ada.

Realitanya nama lama masih bertebaran (nama repo, `APP_NAME` default, judul FastAPI). Untuk dokumen/task/class **baru**, pakai nama baru.

## 7.5 Git & branching

**Sisi Crawler System** [terverifikasi dari `git branch -a`]: branch `main` + branch per orang (`salman`, `sayyid`, `nana`, `cello`) + branch fitur agent (`codex/...`). CI jalan otomatis saat push ke `main`, dengan path filter — hanya file kode yang memicu build.

**Sisi OneBox** [dokumen — `PLAN_KEY_PROCESS_DEMO.md` §3, aturan Pak Agung 28 Jul]:
```
koding di feature/DNGO19-3346 → push → merge ke feature/voc
  → Jenkins auto-build + auto-migration → dev.onebox.co.id/feature/voc/
```
**Tidak ada koding langsung di `feature/voc`** — branch itu hanya untuk merge. Yang wajib: koding di branch DNGO, karena itu yang naik ke release.

## 7.6 Bagaimana kamu sebaiknya berkontribusi

**Untuk perubahan kode biasa:** branch dari `main` → koding → test → PR. Sertakan bukti: perintah test yang dijalankan + hasilnya.

**Kalau kamu menemukan dokumen yang salah/basi:** jangan diam. Tambahkan catatan bertanggal, atau laporkan ke penulisnya. Konvensi di repo ini adalah **tambah entri baru bertanggal di atas, jangan hapus yang lama** [dokumen — contohnya di `DECISION_ui-placement-voc-menu.md`].

**Kalau kamu mau mengusulkan perubahan arsitektur:** jangan langsung koding. Tulis BRAINSTORM dulu — opsi apa saja, plus-minusnya, rekomendasimu. Itu yang diharapkan tim ini, dan jejaknya jelas terlihat di `decisions/`.

**Kalau kamu menemukan sesuatu yang tidak bisa kamu selesaikan sendiri:** tandai `[blocked]` dan sebutkan siapa yang bisa membukanya. Ini bukan tanda gagal — tasklist punya kolom status `blocked` justru karena ini dianggap wajar.

---

# 8. Next Step untuk Kamu

## 8.1 Aksi berurutan, dari yang paling mudah

### Minggu 1 — pahami & buktikan bisa jalan

**1. Baca 5 dokumen Hari 1 (§2).** ±2 jam. Jangan lompat ke kode sebelum ini selesai — kamu akan salah paham soal siapa memiliki apa.

**2. Jalankan sistemnya lokal dengan `REVIEW_SOURCE_MODE=mock`.** Ikuti §6.1. Target: `curl /api/health` mengembalikan `{"status":"ok",...}` dan Swagger di `/api/docs` terbuka.
> **Kenapa mock:** kamu belum butuh Google atau OneBox untuk memahami bentuk sistemnya, dan mock adalah satu-satunya mode yang pasti jalan tanpa kredensial apa pun.

**3. Jalankan test suite.** Target: `69 passed`. Kalau tidak, itu masalah environment — beresin dulu sebelum lanjut. Kamu butuh baseline hijau supaya nanti tahu apakah kegagalan disebabkan perubahanmu.

**4. Telusuri satu alur end-to-end di kode**, urutannya:
```
scripts/refresh_worklist.py
  → app/services/worklist_sync_service.py       (validasi + upsert + rekonsiliasi)
    → app/integrations/onebox_worklist_client.py (login + retry)
```
Lalu alur kedua:
```
apps/api/app_api/routers/integration_crawl_jobs.py   (enqueue)
  → app/services/crawl_job_service.py                (SKIP LOCKED, lease, retry)
    → scripts/run_crawl_worker.py                    (loop worker)
```
Ini dua alur terpenting di repo. Kalau paham keduanya, kamu paham 70% sistemnya.

**5. Buka Swagger dan coba endpoint yang tidak mengubah apa pun**: `/api/health`, lalu register + login, lalu `/api/locations`.

### Minggu 2 — kontribusi kecil yang aman

**6. Perbaiki satu konflik dokumentasi.** Pilih yang paling gampang diverifikasi — misalnya perbarui kolom Status M2 di `VOC_DEV_TASKLIST.md` sesuai kondisi kode (§4.9 K-1). Nilainya: kamu belajar konvensi dokumentasi tim tanpa risiko merusak kode, dan hasilnya langsung berguna buat orang lain.

**7. Baca `tests/test_tenant_isolation.py` dan `tests/test_worklist_sync.py`.** Dua file ini mengajarkan pola test yang dipakai di repo (fixture, session factory, client palsu) — kamu akan butuh itu untuk kontribusi apa pun.

**8. Kalau ditugaskan mengerjakan SPEC multi-tenant:** baca `markdowns/ORIENTASI-integrasi-onebox.md` dulu, lalu mulai dari migration (kolom `onebox_site_id` + `is_active`). Itu satu-satunya langkah yang tidak menunggu siapa pun.

### Yang JANGAN kamu lakukan dulu

- **Jangan sentuh `herminaCrawler-fe/`** — dead code, dan punya git repo terpisah
- **Jangan ubah `docker-compose.yml` atau `deploy.yml`** sebelum paham topologi deployment
- **Jangan jalankan `docker compose up` dengan `.env` produksi** — migration jalan otomatis tiap start
- **Jangan bikin scheduler di sisi Crawler** — dilarang eksplisit oleh ADR-0003
- **Jangan menambahkan `company_id` sebagai parameter request** di endpoint integrasi — itu melubangi isolasi tenant

## 8.2 Pertanyaan untuk kating (teknis)

**Setup & akses**
1. Apakah ada `.env` dev yang bisa saya pakai, atau saya bikin sendiri? Kalau ada `ONEBOX_*` untuk dev, gimana cara mendapatkannya dengan aman?
2. Saya perlu masuk jaringan WireGuard untuk menjangkau OneBox dev (`10.13.13.42`) dan server crawler (`10.13.13.90`)? Siapa yang bisa memberi akses?
3. DATABASE_URL untuk dev — pakai Supabase yang sama dengan tim, atau Postgres lokal sendiri? (Blocker P6 "seeding DB dev seragam" masih `blocked`, jadi saya ingin tahu praktik yang berlaku sekarang.)
4. Saya pakai Mac Apple Silicon / Intel — apakah ada yang pernah kena masalah arsitektur image saat `docker compose pull`? Ini tidak terdokumentasi di repo.

**Kode & status**
5. `VOC_DEV_TASKLIST.md` menandai M2-01/02/03/07 sebagai `todo`, tapi kodenya sudah ada sejak commit `b1ead26`. Boleh saya perbarui tasklist-nya, atau ada alasan sengaja dibiarkan?
6. **ADR-0004 (migrasi DB ke MySQL) disebut 4 kali di `PROJECT_STATUS.md` tapi filenya tidak ada di repo.** Ada di repo OneBox, atau belum di-commit?
7. Tabel `companies` tidak punya kolom `is_active`, padahal `SPEC-multi-tenant-opsi-c.md` §4.4 memerintahkan "tandai company nonaktif". Apakah ini kelewat, atau ada mekanisme lain yang saya belum lihat?
8. Task X1 (`PLAN_KEY_PROCESS_DEMO.md` — buktikan crawl 1 target di server) sudah dijalankan? Hasilnya apa? Ini gerbang yang memblokir banyak hal lain.

**Kerja sehari-hari**
9. Saya kebagian sisi mana — Crawler System, OneBox, atau dua-duanya? Ini menentukan repo mana yang perlu saya clone.
10. Konvensi PR-nya seperti apa? Wajib review sebelum merge ke `main`?
11. Ada standup/sync rutin? Di mana saya melaporkan progres & blocker?

## 8.3 Pertanyaan untuk PM (scope & keputusan)

Kelompok ini bukan pertanyaan teknis — jawabannya mengubah **apa yang dibangun**, bukan cara membangunnya.

1. **Ratifikasi ADR.** ADR-0001/0002/0003 (dan 0004) semuanya "belum diratifikasi Pak Agung". Tim sudah mengeksekusi rework besar di atasnya. Kapan bisa diratifikasi, dan apakah ada bagian yang Bapak keberatan?

2. **Cakupan demo Phase 1.** Apa persisnya yang harus jalan saat demo? `PLAN_KEY_PROCESS_DEMO.md` §5 sudah punya daftar, plus daftar "yang jujur disebut belum jalan" (penjadwalan otomatis, antrean, kuota AI, review kompetitor). Daftar itu masih sesuai ekspektasi?

3. **Kalau Selenium ternyata butuh login Google manual** (GAP-1) — janji "crawl otomatis 3× sehari" tidak bisa ditepati apa adanya. Mana yang dipilih: crawl semi-otomatis dengan sesi diperbarui berkala, atau cari sumber data alternatif?

4. **Retensi data review** (GAP-7). ADR-0001 menyebut review di Crawler sebagai "cache", tapi Google hanya menyimpan riwayat terbatas — kalau dihapus, tidak bisa diambil ulang. Diperlakukan sebagai data primer, atau tetap cache dengan masa simpan tertentu?

5. **Strategi dua engine** (GAP-4). OneBox punya integrasi Google Business Profile resmi; Crawler pakai scraping publik. Coverage dan risiko ToS-nya berbeda. Satu lokasi pakai engine mana — dan siapa yang memutuskan per lokasi?

6. **Prioritas multi-tenant vs demo.** `SPEC-multi-tenant-opsi-c.md` sudah disetujui tapi belum dikerjakan. Apakah ini masuk sprint sekarang, atau setelah demo Phase 1 solid? Setengah langkahnya ada di OneBox, jadi butuh koordinasi lintas tim.

7. **Kuota AI** (GAP-3). Belum ada pembatasan pemakaian token — biayanya belum terkendali. Kapan ini perlu jalan, dan berapa kuota per klien?

8. **DB produksi** (GAP-6). Supabase free tier tidur saat idle dan bikin 500 intermiten. Migrasi ke MySQL server OneBox butuh kredensial dari infra. Bisa dipercepat?

---

## Ringkasan satu halaman

- **Repo ini = mesin crawler**, bukan produk. Otaknya di OneBox — repo lain, tidak ada di laptop kamu.
- **Otoritasnya 3 ADR**, bukan 97 MD. Sisanya detail teknis atau arsip.
- **Kalimat kuncinya:** OneBox tahu APA & KAPAN, Crawler mengeksekusi.
- **Fase sekarang:** merapikan demo Phase 1. Backend matang, tapi **alur ujung-ke-ujung belum pernah dibuktikan** — tahap crawl Google adalah risiko terbesar.
- **Lapisan data sudah multi-tenant.** Yang single-tenant cuma dua baris config.
- **Status di dokumen sering tertinggal dari kode.** Verifikasi ke kode sebelum percaya kolom Status di MD mana pun.
- **Mulai dari:** baca 5 dokumen Hari 1 → jalankan lokal dengan mode `mock` → test hijau → telusuri dua alur di §8.1 nomor 4.

**Tiga hal yang saya temukan dan belum tercatat di dokumen mana pun:**
1. `companies` tidak punya kolom `is_active` — SPEC §4.4 tidak bisa dijalankan tanpanya
2. ADR-0004 dirujuk 4× di `PROJECT_STATUS.md` tapi filenya tidak ada di repo
3. Masalah arsitektur image Docker (ARM64 vs amd64) sama sekali tidak terdokumentasi, padahal CI membangun image tanpa `platforms:` — lihat §6.5
