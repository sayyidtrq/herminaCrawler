# API Design — Hermina Review Intelligence

> Dokumen desain API terpusat untuk backend crawler Hermina. Menggabungkan & merapikan
> dokumentasi API yang sebelumnya tersebar di `existing-system.md §6`, `implementation-plan.md §4`,
> dan `system-design-v2.md §6`. **Inilah sumber acuan tunggal (single source of truth) untuk API.**
>
> Versi API: `0.1.0` · Base path: `/api` · Diverifikasi dari kode di `apps/api/` · Update: 2026-07-06
>
> Dokumen terkait: kesiapan integrasi Onebox → [../information.md](../information.md) · penjelasan folder → [../apps.md](../apps.md)

---

## Daftar Isi
1. [Prinsip & Konvensi](#1-prinsip--konvensi)
2. [Autentikasi](#2-autentikasi)
3. [Format Umum (Envelope, Error, Pagination)](#3-format-umum)
4. [Referensi Endpoint](#4-referensi-endpoint)
   - [4.1 Health](#41-health) · [4.2 Auth](#42-auth) · [4.3 Locations](#43-locations)
   - [4.4 Reviews](#44-reviews) · [4.5 Dashboard](#45-dashboard) · [4.6 Analysis](#46-analysis)
   - [4.7 Fetch Jobs](#47-fetch-jobs) · [4.8 Fetch Logs](#48-fetch-logs) · [4.9 Pipeline](#49-pipeline)
   - [4.10 Exports](#410-exports) · [4.11 Competitors](#411-competitors) · [4.12 Places](#412-places) · [4.13 Settings](#413-settings)
5. [Objek Data (Skema)](#5-objek-data-skema)
6. [Catatan Desain & Rencana Perubahan](#6-catatan-desain--rencana-perubahan)

---

## 1. Prinsip & Konvensi

Referensi kode: [apps/api/main.py](../apps/api/main.py)

- **Arsitektur:** API adalah *wrapper* tipis di atas core service (`app/services/*`). Router **tidak** memuat logika bisnis — hanya validasi input, auth, dan serialisasi. (lihat prinsip di `implementation-plan.md`: *"Jangan rewrite core logic. Bungkus service yang sudah ada menjadi API."*)
- **Base URL:** semua endpoint berprefiks `/api`.
- **Multi-tenant:** setiap request terautentikasi otomatis di-scope ke `company_id` milik token. Tenant tidak bisa melihat data tenant lain.
- **Dokumentasi live (auto-generate FastAPI):**
  - Swagger UI: **`/api/docs`**
  - ReDoc: **`/api/redoc`**
  - OpenAPI JSON: **`/api/openapi.json`** ← file inilah yang dikirim ke tim Onebox
- **Format tanggal:** ISO 8601 dengan timezone (mis. `2026-07-01T02:00:00+07:00`).
- **CORS:** saat ini hanya `http://localhost:3000` & `http://127.0.0.1:3000` (perlu ditambah origin produksi).

---

## 2. Autentikasi

Referensi kode: [apps/api/app_api/dependencies.py](../apps/api/app_api/dependencies.py), [routers/auth.py](../apps/api/app_api/routers/auth.py)

- **Skema:** JWT Bearer (OAuth2 Password flow).
- **Header wajib** di semua endpoint kecuali `/health`, `/auth/register`, `/auth/login`:
  ```
  Authorization: Bearer <access_token>
  ```
- **Algoritma:** HS256 · **Masa aktif:** 7 hari · **Secret:** env `JWT_SECRET_KEY`.
- **Isi payload token saat ini:** `{ "sub": "<user_id>", "exp": <unix_ts> }`
  - ⚠️ `company_id` **belum** ada di token; di-resolve dari DB via `user.company_id`. (Rencana perubahan: §6)
- **Cara dapat token:** `POST /api/auth/login` (form `username`+`password`).

Alur pemakaian:
```
login → simpan access_token → sertakan di header Authorization tiap request
       → server decode → dapat user → dapat company_id → scope query
       → saat 401 (expired), login ulang
```

> Untuk integrasi Onebox (server-to-server) direncanakan penambahan auth machine-to-machine (client-credentials / API key) — detail di [../information.md §2](../information.md).

---

## 3. Format Umum

### 3.1 Envelope list
Endpoint yang mengembalikan koleksi memakai pola:
```json
{ "items": [ ... ], "total": 132 }
```
Khusus endpoint paginated (`/reviews`) menambah:
```json
{ "items": [...], "total": 132, "page": 1, "page_size": 20, "total_pages": 7 }
```

### 3.2 Format error
Referensi kode: [errors.py](../apps/api/app_api/errors.py)
```json
{ "error": { "code": "review_not_found", "message": "Review not found." } }
```
| Status | Kapan |
|---|---|
| `400` | Input tidak valid / pesan error umum |
| `401` | Token hilang/invalid/expired |
| `403` | Fitur tidak diaktifkan untuk company (AI / kompetitor) |
| `404` | Resource tidak ditemukan (pesan mengandung "not found") |
| `422` | Validasi body Pydantic gagal (otomatis dari FastAPI) |
| `500/502` | Error server / gangguan API pihak ketiga (Google) |

### 3.3 Pagination
Offset-based via `page` (mulai 1) & `page_size` (default 20, maks 200). *(Rencana: tambah delta sync `updated_since` + cursor — §6.)*

---

## 4. Referensi Endpoint

Legenda kolom **Auth**: 🔓 publik · 🔒 butuh Bearer token · 🔐 butuh Bearer + flag entitlement aktif.

### 4.1 Health
Referensi: [routers/health.py](../apps/api/app_api/routers/health.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/health` | 🔓 | Status service. |

`200`:
```json
{ "status": "ok", "app": "Hermina Review Intelligence", "env": "local" }
```

### 4.2 Auth
Referensi: [routers/auth.py](../apps/api/app_api/routers/auth.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/auth/register` | 🔓 | Daftar company + user admin. |
| POST | `/api/auth/login` | 🔓 | Login → JWT. Body **form-urlencoded**. |
| GET | `/api/auth/me` | 🔒 | Profil user + info company. |

**POST `/api/auth/register`** — body JSON:
```json
{
  "company_name": "RS Hermina Group",
  "admin_email": "admin@hermina.co.id",
  "admin_password": "hermina123",
  "admin_full_name": "Admin Pusat",
  "ai_enable_flag": true,
  "total_enable_review": 300,
  "analyze_competitor_flag": false
}
```
`200` → objek [User](#user):
```json
{
  "id": 1, "email": "admin@hermina.co.id", "full_name": "Admin Pusat",
  "company_id": 1, "company_name": "RS Hermina Group",
  "ai_enable_flag": true, "total_enable_review": 300, "analyze_competitor_flag": false
}
```
> Aturan password: min 8 karakter, ada huruf & angka, maks 72 byte.

**POST `/api/auth/login`** — body `application/x-www-form-urlencoded`: `username=<email>&password=<password>`
```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer" }
```

### 4.3 Locations
Referensi: [routers/locations.py](../apps/api/app_api/routers/locations.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/locations` | 🔒 | List lokasi (query `active_only`). |
| POST | `/api/locations` | 🔒 | Tambah lokasi. |
| GET | `/api/locations/{id}` | 🔒 | Detail lokasi. |
| PATCH | `/api/locations/{id}` | 🔒 | Update sebagian field. |
| POST | `/api/locations/{id}/toggle-active` | 🔒 | Aktif/nonaktifkan. |
| DELETE | `/api/locations/{id}` | 🔒 | Hapus lokasi. |

**GET `/api/locations`** `200`:
```json
{ "items": [ /* objek Location */ ], "total": 12 }
```
**POST `/api/locations`** — body (field wajib: `branch_name`, `external_place_id`):
```json
{
  "hospital_name": "Hermina", "branch_name": "Hermina Depok",
  "city": "Depok", "address": "Jl. Siliwangi No.50",
  "latitude": -6.401, "longitude": 106.797,
  "source": "selenium", "external_place_id": "ChIJ....",
  "google_maps_url": "https://maps.google.com/...",
  "target_review_count": 200, "is_active": true
}
```
`200` → objek [Location](#location).

### 4.4 Reviews
Referensi: [routers/reviews.py](../apps/api/app_api/routers/reviews.py) · **Endpoint pull utama untuk Onebox.**

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/reviews` | 🔒 | List review + insight AI menempel. |
| GET | `/api/reviews/{id}` | 🔒 | Detail satu review. |

**GET `/api/reviews`** — query params:

| Param | Tipe | Default | Keterangan |
|---|---|---|---|
| `page` | int ≥1 | 1 | Halaman. |
| `page_size` | int 1–200 | 20 | Jumlah per halaman. |
| `location_id` | int | — | Filter lokasi. |
| `rating` | int 1–5 | — | Filter rating. |
| `sentiment` | string | — | `positive`\|`neutral`\|`negative`\|`mixed`. |
| `keyword` | string | — | Cari di teks review. |
| `latest_first` | bool | false | Urut terbaru dulu. |
| `include_raw` | bool | false | Sertakan `raw_payload`. |
| `date_preset` | string | — | Preset rentang tanggal. |
| `date_from` / `date_to` | datetime | — | Rentang custom (ISO 8601). |

`200`:
```json
{
  "items": [
    {
      "id": 1024, "location_id": 5, "location": "Hermina Depok",
      "source": "selenium_google_maps", "external_place_id": "ChIJ...",
      "external_review_id": "Ch9...", "reviewer_name": "Budi S.",
      "reviewer_profile_url": null, "reviewer_photo_url": null,
      "reviewer_local_guide_level": null, "reviewer_total_reviews": 12,
      "rating": 2, "review_text": "Antrian farmasi lama sekali.",
      "review_time": "2026-06-30T08:12:00+07:00", "review_relative_time": "seminggu lalu",
      "review_language": "id", "language": "id", "like_count": 3,
      "owner_response_text": null, "owner_response_time": null,
      "scraped_at": "2026-07-01T02:00:00+07:00", "review_hash": "a1b2...",
      "created_at": "2026-07-01T02:00:05+07:00",
      "analyzed": true, "analysis_id": 900,
      "sentiment": "negative", "sentiment_score": -0.82,
      "issue_category": "waktu_tunggu", "urgency": "high",
      "summary": "Keluhan antrian farmasi lama.",
      "recommended_action": "Tinjau SLA layanan farmasi.",
      "keywords": ["antrian", "farmasi"],
      "is_potential_viral": false, "is_patient_safety_issue": false
    }
  ],
  "total": 132, "page": 1, "page_size": 20, "total_pages": 7
}
```
> `raw_payload` disembunyikan kecuali `include_raw=true` atau setting `SHOW_RAW_PAYLOAD=true`.

### 4.5 Dashboard
Referensi: [routers/dashboard.py](../apps/api/app_api/routers/dashboard.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/dashboard/overview` | 🔒 | Ringkasan agregat seluruh company. |
| GET | `/api/dashboard/locations/{id}` | 🔒 | Ringkasan per lokasi. |
| GET | `/api/dashboard/critical-issues` | 🔒 | Daftar isu kritis. |
| GET | `/api/dashboard/negative-reviews` | 🔒 | Daftar review negatif. |

**GET `/api/dashboard/overview`** `200`:
```json
{
  "total_locations": 12, "total_reviews": 3480,
  "analyzed_reviews": 3120, "pending_analysis": 360,
  "sentiments": { "positive": 1900, "neutral": 500, "negative": 700, "mixed": 20, "unknown": 360 },
  "top_issues": [ { "issue_category": "waktu_tunggu", "count": 210 } ],
  "critical_issues": 34,
  "latest_fetch": "2026-07-01T02:04:10+07:00"
}
```
**GET `/api/dashboard/locations/{id}`** `200`:
```json
{
  "location_id": 5, "location_name": "Hermina Depok",
  "total_reviews": 320, "average_rating": 3.8,
  "sentiments": { "positive": 180, "neutral": 40, "negative": 90, "mixed": 5, "unknown": 5 },
  "top_issues": [ { "issue_category": "waktu_tunggu", "count": 45 } ],
  "critical_issues": 6, "negative_examples": [ /* ... */ ], "management_focus": [ /* ... */ ]
}
```
**GET `/api/dashboard/critical-issues`** & **`/negative-reviews`** `200`:
```json
{ "items": [ { "location": "Hermina Depok", "rating": 1, "review_text": "...", "sentiment": "negative", "issue_category": "patient_safety", "urgency": "high", "recommended_action": "..." } ], "total": 34 }
```

### 4.6 Analysis
Referensi: [routers/analysis.py](../apps/api/app_api/routers/analysis.py) · 🔐 **butuh `ai_enable_flag` aktif** (else `403`).

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/analysis/pending` | 🔐 | Analisis review yang belum dianalisis. |
| POST | `/api/analysis/locations/{id}/rerun` | 🔐 | Ulang analisis 1 lokasi. |
| POST | `/api/analysis/reviews/{id}/rerun` | 🔐 | Ulang analisis 1 review. |

**POST `/api/analysis/pending`** — body: `{ "location_id": 5, "rating": null }`
`200`:
```json
{
  "total": 40, "success": 38, "failed": 1, "skipped_empty": 1,
  "sentiments": { "positive": 12, "neutral": 6, "negative": 18, "mixed": 2, "unknown": 0 },
  "errors": [ { "review_id": 1050, "error": "..." } ]
}
```

### 4.7 Fetch Jobs
Referensi: [routers/fetch_jobs.py](../apps/api/app_api/routers/fetch_jobs.py) · ⚠️ **berjalan sinkron/blocking** (crawling bisa lama).

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/fetch-jobs` | 🔒 | Trigger crawling 1 lokasi. |
| POST | `/api/fetch-jobs/all-active` | 🔒 | Trigger crawling semua lokasi aktif. |

**POST `/api/fetch-jobs`** — body:
```json
{ "location_id": 5, "source": "selenium", "target_review_count": 200, "dry_run": false, "date_preset": null, "date_from": null, "date_to": null }
```
`200`:
```json
{
  "location_id": 5, "location_name": "Hermina Depok", "source": "selenium_google_maps",
  "status": "success",
  "total_fetched": 200, "total_inserted": 25, "total_duplicate": 175, "total_failed": 0,
  "total_skipped_out_of_range": 0, "error_message": null, "metadata": { "target_review_count": 200 }
}
```
> `status`: `success` \| `partial_success` \| `failed` \| `dry_run`. Kuota `target_review_count` divalidasi terhadap plan company (`400` jika melebihi).

### 4.8 Fetch Logs
Referensi: [routers/fetch_logs.py](../apps/api/app_api/routers/fetch_logs.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/fetch-logs` | 🔒 | List log (query `location_id`, `failed_only`, `limit` 1–200). |
| GET | `/api/fetch-logs/latest` | 🔒 | Log terakhir. |

**GET `/api/fetch-logs`** `200`:
```json
{
  "items": [
    {
      "id": 55, "location_id": 5, "source": "selenium_google_maps", "status": "success",
      "total_fetched": 200, "total_inserted": 25, "total_duplicate": 175, "total_failed": 0,
      "error_message": null,
      "started_at": "2026-07-01T02:00:00+07:00", "finished_at": "2026-07-01T02:04:10+07:00"
    }
  ],
  "total": 1
}
```

### 4.9 Pipeline
Referensi: [routers/pipeline.py](../apps/api/app_api/routers/pipeline.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/pipeline/location` | 🔒 | Jalankan fetch → analyze → export sekaligus. |

Body:
```json
{ "location_id": 5, "fetch": true, "analyze": true, "export_csv": false, "dry_run": false, "target_review_count": 200, "source": "selenium" }
```
`200` (ringkas): `{ "location_id": 5, "source": "selenium", "status": "success", "steps": { "fetch": {...}, "analysis": {...} } }`

### 4.10 Exports
Referensi: [routers/exports.py](../apps/api/app_api/routers/exports.py) · ⚠️ **mengembalikan path file di server**, bukan konten (lihat gap di §6).

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/exports/reviews/all.csv` | 🔒 | CSV semua review. |
| POST | `/api/exports/reviews/location/{id}.csv` | 🔒 | CSV review 1 lokasi. |
| POST | `/api/exports/analysis-summary.csv` | 🔒 | CSV ringkasan analisis. |
| POST | `/api/exports/raw-reviews.json` | 🔒 | JSON review mentah. |

`200`: `{ "status": "success", "filename": "reviews_all_20260706.csv", "path": "exports/reviews_all_20260706.csv" }`

### 4.11 Competitors
Referensi: [routers/competitors.py](../apps/api/app_api/routers/competitors.py) · 🔐 **butuh `analyze_competitor_flag` aktif** (else `403`).

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/competitors` | 🔐 | List kompetitor. |
| POST | `/api/competitors` | 🔐 | Tambah kompetitor. |
| GET | `/api/competitors/{id}` | 🔐 | Detail. |
| PATCH | `/api/competitors/{id}` | 🔐 | Update sebagian. |
| POST | `/api/competitors/{id}/toggle-active` | 🔐 | Aktif/nonaktif. |
| DELETE | `/api/competitors/{id}` | 🔐 | Hapus. |

Struktur objek mirip [Location](#location) tapi memakai `name` (bukan `hospital_name`/`branch_name`).

### 4.12 Places
Referensi: [routers/places.py](../apps/api/app_api/routers/places.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/places/resolve` | 🔒 | Resolve lat/lng → Google `place_id`. |

Query: `lat`, `lng` (wajib). `200`:
```json
{ "external_place_id": "ChIJ...", "hospital_name": "RS Hermina Depok", "address": "Jl. ...", "google_maps_url": "https://maps.google.com/..." }
```
> Butuh `GOOGLE_MAPS_API_KEY` di server (else `500`).

### 4.13 Settings
Referensi: [routers/settings.py](../apps/api/app_api/routers/settings.py)

| Method | Path | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/settings` | 🔒 | Config non-rahasia + status masking API key. |
| GET | `/api/settings/database-check` | 🔒 | Cek koneksi DB. |

> API key selalu ditampilkan ter-*masking*; field `*_configured` menandakan ada/tidaknya key.

---

## 5. Objek Data (Skema)

Referensi model: [app/db/models.py](../app/db/models.py) · serializer: [serializers.py](../apps/api/app_api/serializers.py)

### User
| Field | Tipe | Ket |
|---|---|---|
| id | int | |
| email | string | |
| full_name | string \| null | |
| company_id | int | tenant |
| company_name | string | |
| ai_enable_flag | bool | akses fitur AI |
| total_enable_review | int | kuota review |
| analyze_competitor_flag | bool | akses fitur kompetitor |

### Location
`id, hospital_name, branch_name, city, address, latitude, longitude, source, external_place_id, google_maps_url, google_reviews_url, target_review_count (1–300), is_active, created_at, updated_at`

### Review (+ Analysis embedded)
Field review: `id, location_id, location, source, external_place_id, external_review_id, reviewer_name, reviewer_profile_url, reviewer_photo_url, reviewer_local_guide_level, reviewer_total_reviews, rating, review_text, review_time, review_relative_time, review_language, language, like_count, owner_response_text, owner_response_time, scraped_at, raw_payload, review_hash, created_at`
Field analisis (menempel): `analyzed (bool), analysis_id, sentiment, sentiment_score, issue_category, urgency, summary, recommended_action, keywords[], is_potential_viral, is_patient_safety_issue`

### FetchLog
`id, location_id, source, status, total_fetched, total_inserted, total_duplicate, total_failed, error_message, started_at, finished_at`

---

## 6. Catatan Desain & Rencana Perubahan

Poin-poin ini diringkas dari audit kesiapan integrasi Onebox ([../information.md](../information.md)). Perlu dikerjakan sebelum handoff API ke Onebox:

| Prioritas | Rencana | Alasan |
|---|---|---|
| 🔴 | Tambah **`company_id` ke payload JWT** | Flow Onebox butuh token bawa user_id + company_id. |
| 🔴 | Tambah **auth machine-to-machine** (`POST /api/auth/token`, client-credentials/API key) | Onebox adalah service, tak boleh pakai password user. |
| 🔴 | Wajibkan **`JWT_SECRET_KEY`** dari env (hapus default hardcoded) | Keamanan token. |
| 🔴 | Tambah **`GET /api/analysis`** (list insight mandiri + filter) | Sekarang insight hanya nempel di reviews / dashboard agregat. |
| 🔴 | Tambah **delta sync** `updated_since` + cursor pagination | Pull berkala harus efisien (hanya data baru/berubah). |
| 🟠 | Tambah **`response_model` Pydantic** di tiap endpoint | Agar `/api/openapi.json` punya schema response lengkap. |
| 🟠 | Perbaiki **exports** agar konten bisa di-download via API | Sekarang balikin path file server, tak terjangkau Onebox. |
| 🟠 | Pertimbangkan **job async + polling** untuk fetch/analysis | Endpoint sinkron rawan timeout saat crawling lama. |
| 🟢 | Rate limiting, refresh token, sesuaikan CORS produksi | Robustness & keamanan. |

---
*Diverifikasi langsung dari router FastAPI di `apps/api/app_api/routers/` dan service di `app/services/`.*
