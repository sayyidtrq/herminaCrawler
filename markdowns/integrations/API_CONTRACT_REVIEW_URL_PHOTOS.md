# Menambah `review_url` dan `review_photo_urls` ke contract v1

2026-09-22 · untuk dev crawler service · pelengkap
[HANDOFF_REVIEW_DIRECT_LINK.md](HANDOFF_REVIEW_DIRECT_LINK.md)

## Endpoint yang dipakai OneBox

```
GET /integration/v1/reviews?limit=200&cursor=<opaque>
Authorization: Bearer <service token>
X-Request-ID: <opsional, dipantulkan ke meta.request_id>
```

Tenant **tidak** dikirim sebagai parameter — ia ditentukan service token.
Scope yang dibutuhkan: `reviews:read`.

Berkas terkait:

| Peran | Berkas |
|---|---|
| Router + deskripsi contract | `apps/api/app_api/routers/integration_reviews.py:89` |
| **Skema response (kontraknya)** | `apps/api/app_api/integration_schemas.py:64` → `IntegrationReviewItem` |
| Perakit baris dari DB | `app/services/integration_review_service.py:299` → `_project()` |
| Kolom tabel | `app/db/models.py` → `_GoogleReviewColumns` |

## Contoh response yang berlaku sekarang

Berkas: [`contoh-respons/reviews-v1-sekarang.json`](contoh-respons/reviews-v1-sekarang.json)

Contoh itu **tidak diketik tangan**. Ia dibangun lewat
`IntegrationReviewListResponse` — model yang dipakai endpoint sungguhan — lalu
di-dump. Karena `model_config = ConfigDict(extra="forbid")` dan seluruh
fieldnya bertipe ketat, contoh yang berhasil keluar berarti sudah lolos
validasi kontrak. Itulah dasar untuk menyebutnya "terbukti dapat terkirim".

Isinya dua baris yang sengaja berbeda keadaan:

- `id: 18432` — sudah dianalisis, **seluruh** field terisi
- `id: 18433` — belum dianalisis, memperlihatkan nilai bawaan tiap field
  analisa (`null`, kecuali `keywords: []` dan dua flag boolean `false`)

Ringkasnya:

```json
{
  "data": [
    {
      "id": 18432,
      "location_id": 1041,
      "location": "RS Hermina Depok",
      "source": "apify",
      "external_place_id": "ChIJ3W4519YcaS4R5g-B4Tw8T_U",
      "external_review_id": "ChdDSUhNMG9nS0VJQ0FnSUNsdnNyWXN3RRAB",
      "review_hash": "9f2c1b7a4d5e6f80a1b2c3d4e5f60718293a4b5c6d7e8f90",
      "reviewer_name": "Rina Kartika",
      "reviewer_profile_url": "https://www.google.com/maps/contrib/103928471625048372910/reviews",
      "rating": 2,
      "review_text": "Antrean pendaftaran lama sekali, hampir dua jam baru dipanggil.",
      "review_time": "2026-09-18T03:14:00Z",
      "owner_response_text": "Mohon maaf atas ketidaknyamanannya, Bu Rina.",
      "owner_response_time": "2026-09-19T01:02:00Z",
      "updated_at": "2026-09-19T01:05:11Z",
      "sync_updated_at": "2026-09-19T01:05:11Z",
      "analysis_status": "completed",
      "analyzed": true,
      "output_schema_version": "v1",
      "sentiment": "negative",
      "sentiment_score": -0.82,
      "issue_category": "waiting_time",
      "urgency": "high",
      "summary": "Pasien menunggu hampir dua jam di pendaftaran.",
      "recommended_action": "Tinjau kapasitas loket pendaftaran pada jam sibuk.",
      "keywords": ["antrean", "pendaftaran", "lama"],
      "is_potential_viral": false,
      "is_patient_safety_issue": false
    }
  ],
  "page": {
    "limit": 200,
    "has_more": false,
    "next_cursor": null,
    "checkpoint_cursor": "eyJ0IjoiMjAyNi0wOS0xOVQwODo0MTowMloiLCJpZCI6MTg0MzN9",
    "snapshot_at": "2026-09-19T08:41:30Z"
  },
  "meta": { "api_version": "v1", "request_id": "0f8c2d31-6f2a-4c11-9d47-5b1e9a8c7d20" }
}
```

**Tidak ada `review_url`, dan tidak ada field foto apa pun.** Satu-satunya URL
yang dikirim adalah `reviewer_profile_url`, dan itu profil penulisnya.

## Yang paling penting: `extra="forbid"`

`IntegrationReviewItem` memakai `ConfigDict(extra="forbid")`. Konsekuensinya:

> **Menambahkan field di `_project()` saja TIDAK cukup.** Field yang belum
> dideklarasikan di skema akan ditolak, bukan diteruskan diam-diam.

Ini sudah dicoba pada skema yang sebenarnya:

```
review_url             Extra inputs are not permitted
review_photo_urls      Extra inputs are not permitted
```

Jadi urutannya wajib: **skema dulu, baru serializer.**

## Bentuk yang diusulkan

Berkas: [`contoh-respons/reviews-v1-usulan.json`](contoh-respons/reviews-v1-usulan.json)
— juga sudah divalidasi lewat skema (disubclass sementara hanya untuk
memperagakan bentuknya).

Dua field baru di tiap item:

```json
"review_url": "https://www.google.com/maps/reviews/data=!4m8!14m7!1m6!2m5!1sChdDSUhNMG9nS0VJQ0FnSUNsdnNyWXN3RRAB!2m1!1s0x0:0x6f5ae1b0c2d3e4f5",
"review_photo_urls": [
  "https://lh3.googleusercontent.com/places/ANXA/photo-antrean-1.jpg",
  "https://lh3.googleusercontent.com/places/ANXA/photo-antrean-2.jpg"
]
```

Untuk ulasan tanpa tautan/foto:

```json
"review_url": null,
"review_photo_urls": []
```

### Kenapa bentuknya begitu

- **`review_url` nullable, `review_photo_urls` selalu array.** Mengikuti pola
  yang sudah ada di kontrak ini: `keywords` pun tidak pernah `null` melainkan
  `[]`, dengan alasan yang ditulis di skemanya — supaya konsumen tidak perlu
  memeriksa null untuk sebuah koleksi. Kalau `review_photo_urls` kadang `null`
  dan kadang array, setiap pembacanya harus menangani dua bentuk.
- **Jamak, bukan tunggal.** Satu ulasan Google bisa memuat beberapa foto.
  Mengirim satu lalu menambah yang lain belakangan berarti mengubah tipe field
  — dan contract v1 menyatakan field **hanya boleh bertambah, tidak pernah
  berubah tipe**.
- **Namanya `review_photo_urls`, bukan `photo_url`.** Di tabel sudah ada
  `reviewer_photo_url` yang artinya avatar penulis. Dua nama yang hampir sama
  untuk dua hal berbeda adalah sumber kekeliruan yang mahal.

## Daftar perubahan

Urutannya penting — skema dulu, kalau tidak field-nya ditolak.

1. **Skema** `apps/api/app_api/integration_schemas.py`, di
   `IntegrationReviewItem`:
   ```python
   review_url: str | None = None
   review_photo_urls: list[str] = []
   ```
   Taruh setelah `reviewer_profile_url` supaya berkelompok dengan URL lain.
2. **Kolom** `app/db/models.py` → `_GoogleReviewColumns` (dipakai bersama
   `reviews` dan `competitor_reviews`):
   ```python
   review_url: Mapped[str | None] = mapped_column(Text)
   review_photo_urls: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
   ```
   `Text`, bukan `String(255)` — deep link Google panjang. Foto disimpan JSON
   karena jumlahnya tidak tetap.
3. **Migrasi Alembic** di `alembic/versions/` — dua kolom, nullable / berdefault.
4. **Serializer** `app/services/integration_review_service.py` → `_project()`
   (baris 299):
   ```python
   "review_url": review.review_url,
   "review_photo_urls": review.review_photo_urls or [],
   ```
5. **Importer Apify** `scripts/import_apify_reviews.py`: petakan
   `record.get("review_url")` dan `record.get("review_photos_urls")` ke kolom
   baru. Keduanya sudah ada di allow-list `_bounded_raw_payload()` (baris
   121–135), jadi datanya sudah masuk — sekarang tinggal dinaikkan dari
   `raw_payload` menjadi kolom.
6. **Selenium** `app/integrations/google_maps_review_parser.py`: belum punya
   deep link per-ulasan. Biarkan `None` sampai ekstraksinya siap. **Jangan**
   diisi `source_url` (URL halaman tempat) sebagai pengganti — nanti tidak bisa
   dibedakan mana yang direct link dan mana yang bukan.

## Sisi OneBox sudah siap

Sudah di-commit di branch `feature/DNGO19-3549_VOC-AI-Ticket-Entitlement`
(`0e044b9a28`):

- `VocProvider::buildMeta()` menyimpan `review_url` dan `review_photo_urls`
  begitu keduanya muncul di payload
- `VocController::reviewSumberUrl()` memakai nilai itu; logika perakitan URL
  lama sudah dibuang
- Layar Ulasan menampilkan tautan ke ulasannya dan galeri fotonya

Selama crawler belum mengirim, OneBox diam — tombolnya hilang dan foto tidak
muncul. Itu perilaku yang disengaja, bukan kerusakan.

Catatan kecil: `buildMeta()` untuk sementara menerima tiga ejaan nama field
foto (`review_photo_urls`, `review_photos_urls`, `review_photo_url`) karena
kontraknya belum final. **Begitu nama di skema ditetapkan, beri tahu supaya
sisanya dihapus.**

## Yang masih perlu dipastikan

1. **Bentuk `review_url` Apify yang sebenarnya.** Nilai pada contoh di atas
   mengikuti bentuk deep link Google (`/maps/reviews/data=!4m8...`), tetapi
   itu **belum diverifikasi terhadap dataset Apify kita**. Cek satu record
   sungguhan lebih dulu: kalau ternyata isinya URL tempat, seluruh rencana ini
   tidak menyelesaikan masalahnya.
2. **Backfill.** `review_url` sudah tersimpan di `raw_payload` untuk data yang
   pernah di-import lewat Apify, jadi pengisian kolom baru kemungkinan bisa
   dilakukan tanpa crawl ulang. Perlu dihitung berapa baris yang memenuhi.
3. **Kestabilan tautan.** Kalau Google merotasinya, menyimpannya sebagai kolom
   berarti menyimpan nilai yang bisa basi.
