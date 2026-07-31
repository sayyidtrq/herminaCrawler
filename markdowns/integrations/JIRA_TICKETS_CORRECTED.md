## VoC OneBox — Daftar Ticket Jira

> **Keputusan baru:**
> - Restrukturisasi menu navigasi VoC (3 grup: Transaksi/Output/Setting) **TIDAK jadi ticket terpisah** — dikerjakan di `feature/DNGO19-3346_Media-Crawler-Google-Business-Review`.
> - **Delta Sync** (`M3-03`, `M3-04`, `M3-05`) **dikerjakan di branch 3346** — bukan ticket terpisah.
> - **Review Detail** (`M8-02`) **digabung ke dalam `DNGO19-3387` (Review Manage Actions)** — satu ticket untuk seluruh alur "Ulasan" (detail + aksi kelola).
>
> Konvensi tetap: maks 5-6 MD/ticket, 1 screen = 1 ticket, branch 1:1 dengan ticket, jangan campur scope OneBox (PHP, repo `onecloud`) dengan Crawler (Python, repo `hermina_crawler`).

---

## Daftar Ticket (per board, dikonfirmasi dari screenshot)

| Ticket          | Nama                          | Status board         | Branch                                                     |
| --------------- | ----------------------------- | -------------------- | ---------------------------------------------------------- |
| **DNGO19-3385** | VOC : Master-Data-Locations   | IN DEV SPEC REVIEW   | `feature/DNGO19-3385_VOC-Master-Data-Locations`            |
| **DNGO19-3386** | VOC : Master-Data-Competitors | IN DEV SPEC REVIEW   | `feature/DNGO19-3386_VOC-Master-Data-Competitors`          |
| **DNGO19-3387** | VOC : Review Manage Actions   | IN DEV SPEC REVIEW   | `feature/DNGO19-3387_VOC-Review-Manage-Actions`            |
| **DNGO19-3388** | VOC : AI Analysis Setup       | READY TO DEV         | `feature/DNGO19-3388_VOC-AI-Analysis-Setup`                |
| **DNGO19-3407** | VOC : Enhance AI Analysis     | TODO                 | `feature/DNGO19-3407_VOC-Enhance-AI-Analysis`              |
| **DNGO19-3420** | VOC : Fetch Jobs Crawl        | TODO                 | `feature/DNGO19-3420_VOC-Fetch-Jobs-Crawl`                 |
| **DNGO19-3389** | VOC : AI Insights             | TODO                 | `feature/DNGO19-3389_VOC-AI-Insights`                      |
| **DNGO19-3390** | VOC : Crawl Scheduler         | TODO                 | `feature/DNGO19-3390_VOC-Crawl-Scheduler`                  |
| **DNGO19-3391** | VOC : Config Setup            | READY TO DEV         | `feature/DNGO19-3391_VOC-Config-Setup`                     |
| **DNGO19-3392** | VOC : Generate Reports        | READY TO DEV         | `feature/DNGO19-3392_VOC-Generate-Reports`                 |
| **DNGO19-3396** | VOC : Competitor Analysis     | TODO                 | `feature/DNGO19-3396_VOC-Competitor-Analysis`              |
| DNGO19-3346     | Menu Restructure + Delta Sync | *dikerjakan di 3346* | `feature/DNGO19-3346_Media-Crawler-Google-Business-Review` |

---
### DNGO19-3385 — Master-Data-Locations
- **Owner:** Sayyid · **Status:** IN DEV SPEC REVIEW · **MD:** ~1.6 MD
#### Description

> Menyediakan pengelolaan master data lokasi/cabang VoC di OneBox agar admin dapat menentukan lokasi yang akan dipantau dan menyimpan informasi penanggung jawab setiap lokasi.
>
> **Scope:**
> - Mempertahankan fungsi tambah, ubah, aktif/nonaktif, dan hapus lokasi yang sudah tersedia.
> - Menambahkan data PIC lokasi berupa nama, nomor WhatsApp, email, dan ID User OneBox.
> - Menyelesaikan form PIC pada halaman Location dan menghubungkannya dengan proses penyimpanan di backend.
> - Menghapus mekanisme push-sync lama pada tombol resync dan toggle setelah consumer worklist Crawler dinyatakan stabil.
> - Memperbaiki `StatusId` Connection 1039 Hermina Depok agar tidak ikut proses penjadwalan yang tidak sesuai.
> - Memastikan lokasi nonaktif tidak ikut proses crawl tanpa menghapus review dan data historisnya.
>
> **Acceptance Criteria:**
> - Admin dapat mengisi dan memperbarui data PIC lokasi.
> - Data PIC tersimpan dan tampil kembali ketika halaman dibuka ulang.
> - Format email dan nomor WhatsApp divalidasi.
> - Lokasi aktif tersedia pada worklist Crawler.
> - Lokasi nonaktif tidak ikut proses crawl berikutnya.
> - Menonaktifkan lokasi tidak menghapus review atau histori yang sudah ada.
> - Setelah consumer worklist stabil, tombol resync dan toggle tidak lagi memanggil endpoint write lama di Crawler.
> - Connection 1039 Hermina Depok memiliki `StatusId` yang benar dan tidak ikut scheduler yang tidak sesuai.
> - Perubahan tidak mengganggu fungsi CRUD Location yang sudah tersedia.
>
> **Dependency:**
> - Penghapusan push-sync lama hanya dilakukan setelah consumer worklist Crawler terbukti stabil di environment Dev.
>
> **Out of Scope:**
> - Implementasi consumer worklist di repository `hermina_crawler`.
> - Perubahan scheduler utama.
> - Analisis dan report berdasarkan lokasi.

#### Subtask 1

**Summary**

`VOC - Master Data Locations - Complete Location PIC Form and Persistence`

**Description**

> Lengkapi implementasi data PIC pada Master Data Location.
>
> **Scope:**
> - Tambahkan field Nama PIC, Nomor WhatsApp, Email, dan OneBox User ID pada form Location.
> - Muat data PIC ketika Location diedit.
> - Hubungkan field PIC dengan `VocController::locationSaveAction`.
> - Pastikan penyimpanan data PIC tidak mengubah field Location lainnya.
> - Tambahkan validasi format email dan nomor WhatsApp.
> - Tampilkan pesan validasi yang dapat dipahami user.
>
> **Acceptance Criteria:**
> - Field PIC tersedia pada form tambah dan edit Location.
> - Data PIC berhasil disimpan dan tetap tersedia setelah halaman dimuat ulang.
> - Edit data PIC tidak mengubah Place ID, status, atau data Location lain.
> - Email dan nomor WhatsApp dengan format tidak valid ditolak.
> - Kondisi PIC kosong ditangani sesuai ketentuan field wajib atau opsional.

#### Subtask 2

**Summary**

`VOC - Master Data Locations - Remove Legacy Push-Sync Bridge`

**Description**

> Hapus mekanisme transisi yang masih melakukan push data Location ke endpoint write lama di Crawler.
>
> **Scope:**
> - Hapus pemanggilan endpoint push-sync lama dari tombol resync Location.
> - Hapus pemanggilan endpoint push-sync lama dari proses toggle aktif/nonaktif.
> - Pastikan perubahan Location tetap tersedia bagi Crawler melalui worklist.
> - Pastikan tidak terjadi dual-write antara push-sync lama dan worklist.
>
> **Acceptance Criteria:**
> - Tombol resync dan toggle tidak lagi memanggil endpoint write Location lama.
> - Toggle tetap berfungsi di OneBox.
> - Perubahan Location tetap terbaca oleh Crawler melalui worklist.
> - Tidak ada dua proses sinkronisasi untuk satu perubahan.
> - Smoke test tambah, edit, toggle, dan resync Location berhasil.
>
> **Dependency:**
> - Consumer worklist Crawler telah dinyatakan stabil di environment Dev.

#### Subtask 3

**Summary**

`VOC - Master Data Locations - Fix StatusId Hermina Depok Connection 1039`

**Description**

> Perbaiki `StatusId` Connection ID 1039 untuk Hermina Depok yang menyebabkan connection ikut proses penjadwalan yang tidak sesuai.
>
> **Scope:**
> - Periksa data Connection ID 1039.
> - Ubah `StatusId` menjadi `CNS2` sesuai status yang seharusnya.
> - Periksa query scheduler yang sebelumnya memilih connection tersebut.
> - Pastikan perubahan hanya berlaku untuk Connection ID 1039.
>
> **Acceptance Criteria:**
> - Connection ID 1039 memiliki `StatusId=CNS2`.
> - Connection ID 1039 tidak lagi ikut scheduler yang tidak sesuai.
> - Tidak ada Connection lain yang berubah.
> - Perubahan berhasil diverifikasi pada environment Dev.


### DNGO19-3386 — Master-Data-Competitors

- **Owner:** OneBox (OB) · **Status:** IN DEV SPEC REVIEW

#### Description

> Menyediakan pengelolaan master data kompetitor di OneBox agar admin dapat menentukan kompetitor yang ingin dipantau dan membedakannya dari lokasi milik sendiri.
>
> **Scope:**
> - Mempertahankan fungsi tambah, ubah, aktif/nonaktif, dan hapus kompetitor yang sudah tersedia.
> - Menggunakan pola pengelolaan yang konsisten dengan Master Data Location.
> - Menetapkan `StatusId=CNS3` untuk Connection kompetitor.
> - Memastikan Connection kompetitor tidak ikut scheduler yang hanya ditujukan untuk lokasi milik sendiri.
> - Memastikan kompetitor aktif tersedia melalui worklist untuk kebutuhan Crawler.
> - Memastikan review kompetitor tidak otomatis dibuat sebagai Ticket OneBox.
>
> **Acceptance Criteria:**
> - Admin dapat menambah, mengubah, menonaktifkan, dan menghapus kompetitor.
> - Kompetitor baru otomatis menggunakan `StatusId=CNS3`.
> - Mengedit kompetitor tidak mengubah `StatusId` menjadi status Location.
> - Kompetitor tidak ikut scheduler lokasi milik sendiri.
> - Kompetitor aktif tersedia pada worklist.
> - Kompetitor nonaktif tidak diproses pada crawl berikutnya.
> - Review kompetitor tidak dibuat sebagai Ticket OneBox.
> - Perubahan tidak memengaruhi Master Data Location.
>
> **Out of Scope:**
> - Halaman perbandingan performa kompetitor; pekerjaan tersebut berada pada DNGO19-3396.
> - Implementasi endpoint `competitor_reviews` di Crawler.
> - Penambahan data PIC kompetitor sebelum mendapatkan konfirmasi dari Product.

#### Subtask 1

**Summary**

`VOC - Master Data Competitors - Verify Status and Scheduler Exclusion`

**Description**

> Verifikasi bahwa seluruh Connection kompetitor menggunakan `StatusId=CNS3` dan tidak ikut scheduler yang hanya ditujukan untuk lokasi milik sendiri.
>
> **Scope:**
> - Periksa proses create dan update kompetitor.
> - Periksa nilai default `StatusId` kompetitor.
> - Periksa query scheduler yang memilih Connection.
> - Uji kompetitor dalam kondisi aktif dan nonaktif.
>
> **Acceptance Criteria:**
> - Kompetitor baru otomatis memperoleh `StatusId=CNS3`.
> - Edit kompetitor tidak mengganti `StatusId` menjadi status Location.
> - Connection dengan `StatusId=CNS3` tidak ikut scheduler Location.
> - Kompetitor nonaktif tidak ikut proses crawl.
> - Hasil verifikasi dicatat sebagai evidence pada subtask.


### DNGO19-3387 — Review Manage Actions

- **Owner:** OneBox (OB) · **Status:** IN DEV SPEC REVIEW · **MD:** 3 + 4 = **7 MD** ⚠️ melebihi cap 5MD

> **Catatan:** tetap satu ticket induk dan satu branch, tetapi pekerjaan dibagi menjadi dua subtask agar progress dan estimasi dapat dilacak.

#### Description

> Menyediakan alur lengkap untuk melihat detail review dan menindaklanjutinya sebagai Ticket OneBox sehingga agent tidak perlu menggunakan sistem pengelolaan yang terpisah.
>
> **Scope:**
> - Menampilkan detail review dari halaman daftar Ulasan.
> - Menampilkan teks review lengkap, rating, sentiment, urgency, kategori, summary, dan recommended action.
> - Menampilkan informasi lokasi, source, dan waktu review apabila tersedia.
> - Menyediakan akses ke Ticket OneBox yang terkait.
> - Menyediakan aksi assign review/Ticket kepada agent.
> - Menyediakan aksi perubahan status sesuai workflow Ticket OneBox.
> - Menyediakan aksi penambahan internal note.
> - Menggunakan mekanisme Ticket OneBox yang sudah tersedia, bukan membuat sistem assignment, status, atau note baru khusus VoC.
>
> **Acceptance Criteria:**
> - User dapat membuka detail dari satu baris review.
> - Detail yang ditampilkan sesuai review yang dipilih.
> - Teks review di-escape sebelum ditampilkan.
> - Field hasil analisis ditampilkan apabila tersedia; field kosong memiliki empty state yang jelas.
> - User dapat membuka Ticket OneBox yang terkait menggunakan `Ticket.Id`.
> - User yang memiliki permission dapat melakukan assign, mengubah status, dan menambahkan internal note.
> - Internal note tersimpan pada histori Ticket.
> - Aksi yang gagal menampilkan pesan error dan tidak menghasilkan perubahan parsial.
> - Permission mengikuti mekanisme permission Ticket OneBox.
>
> **Technical Reference:**
> - `TicketController::showTicketDetail`
> - `addTaskAssignTo`
> - `saveTicketUpdate`
> - `saveTicketMessage`
> - `openTabTicketDetail(Id, 'ticket-center', 'Case Detail', 'Ticket/showTicketDetail', 'POST')`
>
> **Out of Scope:**
> - Membuat workflow Ticket baru.
> - Membuat tabel assignment atau note khusus VoC.
> - Reply langsung ke Google Business Review.
> - Mengubah hasil AI dari halaman Review Detail.

#### Subtask 1

**Summary**

`VOC - Review Manage Actions - Implement Review Detail`

**Description**

> Implementasikan halaman atau panel Review Detail yang dapat dibuka dari daftar Ulasan.
>
> **Scope:**
> - Gunakan `id` dari `reviewsDataAction` sebagai `Ticket.Id`.
> - Tampilkan teks review lengkap, rating, sentiment, urgency, kategori, summary, dan recommended action.
> - Tampilkan lokasi, source, dan waktu review apabila tersedia.
> - Tampilkan link atau tombol untuk membuka Ticket OneBox.
> - Tangani data analisis yang kosong atau belum selesai.
> - Escape seluruh konten review yang berasal dari sumber eksternal.
>
> **Acceptance Criteria:**
> - Klik satu review membuka detail yang benar.
> - Seluruh field yang tersedia dapat ditampilkan.
> - Field kosong memiliki placeholder yang konsisten.
> - Teks review tidak dapat mengeksekusi HTML atau JavaScript.
> - User dapat membuka Ticket OneBox terkait.
> - Error ketika memuat detail ditampilkan dengan pesan yang jelas.

#### Subtask 2

**Summary**

`VOC - Review Manage Actions - Implement Assign, Resolve, and Internal Note`

**Description**

> Tambahkan aksi assign, perubahan status, dan internal note dari Review Detail menggunakan mekanisme Ticket OneBox yang sudah tersedia.
>
> **Scope:**
> - Tambahkan aksi assign kepada agent.
> - Tambahkan aksi perubahan status sesuai workflow Ticket.
> - Tambahkan form internal note.
> - Gunakan service dan endpoint Ticket OneBox yang sudah tersedia.
> - Terapkan permission yang sama dengan Ticket OneBox.
>
> **Acceptance Criteria:**
> - User yang berwenang dapat memilih agent dan menyimpan assignment.
> - Assignment terbaru ditampilkan setelah penyimpanan berhasil.
> - Status Ticket dapat diubah mengikuti transition yang valid.
> - Internal note tersimpan pada histori Ticket.
> - Aksi yang berhasil langsung tercermin pada Review Detail.
> - Aksi yang gagal tidak mengubah Ticket secara parsial.
> - User tanpa permission tidak dapat menjalankan action.
> - Tidak ada workflow baru yang menduplikasi mekanisme Ticket OneBox.

### DNGO19-3388 — AI Analysis Setup

- **Owner:** OneBox (OB) · **Status:** READY TO DEV · **MD:** 4 MD

#### Description

> Menyediakan konfigurasi analisis AI di OneBox dan mengirimkan konfigurasi tersebut ke Crawler agar proses analisis menggunakan parameter yang konsisten dan dapat dikontrol per Connection.
>
> **Scope:**
> - Menentukan kontrak parameter `ai_enabled`, `model`, `prompt_version`, dan `threshold`.
> - Menampilkan parameter pada halaman AI Analysis Setup.
> - Menyimpan parameter pada `Connection.Options`.
> - Mengirimkan parameter melalui worklist ke Crawler.
> - Menangani Connection lama yang belum memiliki konfigurasi AI.
> - Menjalankan klasifikasi berbasis `Service\Ruling` sebelum proses AI.
> - Menggunakan rule yang sudah tersedia tanpa membuat sistem rule baru.
>
> **Acceptance Criteria:**
> - Admin dapat mengaktifkan atau menonaktifkan analisis AI.
> - Admin dapat memilih model dan prompt version yang valid serta mengatur threshold.
> - Parameter divalidasi sebelum disimpan dan tersimpan per Connection.
> - Worklist mengirim parameter menggunakan nama dan tipe data yang telah disepakati.
> - Connection lama menggunakan nilai default yang aman.
> - Menonaktifkan AI tidak menghentikan proses crawl.
> - `Service\Ruling` dijalankan sebelum proses AI.
>
> **Out of Scope:**
> - Antrean analisis AI di Crawler.
> - Perhitungan `tokens_used`.
> - Perbaikan koneksi LLM lokal.
> - Perbaikan prompt kategori.
> - Halaman hasil AI Insights.

#### Subtask 1

**Summary**

`VOC - AI Analysis Setup - Define AI Configuration Contract`

**Description**

> Definisikan kontrak konfigurasi AI antara OneBox dan Crawler untuk parameter `ai_enabled`, `model`, `prompt_version`, dan `threshold`.
>
> **Scope:**
> - Tentukan tipe data, nilai default, dan nilai yang diperbolehkan untuk setiap parameter.
> - Tentukan perilaku ketika parameter belum tersedia.
> - Tentukan perilaku ketika `ai_enabled=false`.
>
> **Acceptance Criteria:**
> - Nama dan tipe data seluruh parameter terdokumentasi.
> - Nilai default, daftar model, format threshold, dan perilaku Connection lama disepakati.
> - Tim OneBox dan Crawler menggunakan kontrak yang sama.

#### Subtask 2

**Summary**

`VOC - AI Analysis Setup - Persist and Distribute AI Configuration`

**Description**

> Implementasikan form, penyimpanan, dan distribusi konfigurasi AI melalui worklist.
>
> **Scope:**
> - Tampilkan dan simpan konfigurasi AI pada `Connection.Options`.
> - Muat konfigurasi ketika halaman dibuka kembali.
> - Sertakan konfigurasi pada response worklist.
> - Terapkan default untuk Connection yang belum memiliki konfigurasi.
>
> **Acceptance Criteria:**
> - Konfigurasi dapat disimpan dan diedit.
> - Update konfigurasi AI tidak menghapus option Connection lainnya.
> - Worklist mengembalikan parameter sesuai kontrak.
> - Connection lama mendapatkan default yang aman.
> - API key atau credential tidak ikut dikirim sebagai parameter konfigurasi.

#### Subtask 3

**Summary**

`VOC - AI Analysis Setup - Apply Rule-First Classification`

**Description**

> Integrasikan klasifikasi berbasis `Service\Ruling` sebelum proses analisis AI agar rule bisnis yang tersedia diterapkan terlebih dahulu.
>
> **Scope:**
> - Gunakan `Service\Ruling` yang sudah tersedia.
> - Jalankan rule sebelum proses AI.
> - Gunakan struktur hasil klasifikasi yang konsisten.
> - Pastikan alur pembuatan Ticket tetap berfungsi ketika AI dinonaktifkan.
>
> **Acceptance Criteria:**
> - `Service\Ruling` dijalankan sebelum AI.
> - Tidak dibuat service ruling baru yang menduplikasi implementasi existing.
> - Hasil rule tersimpan atau diteruskan menggunakan struktur yang disepakati.
> - Proses Ticket tetap berfungsi ketika AI tidak aktif.

### DNGO19-3407 — Enhance AI Analysis

- **Suggested Summary:** `VOC : Enhance AI Analysis`
- **Owner:** Sayyid
- **Status:** TODO
- **Current Jira Work Type:** Task
- **Recommended Jira Work Type:** New Feature
- **Repository:** `onecloud` (OneBox)
- **Base Branch:** `feature/voc`
- **Branch:** `feature/DNGO19-3407_VOC-Enhance-AI-Analysis`

#### Description

> Meningkatkan performa, kualitas, efisiensi, dan reliability proses AI Analysis yang saat ini masih membutuhkan waktu lama.
>
> Pekerjaan mencakup evaluasi alur analisis yang berjalan saat ini, optimasi proses dan pemanggilan API AI, serta evaluasi model yang digunakan agar hasil analisis tetap akurat dengan waktu proses dan penggunaan resource yang lebih efisien.
>
> **OneCloud Boundary:**
> - Branch DNGO19-3407 di OneCloud menangani orchestration, konfigurasi, pemilihan review yang perlu dianalisis, optimasi request ke service AI/Crawler, validasi response, dan monitoring dari sisi OneBox.
> - Eksekusi LLM dan perubahan runtime/model Python tetap berada di service VoC/Crawler. Jika benchmark mengharuskan perubahan di Crawler, buat linked work item dan branch Crawler terpisah; jangan memasukkan perubahan dua repository ke branch OneCloud ini.
>
> **Scope:**
> - Ukur baseline proses AI Analysis saat ini, termasuk queue time, waktu proses per review/batch, waktu respons API, jumlah token, error rate, dan jumlah retry.
> - Identifikasi bottleneck pada antrean, preprocessing, pemanggilan API AI, parsing response, dan penyimpanan hasil.
> - Optimalkan logika pemanggilan API agar hanya review yang baru, berubah, atau belum memiliki hasil valid yang dianalisis.
> - Terapkan idempotency dan deduplication agar retry atau trigger berulang tidak menghasilkan pemanggilan API dan pencatatan usage ganda.
> - Evaluasi batching, concurrency, rate limit, timeout, retry, dan exponential backoff sesuai kemampuan provider/model.
> - Evaluasi model yang digunakan saat ini dan bandingkan dengan kandidat model lain berdasarkan kualitas hasil, latency, stabilitas, kebutuhan resource, dan biaya/token.
> - Perbaiki prompt, preprocessing, atau parsing response apabila diperlukan untuk menjaga output tetap mengikuti schema sentiment, urgency, category, summary, dan recommended action.
> - Tambahkan monitoring untuk durasi proses, jumlah request, token usage, retry, failure, dan model yang digunakan.
> - Sediakan mekanisme rollback atau fallback apabila model atau konfigurasi baru mengalami masalah.
>
> **Acceptance Criteria:**
> - Baseline performa dan bottleneck proses AI Analysis terdokumentasi.
> - Target improvement untuk latency, throughput, error rate, dan token usage disepakati sebelum implementasi optimasi.
> - Pemilihan model didukung hasil benchmark menggunakan dataset review yang representatif.
> - Proses setelah optimasi menunjukkan improvement terukur dibandingkan baseline berdasarkan target yang disepakati.
> - Review yang sudah memiliki hasil valid tidak dianalisis ulang tanpa alasan yang jelas.
> - Retry tidak menghasilkan duplicate analysis, duplicate API call yang tidak diperlukan, atau duplicate usage record.
> - Error yang dapat di-retry menggunakan retry dan backoff; error permanen tidak diulang tanpa batas.
> - Response model divalidasi sebelum disimpan.
> - Output tetap kompatibel dengan field sentiment, urgency, category, summary, dan recommended action yang digunakan OneBox.
> - Model dan konfigurasi baru dapat di-disable atau dikembalikan ke konfigurasi sebelumnya.
> - Log tidak menyimpan API key, credential, atau teks review lengkap.
>
> **Dependency:**
> - Kontrak parameter AI dari DNGO19-3388.
> - Antrean analisis AI di Crawler.
> - Data `tokens_used` dan status analisis.
> - Dataset review representatif untuk benchmark kualitas.
>
> **Out of Scope:**
> - Perubahan tampilan AI Insights.
> - Perubahan halaman AI Analysis Setup di OneBox, kecuali diperlukan penyesuaian kontrak parameter.
> - Perubahan runtime/model Python, queue worker, atau provider client di repository Crawler; pekerjaan tersebut harus menggunakan linked work item terpisah.
> - Training custom model dari awal tanpa persetujuan Product dan technical review.
> - Perubahan kategori bisnis tanpa persetujuan Product.

#### Subtask 1

**Summary**

`Dev Specification - VOC - Enhance AI Analysis`

**Description**

> Analisis proses AI Analysis yang berjalan saat ini dan tentukan target optimasi yang terukur.
>
> **Scope:**
> - Petakan alur dari review masuk sampai hasil AI tersimpan.
> - Ukur queue time, processing time, API latency, token usage, retry, dan error rate.
> - Identifikasi bottleneck utama.
> - Tentukan dataset benchmark yang mewakili variasi rating, sentiment, urgency, kategori, dan panjang review.
> - Tentukan target latency, throughput, error rate, dan token usage.
> - Dokumentasikan rencana perubahan dan risiko kompatibilitas.
>
> **Acceptance Criteria:**
> - Baseline performa tersedia dan dapat direproduksi.
> - Bottleneck utama teridentifikasi berdasarkan evidence.
> - Dataset benchmark dan metode penilaian disepakati.
> - Target optimasi disetujui sebelum implementation dimulai.
> - Batas scope antara optimasi Crawler dan konfigurasi OneBox terdokumentasi.

#### Subtask 2

**Summary**

`VOC - Enhance AI Analysis - Optimize Processing and API Call Flow`

**Description**

> Optimalkan alur pemrosesan AI dan logika pemanggilan API agar proses lebih cepat, efisien, dan tidak melakukan request yang tidak diperlukan.
>
> **Scope:**
> - Analisis hanya review baru, berubah, atau belum memiliki hasil valid.
> - Tambahkan idempotency dan deduplication untuk analysis job dan API request.
> - Evaluasi penggunaan batch request apabila didukung provider.
> - Atur concurrency dan rate limit agar throughput meningkat tanpa melampaui kapasitas provider.
> - Terapkan timeout, retry terbatas, exponential backoff, dan error classification.
> - Pastikan status analysis hanya menjadi completed setelah response tervalidasi dan hasil berhasil disimpan.
>
> **Acceptance Criteria:**
> - Trigger atau retry berulang tidak membuat analysis record ganda.
> - Review dengan hasil valid tidak memanggil API kembali tanpa explicit rerun.
> - Timeout dan error sementara di-retry sesuai policy.
> - Error permanen tidak di-retry tanpa batas.
> - Analysis yang gagal tidak ditandai completed.
> - Throughput dan latency memenuhi target yang ditentukan pada Dev Specification.
> - Token dan usage tidak tercatat ganda.

#### Subtask 3

**Summary**

`VOC - Enhance AI Analysis - Evaluate AI Model and Integration Contract`

**Description**

> Evaluasi model AI yang digunakan saat ini dan kandidat model lain dari sisi kebutuhan OneBox, lalu finalisasi kontrak integrasi untuk model yang memberikan keseimbangan terbaik antara kualitas hasil, latency, stabilitas, dan penggunaan resource.
>
> **Scope:**
> - Dokumentasikan model dan konfigurasi yang digunakan saat ini.
> - Tentukan kandidat model yang kompatibel dengan kebutuhan deployment.
> - Jalankan benchmark menggunakan dataset review yang telah disepakati.
> - Bandingkan kualitas sentiment, urgency, category, summary, dan recommended action.
> - Bandingkan latency, token usage, error rate, kebutuhan resource, dan biaya apabila menggunakan provider berbayar.
> - Tentukan model utama dan fallback berdasarkan hasil benchmark.
> - Dokumentasikan perubahan yang dapat dilakukan melalui konfigurasi OneCloud dan perubahan yang memerlukan linked work item di Crawler.
>
> **Acceptance Criteria:**
> - Model existing dan seluruh kandidat diuji menggunakan dataset yang sama.
> - Hasil benchmark terdokumentasi dan dapat dibandingkan.
> - Model dipilih berdasarkan evidence, bukan hanya asumsi.
> - Model terpilih memenuhi schema output yang dibutuhkan OneBox.
> - Penurunan kualitas yang signifikan tidak diterima hanya untuk mengejar kecepatan.
> - Model dapat diganti atau dikembalikan melalui konfigurasi tanpa perubahan data historis.
> - Perubahan runtime/model di Crawler tidak dimasukkan ke branch OneCloud DNGO19-3407.

#### Subtask 4

**Summary**

`VOC - Enhance AI Analysis - Add Monitoring, Reliability, and Rollback`

**Description**

> Tambahkan observability dan mekanisme pengamanan agar performa AI Analysis dapat dipantau dan perubahan model atau optimasi dapat dikembalikan dengan aman.
>
> **Scope:**
> - Catat durasi antrean, durasi proses, API latency, jumlah request, retry, failure, token usage, dan model yang digunakan.
> - Tambahkan correlation ID atau analysis job ID untuk menelusuri satu proses tanpa menyimpan data sensitif.
> - Tambahkan alert atau indikator untuk failure rate tinggi, antrean menumpuk, atau latency melewati target.
> - Sediakan feature flag, configuration switch, atau prosedur rollback untuk kembali ke model dan alur sebelumnya.
>
> **Acceptance Criteria:**
> - Metrik utama dapat dipantau per run atau periode.
> - Failure dapat ditelusuri menggunakan job/correlation ID.
> - Log tidak memuat API key, credential, atau teks review lengkap.
> - Kondisi antrean menumpuk dan error rate tinggi dapat diketahui sebelum dilaporkan user.
> - Model atau optimasi baru dapat dinonaktifkan tanpa menghapus hasil analisis historis.
> - Prosedur rollback terdokumentasi dan berhasil diuji.

### DNGO19-3420 — Fetch Jobs Crawl

- **Suggested Summary:** `VOC : Fetch Jobs Crawl`
- **Jira Work Type:** New Feature
- **Owner:** Sayyid
- **Status:** TODO
- **Repository:** `onecloud` (OneBox)
- **Base Branch:** `feature/voc`
- **Branch:** `feature/DNGO19-3420_VOC-Fetch-Jobs-Crawl`

#### Description

> Menyediakan Fetch Jobs Crawl di OneBox untuk menjalankan proses scraping review melalui service Crawler yang terkontrol, sehingga OneBox tidak menjalankan Selenium atau connector scraping secara langsung.
>
> Feature ini menjadi entry point standar untuk menjalankan crawl satu lokasi atau beberapa lokasi aktif, memantau status proses, dan melihat hasil fetch berupa jumlah review yang ditemukan, disimpan, terdeteksi duplikat, atau gagal.
>
> **Scope:**
> - Sediakan service/client OneCloud untuk mengirim request crawl review ke Crawler.
> - Dukung crawl untuk satu lokasi.
> - Dukung crawl untuk seluruh lokasi aktif apabila disetujui dalam Dev Specification.
> - Terima parameter minimum berupa location, source/connector, target review count, dan dry run.
> - Validasi bahwa lokasi aktif, memiliki company/tenant, dan dapat diakses oleh user atau service pemanggil.
> - Kirim request pembuatan crawl job ke service Crawler.
> - Pastikan controller atau UI OneBox hanya memanggil service/client OneCloud, bukan memanggil Selenium atau connector secara langsung.
> - Gunakan proses non-blocking agar request tidak menunggu Selenium selesai.
> - Kembalikan `job_id` atau `batch_id` agar status proses dapat dipantau.
> - Simpan status job: queued, running, success, partial_success, failed, atau cancelled apabila cancel didukung.
> - Simpan hasil proses berupa fetched, inserted, duplicate/deduped, dan failed.
> - Setelah crawl selesai, jalankan atau hubungkan proses sinkronisasi review sesuai mekanisme delta yang telah disepakati.
> - Catat error dan metadata teknis yang aman untuk troubleshooting.
> - Sediakan fetch log atau job detail untuk melihat hasil proses.
>
> **Acceptance Criteria:**
> - Pemanggil dapat membuat Fetch Job untuk satu lokasi aktif.
> - Request mengembalikan `job_id` atau `batch_id` tanpa menunggu seluruh proses scraping selesai.
> - Scraping dijalankan oleh service Crawler; UI dan controller OneBox hanya memanggil service/client OneCloud.
> - Lokasi yang tidak aktif, tidak valid, atau berada di tenant lain ditolak.
> - Job memiliki status yang dapat dipantau dari awal sampai selesai.
> - Hasil job mencatat jumlah review fetched, inserted, deduped, dan failed.
> - Job yang diulang tidak menyebabkan review tersinkron menjadi Ticket ganda.
> - Dry run tidak menyimpan review atau mengubah data produksi.
> - Error pada satu lokasi tidak menyebabkan status lokasi lain menjadi tidak jelas.
> - Timeout dan error sementara ditangani menggunakan retry policy yang terbatas.
> - API key, credential, session, dan raw review text tidak ditampilkan pada log.
>
> **Dependency:**
> - Location/worklist telah tersedia dan ter-scope berdasarkan tenant.
> - Endpoint crawl job pada Crawler tersedia dan dapat diakses dari environment OneBox.
> - Queue, worker, dan connector scraping tersedia di sisi Crawler untuk proses non-blocking.
> - Kunci idempotency review telah ditentukan.
>
> **Out of Scope:**
> - Penjadwalan otomatis tiga window; ditangani DNGO19-3390 Crawl Scheduler.
> - Delta Sync review ke OneBox; ditangani DNGO19-3346.
> - Implementasi queue, worker, Selenium, atau connector scraping di Crawler.
> - AI Analysis setelah review tersimpan.
> - Tampilan AI Insights.
> - Competitor Analysis.

#### Subtask 1

**Summary**

`Dev Specification - VOC - Fetch Jobs Crawl`

**Description**

> Finalisasi kontrak, lifecycle, dan boundary Fetch Jobs Crawl sebelum development.
>
> **Scope:**
> - Tentukan request dan response untuk membuat crawl job.
> - Tentukan penggunaan `job_id` atau `batch_id`.
> - Tentukan status lifecycle job.
> - Tentukan parameter location, source, target review count, dry run, dan date range apabila diperlukan.
> - Tentukan aturan fetch satu lokasi dan fetch seluruh lokasi aktif.
> - Tentukan retry, timeout, cancellation, dan idempotency policy.
> - Tentukan hubungan antara crawl job dan fetch log.
>
> **Acceptance Criteria:**
> - Kontrak request dan response terdokumentasi.
> - Status lifecycle dan transition job terdokumentasi.
> - Aturan tenant, permission, dan validasi lokasi disepakati.
> - Batas target review dan quota disepakati.
> - Perilaku dry run disepakati.
> - Dependency terhadap queue, worker, dan connector terdokumentasi.
> - Scope mendapatkan approval sebelum implementasi dimulai.

#### Subtask 2

**Summary**

`VOC - Fetch Jobs Crawl - Implement OneCloud Fetch Job Service Client`

**Description**

> Implementasikan service/client di OneCloud untuk membuat Fetch Job melalui API Crawler secara non-blocking.
>
> **Scope:**
> - Validasi tenant, lokasi, status aktif, source, target review count, dan dry run.
> - Bentuk request sesuai kontrak API Crawler.
> - Kirim request crawl melalui client/service OneCloud.
> - Terima dan simpan `job_id` atau `batch_id` dari Crawler.
> - Simpan status awal job di OneBox untuk kebutuhan monitoring.
> - Terapkan idempotency agar request yang sama tidak membuat job ganda secara tidak sengaja.
>
> **Acceptance Criteria:**
> - Request valid diteruskan ke service Crawler dan menghasilkan job queued.
> - OneBox menerima response tanpa menunggu Selenium selesai.
> - Request invalid tidak membuat job.
> - Lokasi tenant lain tidak dapat diproses.
> - Duplicate request ditangani sesuai idempotency policy.
> - Credential dan konfigurasi internal tidak dikembalikan pada response.

#### Subtask 3

**Summary**

`VOC - Fetch Jobs Crawl - Implement Trigger and Review Sync Orchestration`

**Description**

> Implementasikan orchestration di OneBox untuk memicu crawl melalui service Crawler, memantau penyelesaiannya, dan melanjutkan sinkronisasi review.
>
> **Scope:**
> - Sediakan trigger Fetch Job dari flow OneBox yang telah disepakati.
> - Pantau status `job_id` atau `batch_id` sampai mencapai status terminal.
> - Simpan pembaruan status dan counters dari Crawler.
> - Setelah crawl berhasil atau partial success, jalankan proses delta pull/sinkronisasi review sesuai kontrak.
> - Pastikan dry run tidak menjalankan penyimpanan atau sinkronisasi review.
> - Tangani job gagal tanpa memajukan checkpoint secara tidak aman.
>
> **Acceptance Criteria:**
> - Satu trigger OneBox menghasilkan satu job Crawler sesuai idempotency policy.
> - OneBox tidak menjalankan Selenium atau connector secara langsung.
> - Status dan counters job tetap konsisten untuk success, partial success, dan failed.
> - Delta pull hanya dijalankan setelah hasil crawl siap.
> - Review yang sudah tersinkron tidak dibuat menjadi Ticket ganda.
> - Dry run tidak menyimpan atau menyinkronkan review.
> - Job gagal tidak memajukan checkpoint.

#### Subtask 4

**Summary**

`VOC - Fetch Jobs Crawl - Implement Job Status, Logs, Retry, and Cancel`

**Description**

> Sediakan halaman/endpoint OneBox untuk memantau dan mengelola Fetch Job yang dijalankan melalui service Crawler.
>
> **Scope:**
> - Sediakan detail status berdasarkan `job_id` atau `batch_id`.
> - Tampilkan started time, finished time, duration, status, counters, dan error summary.
> - Teruskan retry untuk job gagal ke service Crawler sesuai retry policy.
> - Teruskan cancel untuk job queued atau running apabila API Crawler mendukung cancellation yang aman.
> - Pastikan retry menggunakan job atau idempotency context yang sama.
>
> **Acceptance Criteria:**
> - Status job dapat dilihat dari queued sampai terminal.
> - Detail job hanya dapat diakses tenant yang berhak.
> - Retry tidak membuat review atau usage ganda.
> - Job yang tidak retryable ditolak ketika diminta retry.
> - Cancel tidak meninggalkan job pada status running tanpa batas.
> - Log tidak memuat credential atau raw review text lengkap.

### DNGO19-3389 — AI Insights

- **Owner:** OneBox (OB) · **Status:** TODO · **MD:** 3 MD

#### Description

> Menyediakan halaman AI Insights agar user dapat membaca dan memfilter hasil analisis AI yang telah selesai diproses.
>
> **Scope:**
> - Menampilkan daftar hasil analisis AI berupa sentiment, urgency, kategori, summary, dan recommended action.
> - Menyediakan filter berdasarkan rentang tanggal, lokasi, sentiment, urgency, dan kategori.
> - Menyediakan paging dan filtering di server.
> - Menyediakan akses dari hasil Insight ke Review Detail.
> - Menampilkan status yang jelas untuk analisis yang belum selesai atau gagal.
>
> **Acceptance Criteria:**
> - Halaman hanya membaca hasil analisis dan tidak menjalankan proses AI.
> - User dapat memfilter hasil berdasarkan filter yang telah disepakati.
> - Paging dilakukan di server, bukan di browser.
> - User hanya dapat melihat data tenant-nya.
> - User dapat membuka Review Detail dari hasil Insight.
> - Data yang belum selesai dianalisis tidak ditampilkan sebagai hasil final.
> - Analisis gagal dan field hasil AI yang kosong memiliki status yang jelas.
>
> **Dependency:**
> - DNGO19-3388 AI Analysis Setup.
> - Data hasil analisis dari Crawler.
> - Struktur menu VoC dari DNGO19-3346.
>
> **Out of Scope:**
> - Trigger dan rerun analisis.
> - Konfigurasi model atau prompt.
> - Perbaikan kualitas output AI.
> - Pengeditan manual hasil AI.

#### Subtask 1

**Summary**

`Dev Specification - VOC - AI Insights`

**Description**

> Finalisasi kebutuhan halaman AI Insights sebelum development.
>
> **Scope:**
> - Tentukan field, filter, default rentang tanggal, dan sorting.
> - Tentukan status `pending`, `completed`, `failed`, dan `skipped`.
> - Tentukan apakah MVP hanya berupa list atau membutuhkan KPI/chart.
> - Buat wireframe atau referensi tampilan.
> - Dokumentasikan mapping data Crawler ke field OneBox.
>
> **Acceptance Criteria:**
> - Field, filter, default periode, dan sorting disetujui Product.
> - Status analisis dan mapping data terdokumentasi.
> - Wireframe atau contoh tampilan tersedia.
> - Scope implementasi mendapatkan approval Product.

#### Subtask 2

**Summary**

`VOC - AI Insights - Implement Insights Page`

**Description**

> Implementasikan halaman AI Insights berdasarkan Dev Specification yang telah disetujui.
>
> **Scope:**
> - Implementasikan query hasil analisis.
> - Implementasikan filter dan paging server-side.
> - Tampilkan sentiment, urgency, kategori, summary, recommended action, dan status analisis.
> - Tambahkan link ke Review Detail.
> - Tambahkan loading, empty, dan error state.
>
> **Acceptance Criteria:**
> - Data yang ditampilkan sesuai tenant aktif.
> - Filter menghasilkan data yang benar dan paging dilakukan di server.
> - User dapat membuka Review Detail.
> - Loading, empty, dan error state tersedia.
> - Data pending atau failed tidak ditampilkan sebagai hasil completed.

### DNGO19-3390 — Crawl Scheduler

- **Owner:** OneBox (OB)
- **Status:** TODO
- **MD:** hingga 8 MD
- **Catatan estimasi:** estimasi diletakkan pada dua subtask implementasi agar tidak terjadi double counting pada parent.

#### Description

> Menyediakan scheduler otomatis di OneBox untuk menjalankan crawl tiga kali sehari per site tanpa menjalankan Selenium secara blocking dan tanpa menghasilkan run ganda.
>
> **Scope:**
> - Membuat tiga schedule occurrence per site per tanggal lokal: pagi 05:00–06:59, siang 11:00–12:59, dan malam 21:00–22:59.
> - Menghasilkan `planned_at` secara acak dalam setiap window dan menyimpannya agar tidak berubah setelah restart atau retry.
> - Menggunakan timezone site dengan default `Asia/Jakarta`.
> - Menjalankan crawl melalui endpoint enqueue non-blocking.
> - Menggunakan idempotency key `site:local_date:slot`.
> - Mencegah lebih dari satu run aktif pada site dan slot yang sama.
> - Menyimpan histori planned time, actual time, status, dan counters.
> - Menyediakan tombol `Run now` untuk user yang berwenang.
>
> **Acceptance Criteria:**
> - Setiap site aktif memiliki tepat tiga occurrence per tanggal lokal.
> - `planned_at` berada pada window yang benar dan tidak berubah setelah restart.
> - Dua trigger bersamaan hanya menghasilkan satu run.
> - Trigger crawl menerima `batch_id` tanpa menunggu Selenium selesai.
> - Run memiliki status `planned`, `running`, `success`, `partial_success`, `failed`, atau `skipped`.
> - Counter `fetched`, `inserted`, `deduped`, dan `failed` tersimpan.
> - User berwenang dapat menjalankan `Run now`.
> - Manual run tidak merusak occurrence terjadwal.
> - Credential, token, cursor utuh, dan raw review text tidak ditampilkan pada histori.
>
> **Dependency:**
> - Endpoint enqueue non-blocking dan worker crawl di Crawler.
> - Endpoint atau mekanisme monitoring status batch.
> - Delta Sync pada DNGO19-3346.
>
> **Out of Scope:**
> - Membuat scheduler kedua di Crawler.
> - Implementasi worker Selenium.
> - Implementasi checkpoint delta dan targeted backfill.

#### Subtask 1

**Summary**

`VOC - Crawl Scheduler - Implement Scheduler Core and Concurrency Control`

**Description**

> Implementasikan schedule occurrence, random persistent planning, timezone, locking, dan idempotency.
>
> **Scope:**
> - Buat tabel schedule occurrence dengan unique constraint untuk `site_id`, `local_date`, dan `slot`.
> - Buat tiga occurrence per hari untuk setiap site aktif.
> - Generate `planned_at` secara acak dalam window dan simpan timezone site.
> - Terapkan lock agar hanya satu worker menjalankan occurrence.
> - Gunakan idempotency key `site:date:slot`.
> - Pastikan retry menggunakan occurrence yang sama.
>
> **Acceptance Criteria:**
> - Satu site menghasilkan tepat tiga occurrence per tanggal lokal.
> - `planned_at` berada dalam window dan tidak berubah setelah restart.
> - Duplicate occurrence tidak dapat dibuat.
> - Dua worker tidak dapat menjalankan occurrence yang sama.
> - Retry tidak membuat occurrence baru.
> - Lock dilepas dengan aman ketika proses berhasil atau gagal.

#### Subtask 2

**Summary**

`VOC - Crawl Scheduler - Implement Crawl Trigger, Run History, and Run Now`

**Description**

> Hubungkan scheduler ke endpoint enqueue Crawler dan sediakan monitoring lifecycle run serta manual `Run now`.
>
> **Scope:**
> - Kirim request enqueue ke Crawler dan simpan `batch_id`.
> - Pantau batch sampai status terminal.
> - Jalankan delta pull setelah hasil crawl siap.
> - Simpan `started_at`, `finished_at`, status, dan counters.
> - Buat UI histori run dan tombol `Run now`.
> - Tambahkan confirmation dan permission untuk manual run.
>
> **Acceptance Criteria:**
> - Request OneBox tidak menunggu Selenium selesai.
> - `batch_id` berhasil disimpan dan status batch dapat dipantau.
> - Delta pull tidak dijalankan sebelum hasil crawl siap.
> - Histori menampilkan planned time, actual time, status, dan counters.
> - User tanpa permission tidak dapat menjalankan `Run now`.
> - Manual run memiliki audit trail.
> - Error menampilkan kode atau request ID yang aman.

### DNGO19-3391 — Config Setup

- **Owner:** OneBox (OB)
- **Status:** READY TO DEV
- **MD:** 3 MD

#### Description

> Mendaftarkan benefit VoC pada sistem entitlement OneBox dan menerapkan pengukuran pemakaian agar akses crawl, AI, dan competitor feature dapat dibatasi sesuai benefit tenant.
>
> **Scope:**
> - Mendaftarkan benefit `VOC_SCRAPE`, `VOC_AI`, dan `VOC_COMPETITOR`.
> - Menggunakan `verifyBenefit()` untuk kuota berdasarkan jumlah panggilan crawl.
> - Menggunakan `addUsage()` untuk pemakaian berdasarkan nilai, seperti jumlah token AI.
> - Menangani tenant yang tidak memiliki benefit atau kuotanya telah habis.
> - Mencegah pencatatan pemakaian ganda.
>
> **Acceptance Criteria:**
> - Ketiga benefit tersedia pada `Benefit` dan `SiteBenefit`.
> - Tenant tanpa benefit tidak dapat menggunakan feature terkait.
> - Tenant dengan benefit aktif dapat menggunakan feature sampai batas kuota.
> - Satu panggilan crawl dan satu pemakaian token AI masing-masing dicatat satu kali.
> - `verifyBenefit()` dan `addUsage()` tidak digunakan untuk unit pemakaian yang sama.
> - Error benefit ditampilkan tanpa stack trace atau informasi internal.
>
> **Dependency:**
> - Seeding database Dev yang konsisten.
> - Data `tokens_used` dari Crawler untuk pencatatan usage AI.
>
> **Out of Scope:**
> - Menu dan role VoC.
> - Perbaikan `getUserAllRole`.
> - Perhitungan token di Crawler.
> - Billing dan invoice eksternal.

#### Subtask 1

**Summary**

`VOC - Config Setup - Register VoC Benefit Codes`

**Description**

> Daftarkan benefit `VOC_SCRAPE`, `VOC_AI`, dan `VOC_COMPETITOR` pada sistem `Benefit` dan `SiteBenefit`.
>
> **Acceptance Criteria:**
> - Ketiga benefit tersedia di environment Dev.
> - Benefit dapat dialokasikan kepada site.
> - Seed dapat dijalankan ulang tanpa membuat data duplikat.
> - Nilai default dan satuan masing-masing benefit terdokumentasi.

#### Subtask 2

**Summary**

`VOC - Config Setup - Enforce Crawl Call Quota`

**Description**

> Terapkan `verifyBenefit()` pada entry point crawl untuk memeriksa dan mencatat kuota berdasarkan jumlah panggilan.
>
> **Acceptance Criteria:**
> - Crawl tanpa benefit ditolak.
> - Crawl dengan kuota tersedia dapat dijalankan.
> - Kuota bertambah tepat satu kali untuk satu panggilan.
> - Scheduled run dan `Run now` tidak menyebabkan pencatatan ganda.
> - User mendapatkan pesan yang jelas ketika kuota habis.

#### Subtask 3

**Summary**

`VOC - Config Setup - Record AI Usage`

**Description**

> Gunakan `addUsage()` untuk mencatat nilai pemakaian AI berdasarkan `tokens_used` yang diterima dari Crawler.
>
> **Acceptance Criteria:**
> - Usage dicatat setelah nilai `tokens_used` yang valid diterima.
> - Retry tidak mencatat token yang sama dua kali.
> - Nilai kosong, nol, atau invalid ditangani dengan benar.
> - `addUsage()` tidak dipasangkan dengan `verifyBenefit()` untuk satu unit pemakaian yang sama.
> - Implementasi mengikuti kontrak `tokens_used` dari Crawler.

### DNGO19-3392 — Generate Reports

- **Owner:** OneBox (OB)
- **Status:** READY TO DEV · **MD:** 4 MD

#### Description

> Menyediakan fitur export data review VoC ke format CSV dan PDF untuk kebutuhan analisis serta pelaporan kepada stakeholder.
>
> **Scope:**
> - Menyediakan filter rentang tanggal, lokasi, rating, sentiment, kategori, dan urgency apabila tersedia.
> - Menghasilkan CSV berisi data detail review.
> - Menghasilkan PDF berdasarkan template laporan yang disetujui.
> - Menggunakan timezone site pada periode laporan.
> - Membatasi data berdasarkan tenant dan permission user.
>
> **Acceptance Criteria:**
> - CSV dan PDF menggunakan filter yang dipilih user.
> - Export hanya berisi data tenant aktif.
> - CSV dapat dibuka tanpa encoding atau struktur kolom yang rusak.
> - PDF menampilkan judul, periode, waktu generate, dan filter.
> - Nilai kosong ditampilkan secara konsisten.
> - Dataset kosong menghasilkan pesan yang jelas.
> - Review text diperlakukan sebagai untrusted content.
> - Nama file mencakup jenis laporan dan periode.
>
> **Out of Scope:**
> - Mengirim laporan melalui email.
> - Scheduled report.
> - Menyimpan laporan secara permanen.
> - Custom report builder.

#### Subtask 1

**Summary**

`Dev Specification - VOC - Generate Reports`

**Description**

> Finalisasi kebutuhan CSV dan PDF bersama Product sebelum implementasi.
>
> **Scope:**
> - Tentukan kolom CSV, struktur PDF, filter, dan default periode.
> - Tentukan kebutuhan branding, logo, summary, atau chart.
> - Tentukan batas maksimum data.
> - Buat contoh output atau mockup.
>
> **Acceptance Criteria:**
> - Kolom CSV dan template PDF disetujui Product.
> - Filter dan default periode disetujui.
> - Aturan dataset besar ditentukan.
> - Contoh output tersedia.
> - Scope mendapatkan approval Product.

#### Subtask 2

**Summary**

`VOC - Generate Reports - Implement CSV Export`

**Description**

> Implementasikan export data review ke CSV berdasarkan filter dan permission user.
>
> **Acceptance Criteria:**
> - Kolom dan urutan sesuai specification.
> - Encoding mendukung karakter Bahasa Indonesia.
> - Isi file sesuai filter dan data antar-tenant tidak tercampur.
> - Nilai CSV tidak dapat menyebabkan formula injection.
> - Nama file mengikuti konvensi yang disepakati.

#### Subtask 3

**Summary**

`VOC - Generate Reports - Implement PDF Export`

**Description**

> Implementasikan generate PDF berdasarkan template yang telah disetujui.
>
> **Acceptance Criteria:**
> - Layout sesuai template.
> - Judul, periode, filter, dan waktu generate tersedia.
> - Teks panjang tidak keluar dari layout.
> - Page break dan tabel multi-page ditangani.
> - Data sesuai hasil filter.
> - File PDF dapat dibuka dan diunduh.

### DNGO19-3396 — Competitor Analysis

- **Owner:** OneBox (OB)
- **Status:** TODO

#### Description

> Menyediakan halaman perbandingan performa review antara lokasi milik organisasi dan kompetitor yang telah terdaftar.
>
> **Scope awal yang perlu dikonfirmasi Product:**
> - Menyediakan pemilihan lokasi milik sendiri, kompetitor, rentang tanggal, dan source.
> - Menampilkan average rating lokasi sendiri dan kompetitor.
> - Menampilkan review volume gap, negative sentiment gap, dan critical issue gap.
> - Menampilkan top category atau issue, strengths, weaknesses, dan competitor review feed.
> - Memastikan review kompetitor tidak dibuat sebagai Ticket OneBox.
>
> **Acceptance Criteria:**
> - User dapat memilih lokasi sendiri dan kompetitor.
> - Perbandingan menggunakan periode dan source yang sama.
> - Formula setiap KPI terdokumentasi.
> - Data lokasi sendiri dan kompetitor dapat dibedakan dengan jelas.
> - Review kompetitor tidak dibuat sebagai Ticket.
> - User hanya dapat melihat data tenant-nya.
> - Kondisi data kosong ditampilkan dengan jelas.
> - Nilai KPI konsisten dengan data sumber.
>
> **Dependency:**
> - DNGO19-3386 Master Data Competitors.
> - Endpoint `competitor_reviews` dari Crawler.
> - Consumer review kompetitor di OneBox.
> - Struktur menu dari DNGO19-3346.
>
> **Out of Scope:**
> - CRUD kompetitor.
> - Implementasi crawl worker kompetitor.
> - Membuat Ticket dari review kompetitor.
> - Rekomendasi strategi berbasis AI.

#### Subtask 1

**Summary**

`Dev Specification - VOC - Competitor Analysis`

**Description**

> Finalisasi kebutuhan Competitor Analysis bersama Product.
>
> **Scope:**
> - Tentukan KPI yang masuk MVP dan formula masing-masing KPI.
> - Tentukan apakah user dapat membandingkan satu atau beberapa kompetitor.
> - Tentukan default periode, filter source, dan layout halaman.
> - Tentukan aturan ketika data kompetitor kosong atau tidak seimbang.
> - Buat wireframe atau referensi tampilan.
>
> **Acceptance Criteria:**
> - KPI MVP dan formula disetujui Product.
> - Aturan pemilihan kompetitor ditentukan.
> - Filter dan default periode disetujui.
> - Wireframe tersedia.
> - Scope implementasi mendapatkan approval Product.

#### Subtask 2

**Summary**

`VOC - Competitor Analysis - Implement Comparison Data`

**Description**

> Implementasikan pengambilan dan agregasi data untuk membandingkan review lokasi sendiri dengan review kompetitor.
>
> **Scope:**
> - Ambil data berdasarkan tenant.
> - Terapkan filter lokasi, kompetitor, periode, dan source.
> - Hitung KPI berdasarkan formula yang disetujui.
> - Sediakan paging untuk competitor review feed.
> - Pastikan review kompetitor tidak masuk proses pembuatan Ticket.
>
> **Acceptance Criteria:**
> - Query ter-scope berdasarkan tenant.
> - Filter diterapkan secara konsisten.
> - Formula KPI sesuai specification.
> - Review kompetitor tidak dibuat sebagai Ticket.
> - Paging diterapkan pada review feed.
> - Dataset kosong ditangani dengan benar.

#### Subtask 3

**Summary**

`VOC - Competitor Analysis - Implement Analysis UI`

**Description**

> Implementasikan halaman Competitor Analysis berdasarkan Dev Specification.
>
> **Scope:**
> - Tambahkan filter lokasi, kompetitor, periode, dan source.
> - Tampilkan KPI perbandingan, strengths, weaknesses, dan competitor review feed.
> - Tambahkan loading, empty, dan error state.
> - Terapkan role dan entitlement `VOC_COMPETITOR`.
>
> **Acceptance Criteria:**
> - User dapat mengubah seluruh filter.
> - Tampilan membedakan own location dan competitor.
> - KPI sesuai response data.
> - Loading, empty, dan error state tersedia.
> - Competitor review feed memiliki paging.
> - User tanpa permission atau benefit tidak dapat membuka feature.

---

## Branch 3346 — Cakupan yang Dikerjakan di Sana (bukan ticket terpisah)

`feature/DNGO19-3346_Media-Crawler-Google-Business-Review` menanggung 2 hal yang sengaja **tidak** dipecah jadi ticket sendiri:

### Description DNGO19-3346

> Menyediakan fondasi navigasi VoC yang sesuai workflow Product dan mekanisme delta sync yang aman agar feature VoC lain dapat menggunakan struktur menu serta data review yang konsisten.
>
> **Scope:**
> - Restrukturisasi menu VoC menjadi grup Transaksi, Output, dan Setting.
> - Mengubah seed menu dari struktur flat menjadi hierarki tiga level.
> - Implementasi checkpoint delta pull.
> - Targeted backfill untuk lokasi baru.
> - Reconciliation untuk lokasi lama yang belum memiliki Ticket.
>
> **Acceptance Criteria:**
> - Menu VoC tampil sebagai header tersendiri dan semua submenu berada pada grup yang benar.
> - Seed dapat dijalankan ulang tanpa duplikasi.
> - Checkpoint hanya maju setelah seluruh halaman berhasil diproses.
> - Lokasi baru mendapatkan histori lama sebelum masuk delta reguler.
> - Reconciliation tidak membuat Ticket duplikat.
> - Kegagalan sebagian tidak menghilangkan data yang belum berhasil diproses.

### Subtask 1

**Summary**

`VOC - Media Crawler Google Business Review - Restructure VoC Navigation`

**Description**

> Ubah navigasi VoC dari submenu flat menjadi hierarki berdasarkan workflow Product.
>
> **Struktur menu:**
> - Transaksi: Ulasan, Analisis, Insight.
> - Output: Dashboard, Report, Competitor Analysis.
> - Setting: Setup Parameter, Master Data.
>
> **Scope:**
> - Perbarui `scriptdb/voc/voc_setup_all.sql`.
> - Ubah struktur menjadi hierarki Header VoC → Grup → Sub-menu.
> - Pertahankan route menu existing.
> - Atur urutan menu sesuai keputusan Product.
>
> **Acceptance Criteria:**
> - VoC tampil sebagai header menu tersendiri.
> - Semua submenu berada pada grup yang benar.
> - Route existing tetap berfungsi.
> - Seed dapat dijalankan ulang tanpa membuat menu duplikat.
> - Perubahan hierarki tidak membuka permission baru secara tidak sengaja.

### Subtask 2

**Summary**

`VOC - Media Crawler Google Business Review - Implement Safe Delta Checkpoint`

**Description**

> Implementasikan delta pull review menggunakan `checkpoint_cursor`.
>
> **Acceptance Criteria:**
> - Pull berikutnya melanjutkan dari checkpoint terakhir yang berhasil.
> - Checkpoint hanya maju setelah seluruh halaman berhasil diambil dan disimpan.
> - Kegagalan satu halaman tidak memajukan checkpoint.
> - Retry tidak membuat Ticket duplikat.
> - Counter `inserted`, `deduped`, dan `failed` tersedia.
> - Cursor utuh tidak ditampilkan pada log.

### Subtask 3

**Summary**

`VOC - Media Crawler Google Business Review - Implement Targeted Location Backfill`

**Description**

> Jalankan targeted backfill untuk lokasi baru yang telah memiliki review historis di Crawler sebelum lokasi masuk ke aliran delta reguler.
>
> **Scope:**
> - Gunakan `location_id`.
> - Gunakan `updated_since` dengan periode historis yang sesuai.
> - Jalankan backfill sebelum menggunakan checkpoint tenant reguler.
>
> **Acceptance Criteria:**
> - Lokasi baru memperoleh review historis.
> - Review lama tidak terlewat akibat checkpoint tenant yang sudah maju.
> - Rerun tidak membuat Ticket duplikat.
> - Kegagalan backfill dapat dilanjutkan dengan aman.
> - Status dan hasil backfill dapat ditelusuri.

### Subtask 4

**Summary**

`VOC - Media Crawler Google Business Review - Reconcile Reviews Without OneBox Tickets`

**Description**

> Rekonsiliasi lokasi lama yang telah memiliki review di Crawler tetapi belum memiliki Ticket OneBox, termasuk kasus Bekasi.
>
> **Acceptance Criteria:**
> - Lokasi dan review yang terdampak dapat diidentifikasi.
> - Review tanpa Ticket dibuat menjadi Ticket OneBox.
> - Review yang sudah memiliki Ticket dilewati sebagai duplicate.
> - Reconciliation tidak membuat Ticket duplikat.
> - Hasil memiliki counter `inserted`, `deduped`, dan `failed`.
> - Checkpoint tidak berubah secara tidak aman.

**Implikasi urutan kerja:**
- **Ticket yang nambah sub-menu baru (3388, 3389, 3390, 3396) sebaiknya menunggu restrukturisasi menu di 3346 selesai dulu**, supaya sub-menu baru langsung masuk ke grup yang benar.
- **`Crawl Scheduler` (3390) bergantung pada Delta Sync di 3346** — cek dependency ini sebelum mulai development 3390.

---

## 📋 Pending / Perlu Diklarifikasi (list terbuka, jangan diasumsikan selesai)

| # | Item | Kenapa masih terbuka |
|---|---|---|
| 1 | **Isi ticket 3393–3395** | **Hipotesis baru (perlu konfirmasi):** screenshot ticket 3385 menunjukkan subtask `DNGO19-3394 "Dev Specification : VOC : Master-Data-Locations"` — kemungkinan besar 3393/3394/3395 adalah subtask "Dev Specification" milik ticket-ticket induk (bagian dari alur spec-review sebelum status "in development"), **bukan** ticket fitur yang hilang. Kalau benar, Review-Detail dan Delta-Sync memang tidak butuh ticket sendiri (sudah sesuai keputusan digabung ke 3387 dan branch 3346). Tetap cek langsung di Jira untuk memastikan pola penomoran subtask ini konsisten di semua ticket induk. |
| 2 | **Scope persis `Crawl Scheduler` (3390)** | Perlu dikonfirmasi: apakah full M4-01..05 (8MD, exceeds cap) atau sudah dipangkas. Sub-task split direkomendasikan (lihat detail 3390 di atas). |
| 3 | **Scope persis `Competitor Analysis` (3396)** | Pastikan tidak overlap dengan `Master-Data-Competitors` (3386) — 3386 = CRUD/registrasi, 3396 = komparasi/output (asumsi dari notulen meeting, belum dikonfirmasi eksplisit). |
| 4 | **Exception 5MD di 3387 dan 3390** | Dua ticket ini disengaja melebihi cap karena penggabungan scope yang masuk akal secara alur kerja — perlu dikomunikasikan ke Agung sebagai exception yang disadari, bukan kelalaian. |
| 5 | **Target `Enhance AI Analysis` (DNGO19-3407)** | Jira key sudah tersedia. Target latency, throughput, error rate, token usage, kandidat model, dan dataset benchmark tetap harus difinalisasi pada Dev Specification sebelum implementasi dimulai. Jira Work Type saat ini `Task`; direkomendasikan diubah menjadi `New Feature` agar konsisten dengan feature VoC lain. |
| 6 | **Kontrak `Fetch Jobs Crawl` (DNGO19-3420)** | Jira key dan work type `New Feature` sudah tersedia. Kontrak request/response, lifecycle job, batas target review, dry run, retry, cancel, dan penggunaan `job_id` atau `batch_id` tetap harus difinalisasi pada Dev Specification. |

---

## Item yang Sudah Tidak Berlaku dari Draft Sebelumnya

- ~~T1a/T1b Review-Detail + Review-Manage-Actions terpisah~~ → **digabung jadi 3387**.
- ~~T5a Delta-Sync sebagai ticket sendiri~~ → **dikerjakan di branch 3346**.
- ~~T5b/T5c Scheduling-Core + Trigger-UI terpisah~~ → jadi **3390 (Crawl Scheduler)**, kemungkinan perlu sub-task internal karena cap 5MD.
- ~~T8 Menu Navigation Restructure sebagai ticket sendiri~~ → **dikerjakan di branch 3346**.
