# Implementation Plan: QA Fix Master Data Locations

Status: Draft untuk perbaikan dan re-test QA  
Tanggal: 17 September 2026  
Module: Voice of Customer - Pengaturan - Master Data Locations  
Owner implementasi: OneBox  
Dependency: Crawler worklist consumer dan kontrak Connection/Location

## 1. Tujuan

Menyelesaikan seluruh finding QA pada modul Master Data Locations tanpa
merusak fungsi yang sudah lulus, terutama:

- pencarian dan filter lokasi;
- validasi Place ID, PIC, koordinat, dan target review;
- tambah, edit, toggle aktif/nonaktif, dan delete protection;
- mapping Connection ke lokasi OneBox;
- ketersediaan lokasi aktif pada worklist Crawler;
- perilaku UI yang konsisten pada first load, first click, dan direct action.

Dokumen ini menjadi acuan kerja Codex/Claude untuk perbaikan dan acuan QA
untuk re-test. Test case yang sudah `PASS` tidak boleh diubah perilakunya
kecuali ada alasan kontrak yang terdokumentasi.

## 2. Sumber QA dan ringkasan hasil

Sumber: Google Sheet `Testing VOC Master Data Location`  
Spreadsheet: https://docs.google.com/spreadsheets/d/1oKm5v8Zj2XYCWhMcfVsEdUxM7S64HPxTWM9v5Ifjeh0/edit  
Tab utama: `VOC Menu Lokasi`, range yang dibaca: `A1:G1003`  
Tab `VOC Fetch Jobs` terdeteksi kosong pada saat review ini.

Hasil QA:

| Hasil | Jumlah |
|---|---:|
| PASS | 27 |
| FAILED | 6 |
| Total test case berstatus | 33 |

### 2.1 Failed test case

| QA row | Test case | Finding | Kategori | Owner utama |
|---:|---|---|---|---|
| 9 | `TC_008_Admin` | Tiga dari lima KPI card belum memfilter tabel dengan benar | UI behavior / UX | OneBox FE |
| 17 | `TC_016_Admin` | `OneBox User ID=-5` masih dapat lolos jika diketik manual | Backend validation | OneBox BE + FE |
| 21 | `TC_020_Admin` | Google Maps URL tanpa `http/https` masih dapat disimpan | Backend validation | OneBox BE + FE |
| 30 | `TC_029_Admin` | ID Connection pada spec dan database tidak sama | Data contract / fixture | OneBox BE + QA |
| 32 | `TC_031_Admin` | Klik delete dari list ikut membuka Detail Lokasi | Event handling / UI state | OneBox FE |
| 33 | `TC_032_Admin` | Klik edit pertama setelah login/reload menampilkan transisi yang salah | Async loading / UI state | OneBox FE |

### 2.2 Yang sudah lulus dan harus dipertahankan

QA menyatakan PASS untuk search, filter dropdown, modal filter lainnya,
validasi nama/Place ID/email/WhatsApp/koordinat/target review, happy path
tambah dan edit, persistence PIC, toggle status, delete protection, jumlah
review, penghapusan tombol resync, `StatusId` pada record yang diverifikasi,
dan penolakan crawl untuk lokasi nonaktif.

Catatan penting: `TC_004_Admin` PASS karena seluruh lokasi pada dataset QA
memang aktif. Ketiadaan hasil ketika filter Nonaktif bukan bukti bahwa filter
Nonaktif rusak.

## 3. Prinsip penyelesaian

1. Validasi di backend adalah sumber kebenaran. HTML constraint, stepper, dan
   JavaScript hanya membantu user, bukan penjaga data.
2. Identitas lokasi harus stabil berdasarkan record dan field bisnis, bukan
   angka auto-increment yang berbeda antar-environment.
3. Action pada tabel harus terisolasi dari row navigation. Klik Edit, Toggle,
   dan Delete tidak boleh memicu handler klik baris.
4. Worklist Crawler membaca master data OneBox. Perubahan lokasi tidak boleh
   kembali ke mekanisme legacy push-sync atau dual-write.
5. UI tidak boleh menampilkan sukses sebelum response save berhasil. Saat
   request masih berjalan, action harus punya loading state dan tidak dapat
   diklik dua kali.
6. Delete protection wajib ditegakkan dua lapis: UI untuk kejelasan user dan
   backend untuk mencegah race condition atau request manual.

## 4. Scope pekerjaan

### 4.1 KPI card menjadi filter yang deterministik

#### Masalah

`TC_008_Admin` menemukan bahwa hanya dua dari lima card yang bekerja saat
diklik. Salah satu perilaku yang terlihat hanya reset, bukan filter. Card
`Wilayah Operasional`, `Kota Terpantau`, dan `Coverage Benchmark` belum
memiliki perilaku filter yang lengkap.

#### Keputusan produk yang harus dikunci

Setiap card harus memiliki definisi predicate yang dapat dijelaskan. Card
agregat tidak boleh berpura-pura memfilter ke satu nilai jika card tersebut
merangkum banyak nilai.

Rekomendasi kontrak filter:

| KPI card | Definisi metric | Efek klik yang direkomendasikan |
|---|---|---|
| `Wilayah Operasional` | Jumlah wilayah/provinsi unik pada lokasi aktif | Filter ke lokasi aktif dengan wilayah terisi; chip `Wilayah terisi` |
| `Kota Terpantau` | Jumlah kota unik pada lokasi aktif | Filter ke lokasi aktif dengan kota terisi; chip `Kota terisi` |
| `Coverage Benchmark` | Review aktual dibanding target review per lokasi | Filter lokasi di bawah target; chip `Coverage di bawah target` |
| Dua KPI existing | Definisi mengikuti implementasi yang sudah PASS | Pertahankan, tetapi gunakan active filter yang sama |

Jika Product menginginkan card wilayah atau kota membuka satu nilai tertentu,
card harus memiliki selection context, misalnya dropdown wilayah/kota. Jangan
membuat filter yang tidak dapat dipetakan dari angka agregat.

#### Perilaku UI wajib

- Klik card menerapkan filter tanpa full page reload.
- Filter aktif terlihat sebagai chip atau state yang jelas.
- Tabel, counter, dan empty state berubah sesuai filter aktif.
- Klik card yang sama lagi melepas filter tersebut.
- `Reset` mengembalikan seluruh filter, termasuk filter dari KPI card.
- Filter KPI dapat digabung dengan search dan `Filter lainnya`.
- Loading/error state sama dengan filter biasa.

#### Acceptance criteria

- Kelima KPI card memiliki definisi dan test case.
- Kelima KPI card menghasilkan predicate yang dapat diverifikasi dari row
  tabel, bukan hanya mengubah warna card.
- QA dapat membuktikan jumlah row sebelum dan sesudah klik.

### 4.2 Validasi OneBox User ID di backend dan frontend

#### Masalah

`TC_016_Admin` menunjukkan input manual `-5` dapat melewati form. Stepper atau
atribut `min` saja tidak cukup karena request dapat dibuat dari DevTools,
Postman, atau client lama.

#### Kontrak validasi

Field: `pic_onebox_id` atau nama field aktual yang dipetakan ke
`Connection.Options.location.pic_onebox_id`.

- Jika field opsional dan kosong, simpan sebagai `null`/nilai kosong sesuai
  konvensi existing. Jangan mengubah arti field kosong.
- Jika terisi, nilai wajib integer positif: `1, 2, 3, ...`.
- Tolak `0`, bilangan negatif, decimal, scientific notation, alphanumeric,
  whitespace tersembunyi, dan overflow integer.
- Validasi dilakukan sebelum `Connection.Options` ditulis.
- Jika satu field invalid, tidak boleh ada field lain yang tersimpan sebagian.
- Response error harus menunjuk field dan menjelaskan format yang diterima.

#### Implementasi yang disarankan

1. Normalisasi input pada boundary request.
2. Validasi dengan parser integer yang ketat, bukan cast longgar.
3. Validasi ulang pada method save action/service sebelum transaksi database.
4. Tambahkan constraint atau guard repository bila aman untuk row lama.
5. Pada FE gunakan `min=1`, input numeric, pesan inline, dan blok submit.

#### Acceptance criteria

- `-5`, `0`, `1.5`, `abc`, dan format invalid lain ditolak dari UI dan API.
- Nilai `1` dan integer positif valid tersimpan.
- Data lama yang kosong tidak rusak.
- Request invalid tidak mengubah `Connection.Options` atau field lokasi lain.

### 4.3 Validasi Google Maps URL

#### Masalah

`TC_020_Admin` menunjukkan URL tanpa skema `http/https` dapat disimpan.

#### Kontrak validasi

- Nilai kosong mengikuti aturan field existing.
- Nilai terisi harus absolute URL.
- Scheme yang diizinkan hanya `http` dan `https`, case-insensitive.
- Host wajib terisi.
- Tolak `javascript:`, `data:`, `file:`, `//host/path`, teks biasa,
  URL dengan whitespace/control character, dan nilai yang hanya terlihat
  seperti URL.
- Jangan memaksa satu format path Google Maps bila tidak diperlukan.

#### Implementasi yang disarankan

1. Gunakan parser URL native PHP/OneBox, lalu cek `scheme` dan `host`.
2. Jangan hanya mengandalkan regex atau `input type=url`.
3. Simpan URL setelah trim normalisasi yang aman.
4. Tampilkan error pada field dan pertahankan input user.

#### Acceptance criteria

- `https://www.google.com/maps/...` dan `http://...` valid.
- `www.google.com/maps/...`, `google.com/maps/...`, `javascript:...`, dan
  URL tanpa host ditolak.
- Request invalid tidak menulis data parsial.
- Existing URL valid tetap terbaca setelah edit/reload.

### 4.4 Resolusi mismatch Connection ID dan dev spec

#### Temuan

`TC_029_Admin` menguji Connection ID `1039` sebagai Hermina Depok, tetapi
catatan QA menyebut database saat ini tidak cocok. QA mengarahkan pemeriksaan
status berikutnya ke Connection ID `977`, dan `TC_030_Admin` untuk ID `977`
dinyatakan PASS dengan `StatusId=CNS2`.

Ini adalah mismatch antara fixture/spec dan data environment. Belum ada dasar
untuk menyimpulkan bahwa record ID `1039` harus diubah atau dihapus.

#### Prosedur resolusi

1. Ambil record berdasarkan nama Connection, `SiteId`, `ProviderId`, `TargetId`,
   dan mapping `Options.location`.
2. Buktikan record mana yang merepresentasikan Hermina Depok pada environment
   yang sedang diuji.
3. Jika ID adalah kontrak fixture dev, update seed/spec/QA. Jika ID hanya
   auto-increment, ubah test agar tidak hardcode ID.
4. Jika ada dua record bisnis untuk cabang yang sama, lakukan cleanup
   terkontrol dengan backup dan approval owner.
5. Pastikan record target memakai `StatusId=CNS2` dan tidak masuk scheduler
   yang tidak sesuai.

#### Rekomendasi perbaikan test

`TC_029_Admin` tidak boleh menjadikan `Id=1039` sebagai satu-satunya identitas
kecuali migration memang menjamin ID tersebut. Gunakan identity query berikut
sebagai titik awal:

```sql
SELECT Id, Name, SiteId, ProviderId, TargetId, StatusId, Options
FROM Connection
WHERE Name = 'Hermina Depok';
```

Tambahkan filter `SiteId` dan provider sesuai environment target. Assertion
harus memeriksa kombinasi identity dan status, bukan angka auto-increment saja.

#### Acceptance criteria

- QA spec, seed, dan data environment menunjuk record bisnis yang sama.
- Hermina Depok memiliki `StatusId=CNS2` pada record yang benar.
- Test tidak false-negative hanya karena ID auto-increment berbeda.
- Tidak ada perubahan pada Connection yang bukan target.
- Perubahan Connection tetap menghasilkan worklist Crawler yang benar.

### 4.5 Isolasi delete action dari row navigation

#### Masalah

`TC_031_Admin` menemukan klik ikon delete dari tabel dapat ikut membuka Detail
Lokasi. Penyebab paling mungkin adalah event bubbling dari action cell ke
handler klik row atau state detail yang dipakai bersama state modal.

#### Implementasi yang disarankan

- Pisahkan state `selectedLocationForDetail` dan
  `selectedLocationForDelete`.
- Pada action cell, hentikan propagation untuk Delete, Edit, dan Toggle.
- Gunakan button semantik dengan `type=button`, bukan anchor kosong atau
  clickable `div`.
- Handler delete hanya membuka modal; handler row hanya membuka detail jika
  event berasal dari area row yang bukan action cell.
- Modal delete protection tidak boleh memanggil loader detail.
- Backend tetap mengembalikan conflict/validation error bila lokasi memiliki
  review, walaupun counter UI stale.
- Setelah modal ditutup, row selection dan detail route harus tetap sama
  seperti sebelum modal dibuka.

#### Acceptance criteria

- Dari list fresh load, klik delete hanya membuka satu modal.
- Detail Lokasi tidak terbuka di belakang modal.
- Klik delete pada dua lokasi berbeda secara berurutan memilih target yang
  benar setiap kali.
- Lokasi tanpa review tetap menampilkan confirm delete dan dapat dihapus.
- Lokasi dengan review ditolak dengan pesan jelas dan diarahkan untuk
  dinonaktifkan.
- Request langsung ke API tidak dapat menghapus lokasi yang memiliki review.

### 4.6 First edit setelah login atau reload

#### Masalah

`TC_032_Admin` gagal secara kondisional hanya pada klik edit pertama setelah
login/reload. Percobaan berikutnya normal. Ini mengarah ke race condition
antara fetch daftar lokasi, fetch detail/options, dan handler edit.

#### Implementasi yang disarankan

1. Saat halaman pertama dibuka, tampilkan loading state yang jelas dan
   nonaktifkan action yang membutuhkan data sampai data minimum siap.
2. Handler Edit harus membaca row ID yang diklik, bukan object row yang mungkin
   stale atau belum lengkap.
3. Jika detail belum tersedia, handler melakukan fetch detail lalu membuka
   form setelah response sukses. Tampilkan spinner pada action/form.
4. Cegah double click dan cegah response request lama menimpa row yang baru
   dipilih.
5. Jika fetch gagal, form tidak dibuka dalam keadaan kosong; tampilkan error
   yang dapat di-retry.
6. Pastikan form edit tidak melewati atau memicu halaman Detail Lokasi sebagai
   transisi sementara.
7. Setelah save sukses, update row/list dan state detail dari response server;
   jangan hanya mengubah state lokal berdasarkan input mentah.

#### Acceptance criteria

- Pada browser session baru, reload lalu klik Edit pertama kali membuka form
  yang benar.
- Field form berisi data lokasi yang dipilih, bukan data lokasi sebelumnya.
- Tidak ada halaman kosong, detail flash, atau modal ganda.
- Klik Edit berulang pada lokasi berbeda tetap memilih record yang benar.
- Error network memiliki retry dan tidak meninggalkan form setengah terisi.
- `TC_023_Admin` untuk persistence PIC tetap PASS.

## 5. Kontrak data Master Data Location

Field minimum yang harus dipertahankan pada save dan worklist:

| Domain | Field | Aturan |
|---|---|---|
| Identity | `branch_name` | Wajib, uniqueness case-insensitive sesuai QA |
| Identity | `hospital_name` | Disimpan sesuai grouping bisnis |
| Google | `external_place_id` | Wajib, format Place ID, unik sesuai scope tenant/site |
| Google | `google_maps_url` | Absolute URL dengan scheme `http/https` |
| Location | `city`, `address` | Persist dan terbaca saat edit |
| Coordinates | `latitude`, `longitude` | Keduanya kosong atau keduanya valid di Indonesia |
| Crawl | `target_review_count` | Integer 1-300 |
| Ownership | `source`, `SiteId`, provider | Tidak boleh berubah akibat edit PIC |
| PIC | `pic_name`, `pic_wa`, `pic_email`, `pic_onebox_id` | Validasi field-specific dan persist atomik |
| Lifecycle | active/nonactive | Toggle tersimpan dan memengaruhi worklist berikutnya |
| Integration | Connection ID / Target ID / Options | Mapping tidak boleh ditebak dari nama saja |

Setiap save location harus bersifat atomik. Jika validasi satu field gagal,
tidak ada bagian `Options`, Connection, atau data lokasi yang boleh tertulis.

## 6. Regression terhadap Crawler worklist

Perbaikan OneBox tidak selesai hanya karena tabel UI terlihat benar. Setelah
record lokasi disimpan, lakukan verifikasi pada environment Crawler yang benar:

1. OneBox record aktif memiliki `external_place_id` yang benar.
2. Connection memiliki tenant/site/provider dan mapping location yang benar.
3. Crawler melakukan pull/refresh worklist, bukan menerima legacy push-sync.
4. Satu lokasi OneBox menghasilkan satu item lokasi pada worklist.
5. Lokasi nonaktif tidak memiliki `active=true` atau `crawl_enabled=true`.
6. `onebox_connection_id` dan `onebox_location_id` tidak null pada cache Crawler.
7. Fetch job menggunakan `onebox_location_id`, sedangkan target Google tetap
   di-resolve melalui `external_place_id` dari worklist.
8. Toggle atau edit tidak membuat duplicate worklist item.

Smoke command pada Crawler, hanya setelah environment disetujui owner:

```bash
docker compose exec api python -m scripts.refresh_worklist --company-id <expected-company-id> --json
```

Jangan menjalankan command ini ke dev/staging yang sedang dipakai developer
lain tanpa konfirmasi checkout, DB, tenant, dan OneBox base URL.

## 7. Test plan per finding

### 7.1 Unit/API test

- `pic_onebox_id`: kosong, `-5`, `0`, `1`, `1.5`, `abc`, dan overflow.
- `google_maps_url`: kosong, `http`, `https`, no scheme, unsupported scheme,
  no host, whitespace/control character.
- Save atomik: satu field invalid memastikan tidak ada perubahan pada row.
- Delete guard: review count `0` versus `>0` dan race condition sederhana.
- Connection resolver: stable business identity, site/provider guard, status.

### 7.2 Frontend/component test

- Lima KPI card: apply, toggle-off, reset, kombinasi dengan search/modal filter.
- Action cell: delete/edit/toggle tidak bubble ke row detail.
- Modal: target delete benar setelah berpindah row.
- First edit: state fresh load, loading, success, error, retry, rapid click.

### 7.3 QA regression sequence

1. Login ulang atau gunakan browser context baru.
2. Buka Master Data Locations dan tunggu initial data selesai.
3. Jalankan `TC_008_Admin` untuk kelima KPI card.
4. Jalankan `TC_016_Admin` dan `TC_020_Admin` dari UI serta request API.
5. Jalankan `TC_031_Admin` dari list tanpa membuka detail sebelumnya.
6. Jalankan `TC_032_Admin` setelah hard reload/session baru minimal tiga kali.
7. Verifikasi `TC_029_Admin` dengan identity query dan hasil keputusan data.
8. Ulangi test yang sudah PASS dengan fokus regresi: TC_012, TC_013, TC_021,
   TC_022, TC_023, TC_024, TC_025, TC_026, TC_028, TC_030, dan TC_033.
9. Jalankan smoke worklist pada tenant/environment yang sudah disetujui.

## 8. Pembagian pekerjaan

### OneBox frontend

- Implementasi predicate dan active state lima KPI card.
- Stop propagation dan pemisahan state delete/detail.
- First-load/edit state machine, loading, retry, dan double-click guard.
- FE validation sebagai feedback cepat.
- Component/E2E test untuk TC_008, TC_031, dan TC_032.

### OneBox backend

- Strict validation OneBox User ID.
- Strict URL validation.
- Atomic save dan field-level error response.
- Delete protection server-side.
- Resolver Connection berdasarkan business identity dan tenant/site/provider.
- Data/seed/spec reconciliation untuk Hermina Depok.

### Codex / Crawler

- Review kontrak worklist agar field lokasi baru tetap diterima.
- Siapkan read-only refresh dan verification query.
- Pastikan duplicate worklist dan cross-tenant mapping tertolak.
- Smoke test satu lokasi setelah OneBox menyatakan data siap.
- Tidak mengubah data OneBox secara langsung dan tidak menebak tenant dari
  request.

### QA

- Update test case Connection agar membedakan fixed fixture ID dan ID
  auto-increment.
- Re-test enam failed case dan regression subset.
- Catat browser/session state pada TC_031 dan TC_032.
- Verifikasi UI dan database, bukan hanya toast message.

## 9. Definition of Done

- [ ] Semua enam failed test case memiliki fix dan bukti re-test.
- [ ] Kelima KPI card memiliki definisi metric, predicate, dan reset behavior.
- [ ] Backend menolak invalid OneBox User ID dan URL tanpa scheme valid.
- [ ] Save invalid bersifat atomik dan tidak menyimpan data parsial.
- [ ] Connection Hermina Depok sudah direkonsiliasi berdasarkan identity yang
      benar, bukan sekadar mengganti angka ID.
- [ ] Delete dari list tidak membuka detail dan backend tetap melindungi row
      yang memiliki review.
- [ ] Edit pertama setelah fresh login/reload stabil minimal tiga kali.
- [ ] Test PASS existing tidak regresi.
- [ ] Lokasi aktif tetap muncul pada worklist Crawler dengan mapping lengkap.
- [ ] Lokasi nonaktif tidak dapat dibuatkan crawl job.
- [ ] Tidak ada duplicate location/worklist item, cross-tenant leak, atau
      legacy push-sync baru.

## 10. Risiko dan rollback

| Risiko | Dampak | Mitigasi |
|---|---|---|
| KPI predicate salah tafsir | User melihat data yang tidak sesuai ekspektasi | Kunci definisi metric dan uji row-level sebelum merge |
| Validasi backend terlalu ketat untuk data lama | Edit row lama gagal | Terapkan validasi pada input baru, audit data lama, dan sediakan pesan migrasi |
| Update Connection berdasarkan ID salah | Cabang atau scheduler lain berubah | Query identity + site/provider guard + backup + approval |
| Event fix mengubah navigasi tabel | Detail/edit regression | Component/E2E test untuk semua action cell |
| Refresh worklist ke environment salah | Tenant atau DB dev terganggu | Konfirmasi environment dan `whoami` sebelum smoke |
| Tombol UI terlihat sukses tetapi worklist stale | Fetch Jobs tidak mengenali lokasi baru | Refresh worklist dan verifikasi mapping setelah save |

Rollback kode dilakukan melalui revert PR. Rollback data Connection hanya boleh
dengan backup dan query terbatas pada record target yang sudah diidentifikasi.
Jangan menghapus volume database atau melakukan reset seluruh tabel.

## 11. Status eksekusi

Dokumen ini berasal dari hasil baca QA pada 17 September 2026. Belum ada
perubahan server, database, checkout branch, atau redeploy yang dilakukan
sebagai bagian dari penyusunan dokumen ini.
