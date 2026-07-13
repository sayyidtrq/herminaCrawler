# RI-09 — Error Handling & Observability (≤3 MD)

## 1. Tujuan & DoD
Kegagalan integrasi terlihat dan tidak merusak: timeout, 401, 5xx, VoC down. **Selesai kalau:** tiap mode gagal ter-log terstruktur, task tidak crash, tidak ada secret di log, dan ada ringkasan per-run (fetched/inserted/skipped/failed).

## 2. Prasyarat
RI-05; sebaiknya sebelum RI-08 mengaktifkan jadwal.

## 3. File Target
`VoiceOfCustomerSystemClient.php` + `VoiceOfCustomerSystemTask.php` [ubah].

## 4. Langkah
1. **Client:** timeout eksplisit (sudah), 401 → re-login retry 1x (sudah dirancang RI-04), 5xx/timeout → retry max 2x dengan backoff (sleep 2s, 8s) lalu throw. Pola log: `Logger::get('VoiceOfCustomerSystem')` — pesan tanpa credential/token (audit: grep token/password di log dev).
2. **Task:** counter per-run → log ringkasan akhir: `sync done: fetched=120 inserted=37 skipped=83 failed=0 durasi=42s`. Failed>0 → level warning.
3. **Item-level fault isolation** (sudah di RI-05 try/catch per item) — pastikan satu review busuk tidak menghentikan batch; simpan `review_hash` yang gagal di log.
4. **Cek konvensi lokasi log** `[assumption]`: di mana Monolog nulis di deployment ini (`grep -rn "StreamHandler\|path" app/library/Logger.php | head`) supaya lu tahu file mana yang dibaca saat troubleshooting.

## 5. Verifikasi
Simulasi: (a) VoC mati total, (b) VoC mati di tengah, (c) credential salah, (d) satu item JSON rusak (edit fixture). Keempatnya: log jelas, exit rapi, ringkasan akurat.

## 6. Risiko
Retry berlebihan memukul VoC — batasi 2x, backoff. Log membengkak — ringkasan per-run, bukan per-item sukses.

## 9. Estimasi (3 MD)
Hari 1: client retry/backoff. Hari 2: ringkasan + isolasi. Hari 3: simulasi 4 skenario.
