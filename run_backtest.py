"""
Пример запуска симулятора Golden Candle Strategy
================================================

Этот скрипт демонстрирует:
1. Загрузку данных
2. Бэктест с разными конфигурациями
3. Оптимизацию параметров
4. Генерацию отчётов
"""

import pandas as pd
from golden_candle_simulator import (
    prepare_data, 
    run_backtest, 
    calculate_stats, 
    print_stats,
    generate_report,
    optimize_parameters,
    ETH_CONFIG, 
    BTC_CONFIG,
    StrategyConfig
)


def test_eth():
    """Тест ETH с лучшими параметрами"""
    print("\n" + "="*70)
    print("  ETH BACKTEST")
    print("="*70)
    
    # Загрузка данных (замените на свой путь)
    try:
        df_2024 = pd.read_excel('ETHUSDT_30min_2024.xlsx', sheet_name='Data')
        df_2024 = prepare_data(df_2024)
        trades_2024 = run_backtest(df_2024, ETH_CONFIG)
        print_stats(calculate_stats(trades_2024), 'ETH 2024')
        trades_2024.to_excel('eth_trades_2024.xlsx', index=False)
    except FileNotFoundError:
        print("Файл ETHUSDT_30min_2024.xlsx не найден")
    
    try:
        df_2025 = pd.read_excel('ETHUSDT_30min_2025.xlsx', sheet_name='Data')
        df_2025 = prepare_data(df_2025)
        trades_2025 = run_backtest(df_2025, ETH_CONFIG)
        print_stats(calculate_stats(trades_2025), 'ETH 2025')
        trades_2025.to_excel('eth_trades_2025.xlsx', index=False)
    except FileNotFoundError:
        print("Файл ETHUSDT_30min_2025.xlsx не найден")


def test_btc():
    """Тест BTC с лучшими параметрами"""
    print("\n" + "="*70)
    print("  BTC BACKTEST")
    print("="*70)
    
    try:
        df_2024 = pd.read_excel('BTCUSDT_30min_2024.xlsx', sheet_name='Data')
        df_2024 = prepare_data(df_2024)
        trades_2024 = run_backtest(df_2024, BTC_CONFIG)
        print_stats(calculate_stats(trades_2024), 'BTC 2024')
        trades_2024.to_excel('btc_trades_2024.xlsx', index=False)
    except FileNotFoundError:
        print("Файл BTCUSDT_30min_2024.xlsx не найден")
    
    try:
        df_2025 = pd.read_excel('BTCUSDT_30min_2025.xlsx', sheet_name='Data')
        df_2025 = prepare_data(df_2025)
        trades_2025 = run_backtest(df_2025, BTC_CONFIG)
        print_stats(calculate_stats(trades_2025), 'BTC 2025')
        trades_2025.to_excel('btc_trades_2025.xlsx', index=False)
    except FileNotFoundError:
        print("Файл BTCUSDT_30min_2025.xlsx не найден")


def optimize_eth():
    """Оптимизация параметров для ETH"""
    print("\n" + "="*70)
    print("  ETH OPTIMIZATION")
    print("="*70)
    
    try:
        df = pd.read_excel('ETHUSDT_30min_2024.xlsx', sheet_name='Data')
        df = prepare_data(df)
        
        # Сетка параметров
        param_grid = {
            'entry_sigma': [1.9, 2.0, 2.1, 2.2],
            'tp': [150, 175, 200, 225],
            'sl': [50, 75, 100],
            'trail_trigger': [100, 120, 140]
        }
        
        print(f"Тестирование {len(param_grid['entry_sigma']) * len(param_grid['tp']) * len(param_grid['sl']) * len(param_grid['trail_trigger'])} комбинаций...")
        
        results = optimize_parameters(df, param_grid, ETH_CONFIG)
        
        print("\nТОП-10 комбинаций по Net:")
        print(results.head(10).to_string(index=False))
        
        results.to_excel('eth_optimization_results.xlsx', index=False)
        print("\nРезультаты сохранены в eth_optimization_results.xlsx")
        
    except FileNotFoundError:
        print("Файл ETHUSDT_30min_2024.xlsx не найден")


def optimize_btc():
    """Оптимизация параметров для BTC"""
    print("\n" + "="*70)
    print("  BTC OPTIMIZATION")
    print("="*70)
    
    try:
        df = pd.read_excel('BTCUSDT_30min_2024.xlsx', sheet_name='Data')
        df = prepare_data(df)
        
        # Сетка параметров
        param_grid = {
            'entry_sigma': [1.9, 2.0, 2.1],
            'max_sigma': [2.5, 2.7, 2.9, None],
            'tp': [4000, 5000, 6000],
            'sl': [2500, 3000, 3500],
            'trail_trigger': [1500, 2000, 2500]
        }
        
        total = 1
        for v in param_grid.values():
            total *= len(v)
        print(f"Тестирование {total} комбинаций...")
        
        results = optimize_parameters(df, param_grid, BTC_CONFIG)
        
        print("\nТОП-10 комбинаций по Net:")
        print(results.head(10).to_string(index=False))
        
        results.to_excel('btc_optimization_results.xlsx', index=False)
        print("\nРезультаты сохранены в btc_optimization_results.xlsx")
        
    except FileNotFoundError:
        print("Файл BTCUSDT_30min_2024.xlsx не найден")


def custom_config_example():
    """Пример с кастомной конфигурацией"""
    print("\n" + "="*70)
    print("  CUSTOM CONFIG EXAMPLE")
    print("="*70)
    
    # Создание кастомной конфигурации
    my_config = StrategyConfig(
        entry_sigma=2.0,
        max_sigma=2.8,
        vol_multiplier=3.5,
        vol_lookback=6,
        min_body_pct=0.7,
        max_body_pct=3.0,
        tp=250.0,
        sl=80.0,
        trail_trigger=150.0,
        fc_time='22:00',
        commission=0.0005,
        skip_zero_sigma=True
    )
    
    print("Кастомная конфигурация:")
    print(f"  Entry Sigma: {my_config.entry_sigma} - {my_config.max_sigma}")
    print(f"  TP/SL/Trail: ${my_config.tp} / ${my_config.sl} / ${my_config.trail_trigger}")
    print(f"  Volume: {my_config.vol_multiplier}x")
    print(f"  Body: {my_config.min_body_pct}% - {my_config.max_body_pct}%")
    
    try:
        df = pd.read_excel('ETHUSDT_30min_2024.xlsx', sheet_name='Data')
        df = prepare_data(df)
        trades = run_backtest(df, my_config)
        print_stats(calculate_stats(trades), 'Custom')
    except FileNotFoundError:
        print("Файл не найден для тестирования")


if __name__ == '__main__':
    print("="*70)
    print("  Golden Candle Strategy - Quick Start")
    print("="*70)
    print("\nВыберите действие:")
    print("1. test_eth()     - Тест ETH с лучшими параметрами")
    print("2. test_btc()     - Тест BTC с лучшими параметрами")
    print("3. optimize_eth() - Оптимизация ETH")
    print("4. optimize_btc() - Оптимизация BTC")
    print("5. custom_config_example() - Пример кастомной конфигурации")
    print("\nЗапустите нужную функцию в Python или раскомментируйте ниже:")
    
    # Раскомментируйте нужное:
    # test_eth()
    # test_btc()
    # optimize_eth()
    # optimize_btc()
    # custom_config_example()
