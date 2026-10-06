-- ============================================================================
-- Stock Market Analysis in SQL  (MySQL 8 version - run in Workbench / VS Code)
-- Run 01_create_and_load_mysql.sql FIRST (creates database stock_market + 6 tables).
-- Needs MySQL 8.0+ (window functions). Every derived table starts with DROP IF EXISTS.
-- ============================================================================

USE stock_market;

-- TASK 01: How much history do we have? (bajaj_auto)
SELECT COUNT(*)  AS trading_days,
       MIN(date) AS first_day,
       MAX(date) AS last_day
FROM bajaj_auto;

-- TASK 02: Eicher's five best closes
SELECT date, close_price
FROM eicher_motors
ORDER BY close_price DESC
LIMIT 5;

-- TASK 03: TCS year by year
SELECT YEAR(date)       AS year,
       ROUND(AVG(close_price), 2) AS avg_close
FROM tcs
GROUP BY YEAR(date)
ORDER BY year;

-- TASK 04: Find the holes (deliverable_qty IS NULL in any table)
SELECT 'bajaj_auto'    AS stock, date FROM bajaj_auto    WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'eicher_motors' AS stock, date FROM eicher_motors WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'hero_motocorp' AS stock, date FROM hero_motocorp WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'infosys'       AS stock, date FROM infosys       WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'tcs'           AS stock, date FROM tcs           WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'tvs_motors'    AS stock, date FROM tvs_motors    WHERE deliverable_qty IS NULL;

-- TASK 05: Moving averages -> table bajaj1
DROP TABLE IF EXISTS bajaj1;
CREATE TABLE bajaj1 AS
SELECT
  date,
  close_price,
  CASE WHEN ROW_NUMBER() OVER (ORDER BY date) >= 20
       THEN ROUND(AVG(close_price) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW), 2)
  END AS ma20,
  CASE WHEN ROW_NUMBER() OVER (ORDER BY date) >= 50
       THEN ROUND(AVG(close_price) OVER (ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW), 2)
  END AS ma50
FROM bajaj_auto;

SELECT * FROM bajaj1 ORDER BY date;

-- TASK 06: Master table (one row per date, closing price of all six stocks)
DROP TABLE IF EXISTS master_table;
CREATE TABLE master_table AS
SELECT b.date,
       b.close_price AS bajaj,
       t.close_price AS tcs,
       v.close_price AS tvs,
       i.close_price AS infosys,
       e.close_price AS eicher,
       h.close_price AS hero
FROM bajaj_auto b
JOIN tcs           t ON t.date = b.date
JOIN tvs_motors    v ON v.date = b.date
JOIN infosys       i ON i.date = b.date
JOIN eicher_motors e ON e.date = b.date
JOIN hero_motocorp h ON h.date = b.date;

SELECT * FROM master_table ORDER BY date;

-- TASK 07: Golden cross signals -> table bajaj2
DROP TABLE IF EXISTS bajaj2;
CREATE TABLE bajaj2 AS
WITH t AS (
  SELECT date, close_price, ma20, ma50,
         LAG(ma20) OVER (ORDER BY date) AS prev_ma20,
         LAG(ma50) OVER (ORDER BY date) AS prev_ma50
  FROM bajaj1
)
SELECT date, close_price,
  CASE
    WHEN ma20 IS NULL OR ma50 IS NULL OR prev_ma20 IS NULL OR prev_ma50 IS NULL THEN 'Hold'
    WHEN ma20 > ma50 AND prev_ma20 <= prev_ma50 THEN 'Buy'
    WHEN ma20 < ma50 AND prev_ma20 >= prev_ma50 THEN 'Sell'
    ELSE 'Hold'
  END AS `signal`
FROM t;

SELECT * FROM bajaj2 ORDER BY date;

-- TASK 08: How often did it trigger? (bajaj2)
SELECT `signal`, COUNT(*) AS days
FROM bajaj2
GROUP BY `signal`
ORDER BY `signal`;

-- TASK 09: Signal on a given day (2018-06-21) - as a MySQL function
DROP FUNCTION IF EXISTS bajaj_signal;
DELIMITER $$
CREATE FUNCTION bajaj_signal(d DATE)
RETURNS VARCHAR(4) DETERMINISTIC READS SQL DATA
BEGIN
  DECLARE s VARCHAR(4);
  SELECT `signal` INTO s FROM bajaj2 WHERE date = d;
  RETURN s;   -- NULL if the market was closed that day
END $$
DELIMITER ;

SELECT bajaj_signal('2018-06-21') AS `signal`;   -- expected: Buy
SELECT bajaj_signal('2015-05-18') AS `signal`;   -- expected: Buy
SELECT bajaj_signal('2016-01-04') AS `signal`;   -- expected: Hold

-- TASK 10: All six stocks in one query (buys, sells, last signal)
WITH prices AS (
  SELECT 'Bajaj Auto'    AS stock, date, close_price FROM bajaj_auto
  UNION ALL
  SELECT 'Eicher Motors' AS stock, date, close_price FROM eicher_motors
  UNION ALL
  SELECT 'Hero Motocorp' AS stock, date, close_price FROM hero_motocorp
  UNION ALL
  SELECT 'Infosys'       AS stock, date, close_price FROM infosys
  UNION ALL
  SELECT 'TCS'           AS stock, date, close_price FROM tcs
  UNION ALL
  SELECT 'TVS Motors'    AS stock, date, close_price FROM tvs_motors
),
ma AS (
  SELECT stock, date, close_price,
         CASE WHEN ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date) >= 20
              THEN AVG(close_price) OVER (PARTITION BY stock ORDER BY date
                                          ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) END AS ma20,
         CASE WHEN ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date) >= 50
              THEN AVG(close_price) OVER (PARTITION BY stock ORDER BY date
                                          ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) END AS ma50
  FROM prices
),
lagged AS (
  SELECT stock, date, close_price, ma20, ma50,
         LAG(ma20) OVER (PARTITION BY stock ORDER BY date) AS prev_ma20,
         LAG(ma50) OVER (PARTITION BY stock ORDER BY date) AS prev_ma50
  FROM ma
),
sig AS (
  SELECT stock, date, close_price,
         CASE
           WHEN ma20 IS NULL OR ma50 IS NULL OR prev_ma20 IS NULL OR prev_ma50 IS NULL THEN 'Hold'
           WHEN ma20 > ma50 AND prev_ma20 <= prev_ma50 THEN 'Buy'
           WHEN ma20 < ma50 AND prev_ma20 >= prev_ma50 THEN 'Sell'
           ELSE 'Hold'
         END AS `signal`
  FROM lagged
),
latest AS (
  SELECT stock, date, `signal`,
         ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date DESC) AS rn
  FROM sig
  WHERE `signal` <> 'Hold'
)
SELECT s.stock,
       SUM(s.`signal` = 'Buy')  AS buys,
       SUM(s.`signal` = 'Sell') AS sells,
       l.date                 AS last_signal_date,
       l.`signal`             AS last_signal
FROM sig s
JOIN latest l ON l.stock = s.stock AND l.rn = 1
GROUP BY s.stock, l.date, l.`signal`
ORDER BY s.stock;

-- TASK 11: Who went up? (first vs last close, raw prices)
WITH prices AS (
  SELECT 'Bajaj Auto'    AS stock, date, close_price FROM bajaj_auto
  UNION ALL
  SELECT 'Eicher Motors' AS stock, date, close_price FROM eicher_motors
  UNION ALL
  SELECT 'Hero Motocorp' AS stock, date, close_price FROM hero_motocorp
  UNION ALL
  SELECT 'Infosys'       AS stock, date, close_price FROM infosys
  UNION ALL
  SELECT 'TCS'           AS stock, date, close_price FROM tcs
  UNION ALL
  SELECT 'TVS Motors'    AS stock, date, close_price FROM tvs_motors
),
ends AS (
  SELECT stock, MIN(date) AS first_date, MAX(date) AS last_date
  FROM prices
  GROUP BY stock
)
SELECT e.stock,
       f.close_price AS first_close,
       l.close_price AS last_close,
       ROUND(100.0 * (l.close_price - f.close_price) / f.close_price, 1) AS pct_change
FROM ends e
JOIN prices f ON f.stock = e.stock AND f.date = e.first_date
JOIN prices l ON l.stock = e.stock AND l.date = e.last_date
ORDER BY pct_change DESC;

-- TASK 12: The data trap (worst single-day move per stock)
WITH prices AS (
  SELECT 'Bajaj Auto'    AS stock, date, close_price FROM bajaj_auto
  UNION ALL
  SELECT 'Eicher Motors' AS stock, date, close_price FROM eicher_motors
  UNION ALL
  SELECT 'Hero Motocorp' AS stock, date, close_price FROM hero_motocorp
  UNION ALL
  SELECT 'Infosys'       AS stock, date, close_price FROM infosys
  UNION ALL
  SELECT 'TCS'           AS stock, date, close_price FROM tcs
  UNION ALL
  SELECT 'TVS Motors'    AS stock, date, close_price FROM tvs_motors
),
moves AS (
  SELECT stock, date, close_price,
         100.0 * (close_price / LAG(close_price) OVER (PARTITION BY stock ORDER BY date) - 1) AS pct_move
  FROM prices
),
ranked AS (
  SELECT stock, date, close_price, pct_move,
         ROW_NUMBER() OVER (PARTITION BY stock ORDER BY pct_move ASC) AS rn
  FROM moves
  WHERE pct_move IS NOT NULL
)
SELECT stock, date, close_price, ROUND(pct_move, 1) AS pct_move
FROM ranked
WHERE rn = 1
ORDER BY pct_move;

-- TASK 13: Fix it (1:1 bonus adjustment: TCS 2018-05-31, Infosys 2015-06-15)
WITH adjusted AS (
  SELECT 'TCS' AS stock, date,
         CASE WHEN date < '2018-05-31' THEN close_price / 2.0 ELSE close_price END AS adj_close
  FROM tcs
  UNION ALL
  SELECT 'Infosys' AS stock, date,
         CASE WHEN date < '2015-06-15' THEN close_price / 2.0 ELSE close_price END AS adj_close
  FROM infosys
)
SELECT stock,
       ROUND(100.0 * (MAX(CASE WHEN date = '2018-07-31' THEN adj_close END) /
                      MAX(CASE WHEN date = '2015-01-01' THEN adj_close END) - 1), 1) AS adjusted_pct_change
FROM adjusted
GROUP BY stock
ORDER BY stock;

-- TASK 13b: Adjusted price series for TCS and Infosys (used for charts)
DROP TABLE IF EXISTS adjusted_prices;
CREATE TABLE adjusted_prices AS
SELECT 'TCS' AS stock, date, close_price,
       CASE WHEN date < '2018-05-31' THEN close_price / 2.0 ELSE close_price END AS adj_close
FROM tcs
UNION ALL
SELECT 'Infosys' AS stock, date, close_price,
       CASE WHEN date < '2015-06-15' THEN close_price / 2.0 ELSE close_price END AS adj_close
FROM infosys;

SELECT * FROM adjusted_prices ORDER BY stock, date;

-- TASK 14: Stretch - TCS and Infosys signals rebuilt on ADJUSTED prices vs RAW prices
DROP TABLE IF EXISTS signals_compare;
CREATE TABLE signals_compare AS
WITH ma AS (
  SELECT stock, date,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date) >= 20
         THEN AVG(close_price) OVER (PARTITION BY stock ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) END AS r20,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date) >= 50
         THEN AVG(close_price) OVER (PARTITION BY stock ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) END AS r50,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date) >= 20
         THEN AVG(adj_close) OVER (PARTITION BY stock ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) END AS a20,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY stock ORDER BY date) >= 50
         THEN AVG(adj_close) OVER (PARTITION BY stock ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) END AS a50
  FROM adjusted_prices
),
lagged AS (
  SELECT stock, date, r20, r50, a20, a50,
    LAG(r20) OVER (PARTITION BY stock ORDER BY date) AS pr20,
    LAG(r50) OVER (PARTITION BY stock ORDER BY date) AS pr50,
    LAG(a20) OVER (PARTITION BY stock ORDER BY date) AS pa20,
    LAG(a50) OVER (PARTITION BY stock ORDER BY date) AS pa50
  FROM ma
)
SELECT stock, date,
  CASE
    WHEN r20 IS NULL OR r50 IS NULL OR pr20 IS NULL OR pr50 IS NULL THEN 'Hold'
    WHEN r20 > r50 AND pr20 <= pr50 THEN 'Buy'
    WHEN r20 < r50 AND pr20 >= pr50 THEN 'Sell'
    ELSE 'Hold' END AS raw_signal,
  CASE
    WHEN a20 IS NULL OR a50 IS NULL OR pa20 IS NULL OR pa50 IS NULL THEN 'Hold'
    WHEN a20 > a50 AND pa20 <= pa50 THEN 'Buy'
    WHEN a20 < a50 AND pa20 >= pa50 THEN 'Sell'
    ELSE 'Hold' END AS adj_signal
FROM lagged;

SELECT stock,
       SUM(raw_signal = 'Buy')  AS raw_buys,
       SUM(raw_signal = 'Sell') AS raw_sells,
       SUM(adj_signal = 'Buy')  AS adj_buys,
       SUM(adj_signal = 'Sell') AS adj_sells,
       SUM(raw_signal <> 'Hold' AND adj_signal = 'Hold') AS signals_removed_by_adjustment,
       SUM(raw_signal = 'Hold' AND adj_signal <> 'Hold') AS signals_added_by_adjustment
FROM signals_compare
GROUP BY stock
ORDER BY stock;
