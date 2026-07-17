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
  - `scriptdb/voc/voc_menu_seed.sql`
  - `scriptdb/voc/voc_full_seed.sql`
  - `scriptdb/voc/reviews_sample.json`

## 1. Seed MENU (biar menu muncul)
```bash
mysql -uroot <db> < scriptdb/voc/voc_menu_seed.sql
```
Env-agnostic (cari sendiri Id header MM + role). Setelah ini menu "Voice of Customer" akan muncul
di sidebar Media Monitoring (setelah hard-reload). **Menu muncul tapi data masih kosong** — lanjut step 2.

## 2. Seed MASTER DATA (Provider, Category, Location, Connection)
> Buka file, **sesuaikan `SET @site := 169;`** dengan SiteId env kamu, lalu jalankan:
```bash
mysql -uroot <db> < scriptdb/voc/voc_full_seed.sql
```
Output terakhir menampilkan **Id Connection** yang dibuat, contoh:
```
conn_hermina_depok  conn_hga_depok  loc_hermina_onebox  loc_hga_onebox
1041                1042            1705                1706
```
**Catat `conn_hermina_depok` & `conn_hga_depok`** — dipakai di step 4.
(Idempotent untuk Provider/Category; Location/Connection **jangan di-run 2x** — nanti dobel.)

## 3. Copy fixture ke /tmp (dibaca provider mode mock)
```bash
cp scriptdb/voc/reviews_sample.json /tmp/voc_reviews_sample.json
```
> `/tmp` di host WSL ter-mount ke `/tmp` container. Catatan: isi `/tmp` hilang saat WSL restart — copy ulang bila perlu.

## 4. INGEST (tarik review → jadi Ticket)
Ganti `<C>` = nama container webapp, `<connH>`/`<connG>` = Connection Id dari step 2.
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

## 5. Dashboard React (butuh vite dev server)
```bash
cd app/react-views
npm install        # butuh Node 20+ — di WSL pakai nvm, JANGAN npm Windows
npm run dev        # vite di localhost:5173
```
> `NODE_ENV=production` di container bikin `react_url()` cari build produksi; karena itu `dashboard.volt`
> import langsung dari `localhost:5173`. Reviews (Volt) TIDAK butuh ini.

## 6. Buka & test
1. Buka Media Monitoring → **hard-reload (Ctrl+Shift+R)** (biar `routes.js` terbaru & menu ke-refresh).
2. Sidebar kiri → **Voice of Customer** → **Reviews** (harus ada tabel) / **Dashboard** (KPI + chart).
3. URL jadi `.../Mediamonitoring/#/voc/dashboard`.

---

## Troubleshooting
| Gejala | Penyebab | Fix |
|---|---|---|
| Menu VoC tidak muncul | belum seed menu / belum hard-reload / role user beda | jalankan step 1, hard-reload; pastikan user punya role yang lihat MM |
| Reviews kosong (0) | belum seed master data / belum ingest | step 2–4 |
| Reviews/Dashboard error "gagal load data" | Connection/site tidak match, atau ProviderId bukan PVD97 | cek Connection ProviderId='PVD97' & SiteId sesuai |
| Dashboard blank / "pastikan vite nyala" | vite dev server mati / node_modules belum install | step 5 |
| `npm run dev` manggil CMD.EXE / UNC error | kepakai npm Windows | pakai Node WSL (nvm), bukan `/mnt/c/...npm` |

## Untuk produksi (nanti)
- Seed menu/master data → jadikan **migration** resmi.
- **Production build** react-views (`npm run build`) + `NODE_ENV != production` + pakai `react_url()`.
- Set Connection ke **live** (`Options.mock=false` + `Url`/`UserId`/`Password` creds service user VoC) — ganti ingest mock jadi pull API asli.
