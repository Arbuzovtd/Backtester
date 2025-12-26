# Golden Candle Strategy Simulator

## Описание стратегии

Стратегия "Золотые свечи" — трендследящая стратегия для криптовалют (ETH, BTC) на таймфрейме 30 минут.

### Логика входа (Золотая свеча)
Вход происходит при появлении "золотой" свечи, которая соответствует всем критериям:
1. **Объём** >= множитель × средний объём за N предыдущих баров
2. **Размер тела** в заданном диапазоне (% от цены)
3. **Отклонение от VWAP** в сигмах находится в заданном диапазоне
4. **День недели** — не Пт/Сб/Вс (без входов на выходных)

### Логика выхода
- **TP (Take Profit)** — фиксированный уровень прибыли
- **SL (Stop Loss)** — фиксированный уровень убытка
- **Trail to Zero** — после достижения триггера, стоп переносится в безубыток
- **FC (Forced Close)** — принудительное закрытие в воскресенье

---

## Лучшие параметры (2024-2025)

### ETH (ETHUSDT 30min)
| Параметр | Значение | Описание |
|----------|----------|----------|
| TP | $200 | Take Profit |
| SL | $75 | Stop Loss |
| Trail | $120 → 0 | При +$120 стоп в 0 |
| Sigma | ≥ 2.1 | Минимальное отклонение |
| Volume | ≥ 3x | Множитель объёма |
| Body | 0.9% — 10% | Размер тела свечи |
| FC | Вс 23:30 | Принудительное закрытие |

**Результат:** +$4,568 за 2 года (104 сделки, Ratio ~6.5)

### BTC (BTCUSDT 30min)
| Параметр | Значение | Описание |
|----------|----------|----------|
| TP | $5,000 | Take Profit |
| SL | $3,000 | Stop Loss |
| Trail | $2,000 → 0 | При +$2000 стоп в 0 |
| Sigma | 2.0 — 2.7 | Диапазон отклонения |
| Volume | ≥ 4x | Множитель объёма |
| Body | 0.65% — 2.1% | Размер тела свечи |
| FC | Вс 20:00 | Принудительное закрытие |

**Результат:** +$70,973 за 2 года (52 сделки, Ratio ~9.2)

---

## Структура входных данных

Excel файл должен содержать лист `Data` с колонками:

| Колонка | Тип | Описание |
|---------|-----|----------|
| date | datetime | Дата свечи |
| time | time | Время открытия свечи |
| open | float | Цена открытия |
| high | float | Максимум |
| low | float | Минимум |
| close | float | Цена закрытия |
| volume | float | Объём |
| VWAP | float | Volume Weighted Average Price |
| σ | float | Стандартное отклонение (sigma) |
| День | str | День недели на русском (Понедельник, Вторник...) |
| week_key | str | Ключ недели для группировки |

---

## Использование

### Базовый запуск

```python
import pandas as pd
from golden_candle_simulator import (
    prepare_data, run_backtest, calculate_stats, print_stats,
    ETH_CONFIG, BTC_CONFIG, StrategyConfig
)

# Загрузка данных
df = pd.read_excel('ETHUSDT_30min_2024.xlsx', sheet_name='Data')

# Подготовка данных
df = prepare_data(df)

# Бэктест с предустановленной конфигурацией
trades = run_backtest(df, ETH_CONFIG)

# Статистика
stats = calculate_stats(trades)
print_stats(stats, 'ETH 2024')

# Сохранение сделок
trades.to_excel('trades_eth_2024.xlsx', index=False)
```

### Кастомная конфигурация

```python
from golden_candle_simulator import StrategyConfig, run_backtest

# Создание своей конфигурации
my_config = StrategyConfig(
    entry_sigma=2.0,      # Мин. отклонение в сигмах
    max_sigma=2.5,        # Макс. отклонение (None = без ограничения)
    vol_multiplier=3.5,   # Множитель объёма
    vol_lookback=6,       # Период среднего объёма
    min_body_pct=0.8,     # Мин. размер тела %
    max_body_pct=5.0,     # Макс. размер тела %
    tp=180.0,             # Take Profit $
    sl=60.0,              # Stop Loss $
    trail_trigger=100.0,  # Триггер трейлинга $
    fc_time='22:00',      # Forced close время
    commission=0.0005,    # Комиссия
    skip_zero_sigma=True  # Пропускать σ=0
)

trades = run_backtest(df, my_config)
```

### Оптимизация параметров

```python
from golden_candle_simulator import optimize_parameters, ETH_CONFIG

# Сетка параметров для перебора
param_grid = {
    'entry_sigma': [1.9, 2.0, 2.1, 2.2, 2.3],
    'tp': [150, 175, 200, 225, 250],
    'sl': [50, 75, 100],
    'trail_trigger': [100, 120, 140]
}

# Запуск оптимизации
results = optimize_parameters(df, param_grid, base_config=ETH_CONFIG)

# Топ-10 комбинаций
print(results.head(10))

# Сохранение всех результатов
results.to_excel('optimization_results.xlsx', index=False)
```

### Тест на нескольких годах

```python
# Загрузка данных за разные годы
df_2023 = pd.read_excel('ETHUSDT_30min_2023.xlsx', sheet_name='Data')
df_2024 = pd.read_excel('ETHUSDT_30min_2024.xlsx', sheet_name='Data')
df_2025 = pd.read_excel('ETHUSDT_30min_2025.xlsx', sheet_name='Data')

results = []
for year, df in [('2023', df_2023), ('2024', df_2024), ('2025', df_2025)]:
    df = prepare_data(df)
    trades = run_backtest(df, ETH_CONFIG)
    stats = calculate_stats(trades)
    stats['year'] = year
    results.append(stats)
    print_stats(stats, f'ETH {year}')

# Сводная таблица
pd.DataFrame(results).to_excel('multi_year_results.xlsx', index=False)
```

---

## Параметры для оптимизации

### Приоритетные параметры (большое влияние):
1. **entry_sigma** — порог входа (1.8 — 2.5)
2. **max_sigma** — верхний порог для BTC (2.5 — 3.0)
3. **tp** — Take Profit
4. **sl** — Stop Loss
5. **trail_trigger** — триггер трейлинга

### Вторичные параметры (среднее влияние):
6. **vol_multiplier** — множитель объёма (2.5 — 5.0)
7. **min_body_pct** — минимальный размер тела (0.5 — 1.5%)
8. **max_body_pct** — максимальный размер тела (2 — 10%)

### Параметры времени:
9. **fc_time** — время закрытия в Вс (18:00 — 23:30)
10. **vol_lookback** — период среднего объёма (4 — 10)

---

## Метрики качества

| Метрика | Описание | Целевое значение |
|---------|----------|------------------|
| Net | Чистая прибыль | Максимизировать |
| DD | Максимальная просадка | Минимизировать |
| Ratio | Net / |DD| | > 2.0 |
| Win Rate | % прибыльных сделок | > 40% |
| Trades | Количество сделок | > 20/год |

**Важно:** Оптимизируйте по Ratio, а не только по Net — это баланс прибыли и риска.

---

## Рекомендации по оптимизации

1. **Избегайте переоптимизации** — используйте out-of-sample тестирование
2. **Тестируйте на разных годах** — параметры должны работать стабильно
3. **Следите за количеством сделок** — слишком мало = ненадёжная статистика
4. **BTC vs ETH** — параметры сильно различаются из-за разницы в цене
5. **Масштабирование TP/SL** — для BTC примерно x25-30 от ETH

---

## Файлы

- `golden_candle_simulator.py` — основной код симулятора
- `README.md` — эта инструкция
- `ETHUSDT_30min_*.xlsx` — данные ETH (требуется подготовить)
- `BTCUSDT_30min_*.xlsx` — данные BTC (требуется подготовить)

---

## Контакты

При вопросах по логике стратегии или структуре данных — обращайтесь к автору.

**Версия:** 1.0  
**Дата:** Декабрь 2025
