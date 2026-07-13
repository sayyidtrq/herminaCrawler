# Contract API Integrasi v1 — Crawler System → OneBox

- Status: **frozen v1** (per VOC-CS-01)
- Endpoint: `GET /api/integration/v1/reviews`
- OpenAPI: `GET /api/openapi.json`
- Fixture kanonik: `tests/fixtures/voc_reviews_v1.json`
- Audiens: engineer OneBox (RI-01, RI-03, RI-04, RI-05)

Contract ini **terpisah** dari `GET /api/reviews` yang dipakai frontend Crawler. FE boleh berubah bentuk kapan saja; endpoint ini tidak ikut berubah. Aturan evolusi: perubahan hanya boleh **additive** pada v1 (menambah field opsional). Menghapus field, mengganti tipe, atau menyempitkan enum = **breaking**, dan wajib jadi v2.

---

## 1. Request

```
GET /api/integration/v1/reviews?limit=100&updated_since=2026-07-01T00:00:00Z&location_id=10
Authorization: Bearer <service-token>
X-Request-ID: <uuid, opsional>
```

### Parameter

| Parameter | Tipe | Default | Aturan |
|---|---|---|---|
| `limit` | integer | `100` | 1..200. Di luar rentang → `400 INVALID_PARAMETER`. |
| `cursor` | string opaque | – | Nilai dari `page.next_cursor` respons sebelumnya. **Jangan di-parse** — isinya internal dan akan berubah di CS-02. |
| `updated_since` | string | – | UTC ISO 8601 **wajib bersuffix `Z`**. Hanya untuk request pertama (tanpa cursor). Tanpa offset eksplisit → `400`. |
| `location_id` | integer | – | Opsional. Harus milik company pemilik token, kalau tidak → `404 LOCATION_NOT_FOUND`. |

### Aturan cursor

- `cursor` **tidak boleh** digabung dengan `updated_since` → `400 INVALID_CURSOR_CONTEXT`.
- `location_id` **tidak boleh** berubah di tengah paginasi; filter dikunci di dalam cursor → `400 INVALID_CURSOR_CONTEXT`.
- Cursor rusak/dipalsukan → `400 INVALID_CURSOR`.

### `X-Request-ID`

Kalau dikirim, nilainya dipantulkan di `meta.request_id` dan dipakai di log kami. Kalau tidak, server membuat UUID sendiri. **Kirimkan** — ini satu-satunya cara mengkorelasikan pull yang gagal dengan log kami.

---

## 2. Response 200

```json
{
  "data": [ /* IntegrationReviewItem */ ],
  "page": {
    "limit": 100,
    "has_more": false,
    "next_cursor": null,
    "snapshot_at": "2026-07-13T05:00:00Z"
  },
  "meta": { "api_version": "v1", "request_id": "uuid" }
}
```

Contoh lengkap 3 review (positive, negative-critical, unanalyzed) ada di `tests/fixtures/voc_reviews_v1.json`. **Pakai file itu sebagai input mock RI-04** — file yang sama dipakai test kami, jadi kalau parser kalian lolos terhadapnya, parser kalian sinkron dengan produksi.

### Field item

Semua timestamp **UTC ISO 8601 dengan suffix `Z`** (mis. `2026-07-12T03:00:00Z`). Tidak pernah `+00:00`, tidak pernah waktu lokal.

| Field | Tipe | Null? | Catatan |
|---|---|---|---|
| `id` | integer | tidak | PK internal kami. Stabil. |
| `location_id` | integer | tidak | |
| `location` | string | tidak | Nama cabang (`branch_name`). |
| `source` | string | tidak | mis. `selenium_google_maps`. |
| `external_place_id` | string | **ya** | |
| `external_review_id` | string | **ya** | |
| `review_hash` | string | tidak | **Kunci dedup idempoten.** Unik global. Pakai ini untuk upsert, bukan `id`. |
| `reviewer_name` | string | **ya** | Bisa null kalau reviewer anonim. |
| `reviewer_profile_url` | string | **ya** | |
| `rating` | integer | **ya** | 1..5 kalau ada. |
| `review_text` | string | tidak | Bisa string kosong `""`. |
| `review_time` | datetime | **ya** | Waktu review dibuat di sumber. |
| `owner_response_text` | string | **ya** | |
| `owner_response_time` | datetime | **ya** | |
| `updated_at` | datetime | tidak | Kapan baris review terakhir berubah di DB kami. |
| `sync_updated_at` | datetime | tidak | **Watermark sinkronisasi.** Lihat §3. |
| `analyzed` | boolean | tidak | `false` = analisis AI belum jalan. |
| `sentiment` | enum | **ya** | Null ⟺ `analyzed=false`. |
| `sentiment_score` | float | **ya** | 0.0–1.0. Null ⟺ `analyzed=false`. |
| `issue_category` | enum | **ya** | Null ⟺ `analyzed=false`. |
| `urgency` | enum | **ya** | Null ⟺ `analyzed=false`. |
| `summary` | string | **ya** | Null ⟺ `analyzed=false`. |
| `recommended_action` | string | **ya** | Null ⟺ `analyzed=false`. |
| `keywords` | array of string | tidak | **`[]` saat `analyzed=false`**, bukan null. |
| `is_potential_viral` | boolean | tidak | **`false` saat `analyzed=false`**, bukan null. |
| `is_patient_safety_issue` | boolean | tidak | **`false` saat `analyzed=false`**, bukan null. |

> ⚠️ **Perhatikan baris terakhir.** Enam field analisis (`sentiment` … `recommended_action`) jadi **null** saat `analyzed=false`, tapi `keywords` jadi **array kosong** dan dua flag boolean jadi **`false`** — sengaja, supaya kalian tidak perlu null-check koleksi. Ini keputusan kami; kalau OneBox lebih suka ketiganya ikut null, bilang sekarang selagi v1 belum dipakai produksi.

Field yang **tidak akan pernah** muncul: `raw_payload`, `raw_response`, `company_id`. Projection memakai whitelist eksplisit, dan ada test yang gagal kalau salah satunya bocor.

### Enum

Mengikuti `AnalysisService`. Ada test yang gagal kalau daftar di kode analisis dan di contract ini berbeda, jadi enum tidak akan melebar diam-diam.

- **`sentiment`** — `positive`, `neutral`, `negative`, `mixed`, `unknown`
- **`urgency`** — `low`, `medium`, `high`, `critical`, `unknown`
- **`issue_category`** (18) — `doctor_service`, `nurse_service`, `administration`, `waiting_time`, `cleanliness`, `facility`, `parking`, `billing`, `pharmacy`, `emergency_room`, `inpatient`, `customer_service`, `booking_system`, `staff_communication`, `security`, `food`, `general_praise`, `other`

Perlakukan nilai tak dikenal sebagai `unknown`/`other` daripada melempar error — itu memberi kami ruang menambah kategori tanpa memecahkan ingest kalian.

---

## 3. `sync_updated_at` dan semantik delta-sync

`sync_updated_at` = **kapan data ini siap disinkronkan**, bukan sekadar kapan barisnya berubah. Nilainya:

```
max(review.updated_at, review.created_at, waktu analisis terakhir review itu)
```

Bedanya dengan `updated_at`: kalau review sudah lama masuk tapi analisis AI-nya baru selesai hari ini, `updated_at` **tidak bergerak** tapi `sync_updated_at` **bergerak**. Kalau kalian delta-sync pakai `updated_at`, kalian akan **melewatkan review yang baru dianalisis**.

> **Selalu pakai `sync_updated_at` sebagai watermark, jangan `updated_at`.**

Alur yang benar:

1. Request pertama: `?updated_since=<watermark tersimpan>&limit=100`
2. Selama `has_more=true`: request berikutnya `?cursor=<next_cursor>` (**tanpa** `updated_since`)
3. Setelah seluruh siklus sukses di-ingest, simpan `sync_updated_at` tertinggi yang kalian terima sebagai watermark baru
4. Kalau ada page yang gagal, **jangan** majukan watermark — ulangi dari cursor terakhir yang sukses

### ⚠️ Status implementasi (penting)

- **`sync_updated_at` sudah benar nilainya**, dihitung on-the-fly dengan rumus di atas. VOC-CS-02 akan memateralisasi jadi kolom terindeks dengan **nilai yang identik** — jadi nilainya tidak akan berubah, dan parser kalian aman dibuat sekarang.
- **Cursor saat ini masih placeholder** (offset sederhana, belum ditandatangani, urutan berbasis `updated_at`). Bentuk respons sudah final, tapi **jangan andalkan stabilitas cursor lintas insert bersamaan sampai CS-02 selesai.** CS-02 mengganti dengan keyset bertanda tangan atas `(sync_updated_at, id)` plus `checkpoint_cursor` di halaman terakhir.
- Karena cursor opaque, penggantian itu **tidak mengubah contract ini** — asalkan kalian tidak mem-parse isinya.

---

## 4. Autentikasi

```
Authorization: Bearer <service-token>
```

Token bersifat per-company; **tenant ditentukan oleh token**, itu sebabnya `company_id` tidak ada sebagai parameter maupun field. Scope yang dibutuhkan: `reviews:read`.

### ⚠️ Belum aktif

Penerbitan dan verifikasi service token adalah **VOC-CS-03** dan belum selesai. Sampai itu landing, endpoint ini menjawab:

```json
{"error":{"code":"SERVICE_AUTH_NOT_READY","message":"Service token authentication is not configured yet (VOC-CS-03).","request_id":"..."}}
```

dengan status **`503`**. Endpoint sengaja **ditutup total**, bukan dibuka tanpa auth — data review satu tenant tidak boleh terekspos walau sesaat. Bentuk request/response di dokumen ini sudah final, jadi OneBox bisa membangun parser sekarang memakai fixture, tanpa menunggu CS-03.

---

## 5. Error

Semua error memakai envelope yang sama:

```json
{"error": {"code": "INVALID_CURSOR", "message": "Cursor is invalid.", "request_id": "uuid"}}
```

| Status | Code | Kapan |
|---|---|---|
| `400` | `INVALID_PARAMETER` | `limit` di luar 1..200, `updated_since` bukan ISO UTC, tipe parameter salah |
| `400` | `INVALID_CURSOR` | Cursor rusak/dipalsukan |
| `400` | `INVALID_CURSOR_CONTEXT` | Cursor digabung dengan `updated_since`, atau `location_id` berubah di tengah paginasi |
| `401` | `INVALID_SERVICE_TOKEN` | Token malformed/tidak dikenal/kedaluwarsa/dicabut *(aktif setelah CS-03)* |
| `403` | `INSUFFICIENT_SCOPE` | Token tidak punya `reviews:read` |
| `404` | `LOCATION_NOT_FOUND` | `location_id` tidak ada **atau** milik tenant lain (sengaja tidak dibedakan) |
| `500` | `INTERNAL_ERROR` | Kesalahan server |
| `503` | `SERVICE_AUTH_NOT_READY` | CS-03 belum selesai *(sementara)* |

Endpoint ini **tidak pernah** mengembalikan `422` — validasi parameter selalu jadi `400` dengan envelope di atas.

---

## 6. Smoke test

Setelah CS-03 menerbitkan token:

```bash
curl -sS "http://localhost:8000/api/integration/v1/reviews?limit=3" \
  -H "Authorization: Bearer <SERVICE_TOKEN>" \
  -H "X-Request-ID: voc-contract-smoke"
```

---

## 7. Open questions untuk OneBox

1. **`keywords` / flag boolean saat `analyzed=false`** — kami kirim `[]` dan `false`. Kalau kalian lebih suka `null`, ini waktunya bilang (§2).
2. Butuh field yang belum ada di sini? Penambahan bersifat additive dan aman; ajukan sekarang selagi v1 belum jalan di produksi.

Yang **tidak** perlu didiskusikan lagi: struktur contract, penamaan, dan pemilihan route terpisah — itu sudah diputuskan di VOC-CS-01. Tugas OneBox adalah memvalidasi parser terhadap fixture, bukan memilih ulang strukturnya.
