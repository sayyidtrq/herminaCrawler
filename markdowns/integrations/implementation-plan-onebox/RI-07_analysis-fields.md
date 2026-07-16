# RI-07 — Field Analisa Ekstra (≤3 MD)

> Keputusan terkait: D4, D7, D8. Sebagian dieksekusi di RI-05 (Description/Solution/Meta); task ini menyelesaikan `issue_category` + memastikan semua field analisa query-able sesuai kebutuhan dashboard RI-12.

## 1. Tujuan & Definition of Done
Semua output AI VoC punya rumah di OneBox dan **bisa diagregasi dashboard**: sentiment ✅(kolom), urgency ✅(PriorityId), summary/recommended_action ✅(Description/Solution), `issue_category` → `CategoryId` (D7), sisanya di Meta.
**Selesai kalau:** query `GROUP BY t.CategoryId` dan `GROUP BY t.PriorityId` atas ticket review menghasilkan breakdown yang benar.

## 2. Prasyarat & Dependency
RI-05 jalan. D7 ter-ratifikasi (paling mungkin dioverride lead — kerjakan terakhir di antara task ingest).

## 3. File Target
| File | Status |
|---|---|
| Master `Category` seed per site (SQL) | [baru — dev dulu] |
| `onecloud/app/tasks/VoiceOfCustomerSystemTask.php` | [ubah] — map issue_category → CategoryId |

## 4. Langkah Implementasi
1. **Verifikasi model Category** `[assumption]`: `ls app/models | grep -i categ` + `setSource()` + bagaimana `Ticket.CategoryId` dipakai Mediamonitoring (`grep -n "CategoryId" MediamonitoringController.php | head`). Kalau ternyata Mediamonitoring pakai mekanisme lain (mis. `Reference`), ikuti itu — catat di Temuan.
2. **Kumpulkan daftar nilai `issue_category`** dari VoC: `SELECT DISTINCT issue_category FROM review_analysis;` (SQLite/PG sisi VoC) — set-nya kecil (waktu_tunggu, pelayanan, fasilitas, ...).
3. **Seed Category per site** + tabel translasi di config (`categoryMap: ['waktu_tunggu' => <CategoryId>, ...]`) — konsisten pola `locationMap`.
4. **Update task:** isi `Ticket.CategoryId` via map; unmapped → null + warning.
5. **Backfill** ticket review yang sudah terlanjur masuk: script kecil sekali-jalan (UPDATE via join Meta) — atau re-ingest DB dev (lebih murah: hapus & sync ulang, idempotent).

## 5. Cara Verifikasi
```sql
SELECT t.CategoryId, COUNT(*) FROM Ticket t JOIN Message m ON m.Id=t.MessageId
WHERE m.ObjectName='Review' GROUP BY t.CategoryId;   -- breakdown masuk akal, null sedikit
```

## 6. Risiko & Rollback
Kategori AI bisa bertambah nilai baru seiring waktu → unmapped; mitigasi: warning log + review berkala. Rollback: set CategoryId null.

## 7–8. Temuan / API Gap
Kalau daftar kategori perlu stabil: minta Codex kunci enum `issue_category` di prompt AI + expose `GET /api/analysis/categories` (gap kecil, opsional).

## 9. Estimasi (3 MD)
Hari 1: verifikasi Category + kumpulkan nilai. Hari 2: seed + map + update task. Hari 3: backfill + verifikasi agregasi.
