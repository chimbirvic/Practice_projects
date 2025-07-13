-- Вычислим общие значения ключевых показателей сервиса за весь период
SELECT 
    currency_code,
    SUM(revenue) AS total_revenue,
    COUNT(order_id) AS total_orders,
    AVG(revenue) AS avg_revenue_per_order,
    COUNT(DISTINCT user_id) AS total_users
FROM afisha.purchases
GROUP BY currency_code
ORDER BY total_revenue DESC;

-- Для заказов в рублях вычислите распределение выручки и количества заказов по типу устройства device_type_canonical
-- Настройка параметра synchronize_seqscans важна для проверки
WITH set_config_precode AS (
  SELECT set_config('synchronize_seqscans', 'off', true)
)
SELECT
    device_type_canonical,
    SUM(revenue) AS total_revenue,
    COUNT(order_id) AS total_orders,
    AVG(revenue) AS avg_revenue_per_order,
    ROUND(SUM(revenue)::numeric/ (SELECT SUM(revenue) FROM afisha.purchases
WHERE currency_code = 'rub')::numeric,3) AS revenue_share
FROM afisha.purchases
WHERE currency_code = 'rub'
GROUP BY device_type_canonical
ORDER BY revenue_share DESC;

-- Для заказов в рублях вычислим распределение количества заказов и их выручку в зависимости от типа мероприятия event_type_main.
SELECT  e.event_type_main,
        SUM(p.revenue) AS  total_revenue,
        COUNT(p.order_id) AS total_orders,
        AVG(p.revenue) AS avg_revenue_per_order,
        COUNT(DISTINCT e.event_name_code) AS total_event_name,
        AVG(p.tickets_count) AS avg_tickets,
        SUM(p.revenue) * 1.0 / SUM(p.tickets_count) AS avg_ticket_revenue,
        ROUND(SUM(p.revenue)::numeric/(SELECT SUM(revenue) FROM afisha.purchases WHERE currency_code = 'rub' )::numeric,3) AS revenue_share
FROM afisha.purchases AS p
JOIN afisha.events AS e
ON p.event_id=e.event_id
WHERE p.currency_code = 'rub'
GROUP BY event_type_main
ORDER BY total_orders DESC

-- Для заказов в рублях вычислим изменение выручки, количества заказов, уникальных клиентов и средней стоимости одного заказа в недельной динамике.
SELECT
    DATE_TRUNC('week', created_dt_msk)::date AS week,
    SUM(revenue) AS total_revenue,
    COUNT(order_id) AS total_orders,
    COUNT(DISTINCT user_id) AS total_users,
    SUM(revenue) * 1.0 / COUNT(order_id)AS revenue_per_order
FROM afisha.purchases
WHERE currency_code = 'rub'
GROUP BY week
ORDER BY week ASC;

-- Выведем топ-7 регионов по значению общей выручки, включив только заказы за рубли.
SELECT
    r.region_name,
    SUM(p.revenue) AS total_revenue,
    COUNT(p.order_id) AS total_orders,
    COUNT(DISTINCT p.user_id) AS total_users,
    SUM(p.tickets_count) AS total_tickets,
    SUM(p.revenue) * 1.0 / SUM(p.tickets_count) AS one_ticket_cost
FROM afisha.purchases p
JOIN afisha.events e ON p.event_id = e.event_id
JOIN afisha.city c ON e.city_id = c.city_id
JOIN afisha.regions r ON c.region_id = r.region_id
WHERE p.currency_code = 'rub'
GROUP BY r.region_name
ORDER BY total_revenue DESC
LIMIT 7;