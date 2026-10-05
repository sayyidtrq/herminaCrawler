# VoC Learning Note: Switch Engine Crawler ke Apify

**Tujuan dokumen:** membangun pemahaman bersama sebelum ada perubahan kode.
Dokumen ini bukan approval cutover dan bukan implementation code.

**Status:** discovery dan decision preparation  
**Tanggal:** 2026-09-14  
**Owner:** Crawler System + OneBox VoC

## 1. Ringkasan Eksekutif

Crawler Selenium sudah berjalan sekitar satu bulan, lalu sejak 11 September
2026 mengalami kegagalan saat pagination Google Maps. Lima review awal terlihat,
tetapi load-more berhenti pada `GOOGLE_AUTH_REQUIRED` atau state yang setara.
Proxy dan login manual sudah dicoba. API, database, token, queue, worker, URL
Place ID, dan mount profile bukan blocker utama.

Hipotesis IP/reputation Google masuk akal, tetapi belum merupakan bukti final.
Karena itu Apify cocok sebagai eksperimen P0: eksekusinya memakai infrastructure,
browser, dan egress yang berbeda dari server Crawler. Jika Apify berhasil pada
location yang sama sementara Selenium gagal, variabel host/egress/profile menjadi
lebih kuat sebagai penyebab. Jika Apify juga gagal, sumber masalah bisa berada
di Place ID, actor input, Google policy, atau data source.

Keputusan yang dipelajari di sini:

```text
OneBox tetap menjadi orchestrator bisnis.
Crawler tetap menjadi owner CrawlJob, tenant, normalisasi, dedup, dan DB.
Apify hanya menjadi source execution provider.
OneBox tetap menarik review dari contract Crawler yang sama.
```

## 2. Mengapa Tidak Langsung Mengubah OneBox Memanggil Apify

Jika browser OneBox langsung memanggil Apify:

- token Apify berisiko terlihat di browser;
- tenant boundary dan permission berpindah ke layer yang tidak dirancang untuk
  itu;
- retry/idempotency Crawler tidak lagi menjadi pusat;
- hasil dataset harus dipetakan ulang di OneBox;
- observability dan rollback menjadi tersebar;
- scheduler OneBox dan scheduler Apify berpotensi menggandakan crawl.

Desain yang disarankan:

```text
OneBox UI/backend
  -> POST Crawler /api/integration/v1/crawl-jobs
  -> Crawler CrawlJob + worker
  -> Apify Actor run menggunakan token server-side
  -> Apify Dataset
  -> Crawler canonical normalizer + DB Crawler
  -> OneBox GET /api/integration/v1/reviews
  -> OneBox auto-import + native labeling
```

Dengan boundary ini, penggantian engine tidak menjadi penggantian sistem VoC.

## 3. Apa Itu Apify Dalam Konteks Ini

Apify Actor adalah program terisolasi yang menerima JSON input, menjalankan
tugas di platform Apify, lalu dapat menghasilkan Dataset, Key-Value Store,
atau resource output lain. Actor dapat dijalankan manual melalui Console,
REST API, client library, CLI, atau schedule.

Satu run memiliki:

| Komponen | Makna untuk Crawler |
|---|---|
| Actor ID | Program yang dipilih, bukan identitas location/tenant. |
| Actor version | Kontrak perilaku yang harus dipin dan diaudit. |
| Input schema | Nama, tipe, default, required, batas, dan UI input actor. |
| Run ID | Identitas eksekusi provider untuk audit dan retry. |
| Run status | State provider yang dipetakan ke state CrawlJob. |
| Default dataset ID | Tempat item hasil review dibaca. |
| Dataset item | Raw/structured output yang dinormalisasi Crawler. |
| Usage/cost | Compute, proxy, dan output yang harus dibatasi. |

Input schema Apify dapat memvalidasi input sebelum Actor dimulai. Artinya
request ke actor tidak boleh dibangun berdasarkan tebakan nama field dari UI;
schema dan version yang benar harus diekspor serta disimpan sebagai fixture
internal.

## 4. Actor Yang Sedang Dipertimbangkan

### 4.1 Link yang diberikan

```text
https://console.apify.com/actors/pP8fxA1kSf7snQKNW/input
```

Status audit saat dokumen ini dibuat:

- URL menunjuk halaman input Actor di Apify Console.
- Detail tidak dapat dibaca dari sesi publik tanpa autentikasi Console.
- Actor ID/owner/version, input schema, output schema, pricing, proxy policy,
  dan retention belum boleh dianggap confirmed dari link saja.
- Sebelum coding, operator harus membuka Console dan mengekspor snapshot
  schema/input-output yang sudah disanitasi.

### 4.2 Actor publik sebagai referensi pola

Actor publik Google Maps Reviews Scraper yang didokumentasikan Apify memiliki
input umum seperti `startUrls`, `placeIds`, `maxReviews`, sorting, date filter,
language, personal-data switch, dan proxy configuration. Output publiknya
memiliki field review seperti `reviewId`, `name`, `reviewerUrl`,
`reviewerPhotoUrl`, `reviewerNumberOfReviews`, `isLocalGuide`, `text`,
`originalLanguage`, `publishAt`, `publishedAtDate`, dan `stars`.

Informasi itu adalah **candidate mapping**, bukan jaminan bahwa Actor
`pP8fxA1kSf7snQKNW` memakai schema yang sama. Actor yang dipakai harus dinilai
berdasarkan schema aktualnya.

### 4.3 Apa yang harus diambil dari Console

Sebelum implementation, simpan catatan non-secret berikut:

| Area Console | Yang harus dicatat |
|---|---|
| Actor identity | Owner, Actor ID canonical, visibility, maintainer. |
| Version | Latest version, recommended pinned version, last modified. |
| Input schema | Semua field, type, default, enum, min/max, required. |
| Output schema | Semua field, type, nullable, sample item. |
| Place targeting | `placeIds`, `startUrls`, URL format, multiple-place support. |
| Review limit | Max review per place/run, concurrency, scan cap. |
| Sort/date | Newest/relevance/highest/lowest dan semantics date cutoff. |
| Personal data | Name, reviewer ID, profile URL, photo, review URL switch. |
| Owner response | Text/date fields dan apakah selalu populated. |
| Proxy | Default proxy group, region, rotation, custom proxy capability. |
| Runtime | Browser engine, timeout, retry, max duration. |
| Storage | Default dataset, retention, export, pagination. |
| Billing | Price basis, compute/proxy/output charge, free quota, budget control. |
| Integration | API/CLI/client examples, webhook support, run status API. |
| Terms | Actor license, Google data terms, privacy/DPA, acceptable use. |

Jangan simpan API token atau personal data hasil crawl dalam snapshot ini.

## 5. Cara Berpikir Tentang P0 Validation

Uji Apify bukan hanya “run actor berhasil”. Ada tiga pertanyaan terpisah:

### A. Source viability

Apakah Actor dapat membuka Place ID dan membaca lebih dari lima review?

### B. Contract viability

Apakah output Actor dapat diubah ke field canonical Crawler tanpa kehilangan
identity, waktu, rating, response, dan location mapping?

### C. Product viability

Apakah review dapat tersimpan di Crawler, ditarik OneBox, dilabeli native, lalu
dipakai di Kelola Review tanpa tombol tarik kedua?

Semua harus hijau. A hanya hijau tidak cukup untuk cutover.

## 6. Field Canonical Existing Crawler

Boundary existing `ReviewSourceClient` mengembalikan list dictionary. Setelah
itu Crawler melakukan normalisasi dan persistence. Field yang harus dipertahankan:

| Field canonical | Asal/aturan |
|---|---|
| `source` | `apify_google_maps` untuk source baru. Jangan menyamar sebagai Selenium. |
| `external_place_id` | Diambil dari master `Location`, bukan dipercaya dari item provider. |
| `external_review_id` | ID review provider jika tersedia. Identity utama dedup. |
| `reviewer_name` | Nama tampilan atau `Anonymous`. |
| `reviewer_profile_url` | URL profil jika tersedia. |
| `reviewer_photo_url` | URL foto jika personal data diizinkan. |
| `reviewer_local_guide_level` | Map `isLocalGuide=true` ke `Local Guide`. |
| `reviewer_total_reviews` | Parse angka review reviewer bila tersedia. |
| `rating` | Integer 1..5. |
| `review_text` | Teks review, string kosong bila rating-only. |
| `review_relative_time` | Label sumber seperti `3 months ago`. |
| `review_time` | Timestamp absolute hasil parse `publishedAtDate` jika tersedia. |
| `review_language` / `language` | Bahasa asli atau `unknown`. |
| `like_count` | Integer non-negatif bila tersedia. |
| `owner_response_text` | Jawaban pemilik bila tersedia. |
| `owner_response_time` | Timestamp absolute bila tersedia. |
| `scraped_at` | Waktu Crawler menerima item. |
| `raw_payload` | Item provider yang sudah dibatasi dan disanitasi. |
| `review_hash` | Dibuat oleh Crawler dari canonical data. |

## 7. Field Tambahan Yang Berpotensi Berguna

### 7.1 Direct link to review

`review_url` adalah field yang berguna untuk customer support dan audit, tetapi
tidak boleh diasumsikan sudah tersedia sebagai first-class field di kontrak
OneBox. Ada tiga pilihan:

| Pilihan | Dampak |
|---|---|
| Simpan di `raw_payload` saja | Perubahan minimum, tetapi UI/OneBox sulit membuat link stabil. |
| Tambah optional `review_url` di Crawler dan integration contract | Lebih berguna dan additive, perlu migration/projection/OneBox mapping. |
| Rekonstruksi URL dari Place ID + review ID | Tidak selalu stabil; jangan dijadikan default tanpa bukti provider. |

Rekomendasi: jika CEO benar-benar membutuhkan deep link, promosikan menjadi
field optional canonical melalui perubahan additive dan test contract. Jangan
mengorbankan ingestion jika link tidak tersedia.

### 7.2 Photo URL

Crawler sudah memiliki `reviewer_photo_url` pada model internal, tetapi field
yang dikirim integration API dan field OneBox harus diverifikasi. Jika belum
diproyeksikan, tambahkan secara additive hanya setelah keputusan privacy.

Personal data switch harus eksplisit:

- `personalData=false`: minimalkan nama, ID, profile URL, photo URL.
- `personalData=true`: hanya bila product/legal menyetujui kebutuhan VoC.

### 7.3 Place snapshot

Rating Google dan total review adalah metadata tempat, bukan review item. Jika
Actor mengembalikannya, simpan sebagai rating snapshot batch/location. Snapshot
tidak boleh menggagalkan import review.

## 8. Mapping Kandidat Actor ke Sistem

Mapping berikut harus diuji terhadap output Actor aktual:

| Candidate Apify field | Existing field | Validasi |
|---|---|---|
| `reviewId` | `external_review_id` | Tidak null untuk item normal; stabil pada rerun. |
| `reviewUrl` | optional `review_url` | Pastikan URL benar-benar menuju review. |
| `name` | `reviewer_name` | Fallback anonymous. |
| `reviewerUrl` | `reviewer_profile_url` | Optional. |
| `reviewerPhotoUrl` | `reviewer_photo_url` | Respect personal-data policy. |
| `isLocalGuide` | `reviewer_local_guide_level` | Boolean mapping. |
| `reviewerNumberOfReviews` | `reviewer_total_reviews` | Parse number/compact count. |
| `stars` | `rating` | Enforce 1..5. |
| `text` | `review_text` | Rating-only boleh kosong. |
| `publishedAtDate` | `review_time` | Parse UTC; jangan pakai local time. |
| `publishAt` | `review_relative_time` | Simpan sebagai label sumber. |
| `originalLanguage` | `review_language`, `language` | Fallback `unknown`. |
| owner reply fields | `owner_response_text/time` | Nama field harus dari schema aktual. |
| place ID | validate `Location` | Mismatch tidak boleh memindahkan tenant/location. |
| raw item | `raw_payload` | Redact, size bound, no token/cookie/header. |

## 9. Status Provider Dan Status CrawlJob

Crawler tetap authoritative terhadap lifecycle job. Status Apify hanya menjadi
detail provider:

| Apify/provider state | Crawler interpretation | OneBox UI |
|---|---|---|
| run accepted/ready | `queued` | Menunggu worker/provider |
| running | `running` | Mengambil review dari provider |
| dataset being read | `running`/`importing` internal | Membaca hasil review |
| succeeded + items | `succeeded` atau `partial_success` berdasarkan target | Review siap diimport |
| succeeded + zero items | Failed/diagnostic, bukan success palsu | Tampilkan source/target issue |
| failed | `failed` | Tampilkan sanitized provider failure |
| timed out | `retry_wait` atau `failed` sesuai retry policy | Tampilkan timeout dan retry |
| aborted/cancelled | `failed`/cancelled policy | Tampilkan dibatalkan |

Run ID, dataset ID, item count, provider status, dan stop reason masuk metadata
job. Token dan personal data tidak pernah masuk metadata.

## 10. Apify Tidak Sama Dengan API Google Resmi

Apify Actor yang membaca halaman publik adalah pihak ketiga/platform scraping,
bukan Google Places API. Nilai tambahnya adalah browser/egress/orchestration
yang dikelola provider. Konsekuensinya:

- schema Actor bukan kontrak Google;
- Actor version dan maintainer menjadi dependency;
- harga dan limit dapat berubah;
- data review melewati pihak ketiga;
- public visibility tidak menghapus privacy dan compliance obligation.

Google Places API resmi lebih stabil, tetapi review Place Details dibatasi
maksimal lima review dan relevance-based. Ia tidak memenuhi target product
10 sampai 300 review tanpa mengubah requirement.

## 11. Penilaian Klaim Speed, Security, Performance

Jangan menyatakan Apify otomatis lebih cepat, aman, atau performant sebelum
benchmark dengan location dan target yang sama.

Yang mungkin membaik:

- egress/proxy dan browser operation tidak dikelola di host sendiri;
- tidak membutuhkan profile Google lokal pada Crawler;
- provider dapat menjalankan browser dan proxy secara terkelola;
- Crawler tidak lagi menanggung selector DOM Google secara langsung jika Actor
  mengembalikan structured output.

Yang bertambah:

- network hop Crawler -> Apify -> dataset;
- dependency provider dan actor schema;
- billing dan budget control;
- review data keluar dari boundary internal;
- observability lintas sistem.

Benchmark minimal: time-to-first-result, time-to-target-10, success rate,
partial rate, duplicate rate, item completeness, cost per location, dan
OneBox end-to-end latency.

## 12. Mental Model Keputusan

```text
Apakah Selenium gagal karena browser/profile/egress host?
  |-- Apify berhasil -> source/egress host sangat mungkin blocker
  |-- Apify gagal juga -> cek actor input, Place ID, Google policy, data source

Apakah output Apify lengkap dan stable?
  |-- ya -> adapter + contract test + canary
  |-- tidak -> actor lain / field promotion / requirement review

Apakah OneBox tetap bisa auto-import dan labeling?
  |-- ya -> product cutover candidate
  |-- tidak -> integration blocker, bukan source success
```

## 13. Referensi Pembelajaran

- Apify Actors overview: <https://docs.apify.com/actors>
- Apify input schema: <https://docs.apify.com/actors/development/actor-definition/input-schema>
- Apify API v2: <https://docs.apify.com/api/v2>
- Example Google Maps Reviews Actor API: <https://apify.com/compass/google-maps-reviews-scraper/api>
- Example Actor output/input: <https://apify.com/compass/google-maps-reviews-scraper>
- Playwright locator guidance: <https://playwright.dev/docs/locators>
- Google Places review limitation: <https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places>

## 14. Evidence Run Five Coffee Forest, 15 September 2026

Operator menjalankan Actor `pP8fxA1kSf7snQKNW` untuk Place ID
`ChIJ9fLOGgDraS4RRild036hTbY`, Five Coffee Forest.

Hasil penting:

| Field | Observed value |
|---|---|
| Requested target | 500 review |
| `place_reviews_count` | 400 |
| `place_rating` | 4.4 |
| Observed cost | US$0.142 |
| Review sample position | 1 |
| Review sample rating | 5 |
| `reviewed_at_date` | 2026-08-28T00:00:00Z |
| Owner response | Ada, dengan `owner_response_at_date` 2026-09-08T00:00:00Z |
| `review_url` | Ada dan dapat menjadi candidate direct link |
| `scraped_at` | 2026-09-15 02:30:08 UTC |
| Personal information | Off pada Console screenshot |

Output sample juga menunjukkan bahwa `content` dan `content_translated`
berbeda. Mapping awal yang aman adalah menyimpan `content` sebagai
`review_text`, sedangkan terjemahan menjadi optional field/raw payload sampai
contract OneBox disetujui.

Dengan personal information off, field `reviewer_id`, `reviewer_name`,
`reviewer_url`, `reviewer_photo_url`, dan `reviewer_reviews_count` bernilai
null. Ini bukan error ingestion; ini konsekuensi policy data minimization.

Place-level `place_photo_url`, address, category, `fid`, `cid`, dan
`knowledge_graph_id` bukan field review canonical. Jangan memetakan
`place_photo_url` ke `reviewer_photo_url`.

## 15. Pelajaran Dari Evidence

1. `maxReviews=500` berarti cap request. Actual dataset boleh 400 karena place
   hanya memiliki 400 review.
2. Biaya observed adalah US$0.000355 per actual dataset item, bukan per target
   yang diminta.
3. Actor menghasilkan direct review URL dan owner response yang berguna untuk
   product, tetapi field tersebut harus divalidasi end-to-end.
4. `language=en` pada output belum tentu bahasa asli review; karena ada
   `content_language=null` dan `translated_language=en`, jangan menetapkan
   `review_language=en` tanpa aturan source yang jelas.
5. `source="Google"` adalah label provider. Crawler tetap memakai source
   internal seperti `apify_google_maps` agar provenance dan rollback jelas.
6. Evidence ini cukup untuk melanjutkan cost/source spike, belum cukup untuk
   cutover 200 locations.

Perhitungan portfolio berada di:

`04-implementation-plans/crawler/APIFY_COST_MODEL_AND_CAPACITY.md`
