import json
import argparse
import sys
import yaml
import pandas as pd
import pandas_ta as ta
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trade.option_strategy import OptionStrategy, Trade
from trade.trend_momentum_strategy import TrendMomentumStrategy
from backtest.download_backtest_data import BacktestDataDownloader
from candlestick import Candle

def load_config(config_path: Path) -> Dict:
    if not config_path.exists():
        return {}
    with open(config_path, 'r') as f:
        try:
            return yaml.safe_load(f)
        except:
            return {}

def load_data(file_path: Path) -> pd.DataFrame:
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return df.ta.rsi(length=period)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return df.ta.atr(high=df['high'], low=df['low'], close=df['close'], length=period)

def display_summary(completed_trades: List[Trade], symbol: str, lower_interval: str, upper_interval: str):
    console = Console()
    table = Table(title=f"📈 Trade Summary: {symbol} ({lower_interval}/{upper_interval})")
    
    table.add_column("Type", style="cyan")
    table.add_column("Entry Time", style="green")
    table.add_column("Exit Time", style="red")
    table.add_column("Qty", justify="right", style="magenta")
    table.add_column("Entry", justify="right", style="green")
    table.add_column("Exit", justify="right", style="red")
    table.add_column("Stop Loss", justify="right", style="yellow")
    table.add_column("RSI (L/U)", justify="right", style="cyan")
    table.add_column("P&L", justify="right", style="bold")
    table.add_column("R:R", justify="right", style="blue")
    table.add_column("Result", justify="center")

    total_pnl = 0
    wins = 0
    losses = 0

    for t in completed_trades:
        if t.entry_time == t.exit_time:
            continue
            
        pnl_per_unit = t.exit_price - t.entry_price if t.option_type == 'CALL' else t.entry_price - t.exit_price
        quantity = getattr(t, 'quantity', 1) or 1
        total_trade_pnl = pnl_per_unit * quantity
        total_pnl += total_trade_pnl
        
        pnl_style = "green" if total_trade_pnl > 0 else "red"
        result_text = "[green]WIN[/green]" if total_trade_pnl > 0 else "[red]LOSS[/red]"
        
        if total_trade_pnl > 0: wins += 1
        else: losses += 1
            
        # Calculate Risk:Reward
        risk = abs(t.entry_price - t.stop_loss) if getattr(t, 'stop_loss', None) else 0
        rr_ratio = f"{abs(pnl_per_unit)/risk:.1f}" if risk > 0 else "N/A"
        
        # Format times for display
        try:
            e_t = t.entry_time.split('T')[0] + " " + t.entry_time.split('T')[1][:5]
            x_t = t.exit_time.split('T')[0] + " " + t.exit_time.split('T')[1][:5]
        except:
            e_t = t.entry_time
            x_t = t.exit_time
        
        rsi_l = f"{t.rsi:.1f}" if getattr(t, 'rsi', None) is not None else "N/A"
        rsi_u = f"{t.rsi_upper:.1f}" if getattr(t, 'rsi_upper', None) is not None else "N/A"
        rsi_display = f"{rsi_l}/{rsi_u}"

        table.add_row(
            t.option_type,
            e_t,
            x_t,
            str(getattr(t, 'quantity', 'N/A')),
            f"{t.entry_price:.2f}",
            f"{t.exit_price:.2f}",
            f"{t.stop_loss:.2f}" if getattr(t, 'stop_loss', None) else "N/A",
            rsi_display,
            f"[{pnl_style}]{total_trade_pnl:.2f}[/{pnl_style}]",
            rr_ratio,
            result_text
        )

    console.print(table)
    
    # Performance Metrics
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    console.print(f"\n[bold]Performance Metrics:[/bold]")
    console.print(f"Total Trades: {total_trades} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    console.print(f"Total Net P&L: [bold {'green' if total_pnl > 0 else 'red'}]{total_pnl:.2f}[/bold {'green' if total_pnl > 0 else 'red'}]")

def run_backtest_wrapper(df_lower: pd.DataFrame, df_upper: pd.DataFrame, symbol: str, lower_interval: str, upper_interval: str, options: Dict = None, strategy_name: str = 'option', from_date: str = None, to_date: str = None):
    console = Console()
    console.print(f"\n[bold blue]Running MTF backtest for {symbol}[/bold blue]")
    console.print(f"Strategy: {strategy_name}")
    console.print(f"Lower interval: {lower_interval}, Upper interval: {upper_interval}")
    
    # Calculate RSI values for lower and upper timeframe
    df_lower['rsi'] = calculate_rsi(df_lower)
    df_upper['rsi'] = calculate_rsi(df_upper)
    
    # Calculate EMAs for Trend Momentum strategy
    if strategy_name == 'trend_momentum':
        from indicators import calculate_ema
        def df_to_candles(df):
            return [Candle(date=r['date'].isoformat(), open=r['open'], high=r['high'], low=r['low'], close=r['close']) for _, r in df.iterrows()]
        
        df_lower['ema20'] = calculate_ema(df_to_candles(df_lower), 20)
        df_lower['ema50'] = calculate_ema(df_to_candles(df_lower), 50)
        df_lower['ema200'] = calculate_ema(df_to_candles(df_lower), 200)
        df_upper['ema50'] = calculate_ema(df_to_candles(df_upper), 50)
        df_upper['ema200'] = calculate_ema(df_to_candles(df_upper), 200)

    # Calculate ATR for stop loss
    atr_period = options.get('indicators', {}).get('atr', {}).get('period', 14)
    df_lower['atr'] = calculate_atr(df_lower, period=atr_period)
    
    # Filter data based on dates AFTER indicator calculation
    if from_date:
        df_lower = df_lower[df_lower['date'].dt.strftime('%Y%m%d') >= from_date]
        df_upper = df_upper[df_upper['date'].dt.strftime('%Y%m%d') >= from_date]
    if to_date:
        df_lower = df_lower[df_lower['date'].dt.strftime('%Y%m%d') <= to_date]
        # For upper timeframe, we might need a bit more data to match the last lower timeframe candle
        df_upper = df_upper[df_upper['date'].dt.strftime('%Y%m%d') <= to_date]

    console.print(f"Total lower candles (filtered): {len(df_lower)}")
    console.print("-" * 50)
    
    if strategy_name == 'trend_momentum':
        strategy = TrendMomentumStrategy(options, symbol)
    else:
        strategy = OptionStrategy(options, symbol)
    
    completed_trades = strategy.run_backtest(df_lower, df_upper)
    
    display_summary(completed_trades, symbol, lower_interval, upper_interval)

def main():
    parser = argparse.ArgumentParser(description='Backtest candlestick patterns on historical data')
    parser.add_argument('--symbol', type=str, help='Symbol (e.g., nifty50, banknifty)')
    parser.add_argument('--lower-interval', type=str, help='Lower Interval (e.g., 5minute)')
    parser.add_argument('--upper-interval', type=str, help='Upper Interval (e.g., 15minute)')
    parser.add_argument('--from-date', type=str, help='From date (YYYYMMDD)')
    parser.add_argument('--to-date', type=str, help='To date (YYYYMMDD)')
    parser.add_argument('--config', type=str, default='config/backtest.yaml', help='Path to backtest config')
    parser.add_argument('--options', type=str, default='config/options.yaml', help='Path to options config')
    parser.add_argument('--strategy', type=str, default='option', choices=['option', 'trend_momentum'], help='Strategy to use')
    
    args = parser.parse_args()
    
    config = load_config(Path(args.config))
    options = load_config(Path(args.options))
    backtest_config = config.get('backtest', {})
    
    symbol = args.symbol or 'nifty50'
    
    # Priority: Command line > backtest.yaml > options.yaml indices > default
    backtest_lower = backtest_config.get('lower_interval')
    backtest_upper = backtest_config.get('upper_interval')
    
    # Get intervals from options.yaml indices
    index_options = options.get('indices', {}).get(symbol.lower(), {})
    timeframes = index_options.get('timeframes', {})
    
    lower_interval = args.lower_interval or backtest_lower or timeframes.get('lower', '5minute')
    upper_interval = args.upper_interval or backtest_upper or timeframes.get('upper', '15minute')
    
    date_range = backtest_config.get('date_range', '')
    from_date = args.from_date
    to_date = args.to_date
    
    if not from_date and '_' in date_range:
        from_date = date_range.split('_')[0][:8]
    if not to_date and '_' in date_range:
        to_date = date_range.split('_')[1][:8]
    
    data_dir = Path(backtest_config.get('cache_dir', 'history_data'))
    
    def get_df(interval):
        pattern = f"{symbol.lower()}_*_{interval}_*"
        files = list(data_dir.glob(f"{pattern}.json"))
        if not files:
            return pd.DataFrame()
        
        file_path = files[0]
        if from_date or to_date:
            for f in files:
                parts = f.stem.split('_')
                if len(parts) >= 5:
                    file_from = parts[-2][:8]
                    file_to = parts[-1][:8]
                    if (not from_date or file_to >= from_date) and (not to_date or file_from <= to_date):
                        file_path = f
                        break
        
        print(f"Using {interval} data from: {file_path}")
        df = load_data(file_path)
        return df

    df_lower = get_df(lower_interval)
    df_upper = get_df(upper_interval)
    
    if df_lower.empty or df_upper.empty:
        print(f"Missing data locally for {symbol}. Attempting to download...")
        
        # Determine date range for download
        # Use full range from config if possible, otherwise use args
        full_date_range = backtest_config.get('date_range', '')
        if '_' in full_date_range:
            from_full, to_full = full_date_range.split('_')
        else:
            from_full = f"{from_date}0915" if from_date else "202501010915"
            to_full = f"{to_date}1530" if to_date else datetime.now().strftime('%Y%m%d%H%M')
            
        downloader = BacktestDataDownloader(
            backtest_config_path=args.config,
            options_config_path=args.options
        )
        
        indices = {symbol.upper(): ''}
        timeframes_to_download = []
        if df_lower.empty: timeframes_to_download.append(lower_interval)
        if df_upper.empty: timeframes_to_download.append(upper_interval)
        
        try:
            f_dt = datetime.strptime(from_full, '%Y%m%d%H%M')
            t_dt = datetime.strptime(to_full, '%Y%m%d%H%M')
            # Handle inverted range if any
            if t_dt < f_dt:
                f_dt, t_dt = t_dt, f_dt
        except:
            f_dt, t_dt = downloader.get_date_range()
            
        downloader.download_index_data(
            indices=indices,
            timeframes=timeframes_to_download,
            from_date=f_dt,
            to_date=t_dt
        )
        
        # Retry loading
        if df_lower.empty: df_lower = get_df(lower_interval)
        if df_upper.empty: df_upper = get_df(upper_interval)

    if df_lower.empty or df_upper.empty:
        print(f"Unable to resolve missing data for ({lower_interval}, {upper_interval})")
        return

    run_backtest_wrapper(df_lower, df_upper, symbol, lower_interval, upper_interval, options, args.strategy, from_date, to_date)

if __name__ == "__main__":
    main()
