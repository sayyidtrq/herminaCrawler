-- =====================================================================
-- VoC OneBox — AKUN DEV untuk akses Media Monitoring + menu Voice of Customer
--
--   mysql -uroot <db> < scriptdb/voc/voc_dev_user.sql
--
-- IDEMPOTENT: aman di-run ulang (tidak menggandakan User/Contact/Member/UserRole).
--
-- ⚠️ HANYA UNTUK ENVIRONMENT DEV/LOKAL. JANGAN dijalankan di staging/produksi.
--    Script ini membuat akun login dengan password yang tertulis di file ini
--    (file ini masuk git — jadi passwordnya bukan rahasia, dan memang tidak
--    boleh dianggap rahasia). Sengaja DIPISAH dari voc_setup_all.sql supaya
--    pembuatan akun tidak pernah jadi efek samping dari seed master data.
--
-- CARA KERJA: MENGKLONING AKUN REFERENSI.
--   Akses & permission TIDAK ditebak dari struktur menu, melainkan disalin
--   dari akun yang memang sudah terbukti bisa membuka Media Monitoring
--   (@ref_email di bawah). Kalau akun referensi jalan, kloningnya jalan.
--   Yang disalin: daftar Role + organisasi tempat Member-nya bernaung.
--
-- Rantai yang harus lengkap supaya login berhasil (LoginController::choosenSite):
--   User -> Member -> Organization -> Site      (penentu site mana yang boleh)
--   User -> UserRole -> Role -> Permission      (penentu menu apa yang terlihat)
--   User.ContactId <-> Contact.UserId           (tautan DUA ARAH, keduanya diisi)
-- =====================================================================

-- >>> SESUAIKAN dengan env target <<<
SET @site      := 169;
SET @email     := 'voc.dev@onebox.local';   -- domain .local: tidak bisa menerima email betulan
SET @nama      := 'VoC Dev';
SET @password  := 'voc12345';
SET @ref_email := 'admin-news@ciptadrasoft.com';   -- akun contoh yang sudah bisa buka MM

-- ---------------------------------------------------------------------
-- 0) BACA AKUN REFERENSI
-- ---------------------------------------------------------------------
SET @ref := (SELECT Id FROM User WHERE Email=@ref_email LIMIT 1);

-- Organisasi: ikut punya akun referensi. Kalau referensi tidak ada di DB ini,
-- pakai organisasi induk site (TypeId 'OT1'), lalu organisasi apa pun milik site.
SET @org := COALESCE(
  (SELECT m.OrganizationId FROM Member m JOIN Organization o ON o.Id=m.OrganizationId
    WHERE m.UserId=@ref AND o.SiteId=@site ORDER BY m.Id LIMIT 1),
  (SELECT Id FROM Organization WHERE SiteId=@site ORDER BY (TypeId='OT1') DESC, Id LIMIT 1)
);

-- Berapa role yang bisa disalin dari referensi? Dipakai memilih lapis di bawah.
SET @n_ref := (SELECT COUNT(*) FROM UserRole WHERE UserId=@ref AND SiteId=@site);

-- ---------------------------------------------------------------------
-- 1) CONTACT (User.ContactId NOT NULL)
-- ---------------------------------------------------------------------
INSERT INTO Contact (Name, Email, SiteId, IsPerson, TypeId, LevelId, StatusId,
                     CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT @nama, @email, @site, 1, 'CT1', 'CL1', 'CS1', NOW(), 1, NOW(), 1, '3000-01-01 00:00:00'
WHERE @org IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM Contact WHERE Email=@email AND SiteId=@site);
SET @contact := (SELECT Id FROM Contact WHERE Email=@email AND SiteId=@site ORDER BY Id LIMIT 1);

-- ---------------------------------------------------------------------
-- 2) USER
-- ---------------------------------------------------------------------
-- Hash mengikuti Library\Crypter::generatePasswordHash():
--   PasswordSalt = uuid, Password = sha1(PasswordSalt + password)
SET @salt := UUID();

INSERT INTO User (Name, Email, Password, PasswordSalt, Enabled, StatusId, GroupId,
                  Logged, Failed, ContactId, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT @nama, @email, SHA1(CONCAT(@salt, @password)), @salt, 1, 'SMS', 'SMS',
       0, 0, @contact, NOW(), 1, NOW(), 1, '3000-01-01 00:00:00'
WHERE @contact IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM User WHERE Email=@email);
SET @user := (SELECT Id FROM User WHERE Email=@email ORDER BY Id LIMIT 1);

-- Reset password + buka blokir untuk akun yang sudah ada (dev lupa password,
-- atau salah login berkali-kali sampai Failed naik). Hanya menyentuh akun dev ini.
UPDATE User
   SET PasswordSalt = @salt,
       Password     = SHA1(CONCAT(@salt, @password)),
       Enabled      = 1,
       Failed       = 0,
       StatusId     = 'SMS',
       ModifyDate   = NOW()
 WHERE Id = @user;

-- Tautan balik Contact -> User. Akun referensi mengisinya (Contact.UserId=575);
-- tanpa ini pencarian kontak berdasarkan UserId tidak menemukan apa-apa.
UPDATE Contact SET UserId = @user, ModifyDate = NOW()
 WHERE Id = @contact AND (UserId IS NULL OR UserId <> @user);

-- ---------------------------------------------------------------------
-- 3) MEMBER — inilah yang mengikat user ke SITE (lewat Organization)
-- ---------------------------------------------------------------------
-- StatusId 'OFF' / StateId 'UST1' mengikuti akun referensi: akun baru memang
-- belum online. Aplikasi yang mengubahnya saat login.
INSERT INTO Member (Code, Name, OrganizationId, UserId, RoleId, Priority, Enabled,
                    StatusId, StateId, StateDate, ParentId,
                    CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT @site, @nama, @org, @user,
       COALESCE((SELECT m.RoleId FROM Member m WHERE m.UserId=@ref ORDER BY m.Id LIMIT 1), 'MR5'),
       1, 1, 'OFF', 'UST1', NOW(), 0, NOW(), 1, NOW(), 1, '3000-01-01 00:00:00'
WHERE @user IS NOT NULL AND @org IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM Member WHERE UserId=@user AND OrganizationId=@org);

-- Catatan: akun referensi punya 2 row Member (organisasi induk + unit kerja).
-- Yang kedua adalah penempatan struktur organisasi, BUKAN penentu akses —
-- site sudah didapat dari row pertama. Sengaja tidak diikutkan.

-- ---------------------------------------------------------------------
-- 4) ROLE — penentu menu Media Monitoring (dan VoC) terlihat
-- ---------------------------------------------------------------------
-- ⚠️ User TANPA role sama sekali bukan sekadar "menu kosong":
-- ControllerBase::getUserAllRole() mengembalikan string kosong dan pemanggilnya
-- menempelkannya langsung ke `RoleId IN (...)` (MenuController::sideMenuAction),
-- sehingga jadi `IN ()` — bukan SQL yang sah, halaman mati dengan SQLSTATE 1064.
--
-- Akar masalahnya ada di getUserAllRole() dan BELUM diperbaiki: di luar scope
-- pekerjaan VoC, menunggu review senior dev. Selama itu belum beres, SIAPA PUN
-- yang punya user tanpa role kena error yang sama — bukan cuma akun script ini.
-- Yang bisa dilakukan di sini: memastikan script ini tidak ikut membuatnya.
-- Karena itu ada TIGA lapis, dan OUTPUT menolak menyatakan OK kalau role nol.
--
-- Tidak memakai CREATE/DROP TEMPORARY TABLE: pada MySQL dengan
-- enforce_gtid_consistency=ON, statement TEMPORARY dilarang di dalam transaksi,
-- sehingga script gagal kalau dev membungkusnya dengan START TRANSACTION untuk
-- uji coba. Ketersediaan tiap lapis dihitung dulu sebagai angka.

SET @codes := 'userNews,Pimpinan Pusat';   -- role Media Monitoring bawaan OneBox
SET @n_code := (SELECT COUNT(*) FROM Role WHERE FIND_IN_SET(Code, @codes) > 0);

INSERT INTO UserRole (UserId, RoleId, SiteId, CreateDate, ModifyDate)
SELECT @user, r.Id, @site, NOW(), NOW()
FROM Role r
WHERE @user IS NOT NULL
  AND (
    -- Lapis 1 (utama): SALIN PERSIS role akun referensi
    (@n_ref > 0 AND r.Id IN (SELECT ur.RoleId FROM UserRole ur
                              WHERE ur.UserId=@ref AND ur.SiteId=@site))

    -- Lapis 2: referensi tidak ada di DB ini -> pakai Code bawaan
    OR (@n_ref = 0 AND @n_code > 0 AND FIND_IN_SET(r.Code, @codes) > 0)

    -- Lapis 3: pilihan terakhir — role mana pun yang sudah memegang izin menu
    -- di site ini. Lebih baik melihat menu yang sama dengan role lain daripada
    -- tidak punya role sama sekali (lihat peringatan di atas).
    OR (@n_ref = 0 AND @n_code = 0 AND r.Id IN (
        SELECT p.RoleId FROM Permission p
        WHERE p.ObjectName='Menu' AND p.ActionId='ALLOWED' AND p.SiteId=@site))
  )
  AND NOT EXISTS (
    SELECT 1 FROM UserRole ur WHERE ur.UserId=@user AND ur.RoleId=r.Id AND ur.SiteId=@site
  );

-- Catatan: tabel Assignment (kuota penugasan Ticket/Prospect) milik akun
-- referensi TIDAK disalin — itu pengaturan beban kerja, bukan hak akses.
-- Akun dev tidak perlu menerima penugasan otomatis.

-- ---------------------------------------------------------------------
-- 5) OUTPUT — hasil & diagnosa
-- ---------------------------------------------------------------------
SELECT
  CASE
    WHEN @org  IS NULL THEN 'GAGAL: site ini belum punya Organization — cek SET @site di atas'
    WHEN @user IS NULL THEN 'GAGAL: user tidak terbentuk'
    WHEN (SELECT COUNT(*) FROM UserRole WHERE UserId=@user AND SiteId=@site) = 0
      THEN 'GAGAL: user dibuat TAPI TANPA ROLE. Jangan dipakai login — halaman menu akan error. Jalankan voc_setup_all.sql dulu, lalu ulangi script ini.'
    ELSE 'OK — silakan login'
  END                                                                   AS status,
  @user                                                                 AS user_id,
  @email                                                                AS login_email,
  @password                                                             AS login_password,
  @site                                                                 AS site_id,
  @org                                                                  AS organization_id,
  CASE WHEN @n_ref > 0 THEN CONCAT('salinan dari ', @ref_email)
       WHEN @n_code > 0 THEN 'fallback: Role.Code bawaan'
       ELSE 'fallback: role berizin menu di site ini' END               AS sumber_role,
  (SELECT GROUP_CONCAT(r.Name ORDER BY r.Name SEPARATOR ', ')
     FROM UserRole ur JOIN Role r ON r.Id=ur.RoleId
    WHERE ur.UserId=@user AND ur.SiteId=@site)                          AS daftar_role;

-- Perbandingan dengan akun referensi — semua kolom harus sama.
SELECT u.Id, u.Email,
  (SELECT COUNT(*) FROM Contact c WHERE c.Id=u.ContactId)     AS punya_contact,
  (SELECT COUNT(*) FROM Contact c WHERE c.UserId=u.Id)        AS contact_balik_ke_user,
  (SELECT COUNT(*) FROM Member m JOIN Organization o ON o.Id=m.OrganizationId
    WHERE m.UserId=u.Id AND o.SiteId=@site)                   AS member_di_site,
  (SELECT COUNT(*) FROM UserRole ur WHERE ur.UserId=u.Id AND ur.SiteId=@site) AS jml_role
FROM User u WHERE u.Id IN (@ref, @user);

-- =====================================================================
-- LANGKAH BERIKUTNYA
--
-- 1) Login pakai email & password di atas.
-- 2) Kalau diminta memilih site, pilih site yang sesuai (@site).
-- 3) Media Monitoring -> HARD-RELOAD (Ctrl+Shift+R) -> sidebar "Voice of Customer".
--
-- Menu VoC-nya sendiri berasal dari scriptdb/voc/voc_setup_all.sql — jalankan
-- itu DULU. Script ini hanya membuat akun yang berhak melihatnya.
--
-- Macet? Jalankan scriptdb/voc/voc_dev_diagnose.sql (read-only).
-- =====================================================================
