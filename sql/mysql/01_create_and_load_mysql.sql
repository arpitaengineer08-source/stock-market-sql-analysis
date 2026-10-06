-- ============================================================================
-- 01_create_and_load_mysql.sql  -  run this FIRST (MySQL 8.0+)
-- Creates database `stock_market`, six tables, and loads the CLEANED csv files
-- from data/clean/ (dates already ISO, snake_case headers, empty cells -> NULL).
--
-- BEFORE RUNNING:
--   1. Replace every  /FULL/PATH/TO/stock_market_sql  below with the real folder path
--      (use forward slashes, e.g. C:/Users/you/stock_market_sql  on Windows).
--   2. Enable local_infile:   SET GLOBAL local_infile = 1;
--      Workbench: Edit Connection > Advanced > Others: add  OPT_LOCAL_INFILE=1
--      CLI:       mysql --local-infile=1 -u root -p
-- ============================================================================
CREATE DATABASE IF NOT EXISTS stock_market;
USE stock_market;
SET GLOBAL local_infile = 1;

DROP TABLE IF EXISTS bajaj_auto;
CREATE TABLE bajaj_auto (
  `date` DATE PRIMARY KEY,
  open_price DECIMAL(12,2), high_price DECIMAL(12,2), low_price DECIMAL(12,2),
  close_price DECIMAL(12,2), wap DECIMAL(16,4),
  no_of_shares BIGINT, no_of_trades BIGINT, total_turnover DECIMAL(20,2),
  deliverable_qty BIGINT, pct_deli_qty DECIMAL(6,2),
  spread_high_low DECIMAL(12,2), spread_close_open DECIMAL(12,2)
);
LOAD DATA LOCAL INFILE '/FULL/PATH/TO/stock_market_sql/data/clean/bajaj_auto.csv' INTO TABLE bajaj_auto
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(@d,@o,@h,@l,@c,@w,@s,@tr,@to,@dq,@pd,@shl,@sco)
SET `date` = @d,
    open_price = NULLIF(@o,''), high_price = NULLIF(@h,''), low_price = NULLIF(@l,''),
    close_price = NULLIF(@c,''), wap = NULLIF(@w,''), no_of_shares = NULLIF(@s,''),
    no_of_trades = NULLIF(@tr,''), total_turnover = NULLIF(@to,''),
    deliverable_qty = NULLIF(@dq,''), pct_deli_qty = NULLIF(@pd,''),
    spread_high_low = NULLIF(@shl,''), spread_close_open = NULLIF(TRIM(@sco),'');

DROP TABLE IF EXISTS eicher_motors;
CREATE TABLE eicher_motors (
  `date` DATE PRIMARY KEY,
  open_price DECIMAL(12,2), high_price DECIMAL(12,2), low_price DECIMAL(12,2),
  close_price DECIMAL(12,2), wap DECIMAL(16,4),
  no_of_shares BIGINT, no_of_trades BIGINT, total_turnover DECIMAL(20,2),
  deliverable_qty BIGINT, pct_deli_qty DECIMAL(6,2),
  spread_high_low DECIMAL(12,2), spread_close_open DECIMAL(12,2)
);
LOAD DATA LOCAL INFILE '/FULL/PATH/TO/stock_market_sql/data/clean/eicher_motors.csv' INTO TABLE eicher_motors
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(@d,@o,@h,@l,@c,@w,@s,@tr,@to,@dq,@pd,@shl,@sco)
SET `date` = @d,
    open_price = NULLIF(@o,''), high_price = NULLIF(@h,''), low_price = NULLIF(@l,''),
    close_price = NULLIF(@c,''), wap = NULLIF(@w,''), no_of_shares = NULLIF(@s,''),
    no_of_trades = NULLIF(@tr,''), total_turnover = NULLIF(@to,''),
    deliverable_qty = NULLIF(@dq,''), pct_deli_qty = NULLIF(@pd,''),
    spread_high_low = NULLIF(@shl,''), spread_close_open = NULLIF(TRIM(@sco),'');

DROP TABLE IF EXISTS hero_motocorp;
CREATE TABLE hero_motocorp (
  `date` DATE PRIMARY KEY,
  open_price DECIMAL(12,2), high_price DECIMAL(12,2), low_price DECIMAL(12,2),
  close_price DECIMAL(12,2), wap DECIMAL(16,4),
  no_of_shares BIGINT, no_of_trades BIGINT, total_turnover DECIMAL(20,2),
  deliverable_qty BIGINT, pct_deli_qty DECIMAL(6,2),
  spread_high_low DECIMAL(12,2), spread_close_open DECIMAL(12,2)
);
LOAD DATA LOCAL INFILE '/FULL/PATH/TO/stock_market_sql/data/clean/hero_motocorp.csv' INTO TABLE hero_motocorp
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(@d,@o,@h,@l,@c,@w,@s,@tr,@to,@dq,@pd,@shl,@sco)
SET `date` = @d,
    open_price = NULLIF(@o,''), high_price = NULLIF(@h,''), low_price = NULLIF(@l,''),
    close_price = NULLIF(@c,''), wap = NULLIF(@w,''), no_of_shares = NULLIF(@s,''),
    no_of_trades = NULLIF(@tr,''), total_turnover = NULLIF(@to,''),
    deliverable_qty = NULLIF(@dq,''), pct_deli_qty = NULLIF(@pd,''),
    spread_high_low = NULLIF(@shl,''), spread_close_open = NULLIF(TRIM(@sco),'');

DROP TABLE IF EXISTS infosys;
CREATE TABLE infosys (
  `date` DATE PRIMARY KEY,
  open_price DECIMAL(12,2), high_price DECIMAL(12,2), low_price DECIMAL(12,2),
  close_price DECIMAL(12,2), wap DECIMAL(16,4),
  no_of_shares BIGINT, no_of_trades BIGINT, total_turnover DECIMAL(20,2),
  deliverable_qty BIGINT, pct_deli_qty DECIMAL(6,2),
  spread_high_low DECIMAL(12,2), spread_close_open DECIMAL(12,2)
);
LOAD DATA LOCAL INFILE '/FULL/PATH/TO/stock_market_sql/data/clean/infosys.csv' INTO TABLE infosys
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(@d,@o,@h,@l,@c,@w,@s,@tr,@to,@dq,@pd,@shl,@sco)
SET `date` = @d,
    open_price = NULLIF(@o,''), high_price = NULLIF(@h,''), low_price = NULLIF(@l,''),
    close_price = NULLIF(@c,''), wap = NULLIF(@w,''), no_of_shares = NULLIF(@s,''),
    no_of_trades = NULLIF(@tr,''), total_turnover = NULLIF(@to,''),
    deliverable_qty = NULLIF(@dq,''), pct_deli_qty = NULLIF(@pd,''),
    spread_high_low = NULLIF(@shl,''), spread_close_open = NULLIF(TRIM(@sco),'');

DROP TABLE IF EXISTS tcs;
CREATE TABLE tcs (
  `date` DATE PRIMARY KEY,
  open_price DECIMAL(12,2), high_price DECIMAL(12,2), low_price DECIMAL(12,2),
  close_price DECIMAL(12,2), wap DECIMAL(16,4),
  no_of_shares BIGINT, no_of_trades BIGINT, total_turnover DECIMAL(20,2),
  deliverable_qty BIGINT, pct_deli_qty DECIMAL(6,2),
  spread_high_low DECIMAL(12,2), spread_close_open DECIMAL(12,2)
);
LOAD DATA LOCAL INFILE '/FULL/PATH/TO/stock_market_sql/data/clean/tcs.csv' INTO TABLE tcs
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(@d,@o,@h,@l,@c,@w,@s,@tr,@to,@dq,@pd,@shl,@sco)
SET `date` = @d,
    open_price = NULLIF(@o,''), high_price = NULLIF(@h,''), low_price = NULLIF(@l,''),
    close_price = NULLIF(@c,''), wap = NULLIF(@w,''), no_of_shares = NULLIF(@s,''),
    no_of_trades = NULLIF(@tr,''), total_turnover = NULLIF(@to,''),
    deliverable_qty = NULLIF(@dq,''), pct_deli_qty = NULLIF(@pd,''),
    spread_high_low = NULLIF(@shl,''), spread_close_open = NULLIF(TRIM(@sco),'');

DROP TABLE IF EXISTS tvs_motors;
CREATE TABLE tvs_motors (
  `date` DATE PRIMARY KEY,
  open_price DECIMAL(12,2), high_price DECIMAL(12,2), low_price DECIMAL(12,2),
  close_price DECIMAL(12,2), wap DECIMAL(16,4),
  no_of_shares BIGINT, no_of_trades BIGINT, total_turnover DECIMAL(20,2),
  deliverable_qty BIGINT, pct_deli_qty DECIMAL(6,2),
  spread_high_low DECIMAL(12,2), spread_close_open DECIMAL(12,2)
);
LOAD DATA LOCAL INFILE '/FULL/PATH/TO/stock_market_sql/data/clean/tvs_motors.csv' INTO TABLE tvs_motors
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES
(@d,@o,@h,@l,@c,@w,@s,@tr,@to,@dq,@pd,@shl,@sco)
SET `date` = @d,
    open_price = NULLIF(@o,''), high_price = NULLIF(@h,''), low_price = NULLIF(@l,''),
    close_price = NULLIF(@c,''), wap = NULLIF(@w,''), no_of_shares = NULLIF(@s,''),
    no_of_trades = NULLIF(@tr,''), total_turnover = NULLIF(@to,''),
    deliverable_qty = NULLIF(@dq,''), pct_deli_qty = NULLIF(@pd,''),
    spread_high_low = NULLIF(@shl,''), spread_close_open = NULLIF(TRIM(@sco),'');

-- Sanity check: every table must show 889 rows, 2015-01-01 .. 2018-07-31
SELECT 'bajaj_auto' AS tbl, COUNT(*) AS n, MIN(`date`) AS first_day, MAX(`date`) AS last_day FROM bajaj_auto
UNION ALL
SELECT 'eicher_motors' AS tbl, COUNT(*) AS n, MIN(`date`) AS first_day, MAX(`date`) AS last_day FROM eicher_motors
UNION ALL
SELECT 'hero_motocorp' AS tbl, COUNT(*) AS n, MIN(`date`) AS first_day, MAX(`date`) AS last_day FROM hero_motocorp
UNION ALL
SELECT 'infosys' AS tbl, COUNT(*) AS n, MIN(`date`) AS first_day, MAX(`date`) AS last_day FROM infosys
UNION ALL
SELECT 'tcs' AS tbl, COUNT(*) AS n, MIN(`date`) AS first_day, MAX(`date`) AS last_day FROM tcs
UNION ALL
SELECT 'tvs_motors' AS tbl, COUNT(*) AS n, MIN(`date`) AS first_day, MAX(`date`) AS last_day FROM tvs_motors;
