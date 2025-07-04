-- Рассчитываем величину комиссии с каждого заказа, отбираем заказы по дате и городу
WITH orders AS
  (SELECT *,
          revenue * commission AS commission_revenue
   FROM rest_analytics.analytics_events AS events
   JOIN rest_analytics.cities cities ON events.city_id = cities.city_id
   WHERE revenue IS NOT NULL
     AND log_date BETWEEN '2021-05-01' AND '2021-06-30'
     AND city_name = 'Саранск')
SELECT CAST(DATE_TRUNC('month', log_date) AS date) AS "Месяц",
       COUNT(DISTINCT order_id) AS "Количество заказов",
       ROUND(SUM(commission_revenue)::numeric, 2) AS "Сумма комиссии",
       ROUND((SUM(commission_revenue) / COUNT(DISTINCT order_id))::numeric, 2) "Средний чек"
FROM orders
GROUP BY "Месяц"
ORDER BY "Месяц";