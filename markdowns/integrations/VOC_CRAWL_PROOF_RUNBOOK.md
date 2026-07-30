# VOC Crawl Proof Runbook - X1 sampai X5

> Runbook verifikasi end-to-end Voice of Customer di environment Dev. Acuan: ADR-0001, ADR-0002, ADR-0003, `PLAN_KEY_PROCESS_DEMO.md`, dan `PROMPT_VOC_CRAWL_PROOF.md`.
> Status klaim: **[verified-local]**, **[verified-dev]**, **[assumption]**, atau **[blocked]**.

## 1. Target proof

Rantai yang harus terbukti:

~~~text
OneBox menambah Location
  -> Crawler menarik worklist
  -> OneBox enqueue crawl via service API
  -> worker Selenium mengambil review
  -> Crawler menyimpan dan deduplikasi review
  -> tahap AI mengisi sentiment, urgency, category, summary, action
  -> OneBox menarik delta review
  -> OneBox membuat Message/Ticket
  -> pengguna assign, tindak lanjut, dan eskalasi Ticket
~~~

AI sengaja tidak dijalankan otomatis oleh worker crawl. Pemisahan ini mengikuti ADR-0002 dan membuat kegagalan crawl, LLM, serta ingestion dapat di-retry secara independen.

## 2. Status implementasi

| Proses | Status | Bukti |
|---|---|---|
| Worklist OneBox -> Crawler | **[verified-dev]** | Sync pernah menghasilkan `status=synced` dan target masuk cache lokasi. |
| X5 enqueue non-blocking | **[verified-local]** | `POST /api/integration/v1/crawl-jobs`, idempotency, tenant scope, durable queue, lease, retry, dan worker diuji otomatis. |
| Runtime Chromium di image | **[verified-local]** | Chromium dan chromedriver dipaketkan di Dockerfile; unit test pencarian binary lulus. Build image Dev masih perlu dilakukan. |
| X2 persistence + dedup | **[verified-local]** | Test Selenium persistence/dedup dan full test suite lulus. |
| X3 analysis + token usage | **[verified-local]** | Analysis mengembalikan aggregate `tokens_used` dan breakdown provider usage. |
| X4 service auth + delta | **[verified-local]** | Tenant binding, scope, cursor, dan delta contract diuji otomatis. |
| X1 crawl Google real | **[blocked]** sampai proof Dev | Harus dijalankan pada satu target worklist di `ciptadra-svr`. |
| Review -> Ticket -> eskalasi | **[blocked]** sampai proof Dev | Dilakukan setelah X1-X4 menghasilkan satu review baru. |

## 3. Contract X5 yang sudah tersedia

| Endpoint | Scope | Fungsi |
|---|---|---|
| `POST /api/integration/v1/crawl-jobs` | `crawl:enqueue` | Membuat batch durable dan langsung merespons `202`. |
| `GET /api/integration/v1/crawl-jobs` | `crawl:read` | Menampilkan batch terbaru milik tenant token. |
| `GET /api/integration/v1/crawl-jobs/{batch_id}` | `crawl:read` | Menampilkan status dan hasil per `onebox_location_id`. |
| `GET /api/integration/v1/whoami` | service bearer | Memastikan token terikat ke company yang benar. |
| `GET /api/integration/v1/reviews` | `reviews:read` | Menarik review delta tanpa mengubah contract v1. |

Aturan penting:

- `company_id` selalu berasal dari service token, tidak diterima dari payload.
- Target POST memakai `onebox_location_id`, bukan primary key Crawler.
- Target harus ada di worklist cache dan masih `active + crawl_enabled + ingest_reviews`.
- `Idempotency-Key` wajib. Key sama dan payload sama mengembalikan batch lama; key sama dan payload berbeda menghasilkan `409 IDEMPOTENCY_CONFLICT`.
- Satu worker Selenium adalah baseline aman. Job memakai lease dan retry sehingga restart container tidak menghilangkan antrean.

## 4. Deployment Crawler System

P0 migrasi PostgreSQL ke MySQL sedang ditahan. Deploy proof ini tetap memakai database PostgreSQL yang aktif saat ini. Jangan menerapkan stash P0 bersama perubahan X1-X5.

### 4.1 Pre-deploy

~~~bash
cd ~/herminaCrawler
git status --short --branch
git fetch origin
git switch codex/key-process-x1-x5
git pull --ff-only
~~~

Berhenti bila server memiliki perubahan lokal yang tidak dikenal. Jangan melakukan reset atau overwrite.

### 4.2 Build, migration, dan start

~~~bash
docker compose up -d --build --force-recreate
docker compose ps
docker compose logs --tail=200 api crawl-worker
curl -fsS http://127.0.0.1:8000/api/health
~~~

Expected:

- service `api` healthy;
- service `crawl-worker` running;
- migration `20260729_0002` selesai;
- tidak ada loop crash Chromium/worker.

Verifikasi revision:

~~~bash
docker compose exec api python -m alembic current
~~~

## 5. G0 - refresh worklist

~~~bash
docker compose exec api python -m scripts.refresh_worklist --company-id 3 --json
~~~

Gate lulus bila `status=synced`, `fetched>0`, `upserted>=0`, dan `warning=null`. Jika `fetched=0`, periksa SiteId serta flag `active`, `crawl_enabled`, dan `ingest_reviews` di OneBox. Jangan membuat Location Crawler secara manual.

Catat `onebox_location_id` target tanpa menyimpan review text:

~~~bash
docker compose exec api python -c "from app.db.session import get_session_factory; from app.db.models import Location; from sqlalchemy import select; f=get_session_factory(); s=f(); print([(x.onebox_location_id,x.branch_name,x.crawl_enabled,x.ingest_reviews) for x in s.scalars(select(Location).where(Location.company_id==3,Location.is_active.is_(True)))])"
~~~

## 6. Issue service token proof

Perintah berikut otomatis menyertakan default `reviews:read`, lalu menambahkan dua scope crawl:

~~~bash
docker compose exec api python -m scripts.manage_api_client issue --company-id 3 --name onebox-crawl-dev --scope crawl:enqueue --scope crawl:read --expires-days 7
~~~

Raw token hanya tampil sekali. Simpan di secret/config OneBox dan shell sementara, bukan Git, screenshot, atau chat.

~~~bash
export VOC_API=http://127.0.0.1:8000
export VOC_SERVICE_TOKEN="<voc_staging_key.secret>"
curl -fsS "$VOC_API/api/integration/v1/whoami" -H "Authorization: Bearer $VOC_SERVICE_TOKEN"
~~~

Gate lulus bila `company_id=3` dan scopes berisi `reviews:read`, `crawl:enqueue`, serta `crawl:read`.

## 7. X1 dan X5 - enqueue crawl real

Gunakan target kecil agar proof terkendali. Nilai target aktual tetap berasal dari worklist Location.

~~~bash
export ONEBOX_LOCATION_ID="<id-dari-worklist>"
export RUN_ID="voc-proof-$(date -u +%Y%m%dT%H%M%SZ)"

curl -fsS -X POST "$VOC_API/api/integration/v1/crawl-jobs" \
  -H "Authorization: Bearer $VOC_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $RUN_ID" \
  -H "X-Request-ID: $RUN_ID" \
  -d "$(printf '{\"slot\":\"manual-proof\",\"targets\":[{\"onebox_location_id\":%s}]}' "$ONEBOX_LOCATION_ID")"
~~~

Response harus HTTP `202` dengan `batch_id`, status `queued`, dan job yang mengembalikan `onebox_location_id` yang sama. Simpan batch ID:

~~~bash
export BATCH_ID="<batch-id-response>"
curl -fsS "$VOC_API/api/integration/v1/crawl-jobs/$BATCH_ID" \
  -H "Authorization: Bearer $VOC_SERVICE_TOKEN"
docker compose logs --tail=200 crawl-worker
~~~

Gate X1/X5:

| Hasil | Keputusan |
|---|---|
| API cepat memberi `202`, job menjadi `succeeded`, dan `total_fetched>0` | Lulus; lanjut X2. |
| `succeeded` tetapi fetched 0 | Queue terbukti, crawl data belum terbukti; pilih target yang punya review. |
| `retry_wait` | Periksa error tersanitasi dan worker log; tunggu retry. |
| `failed` setelah max attempts | X1 gagal; cek Chromium, jaringan Google, profile, quota, atau selector. |
| `404 TARGET_NOT_FOUND` | Worklist target belum tersinkron atau dinonaktifkan. |

Jalankan POST yang sama dengan `Idempotency-Key` dan payload yang sama. Batch ID harus tetap sama dan job tidak boleh bertambah.

## 8. X2 - persistence dan dedup

Gunakan JWT user hanya untuk endpoint operasional lama selama belum tersedia read-only proof endpoint service. Jangan memasukkan token ke evidence.

~~~bash
export VOC_USER_TOKEN="<jwt-user-sementara>"
curl -fsS "$VOC_API/api/reviews?page=1&page_size=20&latest_first=true" \
  -H "Authorization: Bearer $VOC_USER_TOKEN"
~~~

Bukti X2:

- review terikat ke Location yang memiliki `onebox_location_id` target;
- `external_place_id` sama dengan worklist;
- `review_hash` terisi;
- run kedua tidak membuat duplikat dan menambah counter duplicate atau menghasilkan inserted 0.

Jika mapping lokasi salah, hentikan ingestion OneBox.

## 9. X3 - AI analysis

Tes konektivitas LLM dari container:

~~~bash
docker compose exec api sh -lc 'curl -fsS --connect-timeout 5 "$LOCAL_LLM_BASE_URL" >/dev/null && echo LLM_REACHABLE'
~~~

Jalankan tahap analysis terpisah:

~~~bash
curl -fsS -X POST "$VOC_API/api/analysis/pending" \
  -H "Authorization: Bearer $VOC_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{"location_id":<voc-location-id-internal>}"
~~~

Gate lulus bila success lebih dari 0, `tokens_used` dan `token_usage` tercatat, serta review memiliki sentiment, urgency, issue_category, summary, dan recommended_action.

## 10. X4 - delta pull

~~~bash
export UPDATED_SINCE="<UTC-sebelum-crawl>"
curl -fsS "$VOC_API/api/integration/v1/reviews?limit=100&updated_since=$UPDATED_SINCE" \
  -H "Authorization: Bearer $VOC_SERVICE_TOKEN" \
  -H "X-Request-ID: $RUN_ID-delta"
~~~

Gate lulus bila review X1 muncul dengan lokasi dan hasil analysis benar. Ikuti `next_cursor` ketika `has_more=true`; simpan `checkpoint_cursor` di OneBox hanya setelah seluruh page berhasil di-ingest.

## 11. Handoff ke OneBox

Claude/agen OneBox menjalankan receive pada Connection Dev:

~~~bash
docker exec <onebox-webapp-container> php app/bootstrap.php voice_of_customer_system receive <CONNECTION_ID>
~~~

Verifikasi di UI:

1. Review muncul di VOC Reviews.
2. Ticket Location menunjuk cabang benar, bukan Unknown.
3. Sentiment, urgency, category, summary, dan recommended action tampil.
4. Review negatif menjadi Ticket terbuka.
5. Ticket dapat di-assign, diberi action note, diubah status, dan dieskalasi.
6. Dashboard konsisten dengan jumlah data hasil proof.

## 12. Pembagian dua agen

### Codex - Crawler System

- deploy branch dan verifikasi migration/worker;
- refresh worklist;
- issue token proof dengan scope lengkap;
- menjalankan X1/X5, X2, X3, dan X4;
- menyerahkan evidence tanpa secret atau full review text;
- mencatat blocker Selenium/LLM/network berdasarkan stage yang tepat.

### Claude - OneBox

- memastikan PR OneBox sudah masuk `feature/voc` dan deployed;
- menyimpan service token di secret/config Connection;
- memanggil enqueue dengan `onebox_location_id` dan idempotency key;
- melakukan receive delta dan memajukan checkpoint hanya setelah sukses penuh;
- membuktikan mapping Message/Ticket, Location, assignment, dan escalation;
- menampilkan status batch pada Fetch Jobs tanpa menunggu Selenium di request web.

## 13. Decision gates

| Gate | Lulus bila |
|---|---|
| G0 | API healthy, worker running, worklist synced. |
| G1 | Enqueue memberi 202 dan worker mendapatkan review real. |
| G2 | Location/place/hash benar dan rerun tidak duplikat. |
| G3 | Analysis fields serta token usage terisi. |
| G4 | Service token tenant benar dan delta berisi review proof. |
| G5 | OneBox membuat Ticket yang dapat ditindaklanjuti. |

## 14. Evidence packet

~~~text
00_run_metadata.txt
01_worklist_redacted.json
02_enqueue_response.json
03_batch_final.json
04_worker_log_redacted.txt
05_review_identity_redacted.json
06_analysis_summary.json
07_whoami_redacted.json
08_delta_redacted.json
09_onebox_ingest_counters.txt
10_ticket_redacted.png
~~~

Jangan menyimpan password, raw token/JWT, Selenium cookies/profile, API key, cursor penuh, raw payload, atau full review text.

## 15. Known limitations setelah proof

- Scheduler tiga window masih pekerjaan terpisah; OneBox tetap control plane jadwal.
- Baseline worker hanya satu concurrency untuk menjaga stabilitas Selenium.
- P0 migrasi PostgreSQL ke MySQL ditahan dan harus direbase terhadap migration queue ini saat dilanjutkan.
- Production monitoring, secret rotation, retention, dan capacity test belum dibuktikan oleh proof ini.
