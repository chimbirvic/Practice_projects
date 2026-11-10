# Модель данных

## Общая структура

В окне управления связями Power BI отображалось около 30 активных связей типа «многие к одному» (* : 1). Фактоподобные и периодические таблицы связаны со справочниками торговых точек, SKU, календаря и матриц. Направление фильтрации в просмотренных строках одностороннее, от стороны 1 к стороне *.

Ключевые измерения/справочники, видимые в связях:

- analytics_all_ap — идентификаторы торговых точек и BG;
- sku — идентификатор/название SKU;
- calend — поля календаря и сортировки;
- matrices — список ID матриц;
- таблица актуальных статусов торговых точек (название обрезано в UI).

## Связи, видимые в окне модели

- DMP[ID TT] → analytics_all_ap[id]; DMP[sort] → calend[sort].
- facing[outlet] → analytics_all_ap[id]; facing[sku_MM] → sku[id]; facing[sort] → calend[sort].
- fact[outlet_id] → таблица актуальных статусов торговых точек.
- matrix[id] → matrices[id]; matrix[sku_id] → sku[id].
- OSA_01_2026[SKU] … OSA_07_2026[SKU] и OSA_12_2025[SKU] → sku[name] (в окне также видны первые месячные OSA-связи).
- OSA_all[sort] → calend[sort]; OSA_all[Код BG] → analytics_all_ap[beluga_id].
- plan[outlet_id] → таблица актуальных статусов торговых точек.
- plan_new_visits[ID TT] → analytics_all_ap[id]; plan_new_visits[sort] → calend[sort].
- report_sku[outlet_id] → analytics_all_ap[id]; report_sku[sort] → calend[sort].
- reports[matrix_id_new] → matrices[id]; reports[outlet_id] → таблица актуальных статусов торговых точек и analytics_all_ap[id].
- response[outlet] → analytics_all_ap[id]; response[report_id] → fact[report].
- Доля план new[id] → analytics_all_ap[id]; Доля план new[sort] → calend[sort].

Названия некоторых полей или таблиц могли быть частично обрезаны шириной окна. Этот список отражает только отношения, прочитанные в интерфейсе; он не заменяет полный экспорт модели. Необычное параллельное связывание reports[outlet_id] с двумя таблицами требует отдельной проверки бизнес-смысла и влияния на фильтрацию.

## Файл диаграммы

Схема выбранных связей находится в ../model/relationships.mmd. При публикации проверьте диаграмму по экспорту модели, особенно таблицу статусов торговых точек и все связи месячных таблиц OSA.
