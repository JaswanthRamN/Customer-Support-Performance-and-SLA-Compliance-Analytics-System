-- One ticket is counted once in each independent grouping.
-- Creation month is explicitly UTC, independent of the database session zone.
WITH volume AS (
    SELECT 'month' AS dimension,
           TO_CHAR(DATE_TRUNC('month', created_at AT TIME ZONE 'UTC'), 'YYYY-MM') AS value,
           COUNT(*) AS tickets
    FROM support_analytics.tickets
    GROUP BY 2
    UNION ALL
    SELECT 'priority', priority, COUNT(*) FROM support_analytics.tickets GROUP BY priority
    UNION ALL
    SELECT 'category', category, COUNT(*) FROM support_analytics.tickets GROUP BY category
    UNION ALL
    SELECT 'channel', channel, COUNT(*) FROM support_analytics.tickets GROUP BY channel
)
SELECT dimension, value, tickets
FROM volume
ORDER BY dimension, value;
