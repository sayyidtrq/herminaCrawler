# Cara Jalanin Backend via Docker (Quickstart)

Panduan singkat sehari-hari. Untuk runbook deployment lengkap ke server (reverse proxy, integrasi OneBox, troubleshooting), lihat `DOCKER_BACKEND_DEPLOYMENT_GUIDE.md`.

## Prasyarat

- Docker Desktop (Windows/Mac) atau Docker Engine + Compose plugin (Linux) sudah jalan.
- File `.env` ada di root repo (`cp .env.example .env` lalu sesuaikan).

## Jalanin

```sh
docker compose up -d
```

Itu saja. Yang terjadi otomatis:

1. Postgres 16 start, ditunggu sampai benar-benar siap (healthcheck `pg_isready`).
2. Image api di-build kalau belum ada.
3. Container api start → `entrypoint.sh` jalankan `alembic upgrade head` (idempotent, aman diulang) → uvicorn start di port 8000.

Cek status:

```sh
docker compose ps          # dua-duanya harus "healthy"
docker compose logs -f api # lihat log migration + server
```

Smoke test:

```sh
curl http://localhost:8000/api/health
# {"status":"ok","app":"Hermina Review Intelligence","env":"local","database":{"ok":true,"message":"OK"}}
```

API docs: http://localhost:8000/api/docs

## Perintah Umum

```sh
docker compose up -d            # start (build otomatis kalau perlu)
docker compose build api        # rebuild image setelah ubah kode backend
docker compose restart api      # restart api saja
docker compose logs -f api      # tail log
docker compose down             # stop semua (data Postgres AWET di volume)
docker compose down -v          # stop + HAPUS data Postgres (fresh start)
docker compose exec api python -m alembic current   # cek posisi migration
```

## Test Flow Lengkap (register → login → hit API)

```sh
# register company + admin
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Test Co","admin_email":"test@example.com","admin_password":"testpass1"}'

# login, ambil token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass1"

# pakai token
curl http://localhost:8000/api/locations -H "Authorization: Bearer <access_token>"
```

## Hal yang Sering Bikin Bingung

**"Gua ubah DATABASE_URL di .env kok gak ngefek?"**
`docker-compose.yml` sengaja men-set `DATABASE_URL` di blok `environment:` (menang atas `env_file:`) supaya container api selalu nunjuk ke Postgres bawaan compose (`db:5432`). `.env` lokal lo (yang nunjuk Supabase) tetap dipakai kalau lo jalanin backend TANPA Docker (`python -m uvicorn ...`).

**Mau pakai Supabase/managed Postgres dari dalam Docker?**
Hapus/override baris `environment.DATABASE_URL` di compose, set `DATABASE_URL` di `.env` ke URL Supabase, lalu `docker compose up -d api` (tanpa service `db`).

**`REVIEW_SOURCE_MODE=selenium` di container?**
Tidak didukung — Selenium butuh Chrome profile yang di-login manual (GUI). Di container pakai `mock` atau `google_places`. Config selenium di `.env` tidak bikin container error selama fetch selenium tidak dipanggil.

**Container api restart terus?**
`docker compose logs api` — hampir selalu antara: DATABASE_URL salah, migration gagal, atau entrypoint.sh kena CRLF (jangan save ulang file itu pakai editor yang maksa CRLF; sudah dikunci via `.gitattributes`).

**Frontend?**
FE tidak ikut Docker ini. Jalanin terpisah seperti biasa (`npm run dev` di folder `hermina-crawler-fe`), dia nunjuk ke `http://localhost:8000` yang sekarang dilayani container.
