# Implementation Preparation: Switch Crawler Engine ke Apify

**Status:** backlog preparation, belum ada code dan belum ada cutover  
**Priority:** P0 recovery, kemudian production hardening  
**Owner:** Codex/Crawler System  
**Partner:** Claude/OneBox, Infra/Security, Product/CEO  
**Tanggal:** 2026-09-14

## 1. Tujuan

Menyiapkan perpindahan execution engine dari Selenium self-hosted ke Apify
sebagai source provider, dengan perubahan minimum pada OneBox dan Crawler.

Outcome yang diinginkan:

```text
Admin klik Mulai Crawl di OneBox
  -> OneBox enqueue CrawlJob existing
  -> Crawler worker menjalankan Apify Actor
  -> Crawler membaca dataset dan menormalisasi review
  -> review tersimpan di DB Crawler
  -> OneBox auto-pull delta
  -> review tersimpan di DB OneBox
  -> labeling native
  -> Kelola Review siap digunakan
```

AI analysis tetap asynchronous dan berada di luar critical path fetch review.

## 2. Non-goal

Pekerjaan ini tidak otomatis mencakup:

- mengganti endpoint OneBox atau membuat API baru untuk Apify;
- memindahkan scheduler ke Apify;
- membuat ulang schema review OneBox;
- membangun engine sentiment/AI baru;
- menghapus Selenium sebelum rollback terbukti;
- menyalin token atau Google credentials ke source code;
- menyatakan Apify legal, gratis, atau selalu lebih cepat tanpa review resmi;
- mengubah requirement target 10 sampai 300 review tanpa persetujuan Product.

## 3. Keputusan Yang Harus Disahkan Sebelum Coding

| Keputusan          | Pilihan yang disarankan                                    | Owner approval        | Approval | Notes                                                        |
| ------------------ | ---------------------------------------------------------- | --------------------- | -------- | ------------------------------------------------------------ |
| Actor              | Actor `pP8fxA1kSf7snQKNW` atau actor public yang disetujui | Product + Crawler     | pending  |                                                              |
| Actor version      | Pin versi tertentu, bukan latest floating                  | Crawler + Infra       | pending  |                                                              |
| Source mode        | `apify` via feature flag; Selenium tetap rollback          | Crawler               | ✅        |                                                              |
| Scheduler          | OneBox tetap single scheduler                              | OneBox + Product      | ✅        |                                                              |
| Data privacy       | `personalData` false/true berdasarkan use case dan legal   | Product + Security    |          |                                                              |
| Direct review link | Raw payload dulu atau promote optional `review_url`        | Product + OneBox      | ✅        |                                                              |
| Photo URL          | Pertahankan `reviewer_photo_url` bila diizinkan            | Product + Security    | ✅        |                                                              |
| Date filtering     | Actor newest/date capability versus filter di Crawler      | Crawler + Product     | ✅        |                                                              |
| Target cap         | Existing 1..300 atau actor limit yang lebih kecil          | Product               | ✅        | Tetap gunakan algoritma dipisah menjadi batch dengan max 500 |
| Retry policy       | Retry provider transient, bukan auth/schema                | Crawler               |          |                                                              |
| Cost budget        | Budget per run, tenant, hari, dan bulan                    | Finance/Infra/Product |          |                                                              |
| Data retention     | Dataset/`raw_payload`/debug artifact retention             | Security/Infra        |          |                                                              |

Tidak boleh menggunakan actor hanya karena Console bisa menghasilkan dataset.
Actor harus lulus source, contract, security, cost, dan OneBox acceptance.

## 4. Data Yang Harus Diambil Dari Apify Console

Untuk actor link:

```text
https://console.apify.com/actors/pP8fxA1kSf7snQKNW/input
```

Export atau catat, tanpa token dan personal data:

- canonical Actor ID dan owner;
- visibility public/private dan maintainer;
- version yang dipakai dan changelog;
- input schema lengkap;
- output schema lengkap;
- example input dan example output satu review;
- maximum review per place/run;
- multi-place support dan concurrency;
- sort option dan date-filter semantics;
- `placeIds` versus `startUrls` dan format yang valid;
- `personalData`, review URL, photo, owner response options;
- proxy group, country, rotation, dan custom proxy policy;
- run timeout, retry, resource/memory option;
- default dataset dan retention;
- API endpoint dan authentication method;
- webhook/run polling capability;
- pricing, compute charge, proxy charge, output charge, free quota;
- actor license, acceptable-use, privacy/DPA, dan terms.

Jika Console tidak bisa diakses oleh engineer, minta owner actor mengirim
schema JSON dan sanitized output sample. Jangan mulai mapping dari screenshot
field saja.

## 5. Existing Contract Yang Dipertahankan

### 5.1 Request OneBox ke Crawler

Payload tetap memakai kontrak existing:

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

`date_from`, `date_to`, `scan_limit`, dan `dry_run` tetap disimpan pada request
job. OneBox tidak mengirim Apify token atau memilih actor arbitrary.

### 5.2 Review output

Crawler tetap mengeluarkan contract v1 untuk OneBox. Field provider dipetakan
ke canonical field sebelum persistence dan sebelum endpoint integration.

| Canonical field                | Wajib/optional       | Catatan implementasi                                |
| ------------------------------ | -------------------- | --------------------------------------------------- |
| `source`                       | Wajib                | Nilai baru `apify_google_maps`.                     |
| `external_place_id`            | Wajib untuk location | Ambil dari master Location. Validasi item provider. |
| `external_review_id`           | wajib                | Kunci dedup utama.                                  |
| `reviewer_name`                | Optional             | Fallback `Anonymous`.                               |
| `reviewer_profile_url`         | wajib                | Tergantung personal-data policy.                    |
| `reviewer_photo_url`           | wajib                | Sudah ada di model internal; cek projection OneBox. |
| `reviewer_local_guide_level`   | Optional             | `isLocalGuide` -> `Local Guide`.                    |
| `reviewer_total_reviews`       | Optional             | Parse integer.                                      |
| `rating`                       | wajib                | Valid 1..5.                                         |
| `review_text`                  | Wajib string         | Rating-only boleh `""`.                             |
| `review_relative_time`         | Optional             | Label dari Google.                                  |
| `review_time`                  | Optional             | UTC dari absolute date.                             |
| `review_language` / `language` | Wajib fallback       | `unknown` jika tidak ada.                           |
| `like_count`                   | Wajib fallback       | Non-negative, default 0.                            |
| `owner_response_text`          | Optional             | Map dari schema actor aktual.                       |
| `owner_response_time`          | Optional             | UTC bila ada.                                       |
| `scraped_at`                   | Wajib                | Waktu Crawler menerima data.                        |
| `raw_payload`                  | Internal             | Bounded/redacted, bukan contract OneBox.            |
| `review_hash`                  | Wajib                | Dibuat canonical oleh Crawler.                      |

## 6. Field Tambahan Dari CEO/Product Request

### 6.1 Direct review link

Jika actor memberi `reviewUrl`, field itu bernilai bagi operator karena dapat
membuka konteks review langsung di Google Maps. Namun field ini belum boleh
dianggap tersedia end-to-end.

Task yang diperlukan:

1. pastikan URL benar-benar menuju review, bukan hanya Place page;
2. pastikan URL tidak mengandung token atau session;
3. tambahkan sebagai optional field jika product menyetujui;
4. tambahkan ke model Crawler, integration projection, model OneBox, dan UI;
5. tambah contract fixture dan test backward compatibility;
6. jika belum siap, simpan di bounded `raw_payload` dan jangan tampilkan link
   palsu.

### 6.2 Photo URL dan reviewer information

Photo URL, reviewer ID, profile URL, dan nama reviewer adalah data personal.
Kebutuhan operasional harus dibandingkan dengan minimization policy. Actor yang
memiliki toggle `personalData` harus dijalankan dengan nilai yang telah disetujui,
bukan default Console secara diam-diam.

### 6.3 Place rating snapshot

Rating total dan total review Google adalah snapshot level place. Simpan di
metadata batch/location bila dibutuhkan untuk tren, bukan sebagai nilai rating
review. Snapshot gagal tidak boleh menggagalkan review ingestion.

## 7. Work Breakdown Codex / Crawler

### P0-A. Discovery actor

- [ ] Export actor input schema dari Console.
- [ ] Export actor output schema dan sample sanitized.
- [ ] Catat canonical Actor ID, owner, dan pinned version.
- [ ] Catat max review, date/sort, proxy, retention, pricing.
- [ ] Jalankan satu run dengan Place ID yang sudah known-good.
- [ ] Simpan run ID, dataset ID, item count, latency, dan cost tanpa secret.

### P0-B. Source spike tanpa perubahan pipeline

- [ ] Buat spike client terisolasi atau test harness.
- [ ] Jalankan target 10 pada satu location non-critical.
- [ ] Buktikan lebih dari lima review terbaca.
- [ ] Buktikan place identity cocok dengan input.
- [ ] Buktikan direct review link/photo/owner response jika dibutuhkan.
- [ ] Catat provider empty/partial/error state.
- [ ] Bandingkan hasil dengan Selenium terakhir secara kualitatif.

### P0-C. Adapter boundary

- [ ] Tambahkan source mode `apify` secara validated.
- [ ] Tambahkan `ApifyGoogleMapsReviewClient` ke `ReviewSourceClient`.
- [ ] Jadikan worker menggunakan factory/source selection, bukan Selenium
  hardcode.
- [ ] Pertahankan Selenium sebagai fallback.
- [ ] Pastikan mock source dan Google Places mode tidak berubah.

### P0-D. Provider orchestration

- [ ] Implement start run dengan Bearer token server-side.
- [ ] Implement polling status dengan timeout dan bounded backoff.
- [ ] Ambil dataset menggunakan dataset ID run.
- [ ] Simpan provider run/dataset/status ke metadata job.
- [ ] Definisikan behavior worker lease expiry dan orphan provider run.
- [ ] Jangan membuat provider run ganda saat retry tanpa keputusan eksplisit.

### P0-E. Normalization dan data quality

- [ ] Buat fixture lengkap, minimal, invalid, partial, dan duplicate.
- [ ] Map field actor ke canonical field.
- [ ] Validasi rating, timestamp, language, count, owner response.
- [ ] Terapkan `external_place_id` dari master Location.
- [ ] Pertahankan canonical `review_hash` dan dedup semantics.
- [ ] Redact token/header/cookie dari `raw_payload` dan log.
- [ ] Tambah field `review_url` hanya lewat additive contract jika approved.

### P0-F. Error and status

- [ ] Map 401/403 menjadi provider auth failure, non-retryable.
- [ ] Map 429/5xx/network timeout menjadi transient provider error.
- [ ] Map actor failed/timed-out/aborted secara jujur.
- [ ] Dataset empty tidak menjadi `completed` tanpa diagnosis.
- [ ] Partial dataset tetap menyimpan item valid dan status partial.
- [ ] `stop_reason` terlihat pada API dan UI OneBox.

### P0-G. Test dan rollout

- [ ] Unit test adapter dan normalizer.
- [ ] Contract test `GET /api/integration/v1/reviews`.
- [ ] Integration test fake Apify API.
- [ ] Live target 10 dev.
- [ ] Live target 10 staging pada tiga location.
- [ ] OneBox auto-import dan native labeling.
- [ ] Rerun tidak menggandakan review.
- [ ] Canary production satu tenant/location.
- [ ] Rollback ke Selenium diuji tanpa menghapus DB/volume.

## 8. Work Breakdown Claude / OneBox

Claude tidak perlu membangun client Apify. Fokusnya menjaga pengalaman dan
kontrak OneBox tetap benar:

- [ ] Pastikan backend OneBox tetap yang menambahkan token Crawler, bukan browser.
- [ ] Tidak mengirim token Apify ke frontend.
- [ ] Tetap mengirim `onebox_location_id`, target, date range, sort, dry run.
- [ ] Saat batch `queued/running`, tampilkan status provider tanpa fake percent.
- [ ] Saat provider run selesai, lanjut auto-import tanpa tombol kedua.
- [ ] Import memakai cursor dan checkpoint existing.
- [ ] Upsert memakai `review_hash`/RemoteId tanpa ticket/message ganda.
- [ ] Tampilkan `target`, `scanned`, `fetched`, `inserted`, `duplicate`, `failed`.
- [ ] Tampilkan `provider`, `provider_run_id` yang aman, dan `stop_reason`.
- [ ] Bedakan `completed`, `partial_success`, `failed`, `empty result`, dan
  `auth/provider error`.
- [ ] Pastikan review baru masuk Kelola Review sebelum AI async.
- [ ] Jalankan native sentiment labeling existing.
- [ ] Jangan membuat Ticket untuk review historis karena source berganti.
- [ ] Jika `review_url` disetujui, tampilkan action buka link dengan aman.
- [ ] Jika photo/name disembunyikan oleh policy, UI tidak menganggap field error.
- [ ] Test refresh browser, duplicate click, retry, dan partial import.

## 9. Requirement Infra / Security

- [ ] Buat secret `APIFY_API_TOKEN` di secret store/environment per environment.
- [ ] Token tidak berada di git, Docker image, Console screenshot, atau log.
- [ ] Allowlist outbound HTTPS ke Apify API jika egress firewall berlaku.
- [ ] Tentukan DNS/TLS/timeout dan monitoring request provider.
- [ ] Pisahkan dev, staging, dan production token/budget.
- [ ] Set concurrency rendah untuk canary.
- [ ] Set budget alert dan hard limit bila platform mendukung.
- [ ] Tetapkan retention Apify Dataset dan raw payload internal.
- [ ] Batasi akses ke review personal data dan debug artifact.
- [ ] Review DPA, privacy, acceptable use, Actor license, dan Google terms.
- [ ] Siapkan dashboard provider latency, error, item count, cost, dan import.
- [ ] Pastikan no duplicate schedule antara OneBox dan Apify.

## 10. API/Metadata Design Yang Diusulkan

Tidak perlu database migration jika metadata provider cukup di `result_json` dan
`FetchLog.metadata`. Contoh:

```json
{
  "source": "apify_google_maps",
  "provider": "apify",
  "actor_id": "approved-actor-id",
  "actor_version": "approved-version",
  "provider_run_id": "safe-run-id",
  "provider_dataset_id": "safe-dataset-id",
  "provider_status": "SUCCEEDED",
  "provider_item_count": 10,
  "target_review_count": 10,
  "reviews_scanned": 10,
  "stop_reason": "target_reached"
}
```

Migration hanya diperlukan bila product menginginkan field first-class seperti
`review_url`, provider run table, cost ledger, atau durable continuation state.
Keputusan itu harus dipisah dari spike source.

## 11. Test Matrix

| Test | Expected |
|---|---|
| Actor input valid, target 10 | Run accepted, run ID tersimpan. |
| Actor token invalid | Provider auth failure, tidak retry tanpa batas. |
| Actor 429 | Backoff bounded, job retry/failed sesuai policy. |
| Actor 5xx/network timeout | Transient retry, lease aman. |
| Actor schema invalid | Job gagal jelas, tidak insert data parsial yang salah. |
| Dataset empty | Bukan success palsu; stop/provider reason terlihat. |
| Dataset partial | Item valid tersimpan, status partial. |
| Missing review ID | Fallback identity dan risk flag. |
| Invalid rating | Rating null, item tidak menjatuhkan batch. |
| Missing text | String kosong; rating-only tetap valid. |
| Date absolute | UTC canonical. |
| Duplicate rerun | Duplicate count naik, row tidak berlipat. |
| Place ID mismatch | Tidak boleh masuk location yang salah. |
| OneBox pull | Cursor checkpoint hanya maju setelah seluruh page sukses. |
| Native labeling gagal | Raw review tetap dapat dikelola dan dapat retry label. |
| AI/Ollama mati | Crawl sampai Kelola Review tetap berhasil. |
| Browser refresh/double click | Satu batch melalui idempotency. |

## 12. Acceptance Criteria P0

### Source

- [ ] Actor link/ID/version sudah confirmed dari Console.
- [ ] Satu location dengan Place ID valid menghasilkan minimal 10 item atau
  memberikan partial/failed reason yang jujur.
- [ ] Hasil tidak berhenti di lima card karena local Selenium auth wall.

### Contract

- [ ] Semua field existing tetap tersedia atau perubahan additive.
- [ ] `source`, `external_place_id`, identity, rating, text, timestamp, dan
  owner response teruji.
- [ ] `review_hash` dan dedup tetap konsisten.
- [ ] Tidak ada secret atau raw payload di integration response.

### OneBox

- [ ] User hanya klik `Mulai Crawl` sekali.
- [ ] Crawler menyimpan review.
- [ ] OneBox auto-import tanpa tombol tarik kedua.
- [ ] Review muncul di Kelola Review.
- [ ] Labeling native berjalan atau gagal secara terpisah.
- [ ] Ticket/message tidak terduplikasi.

### Operations

- [ ] Error provider terlihat dan actionable.
- [ ] Cost, latency, success rate, dan item completeness terukur.
- [ ] Rollback ke Selenium tersedia.
- [ ] Runbook on-call selesai.

## 13. Risiko Dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Actor private/permission berubah | Semua job 401/403 | Token/actor access check pada startup/canary. |
| Actor schema berubah | Data salah atau null | Pin version, fixture, schema validator, release gate. |
| Provider rate limit | Queue delay | Concurrency cap, backoff, budget monitor. |
| Provider outage | Crawl tertunda | Status jujur, retry policy, fallback decision. |
| Actor empty result | Success palsu | Empty result non-success kecuali evidence no reviews. |
| Review ID tidak stabil | Duplicate | Canonical fallback identity dan compare rerun. |
| Place mapping salah | Review masuk cabang salah | Identity selalu dari job/location master. |
| Data personal berlebih | Privacy exposure | `personalData` decision, minimization, retention. |
| Cost tidak terkontrol | Budget overrun | max cap, per-tenant budget, alert, kill switch. |
| Apify outage/vendor lock-in | Ketergantungan | Adapter interface dan Selenium rollback. |
| OneBox auto-import gagal | Review tidak terlihat | Poll/import evidence dan cursor recovery. |
| Dual scheduler | Review ganda/biaya ganda | OneBox tetap scheduler tunggal. |

## 14. Rollout Plan

### Phase 0: Research only

- actor schema, pricing, privacy, version, dan sample output confirmed;
- tidak ada code cutover.

### Phase 1: Isolated spike

- satu actor run manual/API;
- satu location;
- target 10;
- hasil disimpan sebagai sanitized evidence.

### Phase 2: Adapter dev

- source flag hanya di dev;
- fake provider tests;
- live run satu location;
- compare dengan Selenium.

### Phase 3: Staging

- pinned version dan staging token;
- tiga location target 10;
- manual dan scheduled run;
- verify auto-import, labeling, dedup, partial.

### Phase 4: Production canary

- satu tenant/location;
- target 10 lalu scheduled delta;
- monitor 24 jam atau periode yang disetujui;
- scale ke target 50 dan location lain hanya setelah gate hijau.

### Phase 5: Cutover decision

- pilih Apify sebagai default, atau tetap hybrid/rollback;
- dokumentasikan alasan, metric, cost, privacy, dan owner operasi;
- hapus Selenium hanya melalui keputusan terpisah setelah periode stabil.

## 15. Pertanyaan Untuk Product/CEO

1. Apakah target utama benar-benar full review 10 sampai 300, bukan hanya lima
   review resmi dari Places API? 
2. Apakah review harus menyertakan nama, reviewer ID, profile URL, dan photo? YA
3. Apakah direct link ke review wajib tampil di UI atau cukup untuk audit internal? wajib tampil UI untuk USER
4. Apakah data review boleh diproses oleh provider cloud pihak ketiga? 
5. Berapa target SLA manual dan scheduled per location? 
6. Berapa acceptable partial rate dan maximum cost per location/month?
7. Apakah actor yang diberikan sudah final, atau masih contoh eksplorasi?
8. Siapa owner token, billing, Actor version, dan incident response?

## 16. Output Yang Harus Dihasilkan Sebelum Coding

- [ ] Actor schema snapshot yang disanitasi.
- [ ] Provider evaluation scorecard.
- [ ] Field mapping matrix yang disetujui.
- [ ] Privacy/data handling decision.
- [ ] Cost model dan budget guard.
- [ ] API metadata/error mapping decision.
- [ ] OneBox acceptance checklist.
- [ ] Rollback plan.
- [ ] Test fixtures dan evidence format.
- [ ] Approval Product/CEO, Crawler, OneBox, dan Infra.

## 17. Referensi

- Apify Actors overview: <https://docs.apify.com/actors>
- Apify input schema: <https://docs.apify.com/actors/development/actor-definition/input-schema>
- Apify API v2: <https://docs.apify.com/api/v2>
- Public Google Maps Reviews Actor API example: <https://apify.com/compass/google-maps-reviews-scraper/api>
- Public Actor field/output example: <https://apify.com/compass/google-maps-reviews-scraper>
- Playwright locator guidance: <https://playwright.dev/docs/locators>
- Google Places review limitation: <https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places>

## 18. Evidence Cost Dan Output Aktual

Pada 2026-09-15, actor `pP8fxA1kSf7snQKNW` dijalankan untuk Five Coffee
Forest dengan Place ID `ChIJ9fLOGgDraS4RRild036hTbY`. Operator meminta 500
review, tetapi actor mengembalikan sampai 400 karena `place_reviews_count`
adalah 400. Biaya observasi US$0.142.

```text
US$0.142 / 400 = US$0.000355 per actual item
US$0.000355 * 1,000 = US$0.355 per 1,000 actual items
```

Screenshot Console menunjukkan harga sekitar US$0.35 per 1,000 review. Nilai
itu cukup dekat sebagai sanity check, tetapi budgeting tetap memakai usage
report aktual actor.

Output sample yang perlu dipertahankan atau diputuskan:

| Output actual | Keputusan mapping |
|---|---|
| `review_id` | `external_review_id` |
| `review_url` | Candidate optional `review_url`; jangan buang jika CEO membutuhkannya. |
| `place_id` | Cocokkan dengan `Location.external_place_id`; jangan trust untuk tenant routing. |
| `place_rating` | Rating snapshot place, bukan rating review. |
| `place_reviews_count` | Place snapshot/capacity evidence. |
| `rating` | Canonical review `rating` 1..5. |
| `content` | Canonical `review_text`. |
| `content_translated` | Optional translation/raw payload; jangan overwrite original text. |
| `reviewed_at` | `review_relative_time`. |
| `reviewed_at_date` | `review_time` UTC. |
| `owner_response` | `owner_response_text`. |
| `owner_response_at_date` | `owner_response_time` UTC. |
| `likes_count` | `like_count`. |
| `review_photos_urls` | Candidate optional review photo array; bukan `reviewer_photo_url`. |
| `place_photo_url` | Place metadata; jangan map ke reviewer photo. |
| reviewer fields null | Expected saat Personal information off, bukan ingestion failure. |
| `fid`, `cid`, `knowledge_graph_id` | Provider metadata/raw payload, bukan review identity utama. |

Detail model initial backfill, cap 500, dan scheduled delta berada di:

`04-implementation-plans/crawler/APIFY_COST_MODEL_AND_CAPACITY.md`

## 19. Updated P0 Exit Gate Berdasarkan Run Aktual

- [ ] Run usage/invoice dikonfirmasi, bukan hanya screenshot price.
- [ ] Actual dataset item count dibandingkan dengan requested target.
- [ ] Actor version dan schema output dicatat.
- [ ] `review_id` stabil pada rerun dan duplicate tidak bertambah salah.
- [ ] `review_url` benar-benar membuka review yang sesuai.
- [ ] Original content dan translated content tidak tertukar.
- [ ] `reviewed_at_date` dan owner response date menjadi UTC canonical.
- [ ] Personal information mode disetujui Product/Security.
- [ ] Cost model untuk 10 site x 20 branch disetujui.
- [ ] Target 10 end-to-end sampai OneBox Kelola Review berhasil.
