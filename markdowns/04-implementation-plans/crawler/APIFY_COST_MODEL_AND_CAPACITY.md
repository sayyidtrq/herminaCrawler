# Apify Cost Model dan Capacity Planning VoC

**Status:** planning estimate berbasis observed run, bukan invoice commitment  
**Tanggal baseline:** 2026-09-15  
**Actor Console ID:** `pP8fxA1kSf7snQKNW`  
**Actor display/slug pada screenshot:** `Google Maps Reviews Scraper`, `web_wanderer/google-reviews-scraper`  
**Scope model:** 10 site/company x 20 cabang = 200 locations

## 1. Tujuan

Dokumen ini menghitung biaya dan kapasitas kasar jika Crawler menggunakan Apify
untuk mengambil Google review. Angka ini dipakai untuk:

- menentukan budget spike dan canary;
- memperkirakan initial backfill;
- memperkirakan scheduled delta fetch;
- memahami pengaruh jumlah company, cabang, dan review;
- menghindari perhitungan yang keliru dari `maxReviews` saja.

Angka final tetap harus diambil dari run usage/invoice Apify karena harga actor,
compute, proxy, storage, pajak, dan plan dapat berubah.

## 2. Evidence Run Yang Diberikan

Input dan output yang diamati:

| Item | Nilai |
|---|---|
| Actor | `pP8fxA1kSf7snQKNW` |
| Place ID | `ChIJ9fLOGgDraS4RRild036hTbY` |
| Place | Five Coffee Forest |
| Requested target | 500 review, berdasarkan keterangan operator |
| Actual place review count | 400 |
| Actual observed result | review positions sampai 400, sesuai data yang diberikan |
| Place rating | 4.4 |
| Observed cost | US$0.142 |
| `scraped_at` | 2026-09-15 02:30:08 UTC |
| Personal information | Off pada screenshot |
| Translation | `en` pada screenshot/output |
| Review sample rating | 5 |
| Review sample text | Tersedia pada `content` dan terjemahan pada `content_translated` |
| Owner response | Tersedia beserta waktu absolute |
| Direct review link | Tersedia pada `review_url` |

### 2.1 Temuan dari target versus hasil

`Number of reviews` adalah batas maksimum yang diminta, bukan jaminan jumlah
hasil. Location hanya memiliki 400 review, sehingga request 500 tidak bisa
menghasilkan 500 review.

Aturan sistem:

```text
requested_limit = batas atas actor
actual_items = item yang berhasil ditulis actor ke dataset
place_reviews_count = total review yang diketahui actor pada place
```

Crawler dan OneBox harus menampilkan tiga angka itu secara terpisah. Jangan
menandai job gagal hanya karena `actual_items < requested_limit` jika actor
memberi evidence bahwa end-of-feed tercapai. Sebaliknya, jangan menandai sukses
penuh jika provider berhenti karena timeout, block, atau schema error.

### 2.2 Evidence price versus observed cost

Screenshot Console menunjukkan harga mulai sekitar US$0.35 per 1,000 reviews.
Observed run menghasilkan:

```text
observed_unit_cost = US$0.142 / 400
                  = US$0.000355 per review
                  = US$0.355 per 1,000 reviews
```

Angka ini konsisten secara kasar dengan tampilan Console. Untuk budgeting,
gunakan `US$0.000355 per actual dataset item` sebagai observed baseline dan
tambahkan contingency. Jangan memakai angka itu sebagai harga kontrak.

## 3. Formula Dasar

```text
cost_per_review = 0.142 / 400 = 0.000355 USD
cost_per_1000 = 0.355 USD
cost_per_branch = actual_reviews_per_branch * 0.000355
cost_per_site = sum(cost_per_branch for 20 branches)
cost_all_companies = cost_per_site * 10
```

Planning budget dengan contingency 20 persen:

```text
planning_cost = observed_cost * 1.20
```

Contingency mencakup item tambahan, retry, run overhead, perubahan actor,
dataset/storage, dan perbedaan billing. Ini bukan klaim bahwa semua biaya pasti
ditagihkan 20 persen.

## 4. Asumsi Portfolio

Tidak ada benchmark publik yang cukup spesifik untuk menyimpulkan rata-rata
review per cabang pada semua customer OneBox. Karena itu angka di bawah adalah
planning bands, bukan fakta customer.

| Skenario | Rata-rata review historis per cabang | Review per site, 20 cabang | Review seluruh portfolio, 200 cabang | Cara membaca |
|---|---:|---:|---:|---|
| Optimal | 300 | 6,000 | 60,000 | Cabang baru/kecil atau backfill minimum |
| Realistic | 1,000 | 20,000 | 200,000 | Campuran cabang kecil dan established |
| Pessimistic | 3,000 | 60,000 | 600,000 | Cabang ramai dengan review bertahun-tahun |

Five Coffee Forest memiliki 400 review, sedangkan contoh cabang rumah sakit
yang pernah terlihat di environment memiliki ribuan review. Itu sebabnya
planning perlu memakai rentang, bukan satu angka tunggal.

## 5. Estimasi Initial Backfill Penuh

### 5.1 Tanpa contingency

| Skenario | Per cabang | Per site, 20 cabang | 10 site/company, 200 cabang |
|---|---:|---:|---:|
| Optimal, 60,000 review | US$0.1065 | US$2.13 | **US$21.30** |
| Realistic, 200,000 review | US$0.3550 | US$7.10 | **US$71.00** |
| Pessimistic, 600,000 review | US$1.0650 | US$21.30 | **US$213.00** |

Rumus contoh realistic:

```text
200 branches * 1,000 reviews * 0.000355
= 200,000 * 0.000355
= US$71.00
```

### 5.2 Dengan contingency 20 persen

| Skenario | Baseline observed | Planning budget +20% |
|---|---:|---:|
| Optimal | US$21.30 | **US$25.56** |
| Realistic | US$71.00 | **US$85.20** |
| Pessimistic | US$213.00 | **US$255.60** |

Interpretasi: apabila seluruh historical review benar-benar diminta dan actor
mengenakan biaya seperti observed run, portfolio 200 cabang berada kira-kira
di rentang US$21.30 sampai US$213.00, atau US$25.56 sampai US$255.60 dengan
contingency planning.

## 6. Estimasi Jika Initial Fetch Dibatasi 500 Review per Cabang

Untuk proses initial fetch yang hanya meminta maksimum 500 review per cabang:

```text
200 branches * 500 = 100,000 requested review slots
100,000 * 0.000355 = US$35.50 observed baseline
US$35.50 * 1.20 = US$42.60 planning budget
```

Ini adalah batas request portfolio, bukan jaminan seluruh historical review.
Jika cabang hanya memiliki 400 review, actor hanya menghasilkan 400. Jika
cabang memiliki 3,000 review, sisa 2,500 tidak otomatis terambil kecuali ada
run lanjutan dengan aturan backfill yang disetujui.

| Kondisi portfolio 200 cabang | Actual item asumsi | Baseline cost | +20% planning |
|---|---:|---:|---:|
| Semua cabang punya >=500 | 100,000 | US$35.50 | US$42.60 |
| Rata-rata 400 seperti sample | 80,000 | US$28.40 | US$34.08 |
| Campuran, 60% cap tercapai dan 40% rata-rata 300 | 84,000 | US$29.82 | US$35.78 |

Rekomendasi: untuk demo, target 10 atau 50 per cabang. Untuk production
backfill, gunakan batch kecil dan ukur actual item/billing sebelum menaikkan cap.

## 7. Estimasi Scheduled Delta per Bulan

Scheduled fetch seharusnya mengambil review baru sejak checkpoint/date cutoff,
bukan mengulang seluruh historical review. Biaya recurring lebih tepat dihitung
dari review baru.

Planning assumption:

| Skenario | Review baru per cabang per bulan | Review baru seluruh portfolio |
|---|---:|---:|
| Optimal | 10 | 2,000 |
| Realistic | 50 | 10,000 |
| Pessimistic | 200 | 40,000 |

### 7.1 Biaya delta bulanan

| Skenario | Baseline observed | +20% planning |
|---|---:|---:|
| Optimal, 2,000 new reviews | US$0.71/month | **US$0.85/month** |
| Realistic, 10,000 new reviews | US$3.55/month | **US$4.26/month** |
| Pessimistic, 40,000 new reviews | US$14.20/month | **US$17.04/month** |

Angka ini hanya output review. Run start, compute, proxy, storage, retry,
tax/plan, dan actor-specific charge harus ditambahkan dari usage report aktual.

## 8. Rekomendasi Cost Control

### Initial

- target default demo 10, bukan 500;
- cap production per location ditentukan Product, misalnya 50 atau 300;
- gunakan `placeIds` dari master Location agar tidak terjadi discovery yang
  tidak perlu;
- jangan mengisi sekaligus Place URL dan Place ID jika actor tidak menjelaskan
  dedup-nya;
- jalankan satu location sebagai canary sebelum 200 locations;
- simpan actual dataset item dan cost setiap run.

### Scheduled

- pakai date cutoff/newer-than sesuai semantics actor;
- gunakan `reviewsSort=newest` bila date filter mensyaratkannya;
- gunakan checkpoint/skip existing IDs bila actor mendukung;
- jangan scrape historical 1,000 review setiap jadwal;
- jadwalkan per batch terbatas agar tidak terjadi 200 run bersamaan;
- gunakan Crawler sebagai scheduler/orchestrator tunggal.

### Budget guard

- hard cap `maxReviews` per location/run;
- cap total actor runs per tenant per day;
- alert ketika cost per 1,000 naik di atas baseline;
- kill switch melalui `REVIEW_SOURCE_MODE` atau provider enable flag;
- retry hanya untuk transient error, bukan schema/auth;
- monitor output count versus target dan place total.

## 9. Data Privacy Dan Field Cost

Screenshot menunjukkan `Personal information` off. Output yang diberikan juga
menunjukkan:

```text
reviewer_id = null
reviewer_name = null
reviewer_url = null
reviewer_photo_url = null
reviewer_reviews_count = null
```

Dengan mode ini, text, rating, time, owner response, direct review URL, dan
place metadata tetap tersedia. Ini menurunkan data personal, tetapi membuat
field reviewer existing tidak terisi.

Keputusan product/security yang diperlukan:

| Mode | Keuntungan | Konsekuensi |
|---|---|---|
| Personal information off | Minimization dan risiko privacy lebih rendah | Nama/profile/photo/Local Guide tidak tersedia |
| Personal information on | Field reviewer lebih lengkap | Data personal masuk dataset dan DB; perlu legal/retention/access control |

Rekomendasi default: mulai dengan personal information off. Aktifkan hanya jika
use case VoC, UI, dan legal benar-benar membutuhkan identitas reviewer.

## 10. Break-even Dengan Selenium Tidak Relevan Hanya Dari Dollar

Selenium lokal dapat terlihat lebih murah jika hanya menghitung server cost,
tetapi perbandingan harus memasukkan:

- waktu maintenance selector/profile/browser;
- failure rate dan job retry;
- biaya operasi manual login;
- waktu investigasi IP/auth wall;
- kehilangan data akibat berhenti di lima review;
- cost of incident dan support.

Apify juga tidak otomatis lebih murah. Decision harus memakai metric:

```text
cost per successful review
cost per successful location
time to target 10
success rate
partial rate
duplicate rate
OneBox end-to-end completion rate
```

## 11. Acceptance Untuk Cost Trial

- [ ] Actual cost run tersimpan dari Apify usage, bukan hanya screenshot.
- [ ] Actor ID/owner/version confirmed.
- [ ] Cost per review dihitung dari actual dataset item.
- [ ] Target 10 dan target 50 diuji terpisah.
- [ ] Initial run dan scheduled delta tidak dicampur.
- [ ] Personal-data mode tercatat.
- [ ] Retry dan failed run dihitung dalam total cost.
- [ ] OneBox auto-import berhasil tanpa duplicate.
- [ ] Cost alert dan max cap aktif sebelum staging.
- [ ] Budget owner menyetujui rollout ke 200 locations.

## 12. Kesimpulan Angka

Dengan observed baseline US$0.142 untuk 400 review:

```text
1 review       = US$0.000355
1,000 review   = US$0.355
20 branches x 10 sites = 200 branches
```

Estimasi initial full backfill:

```text
Optimal      60,000 reviews  -> US$21.30 baseline / US$25.56 planning
Realistic   200,000 reviews  -> US$71.00 baseline / US$85.20 planning
Pessimistic 600,000 reviews  -> US$213.00 baseline / US$255.60 planning
```

Estimasi initial cap 500 per cabang:

```text
100,000 review slots -> US$35.50 baseline / US$42.60 planning
```

Estimasi scheduled delta per bulan:

```text
Optimal      2,000 new -> US$0.71 baseline / US$0.85 planning
Realistic   10,000 new -> US$3.55 baseline / US$4.26 planning
Pessimistic 40,000 new -> US$14.20 baseline / US$17.04 planning
```

Angka ini cukup untuk mengambil keputusan spike dan budget awal, tetapi belum
menjadi commitment produksi sampai usage report actor dikonfirmasi.

## 13. Referensi

- Actor input/output example: <https://apify.com/compass/google-maps-reviews-scraper>
- Actor API pattern: <https://apify.com/compass/google-maps-reviews-scraper/api>
- Apify Actors overview: <https://docs.apify.com/actors>
- Apify input schema: <https://docs.apify.com/actors/development/actor-definition/input-schema>
