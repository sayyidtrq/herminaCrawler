# MUST_READ - Voice of Customer  System x OneBox Integration

Instruksi wajib untuk Claude Code, Codex, dan engineer sebelum lanjut integrasi OneBox.

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

## Required Reading Order

1. markdowns/integrations/MUST_READ.md
2. markdowns/integrations/two_agents_workflow.md
3. markdowns/integrations/tasklist(draft).md
4. markdowns/integrations/developer_guide.md
5. markdowns/integrations/superprompt.md
6. markdowns/integrations/link-docs.md

Dokumen lama boleh belum dimigrasi. Untuk pekerjaan baru, file ini yang menang.

## Rules For New Work

- Jangan hardcode credential API, DB, atau token.
- Jangan commit perubahan config lokal seperti .env, .env.local, atau config development pribadi.
- Jangan coding besar sebelum field mapping OneBox jelas.
- Kalau OneBox butuh parameter yang belum ada, catat sebagai API gap Voice of Customer  System.
- Handoff antar agent wajib menandai status: verified, assumption, atau blocked.

## Current Integration Assumption

- Voice of Customer  System berjalan sebagai 3rd party service.
- Deployment Voice of Customer  System memakai Docker.
- OneBox melakukan pull via REST API.
- Auth/access API dari sisi OneBox masih perlu dikonfirmasi.
- Parameter final dari OneBox masih perlu dikonfirmasi.
