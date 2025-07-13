-- Проект первого модуля: анализ данных для агентства недвижимости
--Автор: Чимбир Виктор  
--Дата: 04.01.2025
--
-- Задача 1: Время активности объявлений
-- Результат запроса должен ответить на такие вопросы:
-- 1. Какие сегменты рынка недвижимости Санкт-Петербурга и городов Ленинградской области 
--    имеют наиболее короткие или длинные сроки активности объявлений?
-- 2. Какие характеристики недвижимости, включая площадь недвижимости, среднюю стоимость квадратного метра, 
--    количество комнат и балконов и другие параметры, влияют на время активности объявлений? 
--    Как эти зависимости варьируют между регионами?
-- 3. Есть ли различия между недвижимостью Санкт-Петербурга и Ленинградской области по полученным результатам?

WITH limits AS (
    SELECT  
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY total_area) AS total_area_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY rooms) AS rooms_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY balcony) AS balcony_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY ceiling_height) AS ceiling_height_limit_h,
        PERCENTILE_DISC(0.01) WITHIN GROUP (ORDER BY ceiling_height) AS ceiling_height_limit_l
    FROM real_estate.flats     
),
-- Найдём id объявлений, которые не содержат выбросы:
filtered_id AS(
    SELECT id
    FROM real_estate.flats  
    WHERE 
        total_area < (SELECT total_area_limit FROM limits)
        AND (rooms < (SELECT rooms_limit FROM limits) OR rooms IS NULL)
        AND (balcony < (SELECT balcony_limit FROM limits) OR balcony IS NULL)
        AND ((ceiling_height < (SELECT ceiling_height_limit_h FROM limits)
            AND ceiling_height > (SELECT ceiling_height_limit_l FROM limits)) OR ceiling_height IS NULL)
    ),
 -- Предсновной запрос 
   GENERAL AS (
   SELECT CASE                                                     -- Разделяем регионы на категории
    	   WHEN c.city= 'Санкт-Петербург' THEN 'Санкт-Петербург'
    	   ELSE 'ЛенОбл'
           END AS region,
           CASE                                                    -- Разделяем на категории временные промежутки
           WHEN a.days_exposition <32 THEN 'До месяца'
           WHEN a.days_exposition BETWEEN 32 AND 92 THEN 'До трех месяцев'
           WHEN a.days_exposition BETWEEN 93 AND 183 THEN 'До полугода'
           WHEN a.days_exposition > 183 THEN 'Более полугода'
           WHEN a.days_exposition IS NULL THEN 'Не продано'
           END AS PERIOD,
           COUNT(a.id) AS flats_count,                                               -- Считаем статистику для созданных категорий
           ROUND(AVG(a.last_price/f.total_area)::NUMERIC,2) AS avg_revenue_per_m2,
           ROUND(AVG(f.total_area)::NUMERIC,2) AS avg_total_area,
           PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY f.rooms) AS rooms_median,
           PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY f.balcony) AS balcony_median,
           PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY f.floors_total) AS floor_median
    FROM real_estate.flats AS f
    JOIN real_estate.city AS c
    ON f.city_id=c.city_id
    JOIN real_estate.advertisement AS a
    ON f.id=a.id
    JOIN real_estate.TYPE AS t
    ON f.type_id=t.type_id
    WHERE f.id IN (SELECT * FROM filtered_id) AND t.TYPE='город'
    GROUP BY region,"period" 
    ORDER BY region DESC,avg_revenue_per_m2 
    )
    -- Основной запрос
    SELECT *,
            ROUND(flats_count::numeric/SUM(flats_count) OVER(PARTITION BY region),2) -- считаем процент объявлений
    FROM general
    
    
-- Задача 2: Сезонность объявлений
-- Результат запроса должен ответить на такие вопросы:
-- 1. В какие месяцы наблюдается наибольшая активность в публикации объявлений о продаже недвижимости? 
--    А в какие — по снятию? Это показывает динамику активности покупателей.
-- 2. Совпадают ли периоды активной публикации объявлений и периоды, 
--    когда происходит повышенная продажа недвижимости (по месяцам снятия объявлений)?
-- 3. Как сезонные колебания влияют на среднюю стоимость квадратного метра и среднюю площадь квартир? 
--    Что можно сказать о зависимости этих параметров от месяца?
    
-- Определим аномальные значения (выбросы) по значению перцентилей:
WITH limits AS (
    SELECT  
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY total_area) AS total_area_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY rooms) AS rooms_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY balcony) AS balcony_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY ceiling_height) AS ceiling_height_limit_h,
        PERCENTILE_DISC(0.01) WITHIN GROUP (ORDER BY ceiling_height) AS ceiling_height_limit_l
    FROM real_estate.flats     
),
-- Найдём id объявлений, которые не содержат выбросы:
filtered_id AS(
    SELECT id
    FROM real_estate.flats AS f 
    JOIN real_estate.TYPE AS t
    ON f.type_id=t.type_id
    WHERE 
        f.total_area < (SELECT total_area_limit FROM limits)
        AND (f.rooms < (SELECT rooms_limit FROM limits) OR rooms IS NULL)
        AND (f.balcony < (SELECT balcony_limit FROM limits) OR balcony IS NULL)
        AND ((f.ceiling_height < (SELECT ceiling_height_limit_h FROM limits)
            AND f.ceiling_height > (SELECT ceiling_height_limit_l FROM limits)) OR ceiling_height IS NULL)
            AND t.TYPE='город'
    ),
-- Посчитаем статистику выложенных объявлений:
    START AS (
    SELECT CASE                                                                -- Создаем столбец с разбвикой по месяцам
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =1 THEN 'Январь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =2 THEN 'Февраль'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =3 THEN 'Март'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =4 THEN 'Апрель'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =5 THEN 'Май'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =6 THEN 'Июнь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =7 THEN 'Июль'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =8 THEN 'Август'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =9 THEN 'Сентябрь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =10 THEN 'Октябрь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =11 THEN 'Ноябрь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition) =12 THEN 'Декабрь'
           END AS month_of_start_exposition,
           EXTRACT(MONTH FROM a.first_day_exposition) AS month_number,
           COUNT(f.id) AS adv_started_count,                                    -- Считаем статистику
           ROUND(AVG(a.last_price/f.total_area)::NUMERIC,2) AS started_avg_price_per_m2,
           ROUND(AVG(f.total_area)::NUMERIC,2) AS started_avg_total_area
    FROM real_estate.advertisement AS a
    JOIN real_estate.flats AS f
    ON a.id=f.id
    WHERE days_exposition IS NOT NULL
    AND a.id IN (SELECT * FROM filtered_id)
    GROUP BY month_of_start_exposition, month_number
    ),
    --Посчитаем статистику проданых квартир(снятых объявлений):
    SOLD AS (
    SELECT  CASE 
	       WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =1 THEN 'Январь'       -- Создаем столбец с разбвикой по месяцам
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =2 THEN 'Февраль'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =3 THEN 'Март'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =4 THEN 'Апрель'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =5 THEN 'Май'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =6 THEN 'Июнь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =7 THEN 'Июль'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =8 THEN 'Август'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =9 THEN 'Сентябрь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =10 THEN 'Октябрь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =11 THEN 'Ноябрь'
           WHEN EXTRACT(MONTH FROM a.first_day_exposition+days_exposition::integer) =12 THEN 'Декабрь'
           END AS month_of_end_exposition,
           COUNT(f.id) AS adv_removed_count,                                                          -- Считаем статистику
           ROUND(AVG(a.last_price/f.total_area)::NUMERIC,2) AS removed_avg_price_per_m2,
           ROUND(AVG(f.total_area)::NUMERIC,2) AS removed_avg_total_area
    FROM real_estate.advertisement AS a
    JOIN real_estate.flats AS f
    ON a.id=f.id
    WHERE days_exposition IS NOT NULL
    AND a.id IN (SELECT * FROM filtered_id)
    GROUP BY month_of_end_exposition 
    )
    -- Основной запрос:                                                       -- Объединяем тамблтцы со статистикой публикации и продажи объявлений в разрезе месяца
    SELECT st.MONTH_number,
           st.month_of_start_exposition AS month,
           st.adv_started_count,
           RANK()OVER(ORDER BY st.adv_started_count DESC) AS start_rank,
           so.adv_removed_count,
           RANK()OVER(ORDER BY so.adv_removed_count DESC) AS end_rank,
           st.started_avg_price_per_m2,
           so.removed_avg_price_per_m2,
           st.started_avg_total_area,
           so.removed_avg_total_area
    FROM START AS st
    JOIN SOLD AS so
    ON st.month_of_start_exposition=so.month_of_end_exposition
    ORDER BY st.adv_started_count DESC
   
    -- Задача 3: Анализ рынка недвижимости Ленобласти
-- Результат запроса должен ответить на такие вопросы:
-- 1. В каких населённые пунктах Ленинградской области наиболее активно публикуют объявления о продаже недвижимости?
-- 2. В каких населённых пунктах Ленинградской области — самая высокая доля снятых с публикации объявлений? 
--    Это может указывать на высокую долю продажи недвижимости.
-- 3. Какова средняя стоимость одного квадратного метра и средняя площадь продаваемых квартир в различных населённых пунктах? 
--    Есть ли вариация значений по этим метрикам?
-- 4. Среди выделенных населённых пунктов какие пункты выделяются по продолжительности публикации объявлений? 
--    То есть где недвижимость продаётся быстрее, а где — медленнее.

-- Определим аномальные значения (выбросы) по значению перцентилей:
WITH limits AS (
    SELECT  
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY total_area) AS total_area_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY rooms) AS rooms_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY balcony) AS balcony_limit,
        PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY ceiling_height) AS ceiling_height_limit_h,
        PERCENTILE_DISC(0.01) WITHIN GROUP (ORDER BY ceiling_height) AS ceiling_height_limit_l
    FROM real_estate.flats     
),
-- Найдём id объявлений, которые не содержат выбросы:
filtered_id AS(
    SELECT id
    FROM real_estate.flats  
    WHERE 
        total_area < (SELECT total_area_limit FROM limits)
        AND (rooms < (SELECT rooms_limit FROM limits) OR rooms IS NULL)
        AND (balcony < (SELECT balcony_limit FROM limits) OR balcony IS NULL)
        AND ((ceiling_height < (SELECT ceiling_height_limit_h FROM limits)
            AND ceiling_height > (SELECT ceiling_height_limit_l FROM limits)) OR ceiling_height IS NULL)
    ),
    advertisement2 AS (
        SELECT *,
               first_day_exposition+days_exposition::integer AS last_day_exposition
        FROM real_estate.advertisement 
    )
    --
    SELECT RANK() OVER(ORDER BY COUNT(f.id) DESC) AS RANK,
           c.city,
           COUNT(a.first_day_exposition) AS adv_started_count,
           COUNT(a.last_day_exposition) AS adv_removed_count,
           ROUND(COUNT(a.last_day_exposition)/COUNT(a.first_day_exposition)::NUMERIC,2) AS percent_removed,
           ROUND(AVG(a.last_price/f.total_area)::NUMERIC,2) AS avg_price_per_m2,
           ROUND(AVG(f.total_area)::NUMERIC,2) AS avg_total_area,
           ROUND(AVG(a.days_exposition)::numeric,2) AS avg_days_exposition,
           PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY a.days_exposition) AS days_eposition_median,
           PERCENTILE_DISC(0.99) WITHIN GROUP (ORDER BY a.days_exposition) AS days_eposition_slow,
           ROUND(AVG(a.last_price)::NUMERIC,2) AS price,
           STRING_AGG(t.TYPE,', ') OVER (PARTITION BY c.city) AS type
    FROM real_estate.flats AS f
    JOIN real_estate.city AS c
    ON f.city_id=c.city_id 
    JOIN advertisement2 AS a
    ON f.id=a.id
    JOIN real_estate.TYPE AS t
    ON f.type_id=t.type_id
    WHERE city != 'Санкт-Петербург' AND f.id IN (SELECT * FROM filtered_id)
    GROUP BY c.city, type
    ORDER BY RANK
    LIMIT 15
 