# Runbook: Import Fixture APIFY Astra ke Dev

Status: prepared locally, belum dijalankan ke database mana pun.

Update 2026-09-15: engine APIFY sudah terbukti mengembalikan review dan
menyelesaikan batch pada UI Fetch. Seeding lokasi Astra baru dilakukan di
OneBox, sehingga langkah berikutnya adalah refresh worklist Crawler sebelum
fixture di-import. Jangan checkout branch `apify-migration`, menjalankan SQL,
atau redeploy environment yang sedang dipakai dev lain dari runbook ini.

Dokumen ini untuk demo Astra saat engine Selenium terkena blokir Google. Ini bukan pengganti adapter APIFY production. Fixture tetap masuk melalui database Crawler agar OneBox menerima review lewat endpoint integration yang sama seperti alur live.

## Jalur utama saat engine APIFY sudah aktif

Jika branch/runtime APIFY sudah dipasang dan terbukti menghasilkan review,
gunakan jalur live ini untuk demo berikutnya:

```text
OneBox seed 36 lokasi
  -> Crawler pull/refresh worklist
  -> OneBox enqueue crawl job per batch
  -> Crawler APIFY worker menyimpan review
  -> OneBox pull review dengan cursor
  -> Kelola Review dan labeling native
```

Dalam jalur ini **tidak ada seeding review manual ke database Crawler**. Data
review dihasilkan oleh job APIFY. Importer fixture di bawah hanya dipakai untuk
backfill/offline recovery ketika data JSON sudah tersedia atau ketika live
provider belum siap. Jangan menjalankan jalur live dan fixture untuk Place ID
yang sama pada waktu yang sama.

### Gerbang refresh worklist setelah lokasi ditambah

Lokasi yang baru disimpan di OneBox tidak perlu dibuat manual di tabel
`Crawler.locations`. Jalankan dari root deployment Crawler yang memang terikat
ke OneBox environment tersebut:

```bash
docker compose exec api python -m scripts.refresh_worklist --company-id 3 --json
```

Lanjut hanya jika hasilnya `status=synced`, `warning=null`, dan seluruh 36
Place ID Astra ditemukan di cache Crawler. `fetched`/`upserted` tidak harus
persis 36 bila tenant sudah memiliki lokasi lain, tetapi target Astra wajib
memiliki `onebox_connection_id`, `onebox_location_id`, `active=true`,
`crawl_enabled=true`, dan `ingest_reviews=true`.

Setelah itu buat crawl job APIFY per batch (12 lokasi), poll status memakai
scope `crawl:read`, lalu biarkan OneBox melakukan pull review. ID
`onebox_location_id` harus diambil dari worklist/cache environment yang sedang
digunakan; jangan menyalin ID dari dev, staging, atau screenshot environment
lain.

### Aturan environment saat dev lain mengerjakan APIFY

Runbook ini tidak mengizinkan tindakan berikut selama branch
`apify-migration` masih aktif dikerjakan:

- checkout atau merge branch tersebut ke checkout yang sedang dipakai dev lain;
- menjalankan SQL seeding atau import fixture ke DB dev;
- rebuild/redeploy stack dev;
- menganggap `refresh_worklist` aman hanya karena endpoint OneBox terlihat sehat.

Yang boleh disiapkan sekarang adalah manifest, audit, dry-run, payload contoh,
dan dokumentasi. Eksekusi refresh/commit harus dilakukan setelah owner
environment menyatakan checkout, DB, `company_id`, dan konfigurasi OneBox sudah
terkunci.

## Keputusan arsitektur

Alur yang dipakai:

```text
Sheet Astra
  -> OneBox master Connection/Location
  -> Crawler worklist sync
  -> Crawler reviews (fixture APIFY)
  -> OneBox GET /api/integration/v1/reviews
  -> Message/Ticket/Review OneBox
  -> native sentiment labeling
```

Jangan insert langsung ke tabel Message, Ticket, atau tabel review OneBox. Jalur langsung melewati dedup, cursor, tenant guard, mapping lokasi, dan lifecycle ingest yang sudah menjadi kontrak service.

## Data audit

Sumber lokal: `C:\Users\sayyi\Documents\data_review_astra`.

| Pemeriksaan | Hasil |
|---|---:|
| File JSON | 38 |
| Record mentah | 10,946 |
| Place ID target dari sheet | 36 |
| Place ID di file | 37 |
| Record target setelah membuang Place ID asing | 10,808 |
| `review_id` unik target | 4,594 |
| Baris duplikat di luar record kanonik | 6,214 |
| Kelompok duplikat `review_id` | 4,503 |
| Kelompok duplikat dengan field bermakna berbeda | 2 |
| Kelompok konten sama dengan `review_id` berbeda | 92 |

Place ID asing adalah `ChIJ1c7qggIeai4RiOYb8gAuxVc` dari file Mangga Dua. Itulah sebabnya importer hanya menerima Place ID yang ada di manifest, bukan semua record yang ditemukan.

Duplikat ditentukan terutama dari `(external_place_id, review_id)`. Konten yang sama tidak otomatis dibuang karena reviewer berbeda dapat menulis teks yang sama. Untuk dua kelompok `review_id` yang memiliki tanggal berbeda, importer memilih record dengan kualitas tertinggi secara deterministik; tanggal absolut terbaru dipilih bila field lain setara.

## Prasyarat sebelum commit

Claude/OneBox harus menyelesaikan hal berikut terlebih dahulu:

1. 36 cabang sudah dibuat pada OneBox dev dari sheet `Asuransi Astra`.
2. Setiap cabang memiliki `SiteId` dev yang benar, provider VoC yang benar, dan `external_place_id` yang sesuai.
3. Setiap koneksi sudah memiliki `Options.company_id` yang sesuai tenant Crawler dev.
4. OneBox service token memiliki scope `reviews:read`.
5. Crawler worklist sudah di-refresh untuk `company_id=3`.
6. Setiap row `Crawler.locations` memiliki `onebox_connection_id` dan `onebox_location_id` yang tidak null.
7. Preflight `whoami` OneBox sudah mengembalikan company yang diharapkan.
8. Satu batch kenari kecil sudah berhasil melalui receive/import, atau bug ingest yang lama sudah dibuktikan selesai.

Jika salah satu prasyarat belum hijau, jalankan importer hanya dalam dry-run. Script akan berhenti sebelum insert bila worklist atau mapping `onebox_location_id` belum lengkap.

## Pembagian tiga batch

Manifest di `scripts/astra_location_manifest.json` berisi 36 row berurutan. Batch operasional masing-masing berisi 12 lokasi:

| Batch | Sequence manifest | Tujuan |
|---|---:|---|
| 1 | 1-12 | canary dan lokasi awal |
| 2 | 13-24 | perluasan setelah batch 1 terverifikasi |
| 3 | 25-36 | penuntasan seluruh cabang |

Audit lokal per batch saat ini:

| Batch | Row mentah | Review ID unik |
|---|---:|---:|
| 1 | 3,610 | 1,847 |
| 2 | 5,600 | 1,947 |
| 3 | 1,598 | 800 |

Angka ini adalah isi fixture lokal sebelum dikurangi `skipped_existing` dari
database Crawler. Angka yang tampil di OneBox dapat lebih kecil karena dedup
atau karena sebagian review sudah pernah dipull.

`3_astra_bandung.json` tetap cocok dipakai sebagai canary terpisah karena isinya kecil. Namun ia bukan batch manifest; gunakan hanya bila ingin menguji jalur OneBox sebelum menjalankan batch 1.

## Cara menjalankan

Semua perintah dijalankan dari root repository Crawler. Path data harus menunjuk folder yang berisi JSON, bukan satu file.

### 1. Dry-run batch 1

```bash
python -m scripts.import_apify_reviews \
  --data-dir "C:\Users\sayyi\Documents\data_review_astra" \
  --company-id 3 \
  --batch 1 \
  --report-json outputs/astra-batch-1-dry-run.json
```

Dry-run harus menampilkan:

- `locations=12`;
- `canonical_rows` sesuai jumlah unique review ID batch;
- `unknown_place_rows=0` untuk batch yang dipilih;
- `out_of_batch_rows` berisi row dari 24 lokasi target lain dan tidak di-import;
- `conflicting_duplicate_groups` hanya sebagai catatan audit;
- `to_insert` sama dengan review baru yang belum ada di Crawler.

### 2. Commit batch

Tambahkan `--commit` hanya setelah preflight OneBox dan Crawler selesai:

```bash
python -m scripts.import_apify_reviews \
  --data-dir "C:\Users\sayyi\Documents\data_review_astra" \
  --company-id 3 \
  --batch 1 \
  --commit \
  --report-json outputs/astra-batch-1-import.json
```

Ulangi untuk `--batch 2` dan `--batch 3` setelah verifikasi OneBox batch sebelumnya. Script idempotent untuk record yang sama: rerun akan menaikkan `skipped_existing`, bukan membuat row review kedua.

### 3. Verifikasi Crawler

Gunakan query read-only berikut pada DB Crawler yang benar:

```sql
SELECT l.branch_name,
       l.onebox_connection_id,
       l.onebox_location_id,
       COUNT(r.id) AS review_count,
       COUNT(DISTINCT r.external_review_id) AS unique_external_review_count
  FROM locations l
  LEFT JOIN reviews r ON r.location_id = l.id
 WHERE l.company_id = 3
 GROUP BY l.id,
          l.branch_name,
          l.onebox_connection_id,
          l.onebox_location_id
 ORDER BY l.id;
```

Pastikan tidak ada `onebox_location_id` null dan tidak ada perbedaan antara `review_count` dan `unique_external_review_count` untuk import ini.

### 4. Handoff ke OneBox

Setelah commit batch:

```text
health -> whoami -> receive -> processpending -> analysis
```

`receive` harus memakai service token OneBox yang sudah terikat ke company yang tepat. Cursor hanya boleh disimpan setelah halaman selesai diproses seluruhnya. `processpending` dan `analysis` mengikuti lifecycle OneBox yang existing; kegagalan labeling tidak boleh menghapus raw review yang sudah masuk.

## Acceptance criteria demo

- 36 cabang tampil pada layar Lokasi OneBox dev dan masing-masing terpetakan ke Place ID yang benar.
- Crawler memiliki 4,594 review ID unik target setelah semua batch, atau angka aktual yang dijelaskan oleh `skipped_existing`.
- Place ID asing tidak masuk.
- Rerun tidak menggandakan review.
- Review tampil di Kelola Review setelah OneBox pull tanpa insert manual ke Message/Ticket.
- `review_hash`, `external_review_id`, `external_place_id`, rating, teks, tanggal, owner response, dan status analisis terbaca.
- Tidak ada review lintas tenant atau lintas cabang.
- Review dengan teks kosong tetap tersimpan sebagai rating-only review.
- AI/Ollama mati tidak boleh menghalangi raw review tampil; labeling/AI ditangani sebagai tahap terpisah.

## Rollback

Jangan gunakan `down -v`, jangan hapus volume PostgreSQL, dan jangan menghapus seluruh tabel review. Karena importer membuat `FetchLog.metadata.fixture_import=true`, rollback terbatas dapat direncanakan berdasarkan batch dan waktu import setelah backup serta persetujuan owner.

Untuk demo, rollback yang paling aman adalah membiarkan row review tetap ada dan menghentikan pull OneBox sementara. Penghapusan row hanya boleh dilakukan dengan query yang dibatasi oleh `source`, batch metadata, daftar location, dan waktu import yang telah diverifikasi.

## Handoff tugas

### Codex / Crawler

- Menjaga manifest dan importer lokal.
- Menjalankan dry-run dan commit ke Crawler setelah environment binding disetujui.
- Mengirim laporan per batch: raw, canonical, inserted, existing, duplicate, unknown, dan conflict.
- Memastikan `sync_updated_at` baru agar OneBox delta pull tidak melewati fixture.

### Claude / OneBox

- Seed 36 master Connection/Location dengan gerbang site/environment.
- Pastikan `Options.company_id`, token, provider, dan `external_place_id` benar.
- Refresh atau trigger worklist Crawler.
- Jalankan `whoami`, `receive`, `processpending`, dan `analysis` per batch.
- Verifikasi counter UI dan Kelola Review.
- Laporkan mapping yang gagal tanpa mengubah data cabang lain.
