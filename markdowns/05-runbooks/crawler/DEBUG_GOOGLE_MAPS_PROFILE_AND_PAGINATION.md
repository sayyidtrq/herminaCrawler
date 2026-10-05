# Runbook Debug Google Maps Profile dan Pagination

**Tujuan:** mendiagnosis crawler Selenium Google Maps yang hanya membaca lima
review, gagal menemukan review container, atau terlihat selesai padahal target
belum terpenuhi.

**Lingkup:** Crawler Service dev, staging, dan production. Runbook ini tidak
menghapus data review, tidak menghapus volume database, dan tidak mengotomasi
login Google.

**Prinsip utama:** API health bukan crawler readiness. Avatar pada browser dan
nama cookie autentikasi juga bukan bukti bahwa Google mengizinkan pagination.
Bukti minimum adalah probe DOM read-only yang melewati lima card dan smoke crawl
target 10 yang menghasilkan metrik yang dapat diaudit.

## 1. Gejala dan arti awal

| Gejala | Arti paling mungkin | Tindakan pertama |
|---|---|---|
| Lima card lalu `no_more_reviews` atau `no_new_review_cards` | Login wall, automation restriction, atau pagination tidak bergerak | Jalankan probe read-only; jangan menganggap daftar selesai |
| `Review container was not found` | Profile/proxy/URL/selector membuat halaman berbeda, atau layout Google berubah | Periksa final URL, tab Ulasan, dialog, dan proxy |
| `GOOGLE_AUTH_REQUIRED` | Google secara eksplisit meminta login sebelum load-more | Login manual pada profile yang sama, tutup browser setup, lalu probe ulang |
| `HTTP ERROR 407` | Proxy membutuhkan autentikasi atau konfigurasi proxy tertinggal | Matikan proxy pada environment dan Preferences setelah membuat backup |
| `SessionNotCreatedException` atau `Chrome not reachable` | Profile masih terkunci, browser setup masih hidup, atau versi Chromium tidak cocok | Stop worker, tutup setup browser, bersihkan lock stale, lalu cek image |
| API `/api/health` 200 tetapi crawl gagal | Hanya API dan database yang sehat | Lanjutkan ke probe Google, bukan restart API berulang |
| Batch hijau dengan `scanned < target` | Status batch atau UI menyamarkan partial result | Audit detail job dan `stop_reason`; jangan gunakan badge selesai sebagai bukti |

## 2. Safety gate sebelum debug

Pastikan operator sudah memilih environment yang benar. Jangan menyalin `.env`,
token, password, cookie, screenshot akun, atau output `docker compose config`
ke chat maupun issue publik.

```bash
cd /home/ubuntu/crawlerService
git branch --show-current
git status --short
git log -1 --oneline
docker compose config --services
docker compose ps
```

Simpan hanya fakta non-rahasia berikut:

- branch dan commit image yang diuji;
- nama container API dan worker;
- batch ID dan job ID;
- status, target, scanned, fetched, matched, inserted, duplicate, failed;
- failure code dan stop reason.

Jangan menjalankan `docker compose down -v`, `docker volume prune`, atau
menghapus container PostgreSQL untuk memperbaiki profile browser.

## 3. Bedakan API health dari crawler readiness

```bash
curl -fsS http://127.0.0.1:8000/api/health
docker compose ps
docker compose logs --since=5m api
docker compose logs --since=5m crawl-worker
```

`200 OK` pada health hanya membuktikan API dapat melayani request dan koneksi
database tersedia. Readiness Google harus dibuktikan dengan probe pada bagian
8 dan real crawl pada bagian 9.

## 4. Pastikan branch dan profile volume tidak tertukar

Checkout directory yang berbeda dapat membuat nama project Compose berbeda dan
akhirnya membuat volume Selenium baru. Tetapkan nama volume per environment
secara eksplisit, contohnya:

```env
SELENIUM_PROFILE_VOLUME=crawlerservice-selenium-profile-dev
```

Dev, staging, dan production wajib memakai volume yang berbeda. Jangan
menjalankan dua worker bersamaan memakai volume yang sama.

```bash
docker inspect "$(docker compose ps -q crawl-worker)" \
  --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'
docker volume inspect VOLUME_NAME
```

Mount yang diharapkan pada worker adalah volume environment tersebut ke
`/app/.selenium-profile`.

## 5. Tangkap bukti batch sebelum melakukan retry

Ambil detail batch dari API menggunakan token dengan scope `crawl:read` dan
simpan respons yang sudah disanitasi. Contoh konseptual:

```bash
export CRAWLER_BASE_URL=http://127.0.0.1:8000
export CRAWL_TOKEN='[isi sementara di shell, jangan dicetak]'
export BATCH_ID='[batch-id]'

curl -fsS \
  -H "Authorization: Bearer ${CRAWL_TOKEN}" \
  "${CRAWLER_BASE_URL}/api/integration/v1/crawl-jobs/${BATCH_ID}"
```

Catat minimal:

```text
batch_id, job_id, status, attempts, target_review_count, scan_limit,
scanned, fetched, matched, inserted, duplicate, failed, failure_code,
stop_reason, final_url, sort_applied
```

Untuk target 10, hasil `scanned=5` bukan bukti bahwa lokasi hanya memiliki lima
review. Untuk target 300, `scan_limit` yang besar juga tidak membuktikan Google
memberikan lebih banyak card.

## 6. Periksa proxy pada dua lapisan

Proxy dapat aktif dari environment dan juga dari sisa extension Preferences.
Periksa keduanya tanpa mencetak credential:

```bash
grep -n '^SELENIUM_PROXY_URL=' .env \
  | sed -E 's#=.*#=[redacted]#'

docker run --rm --entrypoint python \
  -v VOLUME_NAME:/profile \
  ghcr.io/sayyidtrq/herminacrawler:latest \
  -c "import json; p='/profile/Default/Preferences'; d=json.load(open(p)); s=d.get('extensions',{}).get('settings',{}); print('extensions='+str(len(s))); print('proxy_pref_nodes='+str(sum(bool(v.get('preferences',{}).get('proxy')) for v in s.values())))"
```

Jika proxy tidak disetujui untuk environment tersebut:

1. Stop worker.
2. Backup `.env` dan `Default/Preferences` dengan nama bertanggal.
3. Kosongkan `SELENIUM_PROXY_URL`.
4. Hapus hanya node `preferences.proxy` melalui parser JSON, bukan dengan
   replace string.
5. Simpan hasil backup dan catat lokasinya.
6. Jalankan probe ulang.

Contoh pembersihan node Preferences yang terstruktur. Ganti `VOLUME_NAME`
dengan volume yang sudah diverifikasi pada bagian 4:

```bash
docker run --rm --entrypoint python \
  -v VOLUME_NAME:/profile \
  ghcr.io/sayyidtrq/herminacrawler:latest \
  -c "import json,shutil; p='/profile/Default/Preferences'; b=p+'.backup-debug'; shutil.copy2(p,b); d=json.load(open(p)); s=d.get('extensions',{}).get('settings',{}); [v.get('preferences',{}).pop('proxy',None) for v in s.values() if isinstance(v,dict) and v.get('preferences',{}).get('proxy') is not None]; json.dump(d,open(p,'w'),ensure_ascii=True,separators=(',',':')); print('preferences_backup='+b); print('proxy_cleanup_complete')"
```

Perintah ini hanya mengubah Preferences. Cookie dan database review tidak
disentuh. Jika backup belum berhasil dibuat, hentikan proses.

## 7. Pulihkan profile dan login manual dengan aman

### 7.1 Stop worker dan lock stale

```bash
docker compose stop crawl-worker
docker run --rm --entrypoint sh \
  -v VOLUME_NAME:/profile \
  ghcr.io/sayyidtrq/herminacrawler:latest \
  -lc 'find /profile -maxdepth 2 \( -name SingletonLock -o -name SingletonCookie -o -name SingletonSocket -o -name DevToolsActivePort \) -print'
```

Hanya setelah setup browser dipastikan sudah tertutup, hapus file lock stale:

```bash
docker run --rm --entrypoint sh \
  -v VOLUME_NAME:/profile \
  ghcr.io/sayyidtrq/herminacrawler:latest \
  -lc 'find /profile -maxdepth 2 \( -name SingletonLock -o -name SingletonCookie -o -name SingletonSocket -o -name DevToolsActivePort \) -print -delete'
```

### 7.2 Jalankan browser setup pada volume yang sama

Gunakan bind port localhost saja. Jangan expose port setup ke jaringan kantor
atau internet.

```bash
docker rm -f voc-chromium-profile-setup 2>/dev/null || true
docker run -d \
  --name voc-chromium-profile-setup \
  --shm-size=1g \
  --security-opt seccomp=unconfined \
  -e PUID=1000 -e PGID=1000 -e TZ=Asia/Jakarta \
  -e CHROME_CLI="/config/.config/chromium https://www.google.com/maps" \
  -p 127.0.0.1:3000:3000 -p 127.0.0.1:3001:3001 \
  -v VOLUME_NAME:/config/.config/chromium \
  lscr.io/linuxserver/chromium:version-b0ddd401
```

Buka tunnel dari laptop:

```bash
ssh -L 3000:127.0.0.1:3000 ubuntu@SERVER_IP
```

Di browser setup:

1. Login manual ke akun Google operasional yang disetujui.
2. Buka URL Place ID yang sama dengan master location.
3. Buka tab `Ulasan`.
4. Pilih urutan `Terbaru`.
5. Klik load-more atau scroll sampai lebih dari lima card terlihat.
6. Pastikan bukan halaman login, consent, CAPTCHA, atau error 407.
7. Tutup seluruh window browser setup.

Jangan menilai login berhasil hanya dari avatar. Lanjutkan ke verifikasi cookie
dan probe karena Chrome setup dan UC Selenium dapat memiliki perilaku berbeda.

### 7.3 Audit sesi tanpa membocorkan cookie

Audit hanya nama cookie dan jumlahnya:

```bash
docker run --rm --entrypoint python \
  -v VOLUME_NAME:/profile \
  ghcr.io/sayyidtrq/herminacrawler:latest \
  -c "import sqlite3; c=sqlite3.connect('file:/profile/Default/Cookies?mode=ro',uri=True); names={'SID','HSID','SSID','APISID','SAPISID','__Secure-1PSID','__Secure-3PSID','__Secure-1PAPISID','__Secure-3PAPISID'}; rows=c.execute(\"select distinct name from cookies where host_key like '%google.com'\").fetchall(); found=sorted({n for n, in rows if n in names}); print('auth_cookie_names='+','.join(found)); print('auth_cookie_count='+str(len(found)))"
```

Tidak ada nilai cookie yang boleh dicetak, disalin, atau dikirim ke chat.
Jumlah cookie yang positif tetap belum menggantikan probe.

## 8. Jalankan probe DOM read-only

Probe harus memakai URL Place ID produksi yang benar, bukan URL contoh atau
query nama yang tidak cocok. Contoh URL:

```text
https://www.google.com/maps/search/?api=1&query=BRANCH_NAME&query_place_id=PLACE_ID&hl=id
```

Jalankan setelah worker dihentikan agar profile tidak terkunci:

```bash
docker compose run --rm --no-deps \
  -e SELENIUM_HEADLESS=true crawl-worker \
  python -m scripts.diagnose_google_maps_runtime \
  'FULL_GOOGLE_MAPS_URL' \
  --advances 2 --wait-seconds 3 \
  --screenshot /tmp/google-maps-runtime-probe.png
```

Output yang diterima:

- final URL mengarah ke tempat yang benar;
- tab `Ulasan` aktif;
- `navigator_webdriver` bernilai `null` atau `undefined`;
- card awal terbaca;
- setelah advance, card count bertambah melewati lima;
- tidak ada `GOOGLE_AUTH_REQUIRED`, `HTTP 407`, atau `Review container was
  not found`.

Jika probe gagal, jangan lanjut ke smoke crawl. Simpan failure code dan
screenshot di lokasi internal yang aksesnya terbatas.

## 9. Smoke test API target 10

Gunakan service token sementara dengan scope `reviews:read`, `crawl:enqueue`,
dan `crawl:read`. Verifikasi `whoami` menghasilkan company yang sesuai dengan
environment sebelum enqueue.

```bash
docker compose exec -T api python -m scripts.manage_api_client issue \
  --company-id COMPANY_ID \
  --name p0-smoke-$(date +%s) \
  --scope reviews:read \
  --scope crawl:enqueue \
  --scope crawl:read \
  --expires-days 1 </dev/null
```

Simpan token hanya di variable shell yang tidak dicetak. Lakukan:

```bash
curl -fsS -H "Authorization: Bearer ${CRAWL_TOKEN}" \
  http://127.0.0.1:8000/api/integration/v1/whoami

curl -fsS -X POST http://127.0.0.1:8000/api/integration/v1/crawl-jobs \
  -H "Authorization: Bearer ${CRAWL_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: p0-smoke-$(date +%s)-$RANDOM" \
  --data '{"slot":"p0-smoke","targets":[{"kind":"location","onebox_location_id":LOCATION_ID,"target_review_count":10,"sort_by":"newest"}]}'
```

Response menggunakan envelope `data`; ambil `data.batch_id`, bukan hanya
`batch_id` pada root. Poll detail batch memakai scope `crawl:read` sampai status
terminal. Untuk target 10, acceptance minimum adalah:

- worker menjalankan job;
- tidak ada `GOOGLE_AUTH_REQUIRED`;
- `scanned` lebih dari 5 dan target 10 tercapai, atau stop reason jujur;
- `fetched`, `matched`, `inserted`, dan `duplicate` dapat dijelaskan;
- jumlah review baru terlihat pada DB Crawler dan dapat ditarik OneBox;
- token smoke dicabut setelah test.

Setiap job gagal auth harus berhenti satu attempt, bukan diulang tiga kali.

## 10. Verifikasi OneBox setelah crawler hijau

Setelah batch crawler berhasil:

1. Pastikan OneBox menerima status batch dan progress.
2. Pastikan raw review masuk ke DB OneBox melalui flow pull otomatis.
3. Pastikan review tampil di Kelola Review tanpa pull manual tambahan bila
   kontrak environment memang sudah memakai auto-import.
4. Cocokkan `external_review_id`, `onebox_location_id`, rating, timestamp, dan
   jumlah inserted/duplicate.
5. Jangan membuat Ticket dari review historis hanya karena review berhasil
   diimpor; ikuti field `first_seen_at` dan `eligible_for_ticket`.

## 11. Decision tree singkat

```text
API health 200?
  tidak -> pulihkan API/database dan berhenti
  ya -> worker hidup dengan volume yang benar?
          tidak -> perbaiki branch/Compose volume
          ya -> proxy env atau Preferences aktif?
                  ya -> backup, bersihkan, probe ulang
                  tidak -> probe DOM
                           auth wall -> login manual pada profile yang sama
                           407 -> proxy/egress belum bersih
                           container not found -> URL/selector/layout
                           >5 card -> smoke target 10
```

## 12. Rollback dan pemulihan

Jika perubahan profile memperburuk keadaan:

1. Stop worker dan pastikan setup browser tertutup.
2. Pulihkan `Preferences` dari backup bertanggal yang sudah diverifikasi.
3. Pulihkan `.env` dari backup environment yang benar bila proxy memang
   diperlukan.
4. Hapus lock stale saja.
5. Recreate API/worker tanpa flag `-v`.
6. Jalankan health check, probe, lalu smoke kecil.

Jangan menghapus `VOLUME_NAME`, volume PostgreSQL, atau data review sebagai
langkah rollback.

## 13. Evidence incident 14 September 2026

Pada dev, proxy residue sudah dibersihkan dan server kembali ke deployment
canonical. Profile memiliki cookie auth names, tetapi probe dan dua smoke run
tetap menerima `GOOGLE_AUTH_REQUIRED` saat pagination. Lima card awal dan
`navigator.webdriver=null` membuktikan URL, panel, dan anti-detection browser
dasar bukan satu-satunya blocker.

Status incident masih **blocked pada Google session readiness**. Next action
adalah membuktikan bahwa account yang dipakai pada profile yang sama benar-benar
dapat membuka load-more melalui probe Selenium, atau mengubah desain connector
ke sumber Google yang resmi/berlisensi. Jangan menandai P0 resolved hanya dari
container healthy, avatar, atau cookie count.

## 14. Checklist penutupan

- [ ] Environment dan branch sudah dicatat.
- [ ] API healthy dan worker canonical aktif.
- [ ] Volume profile tepat dan tidak dipakai worker lain.
- [ ] Tidak ada proxy aktif yang tidak disetujui.
- [ ] Tidak ada lock browser stale.
- [ ] Login manual selesai pada profile yang sama.
- [ ] Probe melewati lima card.
- [ ] Smoke target 10 berhasil dan metriknya dicatat.
- [ ] Review baru terlihat di Crawler dan OneBox.
- [ ] Failure tidak disamarkan sebagai `no_more_reviews`.
- [ ] Token sementara dicabut.
- [ ] Setup browser dan SSH tunnel ditutup.
