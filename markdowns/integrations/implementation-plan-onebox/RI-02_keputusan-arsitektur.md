# RI-02 — Keputusan Arsitektur (Decision Log) (≤2 MD)

> Status: **keputusan sementara sudah diambil** (default terbaik dipilih berdasarkan verifikasi codebase). Peran task ini berubah dari "bertanya ke lead" menjadi **"minta ratifikasi lead"** — tiap keputusan tinggal di-ACC atau dioverride Pak Agung. Semua keputusan reversible.

## Daftar Keputusan (D1–D8)

| # | Keputusan | Pilihan (default) | Alasan | Bukti |
|---|---|---|---|---|
| D1 | Kunci dedup | `Message.RemoteId = review_hash` | NOT NULL + unique di VoC; `external_review_id` nullable | [verified] models.py |
| D2 | Identitas koneksi per site | **1 row `Connection`** per site, `Code='VoiceOfCustomer'`, dibuat manual (SQL) untuk pilot | pola persis SonarTask (`getSonarConfig` baca `Connection` `Code='Sonar'`); `Message.ConnectionId` valid untuk join UI | [verified] SonarTask:1372–1396 |
| D3 | Auth service-to-service (MVP) | **service user khusus di VoC + JWT login** (`/api/auth/login`) — credential disimpan di config per-env OneBox | jalan hari ini tanpa perubahan VoC; API key/`ApiClient` = fase 2 (handoff Codex) | [verified] auth existing |
| D4 | Rumah field analisa | `summary`→`Ticket.Description` · `recommended_action`→`Ticket.Solution` · `urgency`→`Ticket.PriorityId` (high=TP1, medium=TP2, low=TP3) · sisanya (`rating`, `sentiment_score`, `keywords`, flags, dll)→`MessageContent.Meta` (JSON) | Description/Solution kosong di pola SonarTask (aman); **tanpa migration** — sesuai guardrail | [verified] SonarTask set null; kode TP* diverifikasi di RI-01 L3 |
| D5 | Channel/MediaId | **MediaId baru "Google Review"** (insert master; verifikasi tabel master Media/Reference dulu) | filter per-media adalah mekanisme utama UI Mediamonitoring; nebeng MediaId "news" bikin data campur | [assumption] tabel master — wajib verifikasi |
| D6 | Mapping tenant & lokasi (MVP) | mapping `company_id`/`location_id` VoC → `SiteId`/`LocationId` OneBox via **section config per-env** (`voiceofcustomer` di config file), 1 pilot site dulu; upgrade ke UI-managed nanti | tercepat, tanpa migration; multi-site menyusul | keputusan MVP |
| D7 | `issue_category` | `Ticket.CategoryId` + **seed master Category** per site (kategori dari AI itu set kecil & tetap) | dashboard butuh agregasi per kategori — JSON Meta tidak bisa di-GROUP BY dengan wajar | [assumption] model Category — verifikasi di RI-07 |
| D8 | Sentiment `mixed` | map ke `0` (netral) + simpan nilai asli di `MessageContent.Meta` | OneBox cuma kenal -1/0/1; data asli tidak hilang | [verified] skala dari query Mediamonitoring |

## Langkah Eksekusi
1. Bawa tabel D1–D8 ke Pak Agung (chat/meeting singkat) — format "ini default saya, mohon koreksi kalau ada yang keliru". (0.5 MD)
2. Update dokumen ini dengan hasil (ACC/override per baris) + tanggal. (0.5 MD)
3. Kalau ada override → propagasi ke plan RI terkait (tiap plan menyebut nomor D yang dipakainya).

## Definition of Done
Semua baris D1–D8 berstatus ACC/override, tercatat di sini, dan plan turunannya sudah disesuaikan.

## Risiko
Lead override D4/D7 jadi "kolom baru di Ticket" → butuh migration; dampaknya ke RI-05/07/12 (sudah dirancang mudah beralih — lihat bagian Meta di RI-07).
