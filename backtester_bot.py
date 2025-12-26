#!/usr/bin/env python3
"""
Backtester Bot - Автоматический запуск бэктеста Golden Candle Strategy
========================================================================

Использование:
    python backtester_bot.py <файл.xlsx>
    python backtester_bot.py --interactive
    python backtester_bot.py --help

Примеры:
    python backtester_bot.py BTCUSDT_30min.xlsx
    python backtester_bot.py ETHUSDT_30min.xlsx --config BTC_CONFIG
    python backtester_bot.py data.xlsx --optimize
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
from golden_candle_simulator import (
    prepare_data, run_backtest, calculate_stats, print_stats,
    generate_report, optimize_parameters,
    ETH_CONFIG, BTC_CONFIG, StrategyConfig
)


class Colors:
    """ANSI цвета для консоли"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_banner():
    """Вывод баннера программы"""
    banner = f"""
{Colors.CYAN}{'='*70}
{Colors.BOLD}  🚀 Golden Candle Strategy - Backtester Bot
{Colors.END}{Colors.CYAN}{'='*70}{Colors.END}
"""
    print(banner)


def validate_file(file_path: str) -> tuple[bool, str]:
    """
    Валидация файла данных

    Returns:
        (is_valid, message): кортеж с результатом валидации
    """
    # Проверка существования файла
    if not os.path.exists(file_path):
        return False, f"Файл не найден: {file_path}"

    # Проверка расширения
    if not file_path.endswith('.xlsx'):
        return False, "Файл должен быть в формате .xlsx"

    try:
        # Проверка листов
        xl_file = pd.ExcelFile(file_path)
        if 'Data' not in xl_file.sheet_names:
            return False, "Файл должен содержать лист 'Data'"

        # Проверка структуры
        df = pd.read_excel(file_path, sheet_name='Data', nrows=5)
        required_cols = ['date', 'time', 'open', 'high', 'low', 'close',
                        'volume', 'VWAP', 'σ', 'День', 'week_key']

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return False, f"Отсутствуют колонки: {', '.join(missing)}"

        return True, "OK"

    except Exception as e:
        return False, f"Ошибка чтения файла: {str(e)}"


def detect_asset(df: pd.DataFrame) -> str:
    """
    Автоопределение актива (BTC/ETH) по данным

    Args:
        df: DataFrame с данными

    Returns:
        'BTC' или 'ETH'
    """
    # Проверка наличия колонки symbol
    if 'symbol' in df.columns:
        symbol = df['symbol'].iloc[0].upper()
        if 'BTC' in symbol:
            return 'BTC'
        elif 'ETH' in symbol:
            return 'ETH'

    # Определение по цене
    avg_price = df['close'].mean()
    if avg_price > 10000:
        return 'BTC'
    else:
        return 'ETH'


def get_config_by_asset(asset: str) -> StrategyConfig:
    """Получение конфигурации по типу актива"""
    if asset == 'BTC':
        return BTC_CONFIG
    else:
        return ETH_CONFIG


def run_interactive_mode():
    """Интерактивный режим с запросом файла"""
    print_banner()
    print(f"{Colors.BOLD}Интерактивный режим{Colors.END}")
    print()

    # Поиск Excel файлов в текущей директории
    excel_files = list(Path('.').glob('*.xlsx'))

    if excel_files:
        print(f"{Colors.GREEN}Найдены Excel файлы:{Colors.END}")
        for i, file in enumerate(excel_files, 1):
            print(f"  {i}. {file.name}")
        print()

        choice = input("Введите номер файла или полный путь: ").strip()

        # Выбор по номеру
        if choice.isdigit() and 1 <= int(choice) <= len(excel_files):
            file_path = str(excel_files[int(choice) - 1])
        else:
            file_path = choice
    else:
        file_path = input("Введите путь к Excel файлу: ").strip()

    return file_path


def run_backtest_auto(file_path: str, config_override: str = None,
                      optimize: bool = False, save_report: bool = True) -> dict:
    """
    Автоматический запуск бэктеста

    Args:
        file_path: путь к файлу с данными
        config_override: переопределение конфигурации ('BTC_CONFIG' или 'ETH_CONFIG')
        optimize: запустить оптимизацию параметров
        save_report: сохранить отчёт в Excel

    Returns:
        dict со статистикой
    """
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}📊 Загрузка данных...{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")

    # Валидация файла
    is_valid, message = validate_file(file_path)
    if not is_valid:
        print(f"{Colors.RED}❌ Ошибка: {message}{Colors.END}")
        return None

    print(f"{Colors.GREEN}✓{Colors.END} Файл валиден: {file_path}")

    # Загрузка данных
    df = pd.read_excel(file_path, sheet_name='Data')
    print(f"{Colors.GREEN}✓{Colors.END} Загружено строк: {len(df):,}")

    # Определение актива
    asset = detect_asset(df)
    print(f"{Colors.GREEN}✓{Colors.END} Актив: {Colors.BOLD}{asset}{Colors.END}")

    # Выбор конфигурации
    if config_override:
        config = BTC_CONFIG if config_override == 'BTC_CONFIG' else ETH_CONFIG
        print(f"{Colors.YELLOW}⚠{Colors.END} Использована конфигурация: {config_override}")
    else:
        config = get_config_by_asset(asset)
        print(f"{Colors.GREEN}✓{Colors.END} Конфигурация: {asset}_CONFIG")

    # Подготовка данных
    print(f"\n{Colors.BOLD}🔄 Подготовка данных...{Colors.END}")
    df = prepare_data(df)
    print(f"{Colors.GREEN}✓{Colors.END} Данные подготовлены")

    # Информация о периоде
    date_from = f"{df['date'].min()} {df['time'].min()}"
    date_to = f"{df['date'].max()} {df['time'].max()}"
    print(f"{Colors.CYAN}  Период:{Colors.END} {date_from} - {date_to}")

    # Режим оптимизации
    if optimize:
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}🔍 Режим оптимизации{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")

        # Сетка параметров
        if asset == 'BTC':
            param_grid = {
                'entry_sigma': [1.9, 2.0, 2.1],
                'max_sigma': [2.5, 2.7, 2.9],
                'tp': [4000, 5000, 6000],
                'sl': [2500, 3000, 3500],
            }
        else:
            param_grid = {
                'entry_sigma': [1.9, 2.0, 2.1, 2.2],
                'tp': [150, 175, 200, 225, 250],
                'sl': [50, 75, 100],
                'trail_trigger': [100, 120, 140]
            }

        total_combinations = 1
        for v in param_grid.values():
            total_combinations *= len(v)

        print(f"Тестирование {total_combinations} комбинаций параметров...")
        print()

        results = optimize_parameters(df, param_grid, config)

        print(f"\n{Colors.GREEN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}📈 ТОП-5 комбинаций:{Colors.END}")
        print(f"{Colors.GREEN}{'='*70}{Colors.END}")
        print(results.head(5).to_string(index=False))

        # Сохранение результатов
        if save_report:
            output_file = f"optimization_{asset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            results.to_excel(output_file, index=False)
            print(f"\n{Colors.GREEN}✓{Colors.END} Результаты сохранены: {output_file}")

        return results.iloc[0].to_dict()

    # Обычный бэктест
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}🚀 Запуск бэктеста...{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")

    trades = run_backtest(df, config)
    stats = calculate_stats(trades)

    # Вывод результатов
    print(f"\n{Colors.GREEN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}📊 РЕЗУЛЬТАТЫ{Colors.END}")
    print(f"{Colors.GREEN}{'='*70}{Colors.END}")

    print(f"\n{Colors.BOLD}Сделки:{Colors.END}")
    print(f"  Всего:     {stats['trades']}")
    print(f"  TP:        {stats['tp']} ({stats['tp']/max(stats['trades'], 1)*100:.1f}%)")
    print(f"  SL:        {stats['sl']} ({stats['sl']/max(stats['trades'], 1)*100:.1f}%)")
    print(f"  FC:        {stats['fc']}")
    print(f"  STOP0:     {stats['stop0']}")

    print(f"\n{Colors.BOLD}Финансы:{Colors.END}")
    net_color = Colors.GREEN if stats['net'] > 0 else Colors.RED
    print(f"  Net:       {net_color}${stats['net']:+,.2f}{Colors.END}")
    print(f"  DD:        ${stats['dd']:,.2f}")
    print(f"  Ratio:     {stats['ratio']:.2f}")
    print(f"  Win Rate:  {stats['win_rate']:.1f}%")

    # Сохранение отчёта
    if save_report:
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}💾 Сохранение результатов...{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")

        # Файл со сделками
        trades_file = f"trades_{asset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        trades['cum'] = trades['pnl'].cumsum().round(2)
        trades.to_excel(trades_file, index=False)
        print(f"{Colors.GREEN}✓{Colors.END} Сделки сохранены: {trades_file}")

        # Полный отчёт
        report_file = f"report_{asset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        generate_report(trades, config, report_file, asset)
        print(f"{Colors.GREEN}✓{Colors.END} Отчёт сохранён: {report_file}")

    print(f"\n{Colors.GREEN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}✅ Готово!{Colors.END}")
    print(f"{Colors.GREEN}{'='*70}{Colors.END}\n")

    return stats


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Backtester Bot - автоматический запуск бэктеста',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s BTCUSDT_30min.xlsx
  %(prog)s ETHUSDT_30min.xlsx --config ETH_CONFIG
  %(prog)s data.xlsx --optimize
  %(prog)s --interactive
        """
    )

    parser.add_argument('file', nargs='?', help='Путь к Excel файлу с данными')
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Интерактивный режим')
    parser.add_argument('-c', '--config', choices=['BTC_CONFIG', 'ETH_CONFIG'],
                       help='Переопределить конфигурацию')
    parser.add_argument('-o', '--optimize', action='store_true',
                       help='Запустить оптимизацию параметров')
    parser.add_argument('--no-report', action='store_true',
                       help='Не сохранять отчёт')

    args = parser.parse_args()

    # Интерактивный режим
    if args.interactive or not args.file:
        file_path = run_interactive_mode()
    else:
        file_path = args.file

    # Запуск бэктеста
    if file_path:
        run_backtest_auto(
            file_path=file_path,
            config_override=args.config,
            optimize=args.optimize,
            save_report=not args.no_report
        )
    else:
        print(f"{Colors.RED}Ошибка: не указан файл{Colors.END}")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
