# 📊 Разработка A/B-тестирования и анализ результатов

**Автор**: Чимбир В.И.  
**Дата**: 18.06.2025

---

## 🧭 Описание проекта

В рамках проекта вы выступаете в роли продуктового аналитика развлекательного приложения с «бесконечной лентой» (по аналогии с TikTok).  
Приложение монетизируется двумя способами:

- Подписка (без рекламы)
- Бесплатный доступ с рекламой

Команда разработчиков предложила **новый алгоритм рекомендаций**, и необходимо проверить гипотезу о том, что он увеличит вовлечённость пользователей.

---

## 🎯 Цель

- Подготовить и провести A/B-тест, оценивающий эффективность нового рекомендательного алгоритма
- Проанализировать корректность и результаты теста

---

## 🗂️ Используемые данные

Анализ проводился на основе трёх таблиц:

| Файл | Описание | Период |
|------|----------|--------|
| `sessions_project_history.csv` | Исторические данные по сессиям | 2025-08-15 → 2025-09-23 |
| `sessions_project_test_part.csv` | Первый день A/B-теста | 2025-10-14 |
| `sessions_project_test.csv` | Весь период A/B-теста | 2025-10-14 → 2025-11-02 |

**Ключевые поля:**
- `user_id`, `session_id`, `session_date`, `session_start_ts`
- `install_date`, `session_number`, `registration_flag`
- `page_counter`, `region`, `device`, `test_group`

---

## 🔬 Этапы работы

1. 📥 Импорт и изучение исторических данных
2. 📊 Проведение EDA: количество сессий, поведение пользователей, сравнение по устройствам и регионам
3. 📏 Расчёт необходимых параметров A/B-теста: мощность, размер выборки
4. ✅ Проверка корректности случайного распределения пользователей
5. 📈 Анализ результатов эксперимента:
   - Поведенческие метрики: вовлечённость (например, `page_counter`)
   - Статистический анализ: t-тесты / бутстрэп / доверительные интервалы
6. 🧾 Формулировка выводов и рекомендаций

---

## 🛠️ Используемые технологии

- **Python**: `pandas`, `matplotlib`, `seaborn`, `scipy`
- Визуализация данных
- Статистический анализ и проверка гипотез
- Проведение A/B-тестов по всем правилам (разделение, размер выборки, значимость, мощность)

---

## 📌 Результаты

- Проведён A/B-тест нового рекомендательного алгоритма
- Проверена корректность рандомизации
- Проанализированы метрики вовлечённости
- Сделан вывод о статистической значимости разницы между группами

---


