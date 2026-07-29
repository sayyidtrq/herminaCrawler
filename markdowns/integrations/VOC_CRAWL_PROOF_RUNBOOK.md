# VOC Crawl Proof Runbook

> Protocol verifikasi end-to-end untuk demo Voice of Customer di Dev. Acuan: `PLAN_KEY_PROCESS_DEMO.md`, `PROMPT_VOC_CRAWL_PROOF.md`, ADR-0001, ADR-0002, dan ADR-0003.
>
> Label wajib: **[verified]** = ada bukti command/query/response; **[assumption]** = belum diuji; **[blocked]** = tertahan dependency atau contract gap.

## 1. Tujuan dan scope

Proof ini membuktikan satu target lokasi baru melewati rantai:

```text
OneBox tambah lokasi
 -> OneBox publish worklist
 -> Crawler pull worklist
 -> Crawler crawl Google review
 -> Crawler simpan + dedup + AI analysis
 -> OneBox pull delta
 -> OneBox ingest menjadi Message/Ticket
 -> OneBox tampilkan dashboard dan eskalasi Ticket
```

Ini proof demo, bukan production-readiness review. Gunakan satu company, satu site, satu lokasi, dan target review kecil. Jangan menaruh password, token, cookie, raw cursor, API key, atau full review text di Git, chat, screenshot, atau log.

## 2. Status saat ini

| Tahap | Status | Bukti / catatan |
|---|---|---|
| OneBox -> Crawler worklist pull | **[verified]** | `refresh_worklist` berhasil `status=synced`, `fetched=1`, `upserted=1`, `warning=null`. |
| Service auth review pull | **[verified]** | `/api/integration/v1/whoami` dan `/reviews` memakai bearer service token. |
| Tenant binding | **[verified]** | Company berasal dari token, bukan query request. |
| Crawl target baru | **[blocked]** sampai X1 | Belum ada bukti live target yang baru masuk worklist. |
| Review terikat lokasi benar | **[blocked]** sampai X1/X2 | Harus dibuktikan lewat API evidence. |
| AI analysis target baru | **[blocked]** sampai X2 | LLM harus reachable dari container. |
| Delta ke OneBox | **[assumption]** | Contract tersedia, ingest live terhadap review baru belum dibuktikan. |
| Review -> Ticket -> eskalasi | **[assumption]** | Provider/mapping sudah ada, bukti live Dev belum dilampirkan. |
| Trigger crawl dari OneBox | **[blocked]** | Crawl saat ini JWT user + synchronous; endpoint service-token non-blocking belum ada. |

## 3. Branch dan deployment rule

```text
coding di branch DNG/DNGO
 -> push branch DNG
 -> Pull Request ke feature/voc
 -> merge oleh owner OneBox
 -> deployment/migration ke Dev
 -> uji di https://dev.onebox.co.id/feature/voc/
```

Jangan menganggap branch DNG sudah otomatis tersedia di `dev.onebox.co.id`. Perubahan Crawler System yang diuji di `ciptadra-svr` harus memakai commit/image yang tercatat di evidence packet.

## 4. Contract aktual yang dipakai

### 4.1 Worklist OneBox -> Crawler

```text
POST {ONEBOX_BASE_URL}/api/Authenticate
  form: email, password, siteId

GET {ONEBOX_BASE_URL}/api/VocWorklist
  Authorization: Bearer <JWT>
```

Konfigurasi server Crawler:

```dotenv
ONEBOX_BASE_URL=https://dev.onebox.co.id/feature/voc
ONEBOX_SVC_EMAIL=<service-account>
ONEBOX_SVC_PASSWORD=<secret>
ONEBOX_SITE_ID=<site-id>
ONEBOX_COMPANY_ID=<explicit-voc-company-id>
ONEBOX_WORKLIST_PATH=/api/VocWorklist
```

Item worklist minimal:

```json
{
  "data": [{
    "onebox_location_id": 12,
    "kind": "location",
    "external_place_id": "ChIJ...",
    "branch_name": "Hermina Depok",
    "active": true,
    "crawl_enabled": true,
    "ingest_reviews": true,
    "target_review_count": 5
  }],
  "meta": {"site_id": 169, "count": 1}
}
```

### 4.2 Endpoint Crawler saat ini

| Endpoint | Auth | Sifat | Proof |
|---|---|---|---|
| `POST /api/fetch-jobs` | JWT user | synchronous/blocking | X1 |
| `POST /api/fetch-jobs/all-active` | JWT user | synchronous/blocking | fallback saja |
| `POST /api/pipeline/location` | JWT user | synchronous/blocking | opsi lokal, bukan contract OneBox |
| `GET /api/fetch-logs` | JWT user | history | evidence X1 |
| `POST /api/analysis/pending` | JWT user | synchronous | X3 |
| `GET /api/integration/v1/whoami` | service bearer | validasi tenant | X4 |
| `GET /api/integration/v1/reviews` | service bearer + `reviews:read` | delta pull | X4 |
| `POST /api/integration/v1/crawl-jobs` | belum ada | non-blocking | X5 blocked |
| `GET /api/integration/v1/crawl-jobs/{batch_id}` | belum ada | status batch | X5 blocked |

### 4.3 Delta review contract

```http
GET /api/integration/v1/reviews?limit=100
Authorization: Bearer <VOC_SERVICE_TOKEN>
X-Request-ID: onebox-voc-proof-<run-id>
```

Response harus tetap berbentuk:

```json
{
  "data": [],
  "page": {
    "limit": 100,
    "has_more": false,
    "next_cursor": null,
    "checkpoint_cursor": "<opaque>",
    "snapshot_at": "2026-07-29T00:00:00Z"
  },
  "meta": {"api_version": "v1", "request_id": "<id>"}
}
```

OneBox menyimpan `checkpoint_cursor` hanya sesudah semua page berhasil di-ingest. Jika `has_more=true`, lanjut memakai `next_cursor`. Jangan mencampur crawl cursor milik Crawler dengan ingestion checkpoint milik OneBox.

## 5. G0 - preflight server

Jalankan di `ciptadra-svr`:

```bash
cd ~/herminaCrawler
docker compose ps
curl -fsS http://127.0.0.1:8000/api/health
docker compose logs --tail=100 api
docker compose exec api printenv ONEBOX_BASE_URL
```

Gate G0 lulus bila container healthy, health/database `ok`, migration startup tidak error, dan URL menunjuk Dev feature yang benar.

Refresh worklist:

```bash
docker compose exec api \
  python -m scripts.refresh_worklist \
  --company-id <VOC_COMPANY_ID> \
  --json
```

Expected non-secret evidence:

```json
{"status":"synced","company_id":3,"site_id":169,"fetched":1,"upserted":1,"deactivated":0,"warning":null}
```

Jika `fetched=0`, berhenti. Pastikan OneBox publish item dengan `active=true`, `crawl_enabled=true`, dan `ingest_reviews=true`; jangan membuat `location_id` manual.

## 6. X1 - gerbang crawl satu target

### 6.1 Dapatkan lokasi hasil worklist

Endpoint lokasi saat ini JWT user, bukan service token.

```bash
export VOC_API=http://127.0.0.1:8000
export VOC_USER_TOKEN='<JWT-user-sementara>'

curl -fsS "$VOC_API/api/locations?active_only=true" \
  -H "Authorization: Bearer $VOC_USER_TOKEN"
```

Catat hanya `id`, `branch_name`, `external_place_id`, `onebox_location_id`, `crawl_enabled`, dan `ingest_reviews`. Pilih lokasi dari worklist, lalu:

```bash
export VOC_LOCATION_ID='<id VoC hasil response>'
export RUN_ID="voc-proof-$(date -u +%Y%m%dT%H%M%SZ)"
```

### 6.2 Jalankan crawl dengan target kecil

```bash
curl -fsS -X POST "$VOC_API/api/fetch-jobs" \
  -H "Authorization: Bearer $VOC_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $RUN_ID" \
  -d "{\"location_id\":$VOC_LOCATION_ID,\"source\":\"selenium\",\"target_review_count\":5}"
```

Catat command, waktu UTC, lokasi, durasi, `status`, `total_fetched`, `total_inserted`, `total_duplicate`, `total_failed`, `metadata.headless`, dan error singkat.

Gate X1:

| Hasil | Keputusan |
|---|---|
| `success`/`partial_success` dan `total_fetched > 0` | X1 lulus; lanjut X2. |
| fetched > 0 tetapi semua duplicate | Teknis lulus; butuh review baru/window lain untuk proof ingestion. |
| `failed`, `no such window`, browser crash, atau container review tidak ditemukan | X1 gagal; berhenti dan dokumentasikan. |
| Login Google GUI wajib tiap run | X1 blocked untuk automation; jangan klaim scheduler ready. |

Fetch history:

```bash
curl -fsS "$VOC_API/api/fetch-logs?location_id=$VOC_LOCATION_ID&limit=5" \
  -H "Authorization: Bearer $VOC_USER_TOKEN"
```

## 7. X2 - identity, persistence, dan dedup

```bash
curl -fsS "$VOC_API/api/reviews?location_id=$VOC_LOCATION_ID&page=1&page_size=20&latest_first=true" \
  -H "Authorization: Bearer $VOC_USER_TOKEN"
```

Bukti harus menunjukkan:

```text
review.location_id == VOC_LOCATION_ID
review.external_place_id == location.external_place_id
review.review_hash terisi
```

Ulangi command X1 sekali. Expected: `total_duplicate` naik atau `total_inserted=0`, tanpa review ganda. Jika lokasi/place ID salah, hentikan OneBox ingest dan perbaiki worklist mapping.

## 8. X3 - AI analysis

Pastikan provider LLM reachable dari container; jangan hanya mengetes dari laptop:

```bash
docker compose exec api sh -lc \
  'curl -fsS --connect-timeout 5 "$LOCAL_LLM_BASE_URL" >/dev/null && echo LLM_REACHABLE'
```

Jalankan analysis untuk lokasi proof:

```bash
curl -fsS -X POST "$VOC_API/api/analysis/pending" \
  -H "Authorization: Bearer $VOC_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"location_id\":$VOC_LOCATION_ID}"
```

Verifikasi review kembali: `analyzed=true`, `sentiment`, `urgency`, `issue_category`, `summary`, dan `recommended_action` terisi. Catat `total/success/failed`. Jika `tokens_used` belum dikembalikan oleh contract, tandai **[blocked] metering gap**, jangan mengarang angka.

Gate X3 gagal bila LLM timeout, semua kategori jatuh ke satu kategori tanpa alasan, atau sample critical tidak memiliki flag/urgency yang dapat ditindaklanjuti.

## 9. X4 - service token dan delta pull

Issue token pendek untuk proof; raw token hanya muncul sekali:

```bash
docker compose exec api \
  python -m scripts.manage_api_client issue \
  --company-id <VOC_COMPANY_ID> \
  --name onebox-dev-proof \
  --scope reviews:read \
  --expires-days 7
```

Jangan menaruh token di Git/chat. Validasi tenant tanpa membuka DB:

```bash
export VOC_SERVICE_TOKEN='<raw-token-di-shell-sementara>'

curl -fsS "$VOC_API/api/integration/v1/whoami" \
  -H "Authorization: Bearer $VOC_SERVICE_TOKEN" \
  -H "Accept: application/json"
```

Expected `company_id` harus sama dengan tenant SiteId OneBox dan `scopes` berisi `reviews:read`.

Pull target baru dengan watermark sebelum waktu crawl:

```bash
export UPDATED_SINCE='<UTC sebelum crawl, contoh 2026-07-28T00:00:00Z>'

curl -fsS "$VOC_API/api/integration/v1/reviews?limit=100&location_id=$VOC_LOCATION_ID&updated_since=$UPDATED_SINCE" \
  -H "Authorization: Bearer $VOC_SERVICE_TOKEN" \
  -H "X-Request-ID: $RUN_ID-delta" \
  -H "Accept: application/json"
```

Bukti X4 harus menemukan review X1, lokasi benar, dan field analysis. Jika `has_more=true`, proses `next_cursor`; setelah page terakhir simpan `checkpoint_cursor` di OneBox. Untuk lokasi baru setelah checkpoint tenant maju, gunakan backfill terarah `location_id + updated_since` sebelum memasukkannya ke aliran delta biasa.

## 10. Handoff OneBox: ingest -> Ticket -> eskalasi

Setelah X4 lulus, agen OneBox menjalankan receive pada connection VOC Dev:

```bash
docker exec <onebox-webapp-container> \
  php app/bootstrap.php voice_of_customer_system receive <CONNECTION_ID>
```

Jika analysis pass dipisahkan oleh implementation OneBox:

```bash
docker exec <onebox-webapp-container> \
  php app/bootstrap.php voice_of_customer_system analysis <CONNECTION_ID>
```

Catat hanya counters `fetched`, `inserted`, `deduped`, `failed`, dan `analysis_updated`.

Di UI OneBox verifikasi:

1. Review muncul di VOC/Reviews.
2. `Ticket.LocationId` menunjuk cabang benar, bukan `Unknown`.
3. Rating, sentiment, urgency, category, summary, dan recommended action tampil.
4. Review negatif/critical menjadi Ticket terbuka.
5. Ticket dapat di-assign ke PIC, diberi action note, diubah status, dan dieskalasi.
6. Dashboard menampilkan angka yang konsisten dengan evidence Crawler.

Review yang mengindikasikan keselamatan pasien tetap harus masuk kanal investigasi klinis resmi; Ticket VoC adalah sinyal eskalasi awal.

## 11. Handoff dua agen

### Codex / Crawler System

- [ ] X1 crawl satu target baru berhasil, atau gagal dengan tahap/sebab terdokumentasi.
- [ ] X2 `location_id`, `external_place_id`, dan `review_hash` cocok.
- [ ] X2 run kedua idempotent.
- [ ] X3 analysis success/failure dan LLM reachability tercatat.
- [ ] X4 `whoami` cocok dengan tenant OneBox.
- [ ] X4 delta mengembalikan review baru dan cursor diproses benar.
- [ ] X5 dicatat sebagai gap bila enqueue non-blocking belum ada.

### Claude / OneBox

- [ ] Connection Dev memiliki URL API, auth mode, token, SiteId, dan company benar.
- [ ] Token berada di secret/config, bukan Git.
- [ ] `whoami` diverifikasi sebelum receive.
- [ ] Receive hanya memajukan checkpoint setelah sukses penuh.
- [ ] Mapping menghasilkan `Ticket.LocationId` yang benar.
- [ ] Dedup memakai `review_hash`/RemoteId.
- [ ] Analysis fields dipetakan ke Ticket/Meta.
- [ ] Ticket negatif dapat di-assign dan dieskalasi.
- [ ] UI menampilkan status/history yang benar-benar tersedia.
- [ ] Tombol Run now tidak memanggil endpoint blocking; buat PR X5 dahulu.

## 12. Decision gates dan triage

| Gate | Lulus bila | Jika gagal |
|---|---|---|
| G0 network/config | health 200, worklist synced | perbaiki URL/auth/worklist |
| G1 X1 | fetched > 0 atau failure terjelaskan | cek Selenium/profile/Google access |
| G2 identity | location dan place ID cocok | perbaiki mapping, jangan ingest |
| G3 analysis | field analysis terisi | cek LLM/entitlement/prompt |
| G4 integration | whoami benar + delta berisi review | cek token/scope/cursor/backfill |
| G5 action | Ticket benar, open, assignable | cek Connection/provider/mapping |
| G6 automation | enqueue cepat + batch status | X5 masih blocked; demo manual |

| Gejala | Arti/tindakan |
|---|---|
| worklist `fetched=0` | cek SiteId dan flag worklist |
| `302 /Login` | path web salah; konfirmasi auth API |
| `401` | account/password/SiteId/permission salah |
| Selenium crash/no window | X1 failed; jangan klaim automation |
| LLM timeout | provider tidak reachable dari container |
| delta kosong | checkpoint maju; backfill location + updated_since |
| Ticket `Unknown` | mapping OneBox location gagal |
| `403 INSUFFICIENT_SCOPE` | token tidak punya `reviews:read` |

## 13. Demo script 5-7 menit

1. OneBox: tambah/aktifkan cabang dengan Google Place ID.
2. Crawler: tunjukkan `refresh_worklist` `synced/fetched/upserted`.
3. Crawler: tunjukkan fetch evidence X1, bukan menjalankan Selenium live di depan penonton kecuali gate X1 sudah verified stabil.
4. Crawler: tunjukkan review dengan lokasi/hash/analysis yang benar.
5. Integration: tunjukkan `whoami` dan delta pull; token/cursor tetap disamarkan.
6. OneBox: jalankan receive dan buka Review/Ticket.
7. OneBox: assign Ticket negatif, tambah action note, ubah status/escalate.
8. Dashboard: tunjukkan sentiment, urgency, trend, dan cabang berisiko.
9. Sebutkan batasan yang belum lulus: live Selenium, X5 non-blocking, scheduler tiga window, quota AI, dan competitor review.

## 14. Contract gaps yang ditemukan

1. **[verified]** Crawl, analysis, dan fetch-log hanya menerima JWT user; service token hanya tersedia pada `/api/integration/v1/whoami` dan `/reviews`.
2. **[verified]** `POST /api/fetch-jobs` dan pipeline synchronous/blocking. `/api/integration/v1/crawl-jobs` serta status batch belum ada.
3. **[verified]** Worklist code default memakai `GET /api/VocWorklist`, sedangkan ADR-0003 menyebut `/api/integration/v1/worklist`. Tetapkan satu canonical path.
4. **[verified]** Worklist auth memakai JWT hasil `/api/Authenticate`; review pull memakai opaque `voc_...` token. Keduanya bukan credential yang sama.
5. **[verified]** Review v1 punya `updated_since`, `location_id`, keyset cursor, checkpoint, dan field analysis. `tokens_used` belum terlihat pada projection response; metering menjadi gap bila diwajibkan.
6. **[assumption]** Provider/Connection OneBox Dev sudah diarahkan ke route v1 dan mampu membuat Ticket; perlu evidence dari agen OneBox.
7. **[assumption]** Selenium dapat stabil headless tanpa login GUI setiap run; X1 adalah gerbang untuk mengubahnya menjadi verified.

## 15. Evidence packet

Simpan internal, bukan repo publik:

```text
00_run_metadata.txt       # UTC, branch/image, environment, actor
01_worklist_redacted.json # status/count/site/company
02_fetch_result.json      # counters + metadata
03_fetch_log.json         # target/status/timestamps
04_review_evidence.json   # id/location/place/hash/analysis
05_whoami_redacted.json   # company/name/scopes
06_delta_redacted.json    # item count/page metadata
07_onebox_ingest.txt      # fetched/inserted/deduped/failed
08_ticket_screenshot.png  # detail/dashboard, redact sensitive data
```

Jangan simpan password, raw token/JWT, cookie Selenium, full cursor, API key, raw payload, atau full review text.
