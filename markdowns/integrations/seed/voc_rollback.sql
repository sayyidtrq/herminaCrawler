-- =====================================================================
-- VoC OneBox — ROLLBACK: membatalkan voc_setup_all.sql + voc_dev_user.sql
--
--   ⚠️ HANYA efektif via DBeaver mode MANUAL COMMIT + COMMIT manual di akhir.
--      Lewat `mysql -uroot <db> < voc_rollback.sql`, COMMIT-nya di-comment,
--      jadi transaksi ke-ROLLBACK saat sesi tertutup = TIDAK menghapus apa-apa
--      (fail-safe, tapi jangan mengira CLI-nya "berhasil menghapus").
--
-- IDEMPOTENT: aman di-run ulang. Kalau datanya sudah tidak ada,
-- setiap DELETE hanya melaporkan 0 rows.
--
-- ⚠️ HANYA UNTUK ENVIRONMENT DEV/LOKAL. JANGAN di staging/produksi.
--
-- YANG SENGAJA TIDAK DIHAPUS (baca alasannya di bagian masing-masing):
--   - Reference 'GBUSINESS'  -> master data standar OneBox, dipakai fitur lain
--   - Location Hermina/HGA   -> berpotensi masih dirujuk Ticket
--   - Data hasil INGEST      -> lihat BAGIAN 2, harus dicek manual dulu
--
-- CARA PAKAI:
--   1. Jalankan BAGIAN 0 (preview). Lihat berapa row yang akan kena.
--   2. Jalankan BAGIAN 2 (cek dependensi). Kalau ada anak data, urus dulu.
--   3. Jalankan BAGIAN 3 (rollback) — dibungkus transaksi.
--   4. Lihat hasil verifikasi, lalu COMMIT; atau ROLLBACK; sendiri.
-- =====================================================================

-- >>> SESUAIKAN dengan env target — samakan dengan script seed <<<
SET @site  := 169;
SET @email := 'voc.dev@onebox.local';

-- Daftar slug Category dari voc_setup_all.sql. Dipakai sebagai penanda:
-- HANYA row dengan Remarks di daftar ini yang dihapus, sehingga Category
-- lain milik site yang sama tidak ikut kena.
SET @cat_slugs := 'doctor_service,nurse_service,administration,waiting_time,'
                  'cleanliness,facility,parking,billing,pharmacy,emergency_room,'
                  'inpatient,customer_service,booking_system,staff_communication,'
                  'security,food,general_praise,other';


-- =====================================================================
-- BAGIAN 0 — PREVIEW (read-only, tidak mengubah apa pun)
-- Jalankan ini DULU. Angka di sini = jumlah row yang akan dihapus.
-- =====================================================================

SELECT 'Reference PVD97' AS objek,
       (SELECT COUNT(*) FROM Reference WHERE Id='PVD97') AS akan_dihapus
UNION ALL SELECT 'Category (slug VoC)',
       (SELECT COUNT(*) FROM Category
         WHERE SiteId=@site AND FIND_IN_SET(Remarks, @cat_slugs) > 0)
UNION ALL SELECT 'Connection VoC',
       (SELECT COUNT(*) FROM Connection WHERE SiteId=@site AND ProviderId='PVD97')
UNION ALL SELECT 'Menu voc%',
       (SELECT COUNT(*) FROM Menu WHERE Code LIKE 'voc%')
UNION ALL SELECT 'Permission menu voc%',
       (SELECT COUNT(*) FROM Permission
         WHERE ObjectName='Menu'
           AND ObjectId IN (SELECT Id FROM (SELECT Id FROM Menu WHERE Code LIKE 'voc%') t))
UNION ALL SELECT 'User voc.dev',
       (SELECT COUNT(*) FROM User WHERE Email=@email)
UNION ALL SELECT 'Contact voc.dev',
       (SELECT COUNT(*) FROM Contact WHERE Email=@email AND SiteId=@site);


-- =====================================================================
-- BAGIAN 1 — TANGKAP ID yang dibutuhkan
-- =====================================================================

SET @user    := (SELECT Id FROM User    WHERE Email=@email                LIMIT 1);
SET @contact := (SELECT Id FROM Contact WHERE Email=@email AND SiteId=@site LIMIT 1);

SET @conn_hermina := (SELECT Id FROM Connection
                       WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='4'
                       ORDER BY Id LIMIT 1);
SET @conn_hga     := (SELECT Id FROM Connection
                       WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='2'
                       ORDER BY Id LIMIT 1);


-- =====================================================================
-- BAGIAN 2 — CEK DEPENDENSI (read-only) — JANGAN DILEWATI
--
-- Kalau kamu sudah pernah menjalankan perintah INGEST:
--   php app/bootstrap.php voice_of_customer_system receive/processpending/analysis
-- maka ada data turunan (Ticket dsb) yang menunjuk ke Connection di atas.
-- Menghapus Connection duluan akan gagal karena foreign key, ATAU —
-- lebih buruk — meninggalkan data yatim kalau FK-nya tidak ada.
--
-- Query di bawah menemukan sendiri tabel mana saja yang merujuk Connection,
-- jadi tidak perlu menebak nama tabel.
-- =====================================================================

SELECT TABLE_NAME        AS tabel_anak,
       COLUMN_NAME       AS kolom,
       CONSTRAINT_NAME   AS nama_fk
  FROM information_schema.KEY_COLUMN_USAGE
 WHERE TABLE_SCHEMA = DATABASE()
   AND REFERENCED_TABLE_NAME = 'Connection';

-- Sama untuk Location dan Category:
SELECT TABLE_NAME AS tabel_anak, COLUMN_NAME AS kolom, REFERENCED_TABLE_NAME AS induk
  FROM information_schema.KEY_COLUMN_USAGE
 WHERE TABLE_SCHEMA = DATABASE()
   AND REFERENCED_TABLE_NAME IN ('Location','Category','Reference');

-- Kalau hasilnya kosong: tidak ada FK, aman lanjut.
-- Kalau ada isinya: hapus dulu row anak yang ConnectionId-nya
-- @conn_hermina / @conn_hga, baru jalankan BAGIAN 3.


-- =====================================================================
-- BAGIAN 3 — ROLLBACK
--
-- Dibungkus transaksi supaya bisa dibatalkan. Di DBeaver, pastikan
-- toolbar diganti dari "Auto" ke "Manual Commit" dulu — kalau tidak,
-- START TRANSACTION di bawah tidak berpengaruh dan setiap DELETE
-- langsung permanen.
--
-- Urutan dibalik dari script seed: anak dulu, induk belakangan.
-- =====================================================================

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 3a) AKUN DEV (dari voc_dev_user.sql)
--     Urutan wajib: putus tautan balik -> User -> Contact.
--     User.ContactId NOT NULL menunjuk ke Contact, dan Contact.UserId
--     menunjuk balik ke User. Salah satu harus diputus lebih dulu.
-- ---------------------------------------------------------------------

DELETE FROM UserRole WHERE UserId = @user AND SiteId = @site;
DELETE FROM Member   WHERE UserId = @user;

UPDATE Contact SET UserId = NULL, ModifyDate = NOW() WHERE Id = @contact;

DELETE FROM User    WHERE Id = @user;
DELETE FROM Contact WHERE Id = @contact;

-- Catatan: kolom Creator/Modifier di row lain mungkin berisi Id user ini.
-- Itu kolom audit biasa (bukan foreign key), jadi dibiarkan apa adanya —
-- menimpanya justru memalsukan jejak audit.

-- ---------------------------------------------------------------------
-- 3b) MENU + PERMISSION
--     Permission dihapus lebih dulu karena menunjuk ke Menu.Id.
--     Pola derived table (SELECT ... FROM (SELECT ...) t) dipakai karena
--     MySQL melarang subquery langsung ke tabel yang sedang di-DELETE.
-- ---------------------------------------------------------------------

DELETE FROM Permission
 WHERE ObjectName = 'Menu'
   AND ObjectId IN (SELECT Id FROM (SELECT Id FROM Menu WHERE Code LIKE 'voc%') t);

DELETE FROM Menu WHERE Code LIKE 'voc%';

-- ---------------------------------------------------------------------
-- 3c) CONNECTION
--     Jalankan HANYA setelah BAGIAN 2 bersih. Kalau masih ada Ticket
--     yang menunjuk ke sini, statement ini akan gagal dengan
--     "Cannot delete or update a parent row" — itu perilaku yang benar,
--     bukan bug. Hapus data turunannya dulu.
-- ---------------------------------------------------------------------

DELETE FROM Connection WHERE SiteId = @site AND ProviderId = 'PVD97';

-- ---------------------------------------------------------------------
-- 3d) CATEGORY
--     Dibatasi ke 18 slug bawaan seed. Category lain di site yang sama
--     tidak tersentuh.
-- ---------------------------------------------------------------------

DELETE FROM Category
 WHERE SiteId = @site
   AND FIND_IN_SET(Remarks, @cat_slugs) > 0;

-- ---------------------------------------------------------------------
-- 3e) REFERENCE
--     PVD97 dihapus. GBUSINESS TIDAK.
--
--     GBUSINESS adalah MediaId standar OneBox — seed hanya menyisipkannya
--     kalau belum ada, dan fitur lain (channel Google Business di luar VoC)
--     bergantung padanya. Menghapusnya bisa merusak hal yang tidak ada
--     hubungannya dengan VoC. Kalau kamu benar-benar yakin DB ini bersih
--     dan GBUSINESS memang lahir dari seed VoC, baru buka komentar di bawah.
-- ---------------------------------------------------------------------

DELETE FROM Reference WHERE Id = 'PVD97';

-- DELETE FROM Reference WHERE Id = 'GBUSINESS';   -- <- sengaja dinonaktifkan

-- ---------------------------------------------------------------------
-- 3f) LOCATION — sengaja TIDAK dihapus secara default
--
--     Location bersifat global (tidak punya SiteId) dan menurut komentar
--     di script seed, Id-nya dipakai untuk join Ticket lewat
--     Options.onebox_location_id. Kalau ada Ticket yang sudah masuk,
--     menghapus Location membuat data itu menggantung.
--
--     Buka komentar HANYA kalau BAGIAN 2 menunjukkan tidak ada yang
--     merujuk Location, dan kamu yakin dua row ini lahir dari seed VoC.
-- ---------------------------------------------------------------------

-- DELETE FROM Location WHERE Description IN ('Hermina Depok','HGA Depok');


-- =====================================================================
-- BAGIAN 4 — VERIFIKASI (masih di dalam transaksi)
-- Semua kolom harus 0. Kalau ya, jalankan COMMIT;
-- Kalau ada yang aneh, jalankan ROLLBACK; dan tidak ada yang berubah.
-- =====================================================================

SELECT
  (SELECT COUNT(*) FROM Reference  WHERE Id='PVD97')                        AS sisa_provider,
  (SELECT COUNT(*) FROM Category   WHERE SiteId=@site
                                     AND FIND_IN_SET(Remarks,@cat_slugs)>0) AS sisa_category,
  (SELECT COUNT(*) FROM Connection WHERE SiteId=@site AND ProviderId='PVD97') AS sisa_connection,
  (SELECT COUNT(*) FROM Menu       WHERE Code LIKE 'voc%')                  AS sisa_menu,
  (SELECT COUNT(*) FROM User       WHERE Email=@email)                      AS sisa_user,
  (SELECT COUNT(*) FROM Contact    WHERE Email=@email AND SiteId=@site)     AS sisa_contact;

-- Puas dengan hasilnya?
--   COMMIT;
-- Ada yang salah?
--   ROLLBACK;

-- =====================================================================
-- CATATAN PENTING
--
-- 1. Kalau tujuanmu cuma "seed ulang dari bersih", script ini TIDAK PERLU.
--    voc_setup_all.sql dan voc_dev_user.sql keduanya idempotent — tinggal
--    jalankan lagi. Bagian menu bahkan sudah menghapus dan membuat ulang
--    dirinya sendiri (DELETE FROM Menu WHERE Code LIKE 'voc%').
--
-- 2. Script ini berguna untuk: mengembalikan DB ke kondisi seperti sebelum
--    VoC pernah ada — misalnya menguji seed dari nol, atau membersihkan
--    env sebelum menyerahkan pekerjaan.
--
-- 3. Rollback TIDAK memperbaiki kegagalan koneksi (SQLSTATE 2002).
--    Error itu terjadi sebelum satu query pun terkirim, jadi tidak ada
--    kaitannya dengan isi database.
-- =====================================================================
