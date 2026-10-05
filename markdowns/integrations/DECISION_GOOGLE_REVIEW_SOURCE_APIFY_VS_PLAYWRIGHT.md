# Decision Brief: Google Review Source - Apify vs Playwright

**Status:** ✅ **Accepted (2026-09-20)** — **Apify Google Maps Reviews Actor** dipilih sebagai source produksi. Playwright POC (Bagian 4.2 / Gate B) tidak dilanjutkan. Sisa dokumen ini dipertahankan sebagai catatan analisis dan Gate A yang jadi dasar keputusan — bukan lagi proposal terbuka.
**Owner:** Crawler System  
**Tanggal:** 2026-09-14 (diajukan) · 2026-09-20 (disetujui)  
**Prioritas:** P0 untuk pemulihan bukti crawl nyata  
**Related:** `INCIDENT_P0_GOOGLE_MAPS_ONLY_5_REVIEWS.md`, `DEBUG_GOOGLE_MAPS_PROFILE_AND_PAGINATION.md`, `FETCH_JOBS_E2E_CONTRACT.md`, `05-runbooks/crawler/MIGRATE_GOOGLE_REVIEW_SOURCE_APIFY_OR_PLAYWRIGHT.md`

## 0. Status Implementasi (dicek 2026-09-20)

Keputusan sudah final, tapi kodenya **belum mengikuti** — `REVIEW_SOURCE_MODES` di
`app/config.py:26` masih `{mock, google_places, google_business_profile,
third_party, selenium}`, tidak ada `apify`. `SourceFactory` di Bagian 5 juga
belum ada. Ini murni gap implementasi, dicatat di sini supaya tidak ada yang
mengira Apify sudah aktif di runtime hanya karena keputusannya sudah Accepted.

## 1. Keputusan Yang Dibutuhkan

Tentukan source Google Maps yang dipakai untuk membuktikan dan memulihkan crawl
review:

1. **Apify Google Maps Reviews Actor** sebagai jalur pemulihan P0 dan spike
   production-readiness.
2. **Playwright self-hosted** sebagai jalur POC alternatif apabila perusahaan
   membutuhkan kontrol browser dan data tetap diproses di server sendiri.
3. Selenium saat ini dipertahankan sebagai rollback sementara, tetapi tidak
   boleh dianggap sehat hanya karena API dan container worker sehat.

Rekomendasi awal: **uji Apify lebih dahulu untuk memisahkan masalah source dan
egress dari masalah OneBox/Crawler. Jalankan POC Playwright secara terpisah,
bukan sebagai rewrite paralel yang langsung menggantikan pipeline produksi.**

## 2. Konteks Dan Temuan P0

Target sistem:

```text
OneBox enqueue
  -> Crawler worker mengambil job
  -> source membaca review Google
  -> review dinormalisasi dan disimpan di DB Crawler
  -> OneBox menarik delta otomatis
  -> review masuk DB OneBox
  -> labeling native dan Kelola Review
```

Temuan operasional terakhir pada dev:

- API, database, token, queue, dan worker dapat hidup normal.
- URL Place ID benar dan panel Ulasan dapat dibuka.
- Lima card awal dapat terlihat.
- Probe dan dua smoke run tetap menemui `GOOGLE_AUTH_REQUIRED` saat pagination.
- Proxy environment dan sisa konfigurasi proxy pada profile sudah diperiksa.
- Login manual dan cookie tidak cukup untuk membuktikan load-more dapat dipakai
  oleh runtime worker.

Kesimpulan yang boleh diambil: **runtime Selenium menghadapi Google auth,
automation, atau egress restriction saat pagination.** Kesimpulan bahwa IP
server pasti diblokir belum terbukti secara definitif. Apify membantu menguji
hipotesis itu karena eksekusinya memakai egress dan browser terkelola milik
provider. Playwright dari server yang sama kemungkinan besar masih akan
menghadapi kebijakan Google yang sama.

## 3. Batasan Existing System Yang Harus Dipertahankan

### 3.1 Boundary kode

Saat ini `ReviewSourceClient` memiliki kontrak:

```python
fetch_reviews(location, limit=50, **kwargs) -> list[dict]
```

`FetchService` sudah menjadi tempat untuk memilih source, retry, normalisasi,
date range, perhitungan inserted/duplicate/failed, dan penulisan `FetchLog`
serta `Review`.

Worker masih membangun `SeleniumFetchService` secara langsung. Ini perlu
dirapikan menjadi factory/service yang memilih implementation berdasarkan
feature flag, tanpa mengubah kontrak enqueue OneBox.

### 3.2 Atribut canonical

Setiap source wajib menghasilkan bentuk internal yang diproses oleh normalizer
existing:

| Atribut                        | Aturan                                                                                             |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| `source`                       | Misalnya `apify_google_maps` atau `playwright_google_maps`; jangan mengaku `selenium_google_maps`. |
| `external_place_id`            | Selalu dari master `Location`, bukan dipercaya dari payload provider.                              |
| `external_review_id`           | Identity utama dedup. Jika tidak ada, gunakan fallback yang terdokumentasi.                        |
| `reviewer_name`                | Boleh anonim; field hilang tidak menggagalkan seluruh batch.                                       |
| `reviewer_profile_url`         | Optional (ini boleh)                                                                               |
| `reviewer_photo_url`           | Optional. (ini boleh banget tapi simpen dmnnya harus jelas biar ga lemot)                          |
| `reviewer_local_guide_level`   | Map ke `Local Guide` atau null.                                                                    |
| `reviewer_total_reviews`       | Integer jika dapat diparse, selain itu null.                                                       |
| `rating`                       | Integer 1..5; nilai invalid menjadi null dan dicatat.                                              |
| `review_text`                  | String, boleh kosong.                                                                              |
| `review_time`                  | Timestamp absolute timezone-aware UTC jika tersedia.                                               |
| `review_relative_time`         | Informasi sumber, bukan timestamp presisi.                                                         |
| `review_language` / `language` | Bahasa asli atau `unknown`.                                                                        |
| `like_count`                   | Integer non-negatif, default 0 jika tidak tersedia.                                                |
| `owner_response_text`          | Optional.                                                                                          |
| `owner_response_time`          | Timestamp UTC jika tersedia.                                                                       |
| `scraped_at`                   | Waktu pengambilan source dalam UTC.                                                                |
| `raw_payload`                  | Bounded dan redacted; tidak boleh berisi token/cookie/header.                                      |
| `review_hash`                  | Dibuat Crawler dari canonical data; provider tidak authoritative.                                  |

### 3.3 Kontrak OneBox tetap

OneBox tetap mengirim request enqueue yang sama:

```json
{
  "slot": "manual",
  "targets": [
    {
      "kind": "location",
      "onebox_location_id": 656,
      "target_review_count": 10,
      "sort_by": "newest"
    }
  ]
}
```

`date_from`, `date_to`, `scan_limit`, `dry_run`, dan `sort_by` tetap menjadi
parameter job. Pemilihan provider dilakukan Crawler melalui environment atau
capability policy. OneBox tidak perlu mengetahui token Apify.

## 4. Perbandingan Opsi

| Dimensi | Selenium existing | Apify actor | Playwright self-hosted |
|---|---|---|---|
| Tujuan | Rollback/baseline | Recovery P0 dan validasi source | Kontrol browser jangka panjang |
| Egress | IP server sendiri | Egress/proxy managed provider, tergantung actor/plan | IP server sendiri kecuali ditambah proxy |
| Risiko auth wall | Tinggi, sudah terbukti | Lebih rendah untuk actor public-data, tidak dijamin | Tetap ada; Playwright bukan bypass jaringan |
| Kontrol runtime | Rendah-menengah | Rendah pada browser, tinggi pada orchestration API | Tinggi |
| Operasional | Chrome/driver/profile/lock | Ditangani provider | Browser install/context/profile/memory |
| Kode tambahan | Tidak ada | HTTP client, polling, adapter, budget | Browser client, locator, wait, profile |
| Dependensi | Google + host | Google + Apify + actor marketplace | Google + host |
| Biaya | Server/proxy sendiri | Per run/compute/proxy sesuai plan | Server/proxy sendiri |
| Latensi | Tidak konsisten | Async run + dataset fetch | Tidak konsisten |
| Date range | Scan card dan filter | Semantics actor harus diverifikasi | Scan card dan filter sendiri |
| Stability | DOM Google mudah berubah | Schema actor dapat berubah | DOM Google mudah berubah |
| Privacy | Internal | Data melewati pihak ketiga | Internal |
| Rollback | Env/image | Env jika adapter dipisah | Env jika adapter dipisah |

### 4.1 Apify

**Kekuatan:**

- Egress, Chromium, retry, dan proxy dapat ditangani di luar server Crawler.
- Tidak perlu memasukkan Google password atau cookie ke Crawler.
- Cocok untuk memisahkan problem source/egress dari problem OneBox.
- Async run cocok dengan durable `CrawlJob`.

**Batasan:**

- Actor marketplace bukan API Google resmi. Provider, schema, harga, limit,
  dan availability dapat berubah.
- Author, timestamp, owner response, atau review ID dapat tidak lengkap.
- Run dapat partial, timeout, rate-limited, atau gagal di provider.
- Data review keluar dari boundary server internal.
- Token Apify adalah secret baru dan perlu rotasi serta budget guard.

### 4.2 Playwright

Playwright memberi locator, auto-waiting, isolated browser context, assertion
retry, trace, dan tooling yang lebih terstruktur daripada interaksi Selenium.

**Kekuatan:**

- Selector dan wait strategy dapat dibuat semantic dan teruji.
- Browser context dapat diisolasi per job atau environment.
- Trace/screenshot membantu diagnosis perubahan UI.
- Tidak menambah pihak ketiga untuk pemrosesan data.

**Batasan kritis:**

- **Tidak menyelesaikan IP block.** Dari host yang sama, policy Google bisa sama.
- Tetap tergantung layout, consent, CAPTCHA, dan policy Google.
- Persistent profile memerlukan lock discipline dan storage state sensitif.
- Browser dependency menambah ukuran image, startup time, dan RAM.
- `waitForTimeout` saja bukan readiness signal; gunakan state dan assertion.

### 4.3 Google Places API sebagai non-option

Google Places API resmi lebih stabil secara kontrak, tetapi review Place Details
dibatasi maksimal lima dan urutannya relevance-based. Itu tidak memenuhi target
crawl 10 sampai 300 review dan bukan pengganti langsung tanpa perubahan product
requirement.

## 5. Rekomendasi Arsitektur

```text
OneBox
  -> POST /api/integration/v1/crawl-jobs
  -> Crawler CrawlJob / CrawlBatch
  -> SourceFactory(REVIEW_SOURCE_MODE)
       |-- selenium_google_maps   (rollback)
       |-- apify_google_maps      (P0 recovery)
       `-- playwright_google_maps (POC / controlled fallback)
  -> ReviewSourceClient.fetch_reviews()
  -> canonical review normalizer
  -> ReviewService + FetchLogService
  -> GET /api/integration/v1/reviews
  -> OneBox auto-import + native labeling
```

Tambahkan mode eksplisit:

```text
REVIEW_SOURCE_MODE=selenium
REVIEW_SOURCE_MODE=apify
REVIEW_SOURCE_MODE=playwright
```

Default tetap `selenium` sampai spike dan approval selesai. Staging dan
production harus memilih mode secara eksplisit agar image baru tidak diam-diam
pindah provider.

Metadata dapat memakai `CrawlJob.result_json` dan `FetchLog.metadata` yang
sudah ada:

```json
{
  "source": "apify_google_maps",
  "provider_run_id": "safe-provider-id",
  "provider_dataset_id": "safe-dataset-id",
  "provider_status": "SUCCEEDED",
  "provider_item_count": 10,
  "target_review_count": 10,
  "reviews_scanned": 10,
  "stop_reason": "target_reached"
}
```

Jangan menyimpan token, cookie, authorization header, raw HTML, atau URL yang
mengandung secret di metadata dan log.

## 6. Decision Gate

### Gate A: Apify P0 spike

Lanjut jika:

- satu location valid menghasilkan lebih dari lima review;
- target 10 tercapai atau provider memberi stop reason jujur;
- item dapat dinormalisasi ke contract v1;
- `external_review_id` cukup stabil untuk dedup;
- OneBox pull dan Kelola Review menampilkan review baru;
- biaya, privacy, dan actor version disetujui;
- failed, partial, dan timeout terlihat dengan status yang benar.

### Gate B: Playwright POC

Lanjut jika Apify tidak disetujui karena privacy/cost/vendor, field actor tidak
cukup, atau perusahaan membutuhkan browser self-hosted.

### No-go

- hanya mengukur `/api/health` tanpa crawl nyata;
- menganggap avatar/cookie sebagai bukti pagination;
- mengubah zero/partial result menjadi `completed`;
- menerima review tanpa identity yang dapat dideduplikasi;
- menaruh token di code, screenshot, issue, atau log;
- mengaktifkan dua scheduler untuk location yang sama.

## 7. Risiko Dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| IP/reputation Google memblokir host | Crawl nol/lima card | Uji Apify dengan egress lain; jangan klaim Playwright sebagai solusi jaringan |
| Schema actor berubah | Field hilang/salah | Pin actor/version, fixture contract, schema validation, canary |
| 429 atau 5xx provider | Job menumpuk | Bounded retry, exponential backoff, concurrency dan budget limit |
| Partial/timeout | Review tidak lengkap | Simpan provider status, item count, stop reason; tandai partial |
| Data personal ke pihak ketiga | Compliance risk | Review legal/security, minimize raw payload, retention dan DPA |
| Selector Playwright berubah | Crawl gagal | Locator semantic, card-count assertion, trace on failure |
| Profile dipakai paralel | Lock/corruption/auth error | Satu profile per environment atau isolated context |
| Duplicate antar source | Hitungan ganda | Canonical identity, review_hash, compare sebelum cutover |
| Date semantics berbeda | Review salah periode | Ambil newest, filter UTC di Crawler, catat warning |

## 8. Pembagian Tanggung Jawab

### Crawler/Codex

- adapter dan source factory;
- canonical normalizer dan schema validation;
- polling/backoff/error code/provider metadata;
- cost guard, observability, test, canary, rollback.

### OneBox/Claude

- pertahankan endpoint enqueue dan auto-import;
- tampilkan source/provider, progress, partial, failed, stop reason;
- validasi `external_review_id`, `review_hash`, `onebox_location_id`;
- jangan membuat Ticket dari review historis hanya karena source berganti;
- lakukan acceptance Fetch Jobs, Kelola Review, dan native labeling.

### Infra/Security

- inject secret provider melalui secret store/environment;
- allowlist egress dan monitor biaya;
- pisahkan volume/profile per environment;
- atur retention dan access control raw/debug artifact;
- review privacy sebelum data dikirim ke provider.

## 9. Keputusan Sementara

Sampai Gate A dan B selesai:

- Selenium tersedia untuk rollback dan pembanding.
- Apify kandidat recovery P0 karena mengisolasi variabel egress.
- Playwright kandidat self-hosted, bukan jaminan mengatasi block.
- Pipeline OneBox, schema review, dedup, dan auto-import tidak dirombak.
- Tidak ada cutover production tanpa bukti target 10, import OneBox, dan
  failure handling.

## 10. Referensi

- Apify Google Maps Reviews Actor API: <https://apify.com/compass/google-maps-reviews-scraper/api>
- Apify API v2: <https://docs.apify.com/api/v2>
- Playwright locators: <https://playwright.dev/docs/locators>
- Playwright actionability and auto-waiting: <https://playwright.dev/docs/actionability>
- Playwright BrowserContext and storage state: <https://playwright.dev/docs/api/class-browsercontext>
- Google Places review field and limits: <https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places>
