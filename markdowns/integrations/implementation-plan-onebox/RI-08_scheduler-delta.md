# RI-08 — Scheduler + Delta Sync + Trigger Manual (≤4 MD)

> Keputusan terkait: D1. Prasyarat API gap `updated_since` (Codex) — ada fallback kalau belum siap.

## 1. Tujuan & Definition of Done
`VoiceOfCustomerSystemTask::syncAction` jalan terjadwal, **inkremental** (tidak narik ulang semuanya), dan bisa dipicu manual.
**Selesai kalau:** 2 siklus jadwal berturut-turut: siklus ke-2 hanya memproses review baru; ada cara "Sync Now".

## 2. Prasyarat & Dependency
RI-05 stabil. `updated_since` di VoC (handoff RI-01/03 ke Codex).

## 3. File Target
| File | Status |
|---|---|
| `onecloud/app/tasks/VoiceOfCustomerSystemTask.php` | [ubah] — cursor + delta |
| Registrasi jadwal (supervisor/scheduler existing) | [ubah] `[assumption]` |

## 4. Langkah Implementasi
1. **Temukan mekanisme jadwal existing** `[assumption→verifikasi]`: bagaimana SonarTask/CrawlerTask dijadwalkan — cek `supervisor.sh`, `docker-compose.scheduler.yml`, `crontab -l` di WSL, atau tanya tim. **Ikuti mekanisme yang sama**, jangan bikin baru.
2. **State cursor (sisi OneBox, sesuai erd rancangan):** simpan `last_synced_at` per site. MVP paling murah tanpa migration: **Redis** (`voc_sync_cursor_<SiteId>`) — pola cache config SonarTask [verified line 1373]. Fallback kalau Redis dianggap kurang durable: file/DB — putuskan saat eksekusi, catat.
3. **Delta:** `getReviews(['updated_since' => $cursor, 'latest_first' => false])`; sukses semua → cursor = max(updated_at) response. **Fallback pra-`updated_since`:** `latest_first=true` + berhenti saat ketemu `review_hash` yang sudah ada 2 halaman berturut-turut (dedup tetap jadi jaring pengaman).
4. **Sync Now:** karena scheduled task = CLI, trigger manual dev = jalankan command yang sama. Versi UI (tombol di admin) masuk RI-14/backlog — jangan di sini.
5. **Jangan aktifkan jadwal di environment bersama sebelum RI-09 selesai** (guardrail dari two_agents_workflow: "jangan schedule otomatis dulu").

## 5. Cara Verifikasi
Run terjadwal 2x (interval pendek di dev): log siklus-2 menunjukkan fetch kecil (delta) + 0 insert duplikat; matikan VoC saat siklus → siklus berikutnya recover tanpa kehilangan data (cursor tidak maju saat gagal).

## 6. Risiko & Rollback
Cursor maju padahal batch gagal sebagian → data bolong. Mitigasi: cursor hanya di-update setelah SEMUA halaman siklus sukses. Rollback: hapus key Redis → full resync (aman karena idempotent).

## 7–8. Temuan / API Gap
`updated_since` (sudah diajukan). Tambahan opsional: response `server_time` untuk hindari clock skew.

## 9. Estimasi (4 MD)
Hari 1: temukan & pahami mekanisme jadwal existing. Hari 2: cursor + delta. Hari 3: fallback + failure-recovery test. Hari 4: registrasi jadwal dev + observasi 1 hari.
