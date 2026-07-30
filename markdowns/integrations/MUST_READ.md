# MUST_READ - Voice of Customer  System x OneBox Integration

Instruksi wajib untuk Claude Code, Codex, dan engineer sebelum lanjut integrasi OneBox.

---

## 🚨 BACA PALING AWAL — Architecture Decision Records (ADR)

ADR adalah **otoritas tertinggi**. Kalau ADR bertentangan dengan dokumen lain, **ADR yang menang**.

| ADR | Isi | Status |
|---|---|---|
| `../decisions/ADR-0001-ownership-inversion.md` | **OneBox = System of Record.** Seluruh modul VoC (dashboard, review mgmt, location, competitor, reports, insights, parameter/benefit) dikelola di OneBox. VoC = crawler engine **headless**, hanya scraping. | Accepted · diratifikasi internal 2026-07-22 · **mekanisme provisioning di-amandemen ADR-0003** |
| `../decisions/ADR-0002-ai-execution-split.md` | AI: **parameter & kuota di OneBox, eksekusi di VoC.** VoC wajib mengembalikan `tokens_used`. | Accepted |
| `../decisions/ADR-0003-crawl-execution-pull-queue.md` | **Eksekusi crawl.** Provisioning **push sinkron → pull worklist** (VoC menarik daftar target dari OneBox; simpan lokasi jadi instan). VoC pakai **antrean crawl durable + worker** (bukan fetch blocking), crawl **inkremental** (cursor). Scheduler tiga-window RI-08 tetap, trigger jadi **non-blocking**. | Accepted |

### Daftar modul NON-NEGOTIABLE (ditetapkan 2026-07-22)

Semua ini **dikelola di OneBox**, tanpa kecuali:
setup lokasi · setup competitor · dashboard · review management · location management ·
competitor management · reports · AI analysis · insights · setup parameter/benefit.

**Scraping tetap milik VoC** — jangan pindahkan Selenium/crawling ke OneBox.

Cakupan **AI analysis** dan **insights** masih akan dikaji ulang; kepemilikannya tidak.
Status implementasi per modul + konsekuensi teknis: lihat bagian "Ratifikasi internal" di ADR-0001.

⚠️ Ratifikasi ini **internal dev, belum disetujui Pak Agung.**

## ⛔ DOKUMEN YANG SUDAH TIDAK BERLAKU (jangan jadikan acuan kerja baru)

Semua sudah diberi banner di bagian atas file. Disimpan hanya sebagai histori.

1. `../crawler_system/erd.md` — ERD lama: VoC memiliki Location/Competitor/Company/User
2. `../crawler_system/dfd.md` — DFD lama: VoC punya aktor User/Admin + UI
3. `architecture_diagram.md` + `voc_onebox_architecture.drawio` — VoC digambar punya FE sendiri
4. `implementation-plan-onebox/RI-06_tenant-mapping.md` — mapping lokasi arah terbalik
5. `implementation-plan-onebox/RI-02_keputusan-arsitektur.md` — **sebagian**: D2, D6 batal; D10 direvisi. D1/D3/D4/D5/D7/D8/D9/D11 masih berlaku.

**Aturan menulis dokumen baru:** kalau sebuah keputusan arsitektur berubah, buat ADR baru di `markdowns/decisions/` (format `ADR-####-nama.md`), tandai dokumen lama dengan banner SUPERSEDED **di 5 baris pertama**, lalu daftarkan di sini.

---

## Canonical Naming

Mulai sekarang gunakan nama **Voice of Customer  System** untuk sistem Voice of Customer  + analysis ini.

Jangan gunakan nama lama untuk dokumen baru, task baru, class baru, prompt baru, atau komunikasi implementasi baru.
Nama lama hanya boleh muncul saat membahas dokumen historis, repo/deployment lama, path existing, atau kutipan chat lama.

Naming baru yang dipakai: Voice of Customer SystemClient, Voice of Customer SystemTask, Voice of Customer SystemSync.

## System Boundary

Voice of Customer  System adalah external microservice untuk crawling, review retrieval, analysis, dan data provider API.
OneBox adalah consumer. Untuk fase ini OneBox pull data dari Voice of Customer  System.

Flow utama: Voice of Customer  System API -> OneBox client -> sync task -> Ticket / Message / MessageContent -> Mediamonitoring / VOC UI.

Jangan pindahkan logic Selenium/crawling ke OneBox.

## Agent Ownership

Claude Code fokus pada OneBox: baca struktur, cari pattern existing, implement client/sync task, mapping model, dan validasi UI.
Codex fokus pada Voice of Customer  System: API contract, contoh request/response, docs handoff, API gap, tasklist, dan progress report.

## Peta kerja aktif

**[VOC_DEV_TASKLIST.md](VOC_DEV_TASKLIST.md)** — tasklist development per modul (M0–M9) berikut
prasyarat, owner, dependensi, dan status. Ini yang menentukan **urutan & status** pekerjaan.
Dokumen `RI-xx` dan `VOC-CS-xx` tetap dipakai sebagai **detail teknis** tiap task.

## Required Reading Order

1. markdowns/integrations/MUST_READ.md
2. markdowns/integrations/VOC_DEV_TASKLIST.md
3. markdowns/integrations/two_agents_workflow.md
3. markdowns/integrations/tasklist(draft).md
4. markdowns/integrations/developer_guide.md
5. markdowns/integrations/superprompt.md
6. markdowns/integrations/link-docs.md
7. markdowns/integrations/implementation-plan-crawler-system/VOC-CS-08_consumer-worklist.md

Dokumen lama boleh belum dimigrasi. Untuk pekerjaan baru, file ini yang menang.

## Rules For New Work

- Jangan hardcode credential API, DB, atau token.
- Jangan commit perubahan config lokal seperti .env, .env.local, atau config development pribadi.
- Jangan coding besar sebelum field mapping OneBox jelas.
- Kalau OneBox butuh parameter yang belum ada, catat sebagai API gap Voice of Customer  System.
- Handoff antar agent wajib menandai status: verified, assumption, atau blocked.
- Worklist consumer wajib memakai ONEBOX_COMPANY_ID yang eksplisit; tenant tidak boleh ditebak.
- OneBox adalah scheduler dan master data; Crawler System hanya me-refresh cache target lalu menjalankan crawling.

## Current Integration Assumption

- Voice of Customer  System berjalan sebagai 3rd party service.
- Deployment Voice of Customer  System memakai Docker.
- **Dua arah pull (lihat [ADR-0003](../decisions/ADR-0003-crawl-execution-pull-queue.md)):**
  - VoC **pull worklist** dari OneBox (`GET /api/VocWorklist (configurable)`) untuk tahu target crawl — menggantikan push `POST /api/locations`.
  - OneBox **pull review delta** dari VoC (`GET /api/integration/v1/reviews`) untuk masuk Ticket.
- Trigger crawl dari OneBox bersifat **non-blocking** (enqueue), bukan fetch sinkron menunggu Selenium.
- Auth/access API dari sisi OneBox masih perlu dikonfirmasi.
- Parameter final dari OneBox masih perlu dikonfirmasi.
