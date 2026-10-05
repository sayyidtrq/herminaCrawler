-- =====================================================================
-- TC_029_Admin — rekonsiliasi identitas Connection "Hermina Depok"
-- Rencana: PLAN_QA_FIX_MASTER_DATA_LOCATIONS_2026-09-17.md pasal 4.4
-- Disusun: 17 September 2026
--
-- SELURUH berkas ini HANYA MEMBACA. Tidak ada satu pun UPDATE, INSERT,
-- atau DELETE, dan itu disengaja: rencana QA sendiri menyatakan belum ada
-- dasar untuk menyimpulkan record Id=1039 harus diubah atau dihapus.
-- Yang dibutuhkan lebih dulu adalah bukti record mana yang benar-benar
-- mewakili Hermina Depok pada environment yang sedang diuji.
--
-- Cara pakai: jalankan BLOK 1 sampai 4 berurutan di environment yang
-- sedang diuji QA, lalu tempelkan hasilnya ke tiket. Keputusan di BLOK 5
-- diambil manusia, bukan oleh berkas ini.
--
-- Ganti <SITE_ID> dengan SiteId tenant yang diuji. Tanpa penyaring itu
-- hasilnya bisa memuat baris milik tenant lain, dan justru itulah kelas
-- kesalahan yang sedang dicari.
-- =====================================================================


-- ---------------------------------------------------------------------
-- BLOK 1 — Siapa saja yang bernama Hermina Depok, di tenant mana pun.
--
-- Sengaja TIDAK disaring SiteId: kalau ternyata ada dua baris di dua
-- tenant berbeda, itu temuan tersendiri yang harus terlihat di sini,
-- bukan tersembunyi oleh penyaring.
-- ---------------------------------------------------------------------
SELECT
    c.Id,
    c.Name,
    c.SiteId,
    c.ProviderId,
    c.MediaId,
    c.TargetId,
    c.StatusId,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.branch_name'))       AS branch_name,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.external_place_id')) AS place_id,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.city'))              AS city,
    c.CreateDate,
    c.ModifyDate
FROM Connection c
WHERE c.Name LIKE '%Hermina Depok%'
   OR JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.branch_name')) LIKE '%Hermina Depok%'
ORDER BY c.SiteId, c.Id;


-- ---------------------------------------------------------------------
-- BLOK 2 — Apa isi Id=1039 dan Id=977 sebenarnya.
--
-- QA memakai 1039 sebagai identitas dan menemukan datanya tidak cocok,
-- lalu 977 dinyatakan PASS. Blok ini menunjukkan keduanya berdampingan
-- supaya terlihat apakah keduanya cabang yang sama, cabang berbeda, atau
-- salah satunya milik tenant lain.
-- ---------------------------------------------------------------------
SELECT
    c.Id,
    c.Name,
    c.SiteId,
    c.ProviderId,
    c.TargetId,
    c.StatusId,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.branch_name'))       AS branch_name,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.external_place_id')) AS place_id,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.hospital_name'))     AS hospital_name,
    c.CreateDate
FROM Connection c
WHERE c.Id IN (1039, 977);


-- ---------------------------------------------------------------------
-- BLOK 3 — Identitas bisnis, bukan angka auto-increment.
--
-- Inilah bentuk assertion yang seharusnya dipakai test: kombinasi
-- SiteId + Provider + Place ID. Place ID-lah identitas yang benar-benar
-- stabil — ia milik Google, tidak berubah antar-environment, dan tidak
-- ikut bergeser saat tabel di-seed ulang.
-- ---------------------------------------------------------------------
SELECT
    c.Id,
    c.Name,
    c.SiteId,
    c.StatusId,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.branch_name'))       AS branch_name,
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.external_place_id')) AS place_id
FROM Connection c
WHERE c.SiteId = <SITE_ID>
  AND c.MediaId = 'GBUSINESS'
  AND JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.branch_name')) = 'Hermina Depok';


-- ---------------------------------------------------------------------
-- BLOK 4 — Apakah ada dua baris bisnis untuk satu cabang.
--
-- Place ID kembar bukan sekadar baris berlebih. Pada refresh worklist
-- Crawler, satu pasang (kind, external_place_id) yang kembar menggagalkan
-- SELURUH refresh, bukan hanya baris yang kembar itu — jadi blok ini
-- perlu mengembalikan nol baris sebelum smoke worklist dijalankan.
-- ---------------------------------------------------------------------
SELECT
    JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.external_place_id')) AS place_id,
    COUNT(*)                  AS jumlah_baris,
    GROUP_CONCAT(c.Id ORDER BY c.Id)     AS connection_ids,
    GROUP_CONCAT(c.StatusId ORDER BY c.Id) AS status_ids
FROM Connection c
WHERE c.SiteId = <SITE_ID>
  AND c.MediaId = 'GBUSINESS'
  AND JSON_UNQUOTE(JSON_EXTRACT(c.Options, '$.location.external_place_id')) IS NOT NULL
GROUP BY place_id
HAVING COUNT(*) > 1;


-- ---------------------------------------------------------------------
-- BLOK 5 — Keputusan (diisi manusia, bukan dijalankan)
--
-- Isi setelah BLOK 1-4 dijalankan:
--
--   Record mana yang mewakili Hermina Depok ....... Id = ______
--   SiteId-nya ................................... ______
--   Place ID-nya ................................. ______
--   StatusId-nya CNS2? ........................... ya / tidak
--   Id=1039 itu apa .............................. ______________________
--   Ada duplikat dari BLOK 4? .................... ya / tidak
--
-- Kemudian pilih SATU:
--
--   (a) 1039 adalah fixture dev yang memang dijamin migrasi
--       -> perbaiki seed/spec supaya cocok, jangan ubah test.
--
--   (b) 1039 hanya auto-increment
--       -> ubah TC_029 agar meng-assert kombinasi identitas BLOK 3,
--          bukan angka Id. Ini yang paling mungkin, dan yang
--          direkomendasikan rencana QA pasal 4.4.
--
--   (c) benar ada dua baris bisnis untuk satu cabang
--       -> cleanup terkendali: backup dulu, minta persetujuan owner,
--          batasi query ke Id yang sudah terbukti, lalu jalankan ulang
--          refresh worklist dan pastikan BLOK 4 kembali nol baris.
--
-- Jangan menempuh (c) hanya karena BLOK 1 mengembalikan dua baris.
-- Dua baris di dua SiteId berbeda adalah hal yang normal pada instalasi
-- multi-tenant, dan menghapus salah satunya akan merusak tenant lain.
-- ---------------------------------------------------------------------
