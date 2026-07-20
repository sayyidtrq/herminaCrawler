# VoC di OneBox — Panduan Setup untuk Dev Lain

> Biar dev lain punya menu **Voice of Customer** DI Media Monitoring, lengkap dengan datanya.
> Semua contoh pakai SiteId 169 & DB `onecloud` — sesuaikan dengan env kamu.

## Ringkasan alur
Kode ikut git. **Data/menu = baris DB** (tidak ikut git) → harus di-seed. Data review = hasil **ingest** (bukan seed manual).

```
git pull  →  seed menu  →  seed master data  →  copy fixture  →  ingest  →  (React) npm+vite  →  hard-reload
```

---

## 0. Prasyarat
- Sudah `git pull` (dapat `VocController.php`, `app/views/Voc/`, `app/react-views/src/features/voc/`, `public/js/routes.js`).
- Tahu **nama DB** OneBox kamu (contoh: `onecloud`).
- Tahu **nama container webapp**: `docker ps --format '{{.Names}}' | grep webapp`.
- File seed & fixture ada di **repo OneBox** folder `scriptdb/voc/` (ikut `git pull`):
  - `scriptdb/voc/voc_setup_all.sql`  ← menu + master data (satu file, idempotent)
  - `scriptdb/voc/reviews_sample.json`

## 1. Seed SEMUA (menu + master data) — satu file
> Buka file, **sesuaikan `SET @site := 169;`** dengan SiteId env kamu, lalu jalankan:
```bash
mysql -uroot <db> < scriptdb/voc/voc_setup_all.sql
```
Ini nge-seed **menu VoC** (di sidebar Media Monitoring, env-agnostic — cari sendiri Id header MM + role)
**+ master data** (Provider PVD97, Category, Location, Connection). **Idempotent** — aman di-run ulang, tidak dobel.

Output terakhir menampilkan **Id Connection** yang dibuat, contoh:
```
conn_hermina_depok  conn_hga_depok  loc_hermina_onebox  loc_hga_onebox  mm_header_id
1041                1042            1705                1706            254
```
**Catat `conn_hermina_depok` & `conn_hga_depok`** — dipakai di step 3 (ingest).
Setelah ini **menu muncul** (hard-reload). **Data terisi setelah INGEST** (step 3).

## 2. Copy fixture ke /tmp (dibaca provider mode mock)
```bash
cp scriptdb/voc/reviews_sample.json /tmp/voc_reviews_sample.json
```
> `/tmp` di host WSL ter-mount ke `/tmp` container. Catatan: isi `/tmp` hilang saat WSL restart — copy ulang bila perlu.

## 3. INGEST (tarik review → jadi Ticket)
Ganti `<C>` = nama container webapp, `<connH>`/`<connG>` = Connection Id dari step 1.
```bash
C=$(docker ps -qf name=<webapp>)

# tarik review (mock) per connection
docker exec $C php app/bootstrap.php voice_of_customer_system receive <connH>
docker exec $C php app/bootstrap.php voice_of_customer_system receive <connG>

# proses jadi Ticket (kalau worker queue tidak jalan di dev) + apply analisa
docker exec $C php app/bootstrap.php voice_of_customer_system processpending <connH>
docker exec $C php app/bootstrap.php voice_of_customer_system processpending <connG>
docker exec $C php app/bootstrap.php voice_of_customer_system analysis <connH>
docker exec $C php app/bootstrap.php voice_of_customer_system analysis <connG>
```
Cek: `receive` menampilkan `sync done: fetched=… inserted=…`; `analysis` menampilkan `applyAnalysis: N ticket updated`.
Setelah ini Reviews & Dashboard terisi data.

## 4. (tidak perlu) Vite / Node
> **Semua screen VoC sekarang Volt murni** (termasuk Dashboard). **TIDAK perlu** `npm install` /
> vite / Node sama sekali. Cukup PHP + DB. (Dulu Dashboard pakai React embed; sudah di-rebuild ke Volt
> supaya robust & konsisten — tidak lagi tergantung `localhost:5173`.)

## 5. Buka & test
1. Buka Media Monitoring → **hard-reload (Ctrl+Shift+R)** (biar `routes.js` terbaru & menu ke-refresh).
2. Sidebar kiri → **Voice of Customer** → buka Dashboard / Reviews / Locations / Competitors / Fetch Jobs / Analysis.
3. URL jadi `.../Mediamonitoring/#/voc/<page>`.

---

## Troubleshooting
| Gejala | Penyebab | Fix |
|---|---|---|
| Menu VoC tidak muncul | belum seed / belum hard-reload / role user beda | jalankan step 1, hard-reload; pastikan user punya role yang lihat MM |
| Reviews kosong (0) | belum ingest | step 2–3 (copy fixture + ingest) |
| Semua screen "gagal load data" | Connection/site tidak match, atau ProviderId bukan PVD97 | cek Connection ProviderId='PVD97' & SiteId sesuai |
| Screen blank total | partial gagal render / `routes.js` belum ke-reload | hard-reload (Ctrl+Shift+R); cek Console |

## Untuk produksi (nanti)
- Seed menu/master data → jadikan **migration** resmi.
- Set Connection ke **live** (`Options.mock=false` + `Url`/`UserId`/`Password` creds service user VoC) — ganti ingest mock jadi pull API asli.
