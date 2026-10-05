# Runbook: Migrasi Source Google Review ke Apify atau Playwright

**Tujuan:** menguji source alternatif secara terkontrol, memilih provider yang
layak, lalu mengintegrasikannya ke CrawlJob, DB Crawler, dan auto-import OneBox
tanpa mengubah kontrak review yang sudah berjalan.

**Scope:** Crawler Service dev -> staging -> production canary.  
**Status:** Draft implementation runbook.

**Related:**

- `DECISION_GOOGLE_REVIEW_SOURCE_APIFY_VS_PLAYWRIGHT.md`
- `INCIDENT_P0_GOOGLE_MAPS_ONLY_5_REVIEWS.md`
- `DEBUG_GOOGLE_MAPS_PROFILE_AND_PAGINATION.md`
- `FETCH_JOBS_E2E_CONTRACT.md`
- `api-contract-v1.md`

## 1. Prinsip Operasional

1. Satu scheduler tetap berada di OneBox. Crawler hanya menerima durable job.
2. Source provider boleh berubah di Crawler, tetapi request OneBox dan output
   canonical review tetap kompatibel.
3. API health tidak sama dengan source readiness. Readiness dibuktikan dengan
   crawl nyata.
4. Jangan menjalankan Apify dan Playwright untuk job production yang sama pada
   waktu yang sama sebelum aturan dedup dan cost guard disetujui.
5. Jangan mengirim Google password, cookie, profile archive, atau token provider
   ke repository, issue, chat, atau log.
6. Semua hasil nol harus dibedakan antara `no_reviews`, `provider_empty`,
   `auth_required`, `blocked`, `timeout`, dan `provider_failed`.

## 2. Prasyarat Dan Baseline

Catat sebelum coding:

```text
environment:
branch:
commit:
api_image:
worker_image:
location_id:
onebox_location_id:
external_place_id:
target_review_count:
review_source_mode:
```

Baseline yang wajib tersedia:

- fixture satu item dari output provider yang sudah disanitasi;
- fixture satu item dengan field opsional hilang;
- fixture duplicate dengan ID sama;
- fixture invalid rating dan invalid timestamp;
- hasil smoke Selenium terakhir sebagai pembanding, bukan ground truth;
- `tests/fixtures/voc_reviews_v1.json` untuk contract integration.

Sebelum mengubah source, jalankan:

```bash
python -m pytest tests/test_selenium_scraping.py tests/test_integration_crawl_jobs.py -q
python -m compileall app scripts
```

## 3. Target Arsitektur Implementasi

```text
CrawlWorker
  -> FetchService / FetchSourceFactory
      -> ReviewSourceClient
          -> SeleniumGoogleMapsReviewClient
          -> ApifyGoogleMapsReviewClient
          -> PlaywrightGoogleMapsReviewClient
      -> canonical review normalizer
      -> ReviewService.insert_review()
      -> FetchLogService.finish_log()
```

### 3.1 Refactor boundary terlebih dahulu

Worker saat ini masih membuat `SeleniumFetchService` secara langsung. Buat
worker bergantung pada entry point/factory yang memilih implementation melalui
`REVIEW_SOURCE_MODE`. Pilih pola yang konsisten dengan codebase:

- jadikan `FetchService` entry point yang memilih `ReviewSourceClient`; atau
- buat `FetchServiceFactory` dengan interface fetch yang sama.

Jangan menyalin logic persistence ke client Apify/Playwright. Client hanya
bertanggung jawab membaca source dan mengembalikan item raw yang memenuhi
bentuk minimum.

## 4. Configuration Dan Secret

### 4.1 Common

Tambahkan setting tervalidasi:

```env
REVIEW_SOURCE_MODE=selenium
SOURCE_MAX_CONCURRENCY=1
SOURCE_REQUEST_TIMEOUT_SECONDS=120
SOURCE_MAX_RETRY=2
SOURCE_DEBUG_ARTIFACTS=false
```

Mode hanya boleh `mock`, `google_places`, `google_business_profile`,
`third_party`, `selenium`, `apify`, atau `playwright` setelah implementation
tersedia. Mode yang belum tersedia harus gagal jelas, bukan silently fallback.

### 4.2 Apify

```env
APIFY_API_TOKEN=secret-from-secret-store
APIFY_ACTOR_ID=compass~google-maps-reviews-scraper
APIFY_ACTOR_VERSION=approved-version
APIFY_BASE_URL=https://api.apify.com/v2
APIFY_RUN_TIMEOUT_SECONDS=900
APIFY_POLL_SECONDS=5
APIFY_MAX_POLL_SECONDS=30
APIFY_MAX_REVIEWS_PER_RUN=300
APIFY_MAX_CONCURRENT_RUNS=1
APIFY_PERSONAL_DATA_MODE=approved-value
```

Aturan secret:

- gunakan `Authorization: Bearer <token>`;
- jangan taruh token di query string, source code, `result_json`, atau log;
- jangan mencetak request body jika berisi URL atau personal data;
- token dev, staging, dan production harus berbeda bila policy mengizinkan;
- batasi budget dan concurrency sebelum live test.

### 4.3 Playwright

```env
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_BROWSER=chromium
PLAYWRIGHT_TIMEOUT_SECONDS=30
PLAYWRIGHT_NAVIGATION_TIMEOUT_SECONDS=60
PLAYWRIGHT_MAX_SCROLL_ATTEMPTS=400
PLAYWRIGHT_SCROLL_DELAY_SECONDS=2
PLAYWRIGHT_USER_DATA_DIR=
PLAYWRIGHT_STORAGE_STATE_PATH=
```

Persistent profile hanya dipakai bila kebutuhan login dan ownership sesi sudah
disetujui. Untuk POC pertama, coba signed-out public flow agar dapat dibedakan
antara masalah login dan masalah IP/policy. Jika memakai profile:

- satu profile per environment;
- tidak ada dua worker memakai profile yang sama;
- lock stale ditangani sesuai runbook profile;
- storage state diperlakukan sebagai credential;
- profile tidak masuk image dan tidak di-commit.

## 5. Tahap A - Apify Adapter

### 5.1 Buat client

Buat `app/integrations/apify_google_maps_client.py` yang mengimplementasikan
`ReviewSourceClient`.

Tanggung jawab client:

1. Validasi `external_place_id`, target, timeout, dan actor config.
2. Bentuk input actor dari URL/Place ID yang telah diverifikasi.
3. Start Actor run melalui API.
4. Poll status run dengan timeout dan bounded backoff.
5. Ambil dataset item setelah run selesai.
6. Validasi shape setiap item.
7. Map ke canonical raw review.
8. Mengisi `last_metadata` dengan provider ID/status/count/stop reason.
9. Mengubah error provider ke `ReviewSourceError` dengan `code` dan
   `retriable` yang benar.

### 5.2 Request flow

Flow asynchronous:

```text
POST /v2/acts/{actor_id}/runs
  -> run_id
GET  /v2/actor-runs/{run_id}
  -> RUNNING / SUCCEEDED / FAILED / TIMED-OUT / ABORTED
GET  /v2/datasets/{dataset_id}/items?clean=1
  -> list item
```

Jangan memakai endpoint synchronous untuk scheduled/large job jika dapat
menunggu lebih dari batas request. Polling dijalankan oleh worker dalam lease,
atau dipisahkan menjadi state provider yang dapat dilanjutkan bila diperlukan.

Contoh input konseptual, sesuaikan dengan actor version yang disetujui:

```json
{
  "startUrls": [
    "https://www.google.com/maps/search/?api=1&query=BRANCH&query_place_id=PLACE_ID&hl=id"
  ],
  "maxReviews": 10,
  "language": "id",
  "reviewsSort": "newest"
}
```

Jangan mengasumsikan nama input tanpa memeriksa dokumentasi actor version yang
dipin. Simpan input aman di metadata hanya bila dibutuhkan untuk audit.

### 5.3 Mapping Apify ke canonical review

Mapping kandidat berikut wajib diverifikasi memakai fixture output actor yang
digunakan di environment.

| Field actor kandidat | Canonical field | Aturan |
|---|---|---|
| `reviewId` | `external_review_id` | Wajib bila tersedia; trim dan validasi panjang. |
| `name` | `reviewer_name` | Fallback `Anonymous`. |
| `reviewerUrl` | `reviewer_profile_url` | Optional. |
| `reviewerPhotoUrl` | `reviewer_photo_url` | Optional. |
| `isLocalGuide` / equivalent | `reviewer_local_guide_level` | `true` -> `Local Guide`, selain itu null. |
| `reviewerNumberOfReviews` | `reviewer_total_reviews` | Parse integer/compact count. |
| `stars` | `rating` | Parse integer dan enforce 1..5. |
| `text` | `review_text` | Fallback string kosong. |
| `publishedAtDate` | `review_time` | Parse absolute datetime ke UTC. |
| `publishAt` / relative label | `review_relative_time` | Simpan bila tersedia, bukan timestamp presisi. |
| `originalLanguage` | `review_language`, `language` | Fallback `unknown`. |
| `likesCount` | `like_count` | Non-negative integer, fallback 0. |
| owner response fields | `owner_response_text`, `owner_response_time` | Verifikasi nama field actor. |
| `placeId` | validation only | Cocokkan dengan Location; jangan mengganti ID dari DB. |
| place rating/review count | `rating_snapshot` metadata | Optional; tidak menggagalkan ingestion. |
| full item | `raw_payload` | Redact/bound; jangan simpan auth material. |

Jika actor tidak memberi `reviewId`, gunakan fallback identity dari URL reviewer,
nama, rating, text, dan waktu. Catat `identity_quality=fallback`; ini menjadi
risk approval sebelum production.

### 5.4 Error mapping Apify

| Provider condition | Crawler code | Retry |
|---|---|---|
| 401/403 token atau permission | `PROVIDER_AUTH_FAILED` | Tidak |
| 404 actor/version | `PROVIDER_NOT_FOUND` | Tidak |
| 429 rate limit | `PROVIDER_RATE_LIMITED` | Ya, bounded |
| 5xx/network timeout | `PROVIDER_UNAVAILABLE` | Ya, bounded |
| run `FAILED` | `PROVIDER_RUN_FAILED` | Tergantung error |
| run `TIMED-OUT` | `PROVIDER_TIMEOUT` | Ya maksimal policy |
| run succeeded, dataset empty | `PROVIDER_EMPTY_RESULT` | Tidak otomatis |
| partial items/provider warning | `PROVIDER_PARTIAL_RESULT` | Jangan buang item valid |
| output schema invalid | `PROVIDER_SCHEMA_INVALID` | Tidak; alarm dan fixture update |

## 6. Tahap B - Playwright Adapter

### 6.1 Dependency dan image

Tambahkan dependency Playwright di lock file dan Dockerfile hanya pada image
worker bila API tidak melakukan browser work. Pilih salah satu model:

- install package dan Chromium dengan version pin;
- gunakan base image Playwright yang disetujui infra;
- buat worker image khusus browser source.

Verifikasi image tidak menjalankan browser engine yang tidak diperlukan dan RAM
limit cukup untuk worker.

### 6.2 Client dan context

Buat `app/integrations/playwright_google_maps_client.py` yang implementasi
`ReviewSourceClient`.

Aturan browser:

- public POC memakai isolated non-persistent context;
- profile login hanya jika diperlukan dan serial;
- `context.storage_state()` hanya ke path credential yang dilindungi;
- jangan berbagi page/context antar job;
- tutup page/context/browser pada semua exit path;
- capture trace/screenshot hanya saat debug flag aktif.

### 6.3 Navigation dan locator

Gunakan sinyal halaman, bukan fixed sleep sebagai readiness tunggal:

1. buka URL Place ID canonical;
2. tunggu place header terlihat;
3. buka tab `Ulasan`/`Reviews` dengan locator semantic atau fallback pendek;
4. tunggu review card pertama atau error state eksplisit;
5. scroll container review;
6. tunggu jumlah card bertambah atau state `no_more_reviews` yang benar;
7. berhenti saat target, range, `scan_limit`, atau time limit tercapai.

Selector lebih memilih role/text/label yang stabil. Long CSS chain dan XPath
absolut tidak boleh menjadi satu-satunya selector.

### 6.4 Detection state

Simpan state berikut secara eksplisit:

```text
GOOGLE_AUTH_REQUIRED
GOOGLE_CONSENT_REQUIRED
GOOGLE_CAPTCHA_REQUIRED
PROXY_AUTH_REQUIRED
REVIEW_SURFACE_NOT_FOUND
PAGINATION_STALLED
NO_REVIEWS_VISIBLE
NO_MORE_REVIEWS
TIME_LIMIT
```

`PAGINATION_STALLED` berarti card count tidak bertambah setelah bounded
attempts. Jangan map menjadi `NO_MORE_REVIEWS` tanpa bukti end-of-list.

### 6.5 Uji dari host yang sama

POC Playwright harus menguji host yang sama dengan Selenium dan mencatat:

- public egress IP jika dapat dicatat secara aman;
- final URL/title;
- card count awal dan setelah advance;
- auth/consent/CAPTCHA state;
- `navigator.webdriver` hanya sebagai diagnostic, bukan acceptance utama;
- latency dan memory.

Jika Playwright berhenti di lima card dengan auth wall yang sama, simpulkan
selector bukan satu-satunya masalah dan hentikan optimasi selector.

## 7. Tahap C - Shared Normalizer Dan Persistence

### 7.1 Normalizer

Gunakan satu canonical normalizer untuk Apify, Playwright, dan Selenium. Opsi
refactor aman:

- pertahankan `FetchService.normalize_review()` sebagai boundary persistence;
- tambahkan mapper source-specific sebelum method tersebut; atau
- ekstrak mapper ke `google_review_normalizer.py` tanpa mengubah output.

Jangan membuat tiga versi hashing yang berbeda hanya karena source berbeda.

### 7.2 Identity dan dedup

Urutan identity:

1. `external_review_id` + `source` + `external_place_id` bila tersedia;
2. `review_hash` canonical;
3. fallback composite dengan status kualitas identity.

Sebelum cutover, bandingkan sampel Apify dengan existing review berdasarkan
ID, reviewer name, rating, text, waktu, dan location/place ID. Target bukan
hanya `inserted=10`; `duplicate` dan `inserted` harus dapat dijelaskan.

### 7.3 Metadata dan progress

Gunakan `result_json` dan `FetchLog.metadata` yang sudah tersedia untuk:

- `progress_scanned` dan `progress_fetched`;
- `provider_status`;
- `provider_run_id` dan `provider_dataset_id`;
- `provider_item_count`;
- `stop_reason` dan `source`.

Untuk Apify, progress boleh berbentuk state (`queued`, `running`,
`dataset_loading`, `completed`) jika jumlah live belum diketahui. Jangan
mengarang persentase dari elapsed time.

OneBox menampilkan state:

```text
Menyiapkan crawl
Menunggu worker
Mengambil review dari provider
Menyimpan review ke Crawler
Menyimpan review ke OneBox
Memberi label sentiment
Review siap dikelola
```

Counter akhir:

```text
Target 10 | Terbaca 10 | Baru 3 | Duplikat 7 | Gagal 0
```

## 8. Tahap D - API Dan Scheduler Integration

Tidak perlu membuat endpoint enqueue baru untuk provider.

### 8.1 Enqueue

Pastikan payload lama tetap diterima dan disimpan ke
`job.result_json.request`:

```json
{
  "target_review_count": 10,
  "scan_limit": 50,
  "sort_by": "newest",
  "date_from": null,
  "date_to": null,
  "dry_run": false
}
```

`source` boleh menjadi metadata internal yang dipilih dari environment. Jangan
biarkan caller tenant memilih provider yang belum diizinkan.

### 8.2 Retry dan lease

- retry network/provider transient memakai policy existing;
- auth, schema, dan invalid configuration tidak diulang tanpa batas;
- simpan run ID sebelum polling agar retry tidak membuat run ganda tanpa sadar;
- jika job lease expire, worker berikutnya harus dapat melanjutkan polling atau
  menandai provider run lama sebagai orphan;
- provider run orphan harus terdeteksi dan dapat di-abort bila didukung.

### 8.3 Scheduled dan manual

OneBox tetap memiliki dua cara:

- initial/manual fetch;
- scheduled fetch.

Jangan membuat Apify Scheduler kedua untuk location yang sama. Satu scheduler
di OneBox menjaga audit dan idempotency tetap berada di satu tempat.

## 9. Tahap E - Test Berurutan

### 9.1 Unit test

Tambahkan test untuk config, item provider lengkap/minimal, invalid rating,
timestamp, missing review ID, owner response, place mismatch, provider
401/403/429/5xx/timeout, empty dataset, redaction, dan dedup.

### 9.2 Contract test

Pastikan `GET /api/integration/v1/reviews` tetap mengembalikan:

- `review_hash` stabil dan source benar;
- timestamp UTC dengan suffix `Z`;
- `analysis_status=pending` untuk review baru;
- field analisis sesuai contract;
- tidak ada `raw_payload`, `company_id`, atau secret bocor.

### 9.3 Live Apify smoke

Mulai satu location non-critical:

```text
target_review_count = 10
scan_limit = 50
sort_by = newest
date range = kosong
```

Acceptance minimum:

- run provider punya ID dan status terminal;
- item lebih dari lima atau stop reason jujur;
- minimal 10 review terbaca untuk target 10, atau partial/failed dengan sebab;
- review masuk DB Crawler;
- rerun menghasilkan duplicate yang dapat dijelaskan;
- OneBox pull otomatis berhasil;
- review tampil di Kelola Review;
- native labeling tidak menghalangi raw ingestion;
- token provider tidak muncul di log.

### 9.4 Live Playwright smoke

Jalankan dari host dan location yang sama, tetapi jangan bersamaan dengan
Selenium profile:

- POC signed-out dulu;
- target 10;
- browser headless sesuai deployment;
- capture trace hanya bila gagal;
- catat card count dan state error;
- jika berhasil, ulangi target 50;
- jika gagal di lima card, catat evidence IP/policy/auth dan jangan menyatakan
  adapter production-ready.

### 9.5 OneBox end-to-end

Validasi chain:

```text
Fetch Jobs klik Mulai
  -> queued
  -> running
  -> provider run
  -> crawler inserted/duplicate
  -> OneBox auto-import
  -> review muncul di Kelola Review
  -> sentiment native
  -> pilih review untuk AI async
```

AI tidak berada di critical path crawl. Ollama/LLM dimatikan pun source sampai
Kelola Review harus berhasil.

## 10. Rollout Bertahap

### Dev

1. Selenium tetap baseline.
2. Apify target 10 pada satu location melalui feature flag.
3. Playwright target 10 pada location yang sama setelah Apify selesai.
4. Bandingkan item, identity, latency, status, dan biaya.

### Staging

1. Pin actor/version dan image worker.
2. Gunakan token staging dan budget kecil.
3. Uji tiga location target 10.
4. Uji scheduled run satu kali.
5. Tinjau auto-import dan duplicate.

### Production canary

1. Satu tenant dan satu location.
2. Target 10 manual, lalu satu scheduled delta.
3. Monitor provider error, inserted/duplicate, latency, cost, dan import.
4. Naikkan target 50 setelah target 10 stabil.
5. Perluas location bertahap, bukan seluruh tenant sekaligus.

## 11. Rollback

Rollback source tidak membutuhkan rollback data review:

```env
REVIEW_SOURCE_MODE=selenium
```

Lalu recreate worker/API sesuai deployment runbook tanpa `down -v` dan tanpa
menghapus volume PostgreSQL.

Jika Apify run aktif:

1. hentikan enqueue baru;
2. tunggu atau abort provider run sesuai API;
3. biarkan job yang sudah punya review di-import;
4. tandai job provider failed/partial secara jujur;
5. kembalikan mode source;
6. jalankan smoke baseline.

Jika Playwright profile rusak:

1. stop worker;
2. simpan evidence dan backup profile;
3. jangan menghapus database review;
4. gunakan isolated context atau profile baru yang disetujui;
5. kembali ke Selenium/Apify melalui feature flag.

## 12. Masalah Umum Dan Penyelesaian

| Masalah | Diagnosis | Penyelesaian |
|---|---|---|
| Apify 401/403 | Secret/actor permission salah | Periksa injection dan access; jangan retry tanpa batas |
| Apify 429 | Concurrency/budget/rate limit | Turunkan concurrency, backoff, cek quota |
| Run sukses, 0 item | URL/place/actor/schema/source issue | Cek dataset sample; tandai `PROVIDER_EMPTY_RESULT` |
| Output field berubah | Schema drift | Pin version, update fixture/mapper, block rollout |
| Dataset partial | Actor berhenti setelah beberapa item | Simpan item valid, status partial, expose reason |
| Apify mahal | maxReviews/concurrency terlalu besar | Budget guard, target cap, canary, cost monitor |
| Playwright auth wall | Google session/policy/egress | Probe signed-out; jangan hanya menambah sleep |
| Card Playwright tidak bertambah | Container/selector/DOM virtual | Tunggu count change, scroll container, trace |
| Chromium crash/OOM | Terlalu banyak context/browser | Serial worker, shm size, memory limit, lifecycle |
| Profile lock | Dua runtime memakai profile | Stop browser, cleanup sesuai runbook, satu owner |
| Review ganda | ID/hash source berbeda | Canonical identity dan compare sebelum cutover |
| OneBox tidak tampil | Pull/cursor/tenant/location mapping | Audit batch, cursor checkpoint, company/site/provider |
| Badge selesai, item nol | UI terlalu optimistis | Baca counts, provider status, stop reason, partial |

## 13. Definition Of Done

### Adapter

- [ ] Client implements `ReviewSourceClient`.
- [ ] Source mode tervalidasi dan feature-flagged.
- [ ] Timeout, retry, error code, stop reason terdokumentasi.
- [ ] Provider metadata aman dan dapat diaudit.
- [ ] Raw payload bounded dan tidak membocorkan secret.

### Data

- [ ] Semua canonical fields termapping.
- [ ] `external_place_id` berasal dari master Location.
- [ ] `external_review_id` atau fallback identity terdokumentasi.
- [ ] Rating dan timestamp tervalidasi.
- [ ] Dedup test hijau.

### End-to-end

- [ ] Target 10 menghasilkan lebih dari lima review nyata.
- [ ] Review tersimpan di DB Crawler.
- [ ] OneBox otomatis pull tanpa tombol kedua.
- [ ] Review tampil di Kelola Review.
- [ ] Labeling native tidak menghalangi ingestion.
- [ ] Progress UI menunjukkan state dan counter aktual.
- [ ] Partial/failure tidak disamarkan sebagai completed.
- [ ] AI asynchronous tetap di luar critical path crawl.

### Operasional

- [ ] Token dan budget disetujui.
- [ ] Actor/version atau browser image dipin.
- [ ] Dev/staging/production source mode eksplisit.
- [ ] Rollback diuji.
- [ ] Canary evidence disimpan tanpa personal data berlebih.

## 14. Referensi Teknis

- Apify Actor API: <https://apify.com/compass/google-maps-reviews-scraper/api>
- Apify API v2: <https://docs.apify.com/api/v2>
- Playwright locators: <https://playwright.dev/docs/locators>
- Playwright actionability: <https://playwright.dev/docs/actionability>
- Playwright BrowserContext: <https://playwright.dev/docs/api/class-browsercontext>
- Google Places review limitation: <https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places>
