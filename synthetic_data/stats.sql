SELECT 'user' as tbl, count(*) FROM "user"
UNION ALL SELECT 'hr', count(*) FROM hr
UNION ALL SELECT 'company', count(*) FROM company;
