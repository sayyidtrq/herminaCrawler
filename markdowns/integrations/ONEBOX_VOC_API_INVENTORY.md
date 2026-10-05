# Inventaris API VoC di OneBox (FE ↔ BE)

> Snapshot: `origin/feature/voc` @ `c9c5e15e6d` (24 Sep 2026).
> Sumber: `onecloud/app/controllers/VocController.php` (18.033 baris, **111 action**),
> `controllers/api/v1/VocWorklistController.php`, `tasks/VocTask.php`,
> `services/Provider/VocProvider.php`, semua `views/Voc/*.volt`, `public/js/routes.js`,
> migrasi `Menu.php`, dan repo Crawler (`app/integrations/onebox_worklist_client.py`).
>
> Cara dilacak: setiap `*Action` dipetakan ke **semua** kemunculan `Voc/<nama>` di
> view/JS/PHP (satu lintasan grep atas seluruh `app/` + `public/js/`), lalu tiap call
> site ditelusuri ke fungsi JS pembungkus dan event pemicunya. Nomor baris = baris
> `public function …Action` di `VocController.php` pada snapshot di atas.

## Ringkasan

| | Jumlah |
|---|---|
| Action total | 111 |
| Halaman (render view, dibuka lewat `#/voc/<page>`) | 21 |
| Endpoint JSON | 90 |
| **Endpoint JSON tanpa pemanggil sama sekali (usang)** | **11** |
| Rute halaman yang menunya sudah dipensiunkan (alias bookmark) | 4 |
| Kode mati di luar controller | React `VocDashboard.tsx` + `mount.tsx`, `stub.volt` + `renderStub()` |

**Pola routing monolith ini** (yang bikin BE susah dilacak):

```
Sidebar Menu (tabel Menu, diisi migrasi) → NavigateUrl '#/voc/<page>'
  → public/js/routes.js:183  openTabGeneral("voc_"+page, title, "Voc/"+page)
  → VocController::<page>Action()  → render views/Voc/<page>.volt (atau view lain lewat pick())
  → JS di .volt itu memanggil endpoint JSON: $.getJSON("{{ url('Voc/<endpoint>') }}")
```

Artinya: nama halaman di URL = nama action;

endpoint JSON hanya bisa ditemukan dari
string `url('Voc/…')` di dalam `.volt`. 

Tidak ada file routes terpusat, dan izin per
action ada di peta `VocController.php:~230–360` (`'<action>' => 'voc_<menu>'`).

**Waktu respons terukur di dev** (24 Sep, sesi admin, data ±4.165 review): 
`reviewsAggregate` 51 dtk (cold, lalu cache 120 dtk) · `dashboardData` 16,8 dtk ·
`locationsData` 7–8 dtk · `reviewsData` ~4,5 dtk per halaman · `ratingAlerts` 3,2 dtk ·
`schedulesData` 0,1 dtk.

Legenda status:
✅ used ·
⚠️ dipakai tapi perlu perhatian · 
🪦 unused· 
↪️ alias rute lama

---

## 1. Halaman (page routes)

Semua dibuka lewat hash-route. "Menu" = status baris di tabel Menu menurut migrasi terakhir.

| Halaman | Baris | View yang dirender | Menu sidebar | Status |
|---|---|---|---|---|
| `index` | 486 | redirect → `Voc/dashboard` | – | 🪦 tidak ada yang menautkan; aman dibiarkan (default route) |
| `dashboard` | 491 | `dashboard.volt` | Output › Dashboard Google Review | ✅ |
| `dashboardprofile` | 498 | `dashboardprofile.volt` | Output › Dashboard Profile | ✅ |
| `omnichannel` | 510 | `omnichannel.volt` | Output › Dashboard Omnichannel | ✅ |
| `reports` | 1984 | `reports.volt` | Output › Report | ✅ |
| `trend` | 1751 | `trend.volt` | Output › Tren Bulanan | ✅ |
| `compare` | 1685 | `compare.volt` | Compare | ✅ |
| `workspace` | 517 | `workspace.volt` | Workspace Omnichannel | ✅ |
| `workspacebranch` | 538 | `workspacebranch.volt` | Workspace Cabang | ✅ |
| `actions` | 504 | `actions.volt` | **tidak di menu** — dibuka dari tombol di Dashboard & Dashboard Profile (`openActionsTabDirect`) | ✅ |
| `reviews` | 1012 | `reviews.volt` | Transaksi › Ulasan | ✅ |
| `analysis` | 1066 | `analysis.volt` | Transaksi › Analisis | ✅ |
| `insights` | 1754 | `insights.volt` | Transaksi › Insight | ✅ |
| `settings` | 1989 | `settings.volt` | Setting › Setup Parameter | ✅ |
| `fetchjobs` | 1036 | `fetchjobs.volt` | Setting › Fetch Jobs | ✅ |
| `locations` | 1031 | `locations.volt` | Setting › Lokasi | ✅ |
| `schedules` | 1668 | `schedules.volt` | Setting › Jadwal Crawl | ✅ |
| `competitors` | 1051 | `locations.volt` (sudut pandang kompetitor) | dipensiunkan (migrasi 1786010000000000) | ↪️ alias bookmark |
| `fetchjobscompetitor` | 1059 | `fetchjobs.volt` (sudut pandang kompetitor) | dipensiunkan (1786010000000000) | ↪️ alias bookmark |
| `analysiscompetitor` | 1745 | `compare.volt` | dipensiunkan (1.124.0 `1789454893073811`) | ↪️ alias bookmark |
| `benefit` | 1675 | `settings.volt` | dipensiunkan (1.124.0 `1789454893073811`) | ↪️ alias bookmark |

---

## 2. Dashboard & Output

| Endpoint                | Baris | Method | Dipanggil dari (FE)                                                                                                      | Pemicu / frekuensi                                         | Fungsi                                                                                                                                         | Status                                                                                                         |
| ----------------------- | ----- | ------ | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `dashboardData`         | 7813  | GET    | `dashboard.volt` (`loadDashboard`), `analysis.volt` (`loadInsights`, `days=0`), `omnichannel.volt` (`loadDashboardData`) | 1× saat buka tiap layar + tombol Muat ulang + ganti filter | Agregat penuh Dashboard Google Review: KPI, periode, risiko cabang, top issue, review negatif (semua baris), action tracker, monitoring lokasi | ⚠️ endpoint terberat (16,8 dtk) dan dipakai **3 layar**; layar Analisis memanggilnya hanya untuk panel insight |
| `dashboardProfileData`  | 2965  | GET    | `dashboardprofile.volt` (`load`)                                                                                         | 1× saat buka + ganti filter                                | Payload Dashboard Profile per cabang (total, sentimen, rating, risiko, top kategori)                                                           | ✅                                                                                                              |
| `compareRegionalData`   | 1700  | GET    | `compare.volt` (`regLoad`)                                                                                               | saat tab Regional Comparison dibuka/difilter               | Regional Comparison; memakai builder yang sama dengan `dashboardProfileData`, dipisah demi izin `voc_compare`                                  | ✅                                                                                                              |
| `trendData`             | 12115 | GET    | `trend.volt` (`muat`)                                                                                                    | 1× saat buka + ganti filter                                | Agregat ulasan per bulan (Tren Bulanan)                                                                                                        | ✅                                                                                                              |
| `insightsData`          | 1788  | GET    | `insights.volt` (`loadInsights`)                                                                                         | 1× saat buka                                               | Hasil analisa AI nyata untuk layar Insight (antrean tindak lanjut ≤500, kartu kritis ≤20)                                                      | ✅                                                                                                              |
| `actionsData`           | 8428  | GET    | `actions.volt` (`load`)                                                                                                  | 1× saat buka                                               | Daftar tindak lanjut (Action Tracker penuh)                                                                                                    | ✅                                                                                                              |
| `dashboardFollowUpSave` | 8709  | POST   | `dashboard.volt` (submit modal tindak lanjut), `actions.volt`                                                            | per klik simpan                                            | Simpan tindak lanjut review agar terlihat seluruh tim                                                                                          | ✅                                                                                                              |
| `dashboardReplySave`    | 8760  | POST   | `dashboard.volt` (submit modal balasan)                                                                                  | per klik simpan                                            | Simpan **draft** balasan di OneBox (tidak mem-posting ke Google)                                                                               | ✅                                                                                                              |
| `ratingTargetSave`      | 946   | POST   | `dashboard.volt` (`saveDbTarget`), `locations.volt` (`saveParamTarget`), `compare.volt` (`saveTarget`)                   | per klik simpan                                            | Setel target rating site (Setting `VocRatingTarget`)                                                                                           | ✅                                                                                                              |
| `workspaceData`         | 15768 | GET    | `workspace.volt` (`loadData`)                                                                                            | 1× saat buka + filter                                      | Data kerja lintas channel berbasis Ticket (ID Reference asli)                                                                                  | ✅                                                                                                              |
| `workspaceUpdate`       | 15807 | POST   | `workspace.volt` (`saveCurrent`, `bulkApply`)                                                                            | per simpan / aksi massal                                   | Partial update Ticket (hanya field yang dikirim)                                                                                               | ✅                                                                                                              |
| `workspaceBranchData`   | 551   | GET    | `workspacebranch.volt` (`muat`)                                                                                          | 1× saat buka                                               | Data Workspace Kepala Cabang, satu lokasi (sengaja tidak memakai `dashboardData`)                                                              | ✅                                                                                                              |
| `reportsData`           | 2890  | GET    | `reports.volt` (`loadReports`)                                                                                           | 1× saat buka                                               | Opsi filter + riwayat report dari session                                                                                                      | ✅                                                                                                              |
| `reportGenerate`        | 3032  | POST   | `reports.volt` (submit form)                                                                                             | per klik Generate                                          | Validasi filter, bangun report di backend, catat history                                                                                       | ✅                                                                                                              |
| `reportDownload`        | 3117  | GET    | `reports.volt` (`startDownload`)                                                                                         | per klik unduh                                             | Unduh ulang report dari history                                                                                                                | ✅                                                                                                              |

---

## 3. Ulasan (Reviews) & tindak lanjut

| Endpoint | Baris | Method | Dipanggil dari (FE) | Pemicu / frekuensi | Fungsi | Status |
|---|---|---|---|---|---|---|
| `reviewsData` | 4885 | GET | `reviews.volt` (`loadReviews`, `muatUlasanNegatif`), `fetchjobs.volt` (panel ulasan cabang) | tiap buka, ganti halaman, filter, sort | Daftar ulasan berhalaman (`page`, `page_size` ≤200) | ⚠️ ~4,5 dtk tetap per halaman (filter JSON `Meta` di tiap baris) |
| `reviewsAggregate` | 4877 | GET | `reviews.volt` (`loadReviewAggregate`) | paralel dengan `reviewsData` saat buka/filter | Ringkasan & facet layar Ulasan; memanggil `reviewsDataAction()` internal dengan mode agregat, cache 120 dtk | ⚠️ 51 dtk saat cache dingin |
| `reviewDetail` | 8887 | GET | `reviews.volt` (`openDetail`, deep-link `initialReviewId`), `dashboard.volt` (`openReviewFullWorkspace`) | per klik baris | Detail satu review + analisa + riwayat catatan + status tiket | ✅ |
| `reviewManage` | 9056 | POST | `reviews.volt` (klik simpan di detail) | per aksi | Ubah status/prioritas/PIC, tambah catatan (lewat mekanisme Ticket) | ✅ |
| `reviewEscalate` | 10026 | POST | `reviews.volt`, `dashboard.volt` (`createReviewTicket`), `actions.volt` | per klik "Eskalasi" | Jadikan review tiket operasional | ✅ |
| `reviewForward` | 9368 | POST | `reviews.volt`, `dashboard.volt` (`forwardReviewToPic`), `actions.volt` | per klik "Teruskan" | Teruskan review ke PIC via WhatsApp (kanal OneBox, fallback `wa.me`) | ✅ |
| `reviewEscalationConfigSave` | 9576 | POST | `reviews.volt` | per simpan pengaturan | Simpan ambang ulasan yang layak dieskalasi (DNGO19-3517) | ✅ |
| `reviewEscalationRetry` | 9654 | POST | `reviews.volt` (log eskalasi) | per klik "Coba lagi" | Kirim ulang eskalasi WhatsApp yang gagal | ✅ |
| `reviewAssignees` | 9903 | GET | `reviews.volt` (`loadAssignees`) | saat panel PIC dibuka | Daftar anggota site yang bisa jadi PIC | ✅ |
| `reviewDelete` | 9947 | POST | `reviews.volt` | per klik hapus | Soft-delete review (`Meta.deleted_at`) + tiketnya dikedaluwarsakan | ✅ |
| `ratingTrendData` | 5612 | GET | `reviews.volt` (`renderTrend`) | saat tab Tren dibuka | Garis waktu rating vs target / kompetitor / rata-rata | ✅ |
| `ratingAlerts` | 5754 | GET | `reviews.volt` (`loadAlerts`, dipanggil dari `applyScope`) | 1× saat buka + ganti scope | Lokasi di bawah ambang yang punya PIC | ✅ (panggilan ganda sudah dihapus di PR #94) |
| `ratingAlertForward` | 5849 | POST | `reviews.volt` (`teruskanAlert`) | per klik | Teruskan alert rating rendah ke PIC via WhatsApp | ✅ |

---

## 4. Fetch review (crawl & sinkron)

| Endpoint | Baris | Method | Dipanggil dari (FE) | Pemicu / frekuensi | Fungsi | Status |
|---|---|---|---|---|---|---|
| `crawlStart` | 11826 | POST | `fetchjobs.volt` (`ENDPOINT.location.mulai`) | per klik Mulai | Antre crawl cabang terpilih; Crawler membalas 202 + `batch_id` (tidak menunggu) | ✅ |
| `crawlStatus` | 13265 | GET | `fetchjobs.volt` (`pollBatch`) | **polling tiap 4 dtk** selama batch berjalan (backoff saat gagal) | Status satu batch crawl | ✅ — satu-satunya endpoint polling VoC |
| `crawlEstimate` | 13324 | GET | `fetchjobs.volt` (`muatPerkiraan`) | saat pilih cabang / ganti mode | Perkiraan jumlah ulasan cabang (OB-6); gagal diam-diam | ✅ |
| `crawlHistory` | 13432 | GET | `fetchjobs.volt` (`muatRiwayat`, `muatPreview`) | saat buka + setelah batch selesai | Riwayat batch crawl dibaca langsung dari Crawler | ✅ |
| `crawlImport` | 17315 | POST | `fetchjobs.volt` (`importSatuCabang`) | otomatis setelah crawl satu cabang selesai | Tarik review satu cabang segera setelah crawl-nya selesai | ✅ |
| `syncnow` | 17153 | POST | `fetchjobs.volt` (`ENDPOINT.location.sinkron`) | per klik "Sinkronkan" | Tarik review seluruh cabang dari Crawler (pipeline sama dengan CLI `receive`) | ✅ |
| `schedulesData` | 12557 | GET | `schedules.volt` (`loadSchedules`) | 1× saat buka + setelah aksi | Daftar jadwal + ringkasan run terakhir | ✅ |
| `schedulesKpi` | 12596 | GET | `schedules.volt` (`loadKpi`) | 1× saat buka | Angka ringkas layar Jadwal (dihitung di server) | ✅ |
| `scheduleSave` | 12732 | POST | `schedules.volt` | per simpan | Buat/ubah jadwal | ✅ |
| `scheduleToggle` | 12924 | POST | `schedules.volt` (switch) | per toggle | Aktif/nonaktif jadwal | ✅ |
| `scheduleDelete` | 12975 | POST | `schedules.volt` | per klik | Hapus jadwal (riwayat run ditinggal) | ✅ |
| `scheduleRunNow` | 13010 | POST | `schedules.volt` | per klik | Jalankan sekarang tanpa menggeser jadwal berikutnya | ✅ |
| `scheduleRuns` | 13107 | GET | `schedules.volt` | per klik "Riwayat" | Riwayat run satu jadwal (termasuk yang dilewati) | ✅ |
| `schedulePreview` | 13160 | GET | `schedules.volt` (`refreshPreview`) | saat ekspresi jadwal diubah | Pratinjau waktu jalan dihitung di server | ✅ |

---

## 5. Lokasi (master data cabang, wilayah, kelompok)

| Endpoint | Baris | Method | Dipanggil dari (FE) | Pemicu / frekuensi | Fungsi | Status |
|---|---|---|---|---|---|---|
| `locationsData` | 11209 | GET | `locations.volt` (`loadBranches`), `schedules.volt`, `fetchjobs.volt`, `compare.volt`, `trend.volt`, `dashboard.volt` | 1× saat buka di **6 layar** | Registry cabang + agregat review per cabang | ⚠️ 7–8 dtk; layar yang hanya butuh nama cabang tetap membayar agregatnya |
| `locationDetail` | 11302 | GET | `locations.volt` (klik baris) | per klik | Detail satu cabang (bentuk baris sama dengan `locationsData`) | ✅ |
| `locationSave` | 11409 | POST | `locations.volt` | per simpan | Tambah/ubah cabang; commit lokal, Crawler menarik via worklist (ADR-0003) | ✅ |
| `locationToggle` | 13776 | POST | `locations.volt` | per klik | Aktif/nonaktif cabang (review lama tetap) | ✅ |
| `locationDeleteCheck` | 13813 | GET | `locations.volt` | per klik Hapus | Pra-cek: jumlah review yang ikut terhapus untuk konfirmasi | ✅ |
| `locationDelete` | 13863 | POST | `locations.volt` (`onConfirm`) | per konfirmasi | Hapus cabang + soft-delete review-nya | ✅ |
| `wilayahData` | 13974 | GET | `locations.volt` (`loadWilayah`, `provinceOptions`) | saat buka + panel wilayah | Daftar wilayah + jumlah cabang pemakainya | ✅ |
| `wilayahSave` | 14028 | POST | `locations.volt` | per simpan | Buat/ganti nama wilayah | ✅ |
| `wilayahDeleteCheck` | 14107 | GET | `locations.volt` | per klik Hapus | Pra-cek hapus wilayah | ✅ |
| `wilayahDelete` | 14156 | POST | `locations.volt` | per konfirmasi | Hapus wilayah (diblokir bila masih dipakai) | ✅ |
| `locationWilayahSave` | 14216 | POST | `locations.volt` | per simpan | Petakan cabang ke wilayah (upsert) | ✅ |
| `kelompokData` | 14628 | GET | `locations.volt`, `settings.volt` (×2), `reviews.volt` (`loadKelompokList`) | saat buka layar | Daftar kelompok/holding | ✅ |
| `kelompokSave` | 14676 | POST | `locations.volt` | per simpan | Buat/ubah kelompok | ✅ |
| `kelompokDeleteCheck` | 14750 | GET | `locations.volt` | per klik Hapus | Pra-cek hapus kelompok | ✅ |
| `kelompokDelete` | 14792 | POST | `locations.volt` | per konfirmasi | Hapus kelompok | ✅ |
| `locationKelompokSave` | 14842 | POST | `locations.volt` | per simpan | Petakan satu cabang ke kelompok | ✅ |
| `locationKelompokBulkSave` | 14508 | POST | `settings.volt` | per klik | Tambah banyak cabang tanpa kelompok sekaligus | ✅ |
| `settingsKelompokData` | 14395 | GET | `settings.volt` (`loadKelompokMembers`) | saat tab kelompok dibuka | Anggota kelompok untuk Setup Parameter | ✅ |
| `kelompokScopeSave` | 14311 | POST | `settings.volt` | per simpan | Cakupan kelompok site (kosong = tanpa batas) | ✅ |
| `locationsLookup` | 11351 | GET | — | — | Lookup cabang ringan untuk dropdown pemetaan kompetitor | 🪦 UI pemetaan kompetitor tidak ada |
| `locationResync` | 11655 | POST | — | — | Kirim ulang cabang ke Crawler | 🪦 digantikan worklist; komentar kode sendiri menyebutnya jembatan sementara |
| `locationImport` | 11691 | POST | — | — | Impor lokasi dari Crawler yang belum punya Connection (pra-ADR-0001) | 🪦 alat migrasi sekali pakai |

---

## 6. Kompetitor

| Endpoint | Baris | Method | Dipanggil dari (FE) | Pemicu / frekuensi | Fungsi | Status |
|---|---|---|---|---|---|---|
| `competitorsData` | 14930 | GET | `locations.volt` (`loadCompetitors`), `compare.volt`, `reviews.volt` (`loadCompetitorList`) | saat buka / ganti ke mode kompetitor | Daftar kompetitor + filter server | ✅ |
| `competitorSave` | 15085 | POST | `locations.volt` | per simpan | Buat/ubah kompetitor (dipakai FE; `competitorCreate/Update` membungkus ini) | ✅ |
| `competitorToggle` | 15372 | POST | `locations.volt` | per klik | Aktif/nonaktif kompetitor (FE mengirim status tujuan) | ✅ |
| `competitorDelete` | 15456 | POST | `locations.volt` | per klik | Hapus kompetitor (di Crawler dulu) | ✅ |
| `competitorFetchData` | 10269 | GET | `fetchjobs.volt` (`ENDPOINT.competitor.data`) | saat Fetch Jobs mode kompetitor dibuka | Kompetitor yang memenuhi syarat crawl | ✅ |
| `competitorCrawlStart` | 10471 | POST | `fetchjobs.volt` (`ENDPOINT.competitor.mulai`) | per klik Mulai | Antre crawl kompetitor | ✅ |
| `competitorReviewsData` | 10331 | GET | `fetchjobs.volt`, `reviews.volt` (`loadCompetitorReviews`) | saat panel/scope kompetitor dibuka | Ulasan kompetitor, dibaca langsung dari Crawler | ✅ |
| `competitorResync` | 15421 | POST | `fetchjobs.volt` (`ENDPOINT.competitor.sinkron`) | per klik Sinkronkan | Kirim ulang kompetitor yang gagal terkirim | ⚠️ masih dipakai, padahal kembarannya `locationResync` sudah tidak dipakai |
| `competitorAnalysisData` | 10677 | GET | `compare.volt` | saat buka Compare + filter | Data perbandingan kita vs kompetitor | ✅ |
| `competitorDetail` | 15009 | GET | — | — | Detail satu kompetitor | 🪦 |
| `competitorCreate` | 15048 | POST | — | — | Create eksplisit (membungkus `competitorSave`) | 🪦 FE tetap memakai `competitorSave` |
| `competitorUpdate` | 15068 | POST | — | — | Update eksplisit (membungkus `competitorSave`) | 🪦 |
| `competitorImport` | 15510 | POST | — | — | Impor kompetitor dari Crawler | 🪦 alat migrasi sekali pakai |
| `competitorAssign` | 16798 | POST | — | — | Petakan kompetitor ke cabang (`Options.assignments[]`) | 🪦 UI pemetaan tidak ada |
| `competitorAssignmentDelete` | 16912 | POST | — | — | Lepas pemetaan kompetitor→cabang | 🪦 |

---

## 7. AI / Analisis

| Endpoint | Baris | Method | Dipanggil dari (FE) | Pemicu / frekuensi | Fungsi | Status |
|---|---|---|---|---|---|---|
| `analysisConfigData` | 1069 | GET | `analysis.volt` (`loadConfig`) | 1× saat buka + setelah simpan | Tabel AI Setup per Connection (tanpa kredensial) | ✅ |
| `analysisConfigSave` | 1106 | POST | `analysis.volt` | per simpan | Simpan toggle/model/schema ke `Connection.Options` | ✅ |
| `analysisRun` | 1176 | POST | `analysis.volt`, `reviews.volt` (`runAiAnalysis`) | per klik "Analisis" | Jalankan analisis Crawler untuk satu review atau semua yang pending | ✅ |
| `analysisRollback` | 1397 | POST | `analysis.volt` | jarang (prosedur DNGO19-3407) | Buang hasil satu model AI di Crawler | ✅ |
| `settingsAiEngineSave` | 2156 | POST | `settings.volt` | per simpan | Simpan engine AI site; model dipilih dari service yang tersedia | ✅ |
| `analysisQualitySummary` | 1431 | GET | — | — | Sebaran status analisa N jam terakhir untuk monitoring | 🪦 tidak ada layar yang memanggil |

---

## 8. Setting, akun & benefit

| Endpoint | Baris | Method | Dipanggil dari (FE) | Pemicu / frekuensi | Fungsi | Status |
|---|---|---|---|---|---|---|
| `settingsData` | 2002 | GET | `settings.volt` (`load`) | 1× saat buka | Status & kuota benefit VoC site + data Setup Parameter | ✅ |
| `settingsCompanySave` | 2269 | POST | `settings.volt` | per simpan | Simpan profil perusahaan | ✅ |
| `settingsAccountSave` | 2314 | POST | `settings.volt` | per simpan | Simpan akun | ✅ |
| `benefitPurchase` | 2513 | POST | `settings.volt` | per klik "Aktifkan" | Beli paket (**mock**, tanpa pembayaran) = satu-satunya jalur aktivasi `SiteBenefit` | ✅ |
| `benefitData` | 12423 | GET | — | — | Entitlement vs pemakaian (layar Paket & Kuota lama) | 🪦 layarnya digabung ke Setup Parameter, datanya kini lewat `settingsData` |

---

## 9. Integrasi BE ↔ BE (tidak terlihat dari FE)

| Jalur | Arah | Lokasi | Frekuensi | Fungsi |
|---|---|---|---|---|
| `GET /api/VocWorklist` | Crawler → OneBox | `controllers/api/v1/VocWorklistController.php::get()`; dipanggil `app/integrations/onebox_worklist_client.py` (login via `/api/Authenticate`) | tiap siklus worklist sync Crawler | Crawler menarik daftar target (cabang & kompetitor aktif) — pengganti push `locationResync` (ADR-0003) |
| `VocTask::scheduleAction` (CLI `./runx voc schedule`) | cron OneBox → Crawler | `tasks/VocTask.php:37` | tiap menit (cron) | Collect run yang sudah dikirim, lalu dispatch jadwal yang jatuh tempo (`VocSchedule`/`VocScheduleRun`) |
| `VocProvider::receive()` | OneBox ← Crawler | `services/Provider/VocProvider.php:94` | CLI `voice_of_customer_system receive` + tombol `syncnow`/`crawlImport` | Ingest review ke Message/MessageContent, dedup, labeli pending |
| `VocProvider::applyAnalysis()` | OneBox ← Crawler | `VocProvider.php:1852` | setelah receive / analisis | Tulis hasil AI ke `MessageContent.Meta` |
| `VoiceOfCustomerSystemClient` | OneBox → Crawler | `library/VoiceOfCustomerSystemClient.php` | dari action di atas (`crawlStart`, `crawlStatus`, `crawlHistory`, `competitorReviewsData`, `analysisRun`, `locationDelete`, …) | Klien HTTP ke `/api/integration/*` Crawler |

---

## 10. Kandidat pembersihan

**Endpoint tanpa pemanggil (11)**. Masing-masing sudah punya entri di peta izin
`VocController.php:~230–360`, jadi hapus action **dan** entri petanya bersamaan:

| Endpoint | Alasan usang |
|---|---|
| `locationsLookup`, `competitorAssign`, `competitorAssignmentDelete` | Fitur pemetaan kompetitor→cabang tidak punya UI |
| `locationResync` | Digantikan worklist Crawler (komentar ADR-0003 di `locationSave`) |
| `locationImport`, `competitorImport` | Alat migrasi sekali pakai sebelum ADR-0001 |
| `competitorDetail`, `competitorCreate`, `competitorUpdate` | FE memakai `competitorSave`; versi eksplisit tidak pernah disambungkan |
| `benefitData` | Layar Paket & Kuota digabung ke Setup Parameter (1.124.0) |
| `analysisQualitySummary` | Endpoint monitoring tanpa layar |

**Kode mati di luar controller:**
- `app/react-views/src/features/voc/VocDashboard.tsx` + `mount.tsx`: dashboard React
  lama; `dashboard.volt` sudah tidak memuatnya (satu-satunya rujukan tersisa adalah
  komentar di `mount.tsx`).
- `views/Voc/stub.volt` + `VocController::renderStub()` (baris 2877): tidak dipanggil
  action mana pun.

**Rute alias yang sengaja dipertahankan** (menu pensiun, rute tetap hidup demi bookmark):
`competitors`, `fetchjobscompetitor`, `analysiscompetitor`, `benefit`. Hapus hanya
bila sudah diputuskan tautan lama boleh mati.

**Titik panas beban** (bukan usang, tapi paling layak dioptimalkan):
- `dashboardData`: dipakai 3 layar; Analisis memanggil agregat penuh hanya untuk panel insight.
- `locationsData`: dipakai 6 layar; `schedules`/`fetchjobs`/`trend`/`compare` hanya butuh
  identitas cabang tetapi ikut menunggu agregat review 7–8 dtk. `locationsLookup` yang
  usang justru dibuat untuk kebutuhan ini dan bisa dihidupkan kembali di sana.
- `reviewsAggregate` / `reviewsData`: biaya tetap dari filter JSON `Meta` per baris.

---

## 11. Rencana memecah `VocController` (readability)

### 11.1 Kondisi sekarang (diukur dari snapshot yang sama)

| Metrik | Nilai |
|---|---|
| Ukuran file | 18.033 baris, 1 kelas |
| Isi | 111 action + **200** method `private/protected` + 29 konstanta |
| Peta izin | 1 array statis `$actionPermissionMap` (≈130 baris), dibaca `beforeExecuteRoute` |
| Helper yang dipakai ≥2 modul | 54 helper / 1.609 baris (mis. `queryRows`, `jsonFail`, `vocConnectionFilter`, `reviewFrom`, `vocBenefitState`) |
| Kode mati | 11 action usang (652 baris) + `provisionLocation` yang hanya dipakai action usang (96) + 5 helper tak terpanggil (`countPendingTickets`, `renderStub`, `sentimenTeks`, `labelSentimen`, `sentimentFromRating`; 82 baris) ≈ **830 baris** |
| Test otomatis | tidak ada (tidak ada `tests/` / PHPUnit di repo) |

Baris per modul (action + helper yang **hanya** dipakai modul itu):

| Modul | Action | Helper eksklusif | Total ± |
|---|---|---|---|
| Dashboard & Output | 1.799 | 2.582 (61 helper) | 4.400 |
| Ulasan | 1.997 | 1.687 (36) | 3.700 |
| Fetch & Jadwal | 1.464 | 969 (22) | 2.400 |
| Lokasi / wilayah / kelompok | 1.758 | 369 (6) | 2.100 |
| Kompetitor | 1.475 | 168 (3) | 1.650 |
| AI | 470 | 209 (6) | 680 |
| Setting & benefit | 356 | 261 (5) | 620 |
| Halaman | 205 | – | 205 |

Artinya modul-modulnya **sudah terpisah secara alami**. Yang membuatnya "jorok" adalah
satu file menampung semuanya, logika SQL & aturan bisnis tinggal di controller, dan
54 helper lintas modul tidak punya rumah.

### 11.2 Kenapa bukan dipindah ke `controllers/api/`

Semua endpoint ini dipanggil layar OneBox dengan **session** login dan izin menu
(`canUseVocMenu`). `controllers/api/v1` memakai `Api\RESTController` (JWT +
`verifyBenefit`) untuk konsumen luar. Memindahkannya ke sana mengganti model auth dan
memutus semua `url('Voc/…')` di `.volt`. Tetap di `controllers/`. Yang benar-benar
untuk sistem lain (`VocWorklist`) sudah ada di `api/v1`.

### 11.3 Struktur target

Mengikuti preseden yang sudah ada di repo ini: sub-namespace controller seperti
`Reports\` (`controllers/report/`) dan `Dashboards\` (`controllers/dashboard/`), yang
didaftarkan di `config/loader.php` dan `config/routes.php`.

```
app/controllers/voc/                    namespace Voc
├─ BaseController.php                   extends \ControllerBase — izin, JSON helper, guard method
├─ PageController.php                   21 action halaman (pick('Voc/<page>')), alias bookmark
├─ DashboardController.php              dashboardData, dashboardProfileData, trend, insights, reports, workspace*
├─ ReviewController.php                 reviews*, review*, rating*
├─ FetchController.php                  crawl*, syncnow, crawlImport
├─ ScheduleController.php               schedule*, schedules*
├─ LocationController.php               location*
├─ RegionController.php                 wilayah*, kelompok*, locationWilayahSave, locationKelompok*
├─ CompetitorController.php             competitor*
├─ AnalysisController.php               analysis*, settingsAiEngineSave
└─ SettingController.php                settings*, benefitPurchase

app/library/Voc/                        namespace Library\Voc: logika tanpa HTTP, bisa di-unit-test
├─ ConnectionRepository.php             vocConnectionFilter, vocConnections, findVocConnection,
│                                       connectionOptions, isVocConnection, connectionKind,
│                                       locationMeta, oneboxLocationId, koordinat
├─ ReviewQuery.php                      reviewFrom, activeReview, reviewWaktuSql, reviewSentimentSql,
│                                       reviewBintangSql, reviewCategorySql, buildReviewFilter,
│                                       findReview (gabungkan dengan Library\VocReviewSql yang sudah ada)
├─ RegionScope.php                      kelompokScope*, wilayahByLocationForSite, vocWilayahSiap,
│                                       branchRatingTarget, ambangRating
├─ BenefitGate.php                      vocBenefitState, benefitUsageSnapshot, tolakBenefit, syncAiUsage
└─ CrawlerGateway.php                   analysisClient, vocCredentialTemplate, hasVocCredential,
                                        punyaServiceToken, crawlErrorMessage, clientRequestId
                                        (membungkus VoiceOfCustomerSystemClient)
```

Aturan pembagiannya:
- **Controller** hanya: baca request → panggil library → kirim respons. Tidak ada SQL
  mentah dan tidak ada aturan bisnis.
- **Helper yang dipakai ≥2 modul** masuk `Library\Voc\*`, bukan ke `BaseController`.
  Base yang gemuk hanya memindahkan masalah ke file lain.
- **`BaseController`** tetap tipis: `beforeExecuteRoute` (izin), `queryRows`,
  `ok()`/`fail()`/`jsonFail`, `isJson`.

### 11.4 URL `Voc/<action>` tetap sama (FE tidak disentuh)

Semua `.volt`, `routes.js`, dan baris Menu tetap memakai `Voc/<action>`. Pemetaan ke
controller baru cukup di `config/routes.php`:

```php
// config/routes.php — URL lama tetap hidup, dilayani controller per modul.
$vocRoutes = [
    'review'   => ['reviewsData', 'reviewsAggregate', 'reviewDetail', /* … */],
    'schedule' => ['schedulesData', 'schedulesKpi', 'scheduleSave', /* … */],
    // …
];
foreach ($vocRoutes as $controller => $actions) {
    $router->add('/Voc/(' . implode('|', $actions) . ')(/.*)?', [
        'namespace'  => 'Voc',
        'controller' => $controller,
        'action'     => 1,
        'params'     => 2,
    ]);
}
```

Plus `'Voc' => __DIR__ . '/../controllers/voc/'` di `config/loader.php`. Yang harus
diuji saat PoC:
- **Case-sensitivity rute.** FE konsisten `Voc/camelCase`, tetapi halaman dibuka
  `"Voc/" + page` huruf kecil lewat `routes.js`.
- **Parameter path** seperti `locationDetail/{id}` dan `competitorDetail/{id}`.
- **Jangan pakai `dispatcher->forward()`** untuk mengalihkan. Komentar di
  `VocController:~470` mencatat forward membocorkan state antar-request di worker
  Swoole.

Peta izin ikut pecah: tiap controller mendeklarasikan
`protected static $permissionMap = ['reviewsdata' => 'voc_reviews', …]`, dan
`BaseController::beforeExecuteRoute` membaca `static::$permissionMap`. Perilaku
**fail-closed** tetap: action yang tidak terdaftar ditolak.

### 11.5 Tahapan (strangler, satu modul per PR, tanpa big bang)

| Tahap | Isi | Risiko | Cara memastikan tidak rusak |
|---|---|---|---|
| **0. Jaring pengaman** | Script smoke-test kontrak: panggil semua GET di inventaris ini + POST dengan input kosong (harus 4xx, bukan 500), simpan status + daftar key JSON sebagai snapshot | – | Snapshot jadi pembanding untuk setiap tahap berikutnya |
| **1. Buang kode mati** | 11 action usang, `provisionLocation`, 5 helper mati, entri peta izinnya, React `VocDashboard.tsx`/`mount.tsx`, `stub.volt` (≈830+ baris PHP) | rendah | grep ulang 0 pemanggil + smoke-test |
| **2. Ekstrak library** | Pindahkan 54 helper lintas modul ke `Library\Voc\*`. `VocController` memanggilnya; **belum ada URL yang berubah** | sedang | smoke-test + unit test untuk `ReviewQuery`/`RegionScope` (fungsi murni, mudah dites) |
| **3. PoC routing** | `Voc\BaseController` + modul terkecil **Setting** (620 baris) dipindah dengan route map di atas | sedang, di routing | smoke-test + cek izin 4 role (sama seperti uji `beforeExecuteRoute` sebelumnya) |
| **4. Pindah per modul** | Urutan risiko naik: AI → Kompetitor → Region → Lokasi → Jadwal → Fetch → Ulasan → Dashboard | tiap PR kecil | smoke-test per PR; satu modul per rilis |
| **5. Tutup** | Sisa `VocController` = halaman → jadi `Voc\PageController`; hapus file lama | rendah | smoke-test penuh |

Ulasan dan Dashboard sengaja terakhir: keduanya paling besar, paling sering dipakai,
dan menyimpan query terberat (`reviewsData`, `dashboardData`). Optimasi performa di
§10 lebih aman dikerjakan **setelah** SQL-nya berada di `ReviewQuery`, satu tempat,
bukan sebelum.

### 11.6 Pedoman readability (untuk kode baru & kode yang dipindah)

1. **Action pendek.** Target ≤40 baris: validasi input → panggil library → `ok()`/`fail()`.
   Kalau lebih panjang, logikanya milik library.
2. **Guard deklaratif.** Ganti `if (!$this->request->isPost()) return $this->jsonFail(...)`
   yang diulang di ±60 action dengan satu daftar `protected static $postOnly = [...]`
   yang dicek di `BaseController`.
3. **Satu bentuk respons.** `{ok, data, message}` lewat `ok()`/`fail()`; tidak ada
   `setJsonContent(array(...))` manual di tiap action.
4. **Nama dalam bahasa Inggris** saat dipindah (`tolakBenefit` → `rejectWithoutBenefit`,
   `punyaServiceToken` → `hasServiceToken`, `jadwalBerjalanPerLokasi` →
   `runningSchedulesByLocation`, `koneksiOfficial` → `isOfficialConnection`). Komentar
   tetap boleh bahasa Indonesia.
5. **Komentar = alasan singkat.** Banyak docblock di file ini berupa esai panjang. Simpan
   1–3 baris "kenapa" di kode; pindahkan sejarah keputusan ke ADR/markdown dan rujuk
   namanya (mis. `// ADR-0003: commit lokal instan, crawler menarik via worklist`).
6. **Tipe eksplisit** di file baru: parameter & return type, `declare(strict_types=1)`
   di `library/Voc/*`. Jangan ubah perilaku kode lama hanya demi menambah tipe.
7. **Tidak ada state statis yang berubah** di controller/library. Worker Swoole
   dipakai ulang antar-request, jadi cache per-request harus disimpan di properti
   instance, bukan `static`.
8. **SQL hanya di `Library\Voc\*`**, bukan di controller. Fragmen SQL bersama
   (`reviewFrom`, `activeReview`, filter JSON `Meta`) punya satu sumber supaya angka
   antar-layar tidak saling membantah.
9. **Batas ukuran file.** Patokan tim: controller ≤1.500 baris, library ≤800. Kalau
   lewat, pecah lagi. Bisa dicek otomatis di CI dengan `wc -l`.
10. **Style.** PSR-12 + `php-cs-fixer`/`phpcs`, dijalankan **hanya** pada
    `controllers/voc/` dan `library/Voc/` agar diff tidak meledak ke seluruh repo.

