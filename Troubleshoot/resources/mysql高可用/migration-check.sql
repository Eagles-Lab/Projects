-- 同一份脚本分别在旧库和新主库上执行。
-- 输出包括对象数量和每张表的精确行数，便于保存后使用 diff 比较。

SET SESSION group_concat_max_len = 16777216;

SELECT 'object_summary' AS section,
       (SELECT COUNT(*)
          FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = 'discuz'
           AND TABLE_TYPE = 'BASE TABLE') AS tables_count,
       (SELECT COUNT(*)
          FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = 'discuz'
           AND TABLE_TYPE = 'VIEW') AS views_count,
       (SELECT COUNT(*)
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = 'discuz') AS columns_count,
       (SELECT COUNT(*)
          FROM information_schema.STATISTICS
         WHERE TABLE_SCHEMA = 'discuz') AS index_entries,
       (SELECT COUNT(*)
          FROM information_schema.TRIGGERS
         WHERE TRIGGER_SCHEMA = 'discuz') AS triggers_count,
       (SELECT COUNT(*)
          FROM information_schema.ROUTINES
         WHERE ROUTINE_SCHEMA = 'discuz') AS routines_count,
       (SELECT COUNT(*)
          FROM information_schema.EVENTS
         WHERE EVENT_SCHEMA = 'discuz') AS events_count;

SELECT GROUP_CONCAT(
         CONCAT(
           'SELECT ', QUOTE(TABLE_NAME),
           ' AS table_name, COUNT(*) AS exact_rows FROM `discuz`.`',
           REPLACE(TABLE_NAME, '`', '``'), '`'
         )
         ORDER BY TABLE_NAME
         SEPARATOR ' UNION ALL '
       )
  INTO @row_count_sql
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'discuz'
   AND TABLE_TYPE = 'BASE TABLE';

PREPARE row_count_stmt FROM @row_count_sql;
EXECUTE row_count_stmt;
DEALLOCATE PREPARE row_count_stmt;
