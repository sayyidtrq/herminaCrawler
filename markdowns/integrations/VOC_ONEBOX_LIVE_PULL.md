# OneBox → VoC: Pindah dari Mock ke Pull Data Asli

> Tujuan: OneBox menarik review sungguhan dari VoC System, ter-scope ke tenant yang benar.

## 1. Kondisi sekarang (terverifikasi di codebase VoC)

| Jalur | Status | Catatan |
|---|---|---|
| `GET /api/reviews` (JWT user) | **BISA DIPAKAI** | scope tenant = `company_id` milik user yang login |
| `GET /api/integration/v1/reviews` (service token) | **BELUM BISA** | selalu `503 SERVICE_AUTH_NOT_READY` |

Endpoint integration-nya sendiri sudah jadi dan bagus (keyset cursor, watermark
`sync_updated_at`). Yang belum ada cuma auth-nya — `service_auth.py` dan model `ApiClient`
belum ditulis. Lihat `PROMPT_VOC_AGENT_SERVICE_TOKEN.md`.

**Keputusan:** jalan dulu dengan `api_mode: "user"`, pindah ke `"service"` begitu VOC-CS-03
live. Perpindahannya cuma ganti isi `Connection.Options`, tidak ada perubahan kode.

## 2. Risiko utama yang sekarang sudah ditutup

`/api/reviews` menentukan tenant dari **user yang login**, bukan dari parameter yang dikirim
OneBox. Artinya sebelum ini, salah paste email/password di row `Connection` = review rumah
sakit lain masuk diam-diam ke SiteId ini, tanpa satu pun error.

Sekarang `Options.company_id` **wajib** diisi. Sebelum menarik sebaris pun, provider memanggil
`GET /api/auth/me` dan membandingkan `company_id`-nya. Mismatch → sync dibatalkan.

## 3. Bentuk `Connection.Options` untuk mode live

```json
{
  "api_mode": "user",
  "company_id": 1,
  "mock": false,
  "page_size": 100,
  "max_pages": 20,
  "lookback_days": 0,
  "timeout": 30,
  "location_map": { "2": 1705, "4": 1706 }
}
```

| Key | Arti |
|---|---|
| `company_id` | **wajib.** company_id VoC yang seharusnya terpetakan ke SiteId ini |
| `lookback_days` | `0` = full pull tiap run (dedup yang menahan duplikat). Isi mis. `30` untuk membatasi biaya |
| `location_map` | location_id VoC → LocationId OneBox |

`Connection.Url` = base URL VoC (mis. `http://10.13.13.90:8000`), `UserId` = email service user
VoC, `Password` = passwordnya.

> Kredensial jangan ditulis di dokumen/commit. Kirim lewat channel privat.

## 4. Urutan menjalankan

```bash
C=$(docker ps -qf name=webapp)

# 1) Konektivitas dulu
docker exec $C php app/bootstrap.php voice_of_customer_system health <connId>

# 2) WAJIB: kredensial ini milik company mana?
docker exec $C php app/bootstrap.php voice_of_customer_system whoami <connId>

# 3) Baru tarik
docker exec $C php app/bootstrap.php voice_of_customer_system receive <connId>
docker exec $C php app/bootstrap.php voice_of_customer_system processpending <connId>
docker exec $C php app/bootstrap.php voice_of_customer_system analysis <connId>
```

Output `whoami` yang diharapkan:

```
connection : 1039
OneBox site: 169
VoC user   : integrasi-onebox@…
VoC company: 1 (RS Hermina)
expected   : 1
STATUS     : OK — binding cocok
```

Kalau `STATUS: MISMATCH` → **jangan lanjut `receive`**. Salah satu dari kredensial atau
`Options.company_id` keliru.

## 5. Verifikasi hasil (SQL)

```sql
-- harus 0
SELECT COUNT(*) AS bocor
FROM Ticket t
JOIN Message m   ON m.ObjectId = t.Id AND m.ObjectName = 'Ticket'
JOIN Connection c ON c.Id = m.ConnectionId AND c.ProviderId = 'PVD97'
WHERE t.SiteId <> 169;

-- sebaran per lokasi
SELECT l.Description AS lokasi, COUNT(*) AS jumlah, ROUND(AVG(t.Sentiment),2) AS rating
FROM Ticket t
JOIN Message m    ON m.ObjectId = t.Id AND m.ObjectName = 'Ticket'
JOIN Connection c ON c.Id = m.ConnectionId AND c.ProviderId = 'PVD97'
LEFT JOIN Location l ON l.Id = t.LocationId
WHERE t.SiteId = 169
GROUP BY l.Description;
```

## 6. Hasil run pertama (terverifikasi 2026-07-20)

VoC dijangkau lewat LAN di `http://192.168.1.3:8000` — reachable dari dalam container webapp.
(`10.13.13.90` alamat WireGuard **tidak** reachable dari mesin dev ini; pakai IP LAN saja.)

```
connection 1039 (TargetId=4)  sync done: fetched=25 inserted=15 deduped=10 skipped=0 failed=0
connection 1040 (TargetId=2)  sync done: fetched=50 inserted=45 deduped=5  skipped=0 failed=0
processpending: 15 + 45   applyAnalysis: 15 + 45 ticket updated
```

| Lokasi | Tiket | Rating rata2 | Ada summary | Ada kategori | Prioritas tinggi |
|---|---|---|---|---|---|
| Hermina Depok | 25 | 4.40 | 25 | 25 | 1 |
| HGA Depok | 50 | 3.22 | 48 | 48 | 16 |

- `bocor_ke_site_lain` = **0** — tidak ada tiket PVD97 di luar SiteId 169.
- `deduped` > 0 di run pertama = review yang `review_hash`-nya sudah masuk dari fixture mock.
  Dedup `ensureMessage` bekerja.
- 2 tiket HGA tanpa summary bukan bug: di VoC keduanya masih `analyzed=false`.
  LocationId tetap ter-backfill; summary sengaja dibiarkan null.

### Catatan tenant di data dev

User `test@gmail.com` → `company_id=3 (HGA)`, dan company itu memiliki **dua** lokasi:
`id=2 HGA Depok` dan `id=4 Hermina Depok`. Jadi kedua Connection memang sah memakai
kredensial yang sama. Jangan simpulkan dari nama Connection saja — selalu cek `whoami`
plus daftar lokasi milik company tersebut.
