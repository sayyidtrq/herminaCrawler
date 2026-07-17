# RI-01 — Field Mapping: Review VoC → Ticket/Message OneBox (≤3 MD)

> Status dokumen: **SELESAI 2026-07-14** — deliverable final di [`../implementation-plan/field-mapping-final.md`](../implementation-plan/field-mapping-final.md) (tabel di bawah adalah draft historis; kalau beda, dokumen final yang menang)
> Penanda: `[verified]` = sudah dicek ke file asli · `[assumption]` = perlu dicek · `[blocked]` = butuh keputusan lead/Codex

---

## 1. Tujuan & Definition of Done

Menghasilkan **tabel mapping final** setiap field response `/api/reviews` VoC System ke kolom OneBox (`Ticket` / `Message` / `MessageContent` / `MessageUser` / `Contact`), termasuk nilai-nilai konstanta (TypeId, StatusId, dsb) yang akan dipakai `VoiceOfCustomerSystemTask`.

**Selesai kalau:**
1. Semua field response `/api/reviews` punya baris di tabel mapping: target kolom, transform, atau keputusan "tidak dipetakan + alasan".
2. Daftar field **tanpa rumah** (butuh keputusan lead) terkumpul rapi sebagai bahan RI-02.
3. Dokumen final tersimpan sebagai `markdowns/integrations/implementation-plan/field-mapping-final.md` dan sudah direview Codex (sisi VoC) + saya/user (sisi OneBox).

## 2. Prasyarat & Dependency

- Tidak tergantung task lain (ini task paling hulu). RI-02 (keputusan lead) justru **bergantung pada output task ini**.
- Tidak perlu branch git — task ini dokumen-only, tidak menyentuh kode OneBox.
- Butuh akses baca: repo OneBox WSL + repo VoC lokal (dua-duanya sudah tersedia).
- Butuh akses MySQL dev OneBox (DBeaver, port 3307) untuk verifikasi kode Reference — lihat Langkah 3.

## 3. File Target

| File                                                                                              | Status                        |
| ------------------------------------------------------------------------------------------------- | ----------------------------- |
| `markdowns/integrations/implementation-plan/field-mapping-final.md`                               | [baru] — deliverable utama    |
| `\\wsl.localhost\...\onecloud\app\models\{Ticket,Message,MessageContent,MessageUser,Contact}.php` | [baca-saja]                   |
| `\\wsl.localhost\...\onecloud\app\tasks\SonarTask.php`                                            | [baca-saja] — pattern rujukan |
| `C:\...\hermina_crawler\app\db\models.py` + `apps\api\app_api\routers\reviews.py`                 | [baca-saja]                   |

## 4. Langkah Implementasi

### Langkah 1 — Pahami pattern ingest SonarTask `[verified]`

Sudah diverifikasi dari `SonarTask.php` (line ±495–607), urutan penulisannya:

```
new Ticket()  → save → dapat ticketId
new Message() → save → dapat messageId  (Message.ObjectId = ticketId, Message.RemoteId = kunci dedup)
Ticket.MessageId = messageId → save ulang
new MessageContent() → Id = messageId, ObjectId = ticketId, Body/BodyText = isi
```

Konstanta yang SonarTask pakai (news) — VoC kemungkinan butuh nilai sendiri:
`Ticket`: `PriorityId='TP2'`, `TypeId='TT3'`, `StatusId='TS2'`, `Progress=0`, `UnseenComment=1` · `Message`: `ObjectName='News'`, `TypeId='MST2'`, `StatusId='MSS1'`, `Incoming=1`

### Langkah 2 — Draft tabel mapping (sudah dikerjakan di bawah, tinggal validasi)

#### 2a. `Review` (VoC) → OneBox

| Field VoC | Target OneBox | Transform / Catatan | Status |
|---|---|---|---|
| `id` | — (tidak dipetakan) | pakai identifier eksternal, bukan PK internal VoC | [verified] |
| `company_id` | `SiteId` (semua tabel) | via tabel mapping tenant di sisi OneBox (RI-06) | [blocked] RI-06 |
| `location_id` | `Ticket.LocationId` | SonarTask set `null`; perlu validasi master Location OneBox per site | [blocked] lead |
| `source` (`selenium_google_maps`) | `Message.ObjectName` = `'Review'`? + `MediaId` baru | SonarTask pakai `ObjectName='News'`; review butuh ObjectName/MediaId sendiri | [blocked] lead (= pertanyaan "channel baru?") |
| `external_review_id` | `Message.RemoteId` (alternatif) | nullable di VoC ⚠️ | [verified] nullable |
| `review_hash` | **`Message.RemoteId` (rekomendasi)** | NOT NULL + unique di VoC → dedup key paling stabil; cek `Message::findFirst(RemoteId + SiteId)` sebelum insert (pola SonarTask line 422) | [verified] pattern |
| `reviewer_name` | `Contact.Name` (find-or-create) → `Ticket.ContactId`, `Ticket.Requestor`, `Message.From` | pola SonarTask: satu Contact per author | [verified] pattern |
| `reviewer_profile_url` | `Contact.Url` | kolom ada di Contact | [verified] kolom ada |
| `reviewer_photo_url`, `reviewer_local_guide_level`, `reviewer_total_reviews` | `MessageContent.Meta` (JSON) | tidak ada kolom padanan; jangan bikin kolom baru untuk ini | [assumption] |
| `rating` (1–5) | **tanpa rumah di Ticket** | kandidat: `MessageContent.Meta`, `Ticket.PriorityValue` (salah guna), atau kolom baru | [blocked] lead |
| `review_text` | `Ticket.Subject` (trim, maks ±4000 spt SonarTask) + `MessageContent.Body`/`BodyText` (full) | pola SonarTask line 479 | [verified] pattern |
| `review_time` | `Message.Date` + `Message.ReceiveDate` | ISO 8601 (+TZ) → MySQL datetime; perhatikan timezone site | [verified] pattern |
| `review_language` / `language` | `MessageContent.Meta` | optional | [assumption] |
| `like_count` | `MessageContent.Meta` | optional | [assumption] |
| `owner_response_text` / `owner_response_time` | fase lanjut: `Message` kedua (Incoming=0, ParentId=message pertama) | jangan di MVP | [assumption] |
| `scraped_at`, `raw_payload`, `created_at` | — (tidak dipetakan) | audit internal VoC | [verified] |
| `updated_at` | — (bukan kolom OneBox) | **sudah ada di schema VoC** — dipakai sbg dasar `updated_since` (state cursor disimpan sisi OneBox) | [verified] ada |

#### 2b. `ReviewAnalysis` (VoC) → OneBox

| Field VoC | Target OneBox | Transform / Catatan | Status |
|---|---|---|---|
| `sentiment` (`positive/neutral/negative/mixed`) | `Ticket.Sentiment` | transform: positive→`1`, neutral→`0`, negative→`-1` — terverifikasi dari query Mediamonitoring (`CASE t.Sentiment WHEN -1/0/1`). **`mixed` tidak punya padanan** → usul: map ke `0` + simpan asli di Meta | [verified] skala; [blocked] `mixed` |
| `sentiment_score` | `MessageContent.Meta` | tidak ada kolom padanan | [assumption] |
| `issue_category` | `Ticket.CategoryId` | butuh master Category per site di OneBox (atau mapping kategori); alternatif: tag | [blocked] lead |
| `urgency` (`low/medium/high`) | `Ticket.PriorityId` (`TP*`) | **verified dari Reference: TP1=Low, TP2=Medium, TP3=High** → mapping: low→TP1, medium→TP2, high→TP3 (usul awal kebalik — sudah dikoreksi) | [verified] 2026-07-14 |
| `summary` | `Ticket.Description` | kolom ada, SonarTask set null — aman diisi | [verified] kolom ada |
| `recommended_action` | `Ticket.Solution` | kolom ada; secara semantik pas | [verified] kolom ada |
| `keywords` (JSON) | tag (pola `tagList` SonarTask) | perlu cek mekanisme tag Mediamonitoring dulu | [assumption] |
| `is_potential_viral`, `is_patient_safety_issue` | `MessageContent.Meta` (MVP); nanti trigger AlertRule (fase lanjut) | flag penting — jangan hilang, tapi belum ada rumah struktural | [blocked] lead |
| `model_name`, `prompt_version`, `raw_response` | — (tidak dipetakan) | audit internal VoC | [verified] |

#### 2c. Konstanta yang harus diputuskan untuk `VoiceOfCustomerSystemTask`

| Konstanta | Nilai SonarTask (news) | Untuk VoC Review (verified 2026-07-14) | Status |
|---|---|---|---|
| `Ticket.TypeId` | `'TT3'` | **auto dari `addTicket()`**: TT1 (atau TT3 kalau Setting messaging='Media'); existing Gbusiness pakai TT1 | [verified] Ticketing.php:325–329 |
| `Ticket.StatusId` | `'TS2'` | **auto**: TS2 (New) | [verified] Ticketing.php:332 |
| `Ticket.MediaId` / `Message.MediaId` | per channel Sonar | **reuse `GBUSINESS`** ("Google Business") — sudah ada di Reference + UI existing; TIDAK perlu MediaId baru | [verified] DB dev |
| `Message.TypeId` / `StatusId` | `'MST2'` / `'MSS1'` | sama: MST2 (Inbound) / MSS1 (New); + `PriorityId='MSP1'`, `MethodId='COMMENT'` | [verified] GbusinessProvider::map |
| `Message.ConnectionId` | `$this->sonar->ConId` | Connection per site dgn `ProviderId=PVDxx baru` (Code=`VoiceOfCustomerSystem`), `MediaId='GBUSINESS'` — pola Connection 805 (Gbusiness/PVD49) | [verified] pola; topologi per-lokasi vs per-company = K4 |

### Langkah 3 — Verifikasi kode Reference & Media di DB dev (±0.5 hari)

Buka DBeaver (MySQL port 3307) atau mysql CLI di WSL, jalankan:

```sql
-- daftar kode prioritas/type/status ticket & message
SELECT Id, Type, Name FROM Reference WHERE Id LIKE 'TP%' OR Id LIKE 'TT%' OR Id LIKE 'TS%' OR Id LIKE 'MST%' OR Id LIKE 'MSS%';
-- daftar media (channel) existing
SELECT * FROM Media;      -- atau cek model app/models/Media.php dulu kalau nama tabel beda
```

Expected: dapat daftar kode asli → isi kolom "Untuk VoC Review" di tabel 2c, ubah `[assumption]` jadi `[verified]`.
⚠️ Nama tabel `Reference`/`Media` masih [assumption] — cek `setSource()` di `app/models/Reference.php` dulu.

### Langkah 4 — Susun `field-mapping-final.md` (±0.5 hari)

Gabungkan tabel 2a–2c yang sudah tervalidasi + bagian "Butuh Keputusan Lead" (semua baris [blocked]) + bagian "API Gap". Format tabel sama seperti di atas.

### Langkah 5 — Review silang (±0.5 hari)

- Kirim ke Codex: validasi nama/tipe field sisi VoC + konfirmasi API gap.
- Bawa daftar [blocked] ke Pak Agung (jadi agenda RI-02) — jangan menunggu semua jawaban untuk menutup task ini; task selesai saat daftarnya rapi.

## 5. Cara Verifikasi/Test Manual

Task ini dokumen-only. Verifikasi = checklist:
- [ ] Setiap field di sample response `/api/reviews` (lihat superprompt §5.2) punya baris mapping.
- [ ] Query Langkah 3 sudah dijalankan; hasil tertempel di dokumen final.
- [ ] Tidak ada baris berstatus [assumption] yang bisa dicek sendiri tapi belum dicek.
- [ ] Daftar [blocked] ≤ 8 item dan masing-masing punya usulan default (biar diskusi lead cepat).

## 6. Risiko & Rollback

- **Risiko:** salah asumsi kode Reference → task RI-05 nulis Ticket dengan kode tak dikenal UI. Mitigasi: Langkah 3 wajib, jangan dilewati.
- **Risiko:** `review_hash` VoC bersifat unique **global** (bukan per company) `[verified]` — aman untuk RemoteId, tapi catat kalau nanti multi-company crawl lokasi yang sama bisa bentrok unique constraint di sisi VoC (isu VoC, handoff Codex).
- Rollback: n/a (dokumen).

## 7. Temuan & Deviasi (hasil verifikasi hari ini)

1. **`Review.updated_at` SUDAH ADA** di schema VoC (server_default + onupdate) — deviasi dari tasklist/erd yang menyebut "tambah updated_at". Yang benar-benar belum ada: **param `updated_since` di `/api/reviews`** `[verified dari routers/reviews.py: hanya page, page_size, latest_first, dst]`.
2. Skala sentiment OneBox = integer `-1/0/1` `[verified dari query Mediamonitoring]`, VoC = string 4 nilai — nilai `mixed` butuh keputusan.
3. `MessageContent.Id = Message.Id` (share PK, bukan auto-increment sendiri) `[verified dari SonarTask line 603]` — penting untuk RI-05.
4. SonarTask **tidak** mengisi `Ticket.Content/Description/Solution` — kolom-kolom itu kosong dan aman dipakai VoC untuk summary/recommended_action.

**Tambahan hasil verifikasi 2026-07-14 (WSL onecloud + DB dev):**

5. **OneBox sudah punya pipeline review Google Business** — `GbusinessProvider` (`app/services/Provider/GbusinessProvider.php`), MediaId `GBUSINESS`, Connection contoh Id 805 (PVD49), 571 message di dev, plus UI existing `dashboard/ReviewsController` & `AllReviewsController`. **Pola ingest yang benar untuk review = Provider pattern + `messaging->ensureMessage()`, bukan pola SonarTask** — RI-04/RI-05 perlu menyesuaikan.
6. **Dedup ensureMessage = 3 kolom:** `SiteId + MediaId + RemoteId` (Messaging.php:842) — bukan RemoteId saja.
7. **Rating punya rumah:** `MessageContent.Meta.star` → `addTicket()` otomatis set `Ticket.Sentiment = star (1–5)` (Ticketing.php:334–341). Konsekuensi: untuk tiket review, `Ticket.Sentiment` = rating bintang; AI sentiment (-1/0/1 hanya konvensi news) disimpan di Meta → merevisi D8.
8. **Kode prioritas verified: TP1=Low, TP2=Medium, TP3=High** — usul awal (high→TP1) kebalik, sudah dikoreksi di tabel 2b dan dokumen final.
9. **Ticket dibuat async** oleh job `process` (ProcessingService→addTicket) → field analisa (`Description/Solution/CategoryId/PriorityId`) di-apply lewat **pass kedua** (cari Message by RemoteId → update Ticket via ObjectId) — detail di dokumen final §4.

## 8. API Gap / Handoff ke Codex

1. `GET /api/reviews` belum punya `updated_since` — tambah query param filter `Review.updated_at >= ?` (kolomnya sudah ada, tinggal expose). Prioritas: sebelum RI-08. **[dikonfirmasi 2026-07-14: param list hanya page/page_size/location_id/rating/sentiment/keyword/latest_first/include_raw/date_preset/date_from/date_to]**
2. ~~Konfirmasi `review_hash` di response~~ — **✅ CLOSED: ada di `apps/api/app_api/schemas.py:109` (ReviewResponse.review_hash)**.
3. Catatan unique global `review_hash` (Risiko #2 di atas).
4. **GAP BARU:** `updated_at` tidak di-expose di `ReviewResponse` (hanya `created_at`) — wajib ditambah sebagai cursor delta sync. Prioritas: sebelum RI-08, bareng #1.

## 9. Estimasi Breakdown (3 MD)

| Hari | Kegiatan |
|---|---|
| 1 | Langkah 1–2: baca pattern, validasi draft tabel 2a–2b terhadap model dua sisi |
| 2 | Langkah 3: verifikasi Reference/Media di DB + finalisasi tabel 2c; mulai susun dokumen final |
| 3 | Langkah 4–5: rapikan dokumen final, review silang Codex, siapkan daftar keputusan untuk lead |

> Catatan jujur: karena draft mapping di dokumen ini sudah ±80% terverifikasi, hari 1 kemungkinan lebih cepat — sisa waktunya pakai buat Langkah 3 yang paling rawan salah.
