-- =====================================================================
-- VoC OneBox — SETUP ALL (satu file): master data + menu, sekali jalan.
-- IDEMPOTENT: aman di-run ulang (tidak menggandakan Provider/Category/
-- Location/Connection/Menu).
--
--   mysql -uroot <db> < scriptdb/voc/voc_setup_all.sql
--
-- ⚠️ JALANKAN SELURUH FILE (DBeaver: Alt+X "Execute SQL Script"), JANGAN
--    per-baris (Ctrl+Enter) — blok DELIMITER/CREATE PROCEDURE di bagian menu
--    butuh dijalankan sebagai satu script utuh.
--
-- Setelah ini: (1) copy fixture, (2) INGEST (lihat blok komentar di bawah).
-- Prasyarat: MediaId 'GBUSINESS' standar OneBox (kalau belum ada, di-insert di sini).
-- =====================================================================

-- >>> SESUAIKAN SiteId env target (default 169) <<<
SET @site := 169;

-- ---------------------------------------------------------------------
-- 1) MASTER DATA
-- ---------------------------------------------------------------------

-- MediaId GBUSINESS (guard)
INSERT INTO Reference (Id, Code, Description, GroupId, Sequence, Enabled, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT 'GBUSINESS','Gbusiness','Google Business','Media',0,1,NOW(),1,NOW(),1,'3000-01-01 00:00:00'
WHERE NOT EXISTS (SELECT 1 FROM Reference WHERE Id='GBUSINESS');

-- Provider Voice of Customer System.
-- Code WAJIB pendek: Messaging::getInstance() menyusun nama class provider dari
-- kolom ini (\Service\Provider\{Code}Provider), sementara lebar Reference.Code
-- berbeda antar-environment. Code lama 'VoiceOfCustomerSystem' (21 karakter)
-- menggagalkan seed di DB yang kolomnya lebih sempit. 'Voc' → class VocProvider.
INSERT INTO Reference (Id, Code, Description, GroupId, Sequence, Enabled, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT 'PVD97','Voc','Voice of Customer System','Provider',0,1,NOW(),1,NOW(),1,'3000-01-01 00:00:00'
WHERE NOT EXISTS (SELECT 1 FROM Reference WHERE Id='PVD97');

-- Perbaiki row yang terlanjur ke-seed dengan Code lama (DB yang sudah jalan
-- sebelum perubahan ini). Tanpa baris ini, getInstance() masih mencari class
-- VoiceOfCustomerSystemProvider yang sudah tidak ada.
UPDATE Reference SET Code='Voc' WHERE Id='PVD97' AND Code<>'Voc';

-- Master Category (slug enum VoC di kolom Remarks; dipakai provider utk mapping)
INSERT INTO Category (SiteId, Code, Description, TypeId, GroupId, Remarks, Sequence, Enabled, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT @site, c.Code, c.Description, 'TC1', NULL, c.Remarks, c.Sequence, 1, NOW(), 1, NOW(), 1, '3000-01-01 00:00:00'
FROM (
  SELECT 'doctor_svc' AS Code, 'Pelayanan Dokter'   AS Description, 'doctor_service'      AS Remarks, 1  AS Sequence UNION ALL
  SELECT 'nurse_svc',  'Pelayanan Perawat',  'nurse_service',       2  UNION ALL
  SELECT 'admin',      'Administrasi',       'administration',      3  UNION ALL
  SELECT 'wait_time',  'Waktu Tunggu',       'waiting_time',        4  UNION ALL
  SELECT 'clean',      'Kebersihan',         'cleanliness',         5  UNION ALL
  SELECT 'facility',   'Fasilitas',          'facility',            6  UNION ALL
  SELECT 'parking',    'Parkir',             'parking',             7  UNION ALL
  SELECT 'billing',    'Tagihan/Pembayaran', 'billing',             8  UNION ALL
  SELECT 'pharmacy',   'Farmasi',            'pharmacy',            9  UNION ALL
  SELECT 'er',         'IGD',                'emergency_room',      10 UNION ALL
  SELECT 'inpatient',  'Rawat Inap',         'inpatient',           11 UNION ALL
  SELECT 'cust_svc',   'Customer Service',   'customer_service',    12 UNION ALL
  SELECT 'booking',    'Sistem Booking',     'booking_system',      13 UNION ALL
  SELECT 'staff_comm', 'Komunikasi Staf',    'staff_communication', 14 UNION ALL
  SELECT 'security',   'Keamanan',           'security',            15 UNION ALL
  SELECT 'food',       'Makanan',            'food',                16 UNION ALL
  SELECT 'praise',     'Pujian Umum',        'general_praise',      17 UNION ALL
  SELECT 'other',      'Lainnya',            'other',               18
) c
WHERE NOT EXISTS (SELECT 1 FROM Category x WHERE x.SiteId=@site AND x.Remarks=c.Remarks);

-- Location OneBox (global). Idempotent by Description, lalu tangkap Id.
INSERT INTO Location (Description, City, Longitude, Latitude, Altitude, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT 'Hermina Depok','Depok',0,0,0,NOW(),1,NOW(),1,'3000-01-01 00:00:00'
WHERE NOT EXISTS (SELECT 1 FROM Location WHERE Description='Hermina Depok');
SET @loc_hermina := (SELECT Id FROM Location WHERE Description='Hermina Depok' ORDER BY Id LIMIT 1);

INSERT INTO Location (Description, City, Longitude, Latitude, Altitude, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT 'HGA Depok','Depok',0,0,0,NOW(),1,NOW(),1,'3000-01-01 00:00:00'
WHERE NOT EXISTS (SELECT 1 FROM Location WHERE Description='HGA Depok');
SET @loc_hga := (SELECT Id FROM Location WHERE Description='HGA Depok' ORDER BY Id LIMIT 1);

-- Connection VoC (mock mode). Idempotent by (SiteId, ProviderId, TargetId).
--
-- SEJAK ADR-0001 row Connection BUKAN sekadar konfigurasi channel — ini RECORD
-- MASTER CABANG (OneBox = System of Record). Karena itu Options membawa:
--   Options.location            metadata cabang yang dikelola di layar "Cabang"
--   Options.onebox_location_id  Id master Location OneBox (cermin untuk join Ticket)
--   Options.location_map        {"<location_id VoC>": <LocationId OneBox>}
--   Options.provisioning        status kirim ke VoC ('synced' | 'pending' | 'failed')
--
-- TargetId = location_id VoC (4=Hermina Depok, 2=HGA Depok).
-- external_place_id = Place ID Google (data publik, bukan kredensial) — nilai ini
-- yang dipakai crawler VoC sebagai target. Salah isi = review cabang lain masuk.
INSERT INTO Connection (SiteId, MediaId, ProviderId, Code, Name, UserId, Password, Port, Url, `From`, Options, Priority, Enabled, Error, StatusId, TargetId, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT @site,'GBUSINESS','PVD97','VOC','VoC System - Hermina Depok','','',0,'','Onebox',
  JSON_OBJECT(
    'mock',true,'mock_file','/tmp/voc_reviews_sample.json','page_size',50,'max_pages',10,
    'location_map',JSON_OBJECT('4',@loc_hermina),
    'onebox_location_id',@loc_hermina,
    'location',JSON_OBJECT(
      'branch_name','Hermina Depok','hospital_name','Hermina','city','Depok','address','',
      'external_place_id','ChIJ3W4519YcaS4R5g-B41W8T_U','google_maps_url','',
      'target_review_count',50,'source','selenium'),
    'provisioning',JSON_OBJECT('status','synced','reason','Lokasi sudah ada di VoC (seed)')),
  1,1,0,'CNS1','4',NOW(),1,NOW(),1,'3000-01-01 00:00:00'
WHERE NOT EXISTS (SELECT 1 FROM Connection WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='4');
SET @conn_hermina := (SELECT Id FROM Connection WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='4' ORDER BY Id LIMIT 1);

INSERT INTO Connection (SiteId, MediaId, ProviderId, Code, Name, UserId, Password, Port, Url, `From`, Options, Priority, Enabled, Error, StatusId, TargetId, CreateDate, Creator, ModifyDate, Modifier, ExpireDate)
SELECT @site,'GBUSINESS','PVD97','VOC','VoC System - HGA Depok','','',0,'','Onebox',
  JSON_OBJECT(
    'mock',true,'mock_file','/tmp/voc_reviews_sample.json','page_size',50,'max_pages',10,
    'location_map',JSON_OBJECT('2',@loc_hga),
    'onebox_location_id',@loc_hga,
    'location',JSON_OBJECT(
      'branch_name','HGA Depok','hospital_name','HGA','city','Depok','address','',
      'external_place_id','ChIJtx6hk73raS4RGaf0GgVPPks','google_maps_url','',
      'target_review_count',100,'source','selenium'),
    'provisioning',JSON_OBJECT('status','synced','reason','Lokasi sudah ada di VoC (seed)')),
  1,1,0,'CNS1','2',NOW(),1,NOW(),1,'3000-01-01 00:00:00'
WHERE NOT EXISTS (SELECT 1 FROM Connection WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='2');
SET @conn_hga := (SELECT Id FROM Connection WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='2' ORDER BY Id LIMIT 1);

-- Backfill untuk DB yang sudah ke-seed versi LAMA (belum punya Options.location).
-- Tanpa ini layar "Cabang" menampilkan Place ID kosong, dan menyimpan cabang itu
-- lewat UI akan menandainya 'pending' seolah belum pernah ada di VoC.
-- JSON_MERGE_PATCH dipakai supaya kunci lain (service_token, _sync_cursor,
-- api_mode) tidak ikut tertimpa. Hanya row yang benar-benar belum punya
-- Options.location yang disentuh — perubahan dev tidak akan tertimpa.
UPDATE Connection
   SET Options = JSON_MERGE_PATCH(COALESCE(Options,'{}'), JSON_OBJECT(
         'onebox_location_id',@loc_hermina,
         'location_map',JSON_OBJECT('4',@loc_hermina),
         'location',JSON_OBJECT(
           'branch_name','Hermina Depok','hospital_name','Hermina','city','Depok','address','',
           'external_place_id','ChIJ3W4519YcaS4R5g-B41W8T_U','google_maps_url','',
           'target_review_count',50,'source','selenium'),
         'provisioning',JSON_OBJECT('status','synced','reason','Lokasi sudah ada di VoC (seed)'))),
       ModifyDate = NOW()
 WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='4'
   AND JSON_EXTRACT(COALESCE(Options,'{}'),'$.location') IS NULL;

UPDATE Connection
   SET Options = JSON_MERGE_PATCH(COALESCE(Options,'{}'), JSON_OBJECT(
         'onebox_location_id',@loc_hga,
         'location_map',JSON_OBJECT('2',@loc_hga),
         'location',JSON_OBJECT(
           'branch_name','HGA Depok','hospital_name','HGA','city','Depok','address','',
           'external_place_id','ChIJtx6hk73raS4RGaf0GgVPPks','google_maps_url','',
           'target_review_count',100,'source','selenium'),
         'provisioning',JSON_OBJECT('status','synced','reason','Lokasi sudah ada di VoC (seed)'))),
       ModifyDate = NOW()
 WHERE SiteId=@site AND ProviderId='PVD97' AND TargetId='2'
   AND JSON_EXTRACT(COALESCE(Options,'{}'),'$.location') IS NULL;

-- ---------------------------------------------------------------------
-- 2) MENU (di sidebar Media Monitoring "Semua Sumber") — env-agnostic
-- ---------------------------------------------------------------------

-- Resolve sumber permission SEBELUM cleanup. DB lama memakai menu legacy
-- (mis. listberita/sentiment + NavigateUrl TabelInformasi()), sedangkan DB baru
-- memakai route #/news/list/semua_sumber. Hanya pilih kandidat yang benar-benar
-- memiliki permission ALLOWED agar VoC mengikuti audience menu MM yang nyata.
SET @src := (
  SELECT m.Id
  FROM Menu m
  WHERE m.TypeId='SIDEMENU'
    AND EXISTS (
      SELECT 1 FROM Permission p
       WHERE p.ObjectName='Menu' AND p.ObjectId=m.Id AND p.ActionId='ALLOWED'
    )
    AND (
      m.NavigateUrl='#/news/list/semua_sumber'
      OR m.Code IN ('SemuaSumber','listberita','sentiment')
      OR m.Description IN ('Daftar Berita','Berita','Informasi')
    )
  ORDER BY CASE
    WHEN m.NavigateUrl='#/news/list/semua_sumber' THEN 0
    WHEN m.Code='SemuaSumber' THEN 1
    WHEN m.Code='listberita' THEN 2
    WHEN m.Description IN ('Daftar Berita','Berita') THEN 3
    WHEN m.Code='sentiment' THEN 4
    ELSE 5
  END, m.Id
  LIMIT 1
);
SET @mm := (SELECT ParentId FROM Menu WHERE Id=@src LIMIT 1);

-- Fail-fast: jangan membuat menu VoC orphan dan tanpa permission jika struktur
-- MM berbeda atau source menu belum punya audience.
DROP PROCEDURE IF EXISTS voc_assert_menu_source;
DELIMITER //
CREATE PROCEDURE voc_assert_menu_source()
BEGIN
  IF @src IS NULL OR @mm IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT='VoC seed aborted: MM source menu/parent with ALLOWED permission was not found';
  END IF;
END//
DELIMITER ;
CALL voc_assert_menu_source();
DROP PROCEDURE voc_assert_menu_source;

-- Bersihkan menu VoC lama (idempotent) setelah source valid.
DELETE FROM Permission WHERE ObjectName='Menu' AND ObjectId IN (SELECT Id FROM (SELECT Id FROM Menu WHERE Code LIKE 'voc%') t);
DELETE FROM Menu WHERE Code LIKE 'voc%';

INSERT INTO Menu (Code,TypeId,NavigateUrl,Visible,Enabled,Description,ImageUrl,Priority,BeginGroup,Collapsed,Level,CreateDate,Creator,ModifyDate,Modifier,ExpireDate,ParentId)
VALUES ('voc','SIDEMENU','',1,1,'Voice of Customer','fi-rr-comment-heart',6,1,1,1,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@mm);
SET @voc := LAST_INSERT_ID();

INSERT INTO Menu (Code,TypeId,NavigateUrl,Visible,Enabled,Description,Priority,BeginGroup,Collapsed,Level,CreateDate,Creator,ModifyDate,Modifier,ExpireDate,ParentId) VALUES
('voc_dashboard',  'SUBSIDEMENU','#/voc/dashboard',  1,1,'Dashboard',  1,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_reviews',    'SUBSIDEMENU','#/voc/reviews',    1,1,'Reviews',    2,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_locations',  'SUBSIDEMENU','#/voc/locations',  1,1,'Locations',  3,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_competitors','SUBSIDEMENU','#/voc/competitors',1,1,'Competitors',4,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_fetchjobs',  'SUBSIDEMENU','#/voc/fetchjobs',  1,1,'Fetch Jobs', 5,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_analysis',   'SUBSIDEMENU','#/voc/analysis',   1,1,'Analysis',   6,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_insights',   'SUBSIDEMENU','#/voc/insights',   1,1,'Insights',   7,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_reports',    'SUBSIDEMENU','#/voc/reports',    1,1,'Reports',    8,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc),
('voc_settings',   'SUBSIDEMENU','#/voc/settings',   1,1,'Settings',   9,1,1,2,NOW(),1,NOW(),1,'3000-01-01 00:00:00',@voc);

-- Permission: samakan dengan item "Daftar Berita" (semua_sumber) -> audience sama
INSERT INTO Permission (ObjectName,ObjectId,RoleId,ActionId,SiteId,CreateDate,Creator,ModifyDate,Modifier,ExpireDate)
SELECT DISTINCT 'Menu', vm.Id, ep.RoleId, ep.ActionId, ep.SiteId, NOW(),1,NOW(),1,'3000-01-01 00:00:00'
FROM Menu vm
CROSS JOIN Permission ep
WHERE vm.Code LIKE 'voc%'
  AND ep.ObjectName='Menu' AND ep.ActionId='ALLOWED' AND ep.ObjectId=@src;

-- ---------------------------------------------------------------------
-- 3) OUTPUT — Id yang dibutuhkan untuk INGEST
-- ---------------------------------------------------------------------
SELECT @conn_hermina AS conn_hermina_depok, @conn_hga AS conn_hga_depok,
       @loc_hermina  AS loc_hermina_onebox, @loc_hga  AS loc_hga_onebox,
       @mm AS mm_header_id;

-- =====================================================================
-- LANGKAH BERIKUTNYA (di shell, bukan SQL):
--
-- 1) Copy fixture ke /tmp (ter-mount ke container webapp):
--      cp scriptdb/voc/reviews_sample.json /tmp/voc_reviews_sample.json
--
-- 2) INGEST (ganti <C>=container webapp, <H>/<G>=conn id dari OUTPUT di atas):
--      C=$(docker ps -qf name=<webapp>)
--      docker exec $C php app/bootstrap.php voice_of_customer_system receive <H>
--      docker exec $C php app/bootstrap.php voice_of_customer_system receive <G>
--      docker exec $C php app/bootstrap.php voice_of_customer_system processpending <H>
--      docker exec $C php app/bootstrap.php voice_of_customer_system processpending <G>
--      docker exec $C php app/bootstrap.php voice_of_customer_system analysis <H>
--      docker exec $C php app/bootstrap.php voice_of_customer_system analysis <G>
--
-- 3) Buka Media Monitoring -> HARD-RELOAD (Ctrl+Shift+R) -> sidebar "Voice of Customer".
--
-- ---------------------------------------------------------------------
-- OPSIONAL — pindah dari MOCK ke VoC BETULAN
-- ---------------------------------------------------------------------
-- Seed ini sengaja berhenti di mock: file ini masuk git, jadi TIDAK BOLEH
-- memuat kredensial apa pun. Kalau mau menarik data sungguhan, minta ke tim:
--   - service token VoC   (untuk BACA review — /api/integration/v1/*)
--   - akun user VoC       (untuk TULIS lokasi/kompetitor — /api/locations)
-- lalu jalankan sendiri, DI LUAR file ini (jangan di-commit):
--
--   UPDATE Connection
--      SET Url='http://<host-voc>:8000',
--          UserId='<email akun VoC>',
--          Password='<password>',
--          Options=JSON_MERGE_PATCH(Options, JSON_OBJECT(
--                    'mock',false,'api_mode','service',
--                    'company_id',<company_id VoC>,
--                    'service_token','<token>'))
--    WHERE SiteId=@site AND ProviderId='PVD97';
--
-- Verifikasi SEBELUM menarik data (memastikan kredensial ini memang milik
-- company yang benar — kalau meleset, sync ditolak, bukan menarik data tenant lain):
--   docker exec $C php app/bootstrap.php voice_of_customer_system whoami <connId>
-- =====================================================================
