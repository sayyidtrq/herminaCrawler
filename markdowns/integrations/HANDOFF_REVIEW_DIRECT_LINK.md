# Atribut Review Direct Link — keadaan sekarang & yang perlu dikerjakan

2026-09-22 · hasil penelusuran kode, untuk diteruskan ke dev OneBox/crawler

## Jawaban singkat

**Atribut link ulasan belum ada.** Yang ada sekarang di layar Ulasan — tombol
"Lihat di Google" — memakai URL yang **dirakit OneBox sendiri dari Place ID**,
bukan link yang dikirim crawler.

Link rakitan itu **bukan direct link ke ulasan**. Ia mendarat di daftar ulasan
milik tempatnya.

Apify memang sudah punya atributnya (`review_url`), dan skrip import kita sudah
membacanya — tetapi nilainya **berhenti di `raw_payload`**, tidak pernah sampai
ke OneBox.

## Keadaan sekarang, per lapis

| # | Lapis | Berkas | Keadaan |
|---|---|---|---|
| 1 | Sumber Apify | `scripts/import_apify_reviews.py:322` | `review_url` **dibaca**, tapi hanya masuk `raw_payload` lewat allow-list `_bounded_raw_payload()` (baris 121–135) |
| 2 | Sumber Selenium | `app/integrations/google_maps_review_parser.py:59,80` | **Tidak ada** deep link per-ulasan. Yang ada `source_url` = URL halaman yang di-scrape (level tempat), dan itu pun hanya ke `raw_payload` |
| 3 | DB crawler | `app/db/models.py` → `_GoogleReviewColumns` | **Tidak ada kolom `review_url`.** Kolom URL yang ada cuma `reviewer_profile_url` dan `reviewer_photo_url` (keduanya milik reviewer, bukan ulasan) |
| 4 | Payload ke OneBox | `app/services/integration_review_service.py:299` → `_project()` | **Tidak mengirim** `review_url`, dan **tidak mengirim `raw_payload`** |
| 5 | OneBox simpan | `app/services/Provider/VocProvider.php` → `buildMeta()` | Meta berisi `external_place_id`, `external_review_id`, `reviewer_profile_url`, dll — **tidak ada link ulasan** |
| 6 | OneBox sajikan | `app/controllers/VocController.php:6786` → `reviewSumberUrl()` | **Merakit** URL-nya sendiri (lihat bawah) |
| 7 | UI | `app/views/Voc/reviews.volt:1258` & `:5663` | `#mr-src-link` membaca `d.review_url`; tombol disembunyikan kalau nilainya kosong |

### Isi `reviewSumberUrl()` yang sekarang

```php
$url = 'https://search.google.com/local/reviews?placeid=' . rawurlencode($place);
return $review !== '' ? $url . '#' . rawurlencode($review) : $url;
```

Dua hal yang perlu disadari:

1. **Fragment `#<external_review_id>` tidak dihormati Google.** Halaman itu
   tidak punya anchor dengan id tersebut, jadi browser mengabaikannya dan
   pengguna mendarat di **daftar ulasan tempat**, bukan ulasan yang diklik.
   Pada tempat dengan ribuan ulasan, ulasan yang dicari praktis tidak ketemu.
2. **Kalau `external_place_id` kosong, fungsinya mengembalikan `null`** dan
   tombolnya hilang sama sekali.

Jadi sisi baiknya: **kontrak `review_url` di UI sudah ada dan sudah dipakai.**
Yang perlu diganti isinya, bukan dibangun dari nol.

## Yang perlu dikerjakan

Rantainya tujuh titik. Kalau satu saja dilewat, atributnya tidak sampai ke
layar — dan kegagalannya senyap (tombol tetap muncul, cuma mengarah ke tempat).

### Sisi crawler

1. **Tambah kolom** `review_url: Mapped[str | None] = mapped_column(Text)` ke
   `_GoogleReviewColumns` di `app/db/models.py`. Kelas itu dipakai bersama
   `reviews` dan `competitor_reviews`, jadi satu perubahan kena keduanya.
   Pakai `Text`, jangan `String(255)`: deep link Google panjang (lihat catatan
   bentuk URL di bawah).
2. **Migrasi Alembic** (`alembic/versions/`) — kolom nullable, tanpa default.
3. **Apify importer** `scripts/import_apify_reviews.py`: petakan
   `record.get("review_url")` ke kolom baru, sejajar dengan
   `"reviewer_profile_url": record.get("reviewer_url")` di baris 194.
   Biarkan tetap ada di `raw_payload` supaya data lama tidak berubah artinya.
4. **Selenium parser** `app/integrations/google_maps_review_parser.py`: perlu
   ekstraksi deep link per-ulasan. **Ini pekerjaan riset DOM tersendiri** —
   lihat "Yang belum diketahui" di bawah. Sampai itu selesai, isi `None`;
   **jangan** diisi `source_url` sebagai pengganti, karena nanti tidak bisa
   dibedakan mana yang direct link dan mana yang cuma link tempat.
5. **Payload integrasi** `app/services/integration_review_service.py`, fungsi
   `_project()` (baris 299): tambahkan `"review_url": review.review_url`.

### Sisi OneBox

6. **Simpan ke Meta** di `VocProvider::buildMeta()`:
   `'review_url' => $row['review_url'] ?? null`.
7. **Pakai saat menyajikan** di `VocController::reviewSumberUrl()`: kalau
   `$meta['review_url']` terisi, pakai itu; kalau tidak, jatuh ke rakitan yang
   sekarang. Dengan begitu ulasan lama tetap punya tombol, dan ulasan baru
   dapat link yang benar — tanpa perlu backfill lebih dulu.

UI **tidak perlu diubah** untuk fungsinya, karena sudah membaca `d.review_url`.

## Yang belum diketahui — perlu dipastikan dev yang mengerjakan

1. **Bentuk dan kestabilan `review_url` Apify.** Perlu dilihat pada dataset
   nyata: apakah bentuknya `https://www.google.com/maps/reviews/data=!4m...`
   (deep link betulan) atau sekadar URL tempat. Kalau ternyata URL tempat,
   seluruh rencana ini tidak menyelesaikan masalah dan perlu dibahas ulang.
   **Cek dulu satu record Apify sebelum menulis kode apa pun.**
2. **Apakah link-nya permanen.** Kalau Google merotasi, menyimpannya sebagai
   kolom berarti menyimpan nilai yang bisa basi. Perlu keputusan: simpan apa
   adanya, atau simpan komponennya lalu rakit saat tampil.
3. **Selenium.** Apakah deep link per-ulasan bisa diambil dari DOM tanpa
   menekan tombol Share tiap ulasan. Kalau harus menekan tombol, ongkos
   crawl-nya naik drastis dan perlu ditimbang ulang.
4. **Ulasan lama.** Apify menyimpan `review_url` di `raw_payload` untuk data
   yang sudah ter-import, jadi backfill dari `raw_payload` ke kolom baru
   **mungkin bisa** tanpa crawl ulang. Perlu dicek berapa banyak baris yang
   `raw_payload`-nya memang memuat kunci itu.
5. **Perilaku fallback.** Kalau `review_url` kosong, tombolnya tetap mengarah
   ke tempat (seperti sekarang) atau labelnya dibedakan? Saran: bedakan
   labelnya — "Lihat ulasan di Google" untuk direct link, "Lihat di Google"
   untuk link tempat — supaya pengguna tahu apa yang akan dibuka.

## Catatan

- Perubahan ini **menambah kolom, bukan mengubah yang ada**, jadi aman untuk
  data lama. Yang perlu dijaga cuma satu: jangan mengisi kolom baru dengan
  URL tempat sebagai pengganti sementara.
- `raw_payload` tidak dikirim ke OneBox, dan sebaiknya tetap begitu — ia bisa
  besar dan bentuknya tidak dijanjikan stabil. Yang dikirim cukup kolom baru.
