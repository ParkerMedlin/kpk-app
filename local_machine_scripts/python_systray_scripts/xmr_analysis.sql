WITH hourly AS (
  SELECT
    tank_name,
    date_trunc('hour', timestamp) as hour,
    AVG(filled_gallons::float) as avg_gallons
  FROM core_tanklevellog
  WHERE timestamp > NOW() - INTERVAL '60 days'
    AND EXTRACT(HOUR FROM timestamp) NOT BETWEEN 6 AND 17
  GROUP BY tank_name, date_trunc('hour', timestamp)
),
with_lag AS (
  SELECT
    tank_name,
    hour,
    avg_gallons,
    LAG(avg_gallons) OVER (PARTITION BY tank_name ORDER BY hour) as prev_gallons
  FROM hourly
),
moving_ranges AS (
  SELECT
    tank_name,
    avg_gallons - prev_gallons as change,
    ABS(avg_gallons - prev_gallons) as moving_range
  FROM with_lag
  WHERE prev_gallons IS NOT NULL
)
SELECT
  tank_name,
  ROUND(AVG(change)::numeric, 3) as avg_change,
  ROUND(AVG(moving_range)::numeric, 3) as avg_mr,
  ROUND((2.66 * AVG(moving_range))::numeric, 3) as ucl_3sigma,
  COUNT(*) as n
FROM moving_ranges
GROUP BY tank_name
ORDER BY tank_name;
