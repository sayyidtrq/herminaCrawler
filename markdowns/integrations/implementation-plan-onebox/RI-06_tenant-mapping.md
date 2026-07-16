# RI-06 — Mapping Site ↔ Lokasi (≤3 MD)

> Keputusan terkait: D2, D6. Sebagian besar sudah "terserap" ke RI-04/05 — task ini merapikan & memvalidasi.

## 1. Tujuan & Definition of Done
Review dari lokasi VoC tertentu mendarat di `SiteId` + `LocationId` OneBox yang benar.
**Selesai kalau:** ingest 2 lokasi VoC berbeda → Ticket-nya beda `LocationId`; site lain tidak kecipratan data.

## 2. Prasyarat & Dependency
RI-05 berjalan. Keputusan D6 (config-based MVP).

## 3. File Target
| File | Status |
|---|---|
| `onecloud/app/config/development.php` section `voiceofcustomer` | [ubah] tambah `locationMap` |
| `onecloud/app/tasks/VoiceOfCustomerSystemTask.php` | [ubah] resolver |

## 4. Langkah Implementasi
1. **Struktur config (D6):**
   ```php
   'voiceofcustomer' => [
       ...,
       'siteId' => 1,                       // pilot
       'locationMap' => [                   // voc location_id => OneBox LocationId
           5 => 101,   // Hermina Depok  => LocationId site
           7 => 102,
       ],
       'defaultLocationId' => null,
   ],
   ```
2. **Resolver di task:** `mapLocation(int $vocLocId): ?int` — lookup `locationMap`, fallback `defaultLocationId` + log warning "unmapped location".
3. **Validasi master lokasi OneBox:** cek dulu bagaimana `LocationId` dipakai (`grep -n "LocationId" app/controllers/MediamonitoringController.php | head`) dan master lokasinya di mana (`app/models/Location*.php`?) — isi nilai map dengan Id yang beneran ada. `[assumption→verifikasi]`
4. **Filter sisi VoC:** panggil `getReviews(['location_id' => <vocLocId>])` per entry map — supaya hanya lokasi ter-mapping yang ditarik (hemat + aman).

## 5. Cara Verifikasi
```sql
SELECT t.LocationId, COUNT(*) FROM Ticket t JOIN Message m ON m.Id=t.MessageId
WHERE m.ObjectName='Review' GROUP BY t.LocationId;  -- sesuai map
SELECT COUNT(*) FROM Ticket WHERE SiteId <> <pilot> AND Id IN (SELECT ObjectId FROM Message WHERE ObjectName='Review'); -- HARUS 0
```

## 6. Risiko & Rollback
Unmapped location masuk tanpa lokasi → dashboard per-lokasi bolong; mitigasi: log warning + laporan jumlah unmapped di akhir sync. Rollback: revert config.

## 7–8. Temuan / API Gap
Kalau butuh daftar lokasi programatik: minta Codex expose `GET /api/locations` (gap kecil).

## 9. Estimasi (3 MD)
Hari 1: struktur config + resolver. Hari 2: validasi master LocationId OneBox. Hari 3: test 2 lokasi + laporan unmapped.
