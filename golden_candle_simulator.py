"""
Golden Candle Strategy Simulator
================================
Симулятор стратегии "Золотые свечи" для криптовалют (ETH, BTC)

Автор: Denis
Версия: 1.0
Дата: Декабрь 2025

Лучшие результаты (2024-2025):
- ETH: +$4,568 (104 сделки, Ratio ~6.5)
- BTC: +$70,973 (52 сделки, Ratio ~9.2)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# КОНФИГУРАЦИЯ ПАРАМЕТРОВ
# =============================================================================

@dataclass
class StrategyConfig:
    """
    Конфигурация параметров стратегии
    
    Параметры входа (золотая свеча):
    - entry_sigma: минимальное отклонение от VWAP в сигмах для входа
    - max_sigma: максимальное отклонение (None = без ограничения)
    - vol_multiplier: минимальный множитель объёма относительно среднего
    - vol_lookback: период расчёта среднего объёма (в барах)
    - min_body_pct: минимальный размер тела свечи в % от цены
    - max_body_pct: максимальный размер тела свечи в % от цены
    
    Параметры выхода:
    - tp: Take Profit в $ (абсолютное значение)
    - sl: Stop Loss в $ (абсолютное значение)
    - trail_trigger: уровень прибыли для активации трейлинга в 0
    
    Параметры времени:
    - no_entry_days: дни недели без входов (на русском)
    - fc_time: время принудительного закрытия в воскресенье (HH:MM)
    
    Прочее:
    - commission: комиссия (0.0005 = 0.05%)
    - skip_zero_sigma: пропускать свечи с σ=0 (первые свечи недели)
    """
    # Параметры входа
    entry_sigma: float = 2.1
    max_sigma: Optional[float] = None  # None = без ограничения
    vol_multiplier: float = 3.0
    vol_lookback: int = 6
    min_body_pct: float = 0.9
    max_body_pct: float = 10.0
    
    # Параметры выхода
    tp: float = 200.0
    sl: float = 75.0
    trail_trigger: float = 120.0
    
    # Параметры времени
    no_entry_days: List[str] = None  # По умолчанию: Пт, Сб, Вс
    fc_time: str = '23:30'  # Forced close в воскресенье
    
    # Прочее
    commission: float = 0.0005
    skip_zero_sigma: bool = True
    
    def __post_init__(self):
        if self.no_entry_days is None:
            self.no_entry_days = ['Пятница', 'Суббота', 'Воскресенье']


# Предустановленные конфигурации для ETH и BTC
ETH_CONFIG = StrategyConfig(
    entry_sigma=2.1,
    max_sigma=None,  # Без ограничения сверху
    vol_multiplier=3.0,
    vol_lookback=6,
    min_body_pct=0.9,
    max_body_pct=10.0,
    tp=200.0,
    sl=75.0,
    trail_trigger=120.0,
    fc_time='23:30',
    commission=0.0005,
    skip_zero_sigma=True
)

BTC_CONFIG = StrategyConfig(
    entry_sigma=2.0,
    max_sigma=2.7,  # Ограничение сверху
    vol_multiplier=4.0,
    vol_lookback=6,
    min_body_pct=0.65,
    max_body_pct=2.1,
    tp=5000.0,
    sl=3000.0,
    trail_trigger=2000.0,
    fc_time='20:00',
    commission=0.0005,
    skip_zero_sigma=True
)


# =============================================================================
# ПОДГОТОВКА ДАННЫХ
# =============================================================================

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка данных для бэктеста
    
    Требуемые колонки в исходном DataFrame:
    - date: дата
    - time: время
    - open, high, low, close: OHLC
    - volume: объём
    - VWAP: Volume Weighted Average Price
    - σ (sigma): стандартное отклонение
    - День: день недели на русском
    - week_key: ключ недели для группировки
    
    Добавляемые колонки:
    - dist: отклонение от VWAP в сигмах
    - body: размер тела свечи в $
    - body_pct: размер тела в % от цены
    - avg_vol: средний объём за lookback период
    - vol_ratio: отношение текущего объёма к среднему
    """
    df = df.copy()
    
    # Расчёт отклонения в сигмах
    df['dist'] = np.where(
        df['σ'] > 0, 
        (df['close'] - df['VWAP']) / df['σ'], 
        0
    )
    
    # Размер тела свечи
    df['body'] = abs(df['close'] - df['open'])
    df['body_pct'] = df['body'] / df['close'] * 100
    
    # Направление свечи
    df['bullish'] = df['close'] > df['open']
    df['bearish'] = df['close'] < df['open']
    
    # Средний объём (за предыдущие vol_lookback баров)
    df['avg_vol'] = df['volume'].shift(1).rolling(6).mean()
    df['vol_ratio'] = df['volume'] / df['avg_vol']
    
    return df


def update_vol_ratio(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Пересчёт vol_ratio с другим lookback периодом"""
    df = df.copy()
    df['avg_vol'] = df['volume'].shift(1).rolling(lookback).mean()
    df['vol_ratio'] = df['volume'] / df['avg_vol']
    return df


# =============================================================================
# ОПРЕДЕЛЕНИЕ ЗОЛОТОЙ СВЕЧИ
# =============================================================================

def is_gold_candle(row: pd.Series, config: StrategyConfig) -> Tuple[bool, Optional[str]]:
    """
    Проверка, является ли свеча золотой
    
    Условия золотой свечи:
    1. Объём >= vol_multiplier * средний объём
    2. Размер тела в диапазоне [min_body_pct, max_body_pct]
    3. σ > 0 (если skip_zero_sigma=True)
    4. |dist| >= entry_sigma
    5. |dist| <= max_sigma (если задано)
    
    Returns:
        (is_gold, side): (True/False, 'BUY'/'SELL'/None)
    """
    # Проверка объёма
    if pd.isna(row['vol_ratio']) or row['vol_ratio'] < config.vol_multiplier:
        return False, None
    
    # Проверка размера тела
    if not (config.min_body_pct <= row['body_pct'] <= config.max_body_pct):
        return False, None
    
    # Пропуск σ=0
    if config.skip_zero_sigma and row['σ'] == 0:
        return False, None
    
    # Проверка сигмы
    dist = row['dist']
    
    # BUY: dist >= entry_sigma (и <= max_sigma если задано)
    if dist >= config.entry_sigma:
        if config.max_sigma is None or dist <= config.max_sigma:
            return True, 'BUY'
    
    # SELL: dist <= -entry_sigma (и >= -max_sigma если задано)
    if dist <= -config.entry_sigma:
        if config.max_sigma is None or dist >= -config.max_sigma:
            return True, 'SELL'
    
    return False, None


# =============================================================================
# БЭКТЕСТЕР
# =============================================================================

def run_backtest(df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """
    Запуск бэктеста стратегии
    
    Args:
        df: DataFrame с подготовленными данными
        config: конфигурация стратегии
    
    Returns:
        DataFrame со сделками:
        - side: направление (BUY/SELL)
        - entry_date, entry_time: дата и время входа
        - exit_date, exit_time: дата и время выхода
        - entry_price, exit_price: цены входа и выхода
        - pnl: прибыль/убыток с учётом комиссии
        - outcome: результат (TP/SL/STOP0/FC)
        - week: ключ недели
    """
    # Пересчёт vol_ratio если lookback отличается от 6
    if config.vol_lookback != 6:
        df = update_vol_ratio(df, config.vol_lookback)
    else:
        df = prepare_data(df)
    
    trades = []
    
    # Состояние позиции
    in_position = False
    entry_price = None
    side = None
    entry_time = None
    entry_date = None
    max_profit = 0
    stop_at_zero = False
    
    for idx in range(1, len(df)):
        row = df.iloc[idx]
        close = row['close']
        day = row['День']
        date_str = str(row['date'])[:10]
        time_str = str(row['time'])[:5]
        week = row['week_key']
        
        # === УПРАВЛЕНИЕ ПОЗИЦИЕЙ ===
        if in_position:
            # Расчёт текущего P&L
            if side == 'BUY':
                current_pnl = close - entry_price
            else:
                current_pnl = entry_price - close
            
            # Обновление максимальной прибыли
            if current_pnl > max_profit:
                max_profit = current_pnl
            
            # Активация трейлинга
            if current_pnl >= config.trail_trigger and not stop_at_zero:
                stop_at_zero = True
            
            # Проверка условий выхода
            outcome = None
            exit_pnl = current_pnl
            
            # Take Profit
            if current_pnl >= config.tp:
                outcome = 'TP'
                exit_pnl = config.tp
            
            # Stop Loss
            elif current_pnl <= -config.sl:
                outcome = 'SL'
                exit_pnl = -config.sl
            
            # Trailing Stop at Zero
            elif stop_at_zero and current_pnl <= 0:
                outcome = 'STOP0'
                exit_pnl = 0
            
            # Forced Close (воскресенье)
            elif day == 'Воскресенье' and time_str >= config.fc_time:
                outcome = 'FC'
            
            # Закрытие позиции
            if outcome:
                comm = (entry_price + close) * config.commission
                trades.append({
                    'side': side,
                    'entry_date': entry_date,
                    'entry_time': entry_time,
                    'exit_date': date_str,
                    'exit_time': time_str,
                    'entry_price': entry_price,
                    'exit_price': close,
                    'pnl': exit_pnl - comm,
                    'outcome': outcome,
                    'week': week
                })
                in_position = False
        
        # === ВХОД В ПОЗИЦИЮ ===
        if not in_position:
            # Проверка дня недели
            if day in config.no_entry_days:
                continue
            
            # Проверка золотой свечи
            is_gold, gold_side = is_gold_candle(row, config)
            
            if is_gold:
                in_position = True
                entry_price = close
                side = gold_side
                entry_time = time_str
                entry_date = date_str
                max_profit = 0
                stop_at_zero = False
    
    return pd.DataFrame(trades)


# =============================================================================
# СТАТИСТИКА И ОТЧЁТЫ
# =============================================================================

def calculate_stats(trades: pd.DataFrame) -> dict:
    """Расчёт статистики по сделкам"""
    if len(trades) == 0:
        return {
            'trades': 0, 'tp': 0, 'sl': 0, 'fc': 0, 'stop0': 0,
            'net': 0, 'dd': 0, 'ratio': 0, 'win_rate': 0
        }
    
    net = trades['pnl'].sum()
    cum = trades['pnl'].cumsum()
    dd = (cum - cum.cummax()).min()
    ratio = -net / dd if dd < 0 else float('inf')
    
    wins = len(trades[trades['pnl'] > 0])
    win_rate = wins / len(trades) * 100
    
    return {
        'trades': len(trades),
        'tp': len(trades[trades['outcome'] == 'TP']),
        'sl': len(trades[trades['outcome'] == 'SL']),
        'fc': len(trades[trades['outcome'] == 'FC']),
        'stop0': len(trades[trades['outcome'] == 'STOP0']),
        'net': net,
        'dd': dd,
        'ratio': ratio,
        'win_rate': win_rate
    }


def print_stats(stats: dict, label: str = ''):
    """Вывод статистики"""
    print(f"{label}: {stats['trades']} сделок | "
          f"TP:{stats['tp']} SL:{stats['sl']} FC:{stats['fc']} STOP0:{stats['stop0']} | "
          f"Net ${stats['net']:+,.0f} | DD ${stats['dd']:,.0f} | "
          f"Ratio {stats['ratio']:.2f} | WinRate {stats['win_rate']:.1f}%")


def generate_report(trades: pd.DataFrame, config: StrategyConfig, 
                    output_path: str, asset: str = 'ASSET'):
    """Генерация Excel отчёта"""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Параметры
        params = pd.DataFrame([
            {'Параметр': 'TP', 'Значение': f'${config.tp:,.0f}'},
            {'Параметр': 'SL', 'Значение': f'${config.sl:,.0f}'},
            {'Параметр': 'Trail', 'Значение': f'${config.trail_trigger:,.0f} → 0'},
            {'Параметр': 'Sigma min', 'Значение': config.entry_sigma},
            {'Параметр': 'Sigma max', 'Значение': config.max_sigma or '—'},
            {'Параметр': 'Volume', 'Значение': f'{config.vol_multiplier}x'},
            {'Параметр': 'Body', 'Значение': f'{config.min_body_pct}% — {config.max_body_pct}%'},
            {'Параметр': 'FC', 'Значение': f'Вс {config.fc_time}'},
        ])
        params.to_excel(writer, sheet_name='Параметры', index=False)
        
        # Статистика
        stats = calculate_stats(trades)
        summary = pd.DataFrame([stats])
        summary.to_excel(writer, sheet_name='Статистика', index=False)
        
        # Сделки
        trades_out = trades.copy()
        trades_out['cum'] = trades_out['pnl'].cumsum().round(2)
        trades_out.to_excel(writer, sheet_name='Сделки', index=False)
        
        # Помесячно
        if len(trades) > 0:
            trades_out['month'] = pd.to_datetime(trades_out['entry_date']).dt.to_period('M')
            monthly = trades_out.groupby('month').agg({
                'pnl': ['count', 'sum'],
                'outcome': lambda x: (x == 'TP').sum()
            }).round(0)
            monthly.columns = ['Сделок', 'Net', 'TP']
            monthly['Cum'] = monthly['Net'].cumsum()
            monthly.to_excel(writer, sheet_name='Помесячно')


# =============================================================================
# ОПТИМИЗАТОР ПАРАМЕТРОВ
# =============================================================================

def optimize_parameters(df: pd.DataFrame, 
                       param_grid: dict,
                       base_config: StrategyConfig = None) -> pd.DataFrame:
    """
    Оптимизация параметров стратегии
    
    Args:
        df: DataFrame с данными
        param_grid: словарь с параметрами для перебора
            Пример: {
                'entry_sigma': [1.9, 2.0, 2.1],
                'tp': [150, 200, 250],
                'sl': [50, 75, 100]
            }
        base_config: базовая конфигурация (если None, используется ETH_CONFIG)
    
    Returns:
        DataFrame с результатами всех комбинаций
    """
    if base_config is None:
        base_config = ETH_CONFIG
    
    results = []
    
    # Генерация всех комбинаций
    import itertools
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    for combo in itertools.product(*values):
        # Создание конфигурации с новыми параметрами
        config_dict = {
            'entry_sigma': base_config.entry_sigma,
            'max_sigma': base_config.max_sigma,
            'vol_multiplier': base_config.vol_multiplier,
            'vol_lookback': base_config.vol_lookback,
            'min_body_pct': base_config.min_body_pct,
            'max_body_pct': base_config.max_body_pct,
            'tp': base_config.tp,
            'sl': base_config.sl,
            'trail_trigger': base_config.trail_trigger,
            'fc_time': base_config.fc_time,
            'commission': base_config.commission,
            'skip_zero_sigma': base_config.skip_zero_sigma
        }
        
        # Обновление параметрами из комбинации
        for key, value in zip(keys, combo):
            config_dict[key] = value
        
        config = StrategyConfig(**config_dict)
        
        # Запуск бэктеста
        trades = run_backtest(df, config)
        stats = calculate_stats(trades)
        
        # Сохранение результата
        result = {key: value for key, value in zip(keys, combo)}
        result.update(stats)
        results.append(result)
    
    return pd.DataFrame(results).sort_values('net', ascending=False)


# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

def main():
    """Пример использования симулятора"""
    
    print("="*70)
    print("  Golden Candle Strategy Simulator")
    print("="*70)
    
    # Пример загрузки данных
    # df = pd.read_excel('ETHUSDT_30min.xlsx', sheet_name='Data')
    
    # Пример запуска для ETH
    # df = prepare_data(df)
    # trades = run_backtest(df, ETH_CONFIG)
    # stats = calculate_stats(trades)
    # print_stats(stats, 'ETH')
    
    # Пример запуска для BTC
    # trades = run_backtest(df, BTC_CONFIG)
    # stats = calculate_stats(trades)
    # print_stats(stats, 'BTC')
    
    # Пример оптимизации
    # param_grid = {
    #     'entry_sigma': [1.9, 2.0, 2.1, 2.2],
    #     'tp': [150, 175, 200, 225, 250],
    #     'sl': [50, 75, 100, 125]
    # }
    # results = optimize_parameters(df, param_grid, ETH_CONFIG)
    # print(results.head(10))
    
    print("\nДля запуска:")
    print("1. Загрузите данные: df = pd.read_excel('file.xlsx', sheet_name='Data')")
    print("2. Подготовьте данные: df = prepare_data(df)")
    print("3. Запустите бэктест: trades = run_backtest(df, ETH_CONFIG)")
    print("4. Посмотрите статистику: print_stats(calculate_stats(trades))")


if __name__ == '__main__':
    main()
