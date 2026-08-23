-- 同一份脚本分别在旧库和新主库执行。
-- 输出表总数和每张表的精确行数，便于使用 diff 比较。

SET SESSION group_concat_max_len = 16777216;

SELECT 'tables_count' AS item, COUNT(*) AS exact_rows
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'discuz'
   AND TABLE_TYPE = 'BASE TABLE';

SELECT GROUP_CONCAT(
         CONCAT(
           'SELECT ', QUOTE(TABLE_NAME),
           ' AS table_name, COUNT(*) AS exact_rows ',
           'FROM `discuz`.`', TABLE_NAME, '`'
         )
         ORDER BY TABLE_NAME
         SEPARATOR ' UNION ALL '
       )
  INTO @sql
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'discuz'
   AND TABLE_TYPE = 'BASE TABLE';

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
