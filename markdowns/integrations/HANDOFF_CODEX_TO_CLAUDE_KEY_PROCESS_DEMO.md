# Handoff Codex ke Claude - Key Process Demo VoC

## 1. Tujuan handoff

Dokumen ini menjadi context passing untuk melanjutkan pembuktian alur utama Voice of
Customer (VoC):

`OneBox Location -> Crawler worklist -> Google review crawl -> AI analysis -> OneBox Ticket -> escalation`

Gunakan istilah **Crawler System** untuk nama layanan. Nama repository dan identifier lama
seperti `herminaCrawler` atau `hermina-review-api` tetap dipertahankan jika memang merupakan
nama teknis existing.

## 2. Dokumen wajib dibaca

Urutan baca:

1. `markdowns/integrations/PLAN_KEY_PROCESS_DEMO.md`
2. `markdowns/integrations/PROMPT_VOC_CRAWL_PROOF.md`
3. `markdowns/integrations/VOC_CRAWL_PROOF_RUNBOOK.md`
4. Dokumen ADR dan implementation plan yang direferensikan oleh ketiga dokumen tersebut.

Runbook adalah sumber utama untuk command, evidence, decision gate, dan urutan demonstrasi.
Jangan membuat flow pengujian baru yang bertentangan dengan runbook tanpa mencatat alasannya.

## 3. Kondisi sistem yang sudah terbukti

### Crawler System

- Backend berjalan sebagai container `hermina-review-api` pada port `8000`.
- Health check `/api/health` berhasil dan database terhubung.
- Alembic migration dijalankan otomatis melalui `entrypoint.sh`.
- Crawler System dapat mengakses OneBox dev melalui HTTPS.
- OneBox worklist authentication dan sinkronisasi sudah berhasil.
- Worklist bersifat tenant-scoped menggunakan `company_id` dan `site_id`.
- Endpoint crawl existing masih memakai JWT user dan berjalan sinkron:
  - `POST /api/fetch-jobs`
  - `POST /api/fetch-jobs/all-active`
  - `POST /api/pipeline/location`
- Endpoint AI analysis existing:
  - `POST /api/analysis/pending`
- Endpoint service-to-service untuk OneBox menarik review:
  - `GET /api/integration/v1/reviews`
  - `GET /api/integration/v1/whoami`
- Service token bersifat tenant-bound dan menggunakan scope.
- Contract response integration reviews tidak boleh diubah:
  - `data[]`
  - `page.next_cursor`
  - `page.checkpoint_cursor`
  - `page.has_more`

### OneBox

- Perubahan OneBox dikembangkan di feature branch terkait DNGO, lalu dipush dan dibuat
  PR/merge ke `feature/voc`.
- Environment dev yang menjadi target integrasi adalah
  `https://dev.onebox.co.id/feature/voc`.
- Flow lokal review menjadi Message/Ticket sudah pernah diverifikasi.
- Pembuktian ulang pada environment dev untuk review baru hasil crawl masih diperlukan.

## 4. Implementasi terakhir oleh Codex

### 4.1 Tenant isolation pada pipeline Selenium

File:

`apps/api/app_api/routers/pipeline.py`

Sebelumnya `SeleniumFetchService()` dibuat tanpa `company_id`. Kondisi tersebut berpotensi
membuat request dengan `location_id` tebakan melewati validasi ownership tenant pada jalur
pipeline Selenium.

Codex mengubah konstruksi service menjadi tenant-scoped:

```python
SeleniumFetchService(company_id=current_user.company_id)
```

Perubahan ini hanya memengaruhi `POST /api/pipeline/location`. Endpoint
`POST /api/fetch-jobs` memiliki flow terpisah dan tetap harus diverifikasi ownership serta
hasil runtime-nya saat proof.

### 4.2 Runbook pembuktian end-to-end

Codex dan agent pendamping membuat:

`markdowns/integrations/VOC_CRAWL_PROOF_RUNBOOK.md`

Runbook mencakup:

- preflight deployment;
- X1: crawl review real;
- X2: verifikasi identity dan deduplication;
- X3: AI analysis;
- X4: service-token delta pull;
- handoff dan receive dari OneBox;
- verifikasi Ticket, assignment, escalation, dan dashboard;
- evidence yang harus disimpan;
- aturan branch dan deployment;
- stop condition jika Selenium atau network gagal.

### 4.3 Hasil verifikasi lokal

Verifikasi terakhir:

```text
python -m ruff check app/integrations/selenium_google_maps_client.py tests/test_selenium_scraping.py
PASS

python -m pytest -q tests/test_selenium_scraping.py
4 passed

python -m pytest -q tests --ignore=tests/test_real_integrations.py
68 passed

docker build -t herminacrawler:selenium-proof .
PASS

Chromium 150.0.7871.181
ChromeDriver 150.0.7871.181

Headless browser startup smoke test di dalam image
PASS
```

Tenant isolation dan runbook sudah berada pada commit `aa203cb`.

Perbaikan runtime Selenium sudah:

- di-commit sebagai `81565bf fix: package Selenium browser runtime`;
- di-push ke branch `codex/fix-selenium-container-runtime`;
- siap dibuatkan PR ke `main`.

### 4.4 Hasil preflight server Crawler

Server `ciptadra-svr` sudah diperiksa tanpa mengubah data produksi:

- repository bersih pada `main` commit `aa203cb`;
- container `hermina-review-api` berstatus healthy;
- `/api/health` mengembalikan status aplikasi dan database `ok`;
- worklist company `3`, site `169` berhasil sinkron;
- target proof terpilih adalah Crawler `location_id=8`, OneBox location `656`;
- target tersebut aktif untuk crawl dan ingest, serta belum memiliki review sebelum proof.

Diagnostic crawl target `5` review berhenti sebelum membuka Google Maps karena image lama
tidak memiliki Chrome/Chromium dan ChromeDriver. Selenium Manager kemudian gagal mengunduh
driver dari `storage.googleapis.com`, menghasilkan `NoSuchDriverException`. Fetch log gagal
tercatat dan tidak ada review parsial yang masuk.

Patch `81565bf` menutup akar masalah tersebut dengan memasang Chromium dan ChromeDriver
versi distro yang sama, memilih binary lokal secara eksplisit, serta menambahkan flag
container-safe. Live crawl X1 tetap harus diulang setelah patch masuk `main`, image baru
ter-deploy, dan `SELENIUM_HEADLESS=true` diterapkan pada server.

## 5. Hal yang belum boleh diklaim selesai

- Crawl review Google real untuk target/location baru belum dibuktikan sampai tersimpan.
- Patch browser runtime belum ter-deploy ke `ciptadra-svr`.
- AI analysis untuk review hasil crawl baru belum dibuktikan pada deployment server.
- Delta review baru belum dibuktikan berhasil ditarik oleh OneBox dev.
- Review baru belum dibuktikan menjadi Ticket dan tampil di dashboard OneBox dev.
- Endpoint durable non-blocking `POST /api/integration/v1/crawl-jobs` belum ada.
- Endpoint status durable crawl job belum ada.
- Worker/queue durable khusus crawling belum ada.
- Scheduler production belum menjadi bagian dari proof ini.
- Tombol OneBox "Run now" belum boleh diarahkan ke endpoint synchronous/blocking sebagai
  desain final.

## 6. Yang Claude sudah bisa lakukan sekarang

Claude dapat langsung mengerjakan aktivitas berikut.

### A. Menyiapkan perubahan untuk deployment Crawler System

1. Buka PR branch `codex/fix-selenium-container-runtime` ke `main`.
2. Pastikan PR hanya membawa patch runtime Selenium dan dokumen handoff yang memang
   disengaja; jangan memasukkan `.obsidian/workspace.json` atau file unrelated.
3. Setelah merge ke `main`, pantau GitHub Actions:
   test -> build GHCR image -> deploy self-hosted runner.
4. Pastikan container aktif memakai deployment directory yang benar. Workflow existing
   menggunakan `/opt/hermina-crawler`.
5. Pada server, set `SELENIUM_HEADLESS=true`, recreate container, lalu verifikasi versi
   Chromium dan ChromeDriver dari dalam container sebelum menjalankan X1.

### B. Menjalankan proof X1-X4

Ikuti `VOC_CRAWL_PROOF_RUNBOOK.md`:

1. Jalankan preflight health, logs, environment, dan worklist.
2. X1: crawl satu location aktif dengan target awal `5` review.
3. X2: verifikasi review tersimpan, identity benar, dan rerun tidak membuat duplikat.
4. X3: verifikasi LLM reachable, lalu jalankan analysis dan periksa seluruh field hasil.
5. X4: issue service token sementara, verifikasi `whoami`, lalu tarik integration delta.
6. Simpan request ID, timestamp, location ID, fetch log, review ID/hash, dan hasil analysis.

Service token tidak dapat menggantikan JWT user untuk endpoint crawl existing. Jangan
menaruh token, password, cookie, atau API key pada chat, screenshot, commit, maupun log.

### C. Menjalankan proof OneBox

Setelah X4 berhasil:

1. Pastikan `Connection` OneBox dev menunjuk ke Crawler System dan token tenant yang benar.
2. Jalankan action `voice_of_customer_system receive <CONNECTION_ID>` pada container webapp
   OneBox.
3. Verifikasi review menjadi Message/Ticket.
4. Verifikasi SiteId, LocationId, Contact/reviewer, sentiment, urgency, summary,
   recommended action, assignment, dan escalation.
5. Verifikasi review/ticket muncul pada list, detail, dan dashboard VoC.

### D. Melakukan diagnosis berbasis gate

- Jika X1 gagal, jangan lanjut dengan klaim end-to-end. Simpan error Selenium secara lengkap.
- Jika X1 berhasil tetapi X3 gagal, fokus pada network/model LLM tanpa mengulang crawling.
- Jika X3 berhasil tetapi X4 kosong, periksa watermark, cursor, company, dan location filter.
- Jika X4 berhasil tetapi OneBox tidak membuat Ticket, fokus pada Connection, mapping,
  dedup RemoteId, dan task receive.
- Data cached real boleh dipakai untuk membuktikan downstream hanya jika diberi label jelas
  sebagai fallback, bukan full live crawl proof.

## 7. Keputusan implementasi X5

Jangan langsung membangun X5 sebelum X1 membuktikan Selenium layak dijalankan pada server.
Jika X1 stabil dan X5 disetujui, desain yang direkomendasikan:

- `POST /api/integration/v1/crawl-jobs` mengembalikan `202` dan `batch_id`;
- `GET /api/integration/v1/crawl-jobs/{batch_id}` untuk status;
- opaque service token dengan scope misalnya `crawl:write`;
- job terikat `company_id`;
- idempotency key wajib;
- tabel job durable di database;
- worker terpisah mengambil queued job secara aman;
- concurrency Selenium dibatasi;
- restart API tidak menghilangkan job;
- OneBox hanya enqueue dan memantau, Crawler System memiliki eksekusi crawling.

Jangan menggunakan FastAPI `BackgroundTasks` sebagai queue production karena state job akan
hilang ketika process/container restart.

## 8. Definition of done demo

Demo baru boleh disebut end-to-end apabila tersedia satu rantai evidence dengan identitas
yang dapat dilacak:

1. Location OneBox aktif masuk ke worklist Crawler System.
2. Location tersebut dicrawl dan menghasilkan review Google real.
3. Review tersimpan dengan identity dan dedup key yang benar.
4. Review memperoleh hasil AI analysis.
5. Review terlihat pada integration delta Crawler System.
6. OneBox menerima review yang sama.
7. OneBox membuat atau memastikan Message/Ticket tanpa duplikasi.
8. Ticket dapat di-assign, dieskalasi, dan terlihat pada dashboard.

## 9. Instruksi langsung untuk Claude

```text
Lanjutkan pembuktian key process VoC dari state repository saat ini.

Baca terlebih dahulu:
- markdowns/integrations/PLAN_KEY_PROCESS_DEMO.md
- markdowns/integrations/PROMPT_VOC_CRAWL_PROOF.md
- markdowns/integrations/VOC_CRAWL_PROOF_RUNBOOK.md
- markdowns/integrations/HANDOFF_CODEX_TO_CLAUDE_KEY_PROCESS_DEMO.md

Jangan ulangi implementasi worklist, service auth, tenant isolation, atau patch browser
runtime yang sudah tersedia. Pertama pastikan PR branch
codex/fix-selenium-container-runtime sudah merge dan image commit tersebut benar-benar
ter-deploy. Set SELENIUM_HEADLESS=true pada server, lalu mulai dari preflight browser dan X1.

Prioritas eksekusi adalah X1 -> X2 -> X3 -> X4 -> OneBox receive -> Ticket/escalation.
Gunakan target awal 5 review. Simpan evidence per gate dan berhenti pada komponen pertama
yang gagal. Jangan mengklaim X5, scheduler, atau full end-to-end selesai sebelum seluruh
definition of done terpenuhi.

Untuk perubahan OneBox, gunakan feature branch DNGO terkait dan PR/merge ke feature/voc.
Untuk perubahan Crawler System, gunakan feature branch repository Crawler dan PR/merge ke
main. Jangan memasukkan secret atau file unrelated ke commit.
```
