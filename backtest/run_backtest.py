import json
import argparse
import sys
import yaml
import pandas as pd
import numpy as np
import pandas_ta as ta
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from concurrent.futures import ThreadPoolExecutor, as_completed

# Global lock for thread-safe printing
print_lock = threading.Lock()

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trade.option_strategy import OptionStrategy, Trade
from trade.trend_momentum_strategy import TrendMomentumStrategy
from trade.market_structure_strategy import MarketStructureStrategy
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
    rsi = df.ta.rsi(length=period)
    if isinstance(rsi, pd.DataFrame):
        return rsi.iloc[:, 0]
    return rsi

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    atr = df.ta.atr(high=df['high'], low=df['low'], close=df['close'], length=period)
    if isinstance(atr, pd.DataFrame):
        return atr.iloc[:, 0]
    return atr

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_df = df.ta.macd(close=df['close'], fast=fast, slow=slow, signal=signal)
    return macd_df

def calculate_stochastic(df: pd.DataFrame, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    stoch_df = df.ta.stoch(high=df['high'], low=df['low'], close=df['close'], k=k, d=d, smooth_k=smooth_k)
    return stoch_df

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

    with print_lock:
        console.print(table)
        
        # Performance Metrics
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        console.print(f"\n[bold]Performance Metrics:[/bold]")
        console.print(f"Total Trades: {total_trades} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
        console.print(f"Total Net P&L: [bold {'green' if total_pnl > 0 else 'red'}]{total_pnl:.2f}[/bold {'green' if total_pnl > 0 else 'red'}]")

def run_strategy_for_week(strategy_name: str, options: Dict, symbol: str, df_lower_week: pd.DataFrame, df_upper: pd.DataFrame, week_start: pd.Timestamp, week_end: pd.Timestamp) -> List[Trade]:
    """
    Helper function to run backtest for a specific week and filter results.
    """
    if strategy_name == 'trend_momentum':
        strategy = TrendMomentumStrategy(options, symbol)
    elif strategy_name == 'market_structure':
        strategy = MarketStructureStrategy(options, symbol)
    else:
        strategy = OptionStrategy(options, symbol)
        
    trades = strategy.run_backtest(df_lower_week, df_upper)
    
    # Filter trades to only those that started within this week's boundary
    # This prevents duplicate trades from context candles
    filtered_trades = []
    for t in trades:
        try:
            entry_dt = pd.to_datetime(t.entry_time)
            # Ensure entry_dt is timezone-aware if week_start is
            if week_start.tzinfo and not entry_dt.tzinfo:
                entry_dt = entry_dt.tz_localize(week_start.tzinfo)
            elif week_start.tzinfo and entry_dt.tzinfo:
                entry_dt = entry_dt.tz_convert(week_start.tzinfo)
                
            # Use date comparison for week boundaries
            if week_start <= entry_dt <= week_end:
                t.symbol = symbol # Ensure symbol is set
                filtered_trades.append(t)
        except Exception as e:
            # Skip trades that cause parsing errors to avoid potential duplicates from context
            with print_lock:
                print(f"Warning: Could not parse entry time '{t.entry_time}': {e}")
            
    return filtered_trades

def run_backtest_wrapper(df_lower: pd.DataFrame, df_upper: pd.DataFrame, symbol: str, lower_interval: str, upper_interval: str, options: Dict = None, strategy_name: str = 'option', from_date: str = None, to_date: str = None):
    if df_lower.empty or df_upper.empty:
        with print_lock:
            print(f"Skipping backtest for {symbol}: Empty data provided.")
        return []
        
    console = Console()
    with print_lock:
        console.print(f"\n[bold blue]Running Parallel Weekly MTF backtest for {symbol}[/bold blue]")
        console.print(f"Strategy: {strategy_name}")
        console.print(f"Lower interval: {lower_interval}, Upper interval: {upper_interval}")
    
    # Calculate RSI values for lower and upper timeframe
    df_lower.loc[:, 'rsi'] = calculate_rsi(df_lower)
    df_upper.loc[:, 'rsi'] = calculate_rsi(df_upper)
    
    # Ensure date is datetime
    if not df_lower.empty:
        df_lower['date'] = pd.to_datetime(df_lower['date'])
    if not df_upper.empty:
        df_upper['date'] = pd.to_datetime(df_upper['date'])

    # Calculate MACD and Stochastic for Double Cross strategy
    macd_config = options.get('indicators', {}).get('macd', {})
    stoch_config = options.get('indicators', {}).get('stochastic', {})
    
    if not df_lower.empty:
        if macd_config.get('enabled', True):
            macd_lower = calculate_macd(
                df_lower, 
                fast=macd_config.get('fast', 12), 
                slow=macd_config.get('slow', 26), 
                signal=macd_config.get('signal', 9)
            )
            if macd_lower is not None:
                df_lower = df_lower.loc[:, ~df_lower.columns.duplicated()]
                macd_lower = macd_lower.loc[:, ~macd_lower.columns.duplicated()]
                df_lower = pd.concat([df_lower, macd_lower], axis=1)
            
        if stoch_config.get('enabled', True):
            stoch_lower = calculate_stochastic(
                df_lower,
                k=stoch_config.get('k', 14),
                d=stoch_config.get('d', 3),
                smooth_k=stoch_config.get('smooth_k', 3)
            )
            if stoch_lower is not None:
                df_lower = df_lower.loc[:, ~df_lower.columns.duplicated()]
                stoch_lower = stoch_lower.loc[:, ~stoch_lower.columns.duplicated()]
                df_lower = pd.concat([df_lower, stoch_lower], axis=1)

    # Remove any duplicates after all concats
    df_lower = df_lower.loc[:, ~df_lower.columns.duplicated()]

    # Calculate EMAs for Trend Momentum or Market Structure strategy
    if strategy_name in ['trend_momentum', 'market_structure']:
        from indicators import calculate_ema
        def df_to_candles(df):
            return [Candle(date=r['date'].isoformat(), open=r['open'], high=r['high'], low=r['low'], close=r['close']) for _, r in df.iterrows()]
        
        def get_ema_series(df, period):
            s = calculate_ema(df_to_candles(df), period)
            if s is None or s.empty:
                return pd.Series([np.nan] * len(df), index=df.index)
            return s
        
        df_lower['ema20'] = get_ema_series(df_lower, 20)
        df_lower['ema50'] = get_ema_series(df_lower, 50)
        df_lower['ema200'] = get_ema_series(df_lower, 200)
        df_upper['ema50'] = get_ema_series(df_upper, 50)
        df_upper['ema200'] = get_ema_series(df_upper, 200)

    # Calculate ATR for stop loss
    atr_period = options.get('indicators', {}).get('atr', {}).get('period', 14)
    df_lower['atr'] = calculate_atr(df_lower, period=atr_period)
    
    with print_lock:
        console.print(f"Total lower candles (before filtering): {len(df_lower)}")
    
    # Filter data based on dates AFTER indicator calculation
    if from_date:
        df_lower = df_lower[df_lower['date'].dt.strftime('%Y%m%d') >= from_date]
        df_upper = df_upper[df_upper['date'].dt.strftime('%Y%m%d') >= from_date]
    if to_date:
        df_lower = df_lower[df_lower['date'].dt.strftime('%Y%m%d') <= to_date]
        df_upper = df_upper[df_upper['date'].dt.strftime('%Y%m%d') <= to_date]

    with print_lock:
        console.print(f"Total lower candles (after filtering): {len(df_lower)}")
        if not df_lower.empty:
            console.print(f"Date range in data: {df_lower['date'].min()} to {df_lower['date'].max()}")
        console.print("-" * 50)

    if df_lower.empty:
        return []

    # Split into weeks and run in parallel
    df_lower_reset = df_lower.reset_index(drop=True)
    # Use isocalendar week for consistent splitting
    iso_cal = df_lower_reset['date'].dt.isocalendar()
    df_lower_reset['week'] = iso_cal.week + (iso_cal.year * 100)
    groups = list(df_lower_reset.groupby('week'))
    
    with print_lock:
        console.print(f"Processing {len(groups)} weeks in parallel...")
    
    completed_trades = []
    # Context candles needed (using 100 to be safe for all strategies)
    CONTEXT_SIZE = 100
    
    with ThreadPoolExecutor(max_workers=min(10, len(groups))) as executor:
        futures = []
        for name, group in groups:
            start_idx = group.index[0]
            end_idx = group.index[-1]
            
            context_start = max(0, start_idx - CONTEXT_SIZE)
            df_week_with_context = df_lower_reset.iloc[context_start : end_idx + 1].copy()
            
            week_start = group['date'].min()
            week_end = group['date'].max()
            
            futures.append(executor.submit(
                run_strategy_for_week, 
                strategy_name, 
                options, 
                symbol, 
                df_week_with_context, 
                df_upper, 
                week_start, 
                week_end
            ))
            
        for future in as_completed(futures):
            try:
                week_trades = future.result()
                completed_trades.extend(week_trades)
            except Exception as e:
                with print_lock:
                    print(f"Error in weekly backtest: {e}")
                    import traceback
                    traceback.print_exc()

    # Sort trades by entry time
    completed_trades.sort(key=lambda x: x.entry_time)
    
    # Final deduplication to be safe
    seen_trades = set()
    unique_trades = []
    for t in completed_trades:
        trade_id = (t.entry_time, t.option_type, getattr(t, 'pattern', ''))
        if trade_id not in seen_trades:
            seen_trades.add(trade_id)
            unique_trades.append(t)
    completed_trades = unique_trades
        
    display_summary(completed_trades, symbol, lower_interval, upper_interval)
    return completed_trades


def display_combined_summary(all_trades: List[Trade]):
    if not all_trades:
        return
        
    console = Console()
    table = Table(title="📊 [bold blue]Combined Performance Summary (All Indices)[/bold blue]")
    
    table.add_column("Symbol", style="cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Entry Time", style="green")
    table.add_column("Exit Time", style="red")
    table.add_column("Qty", justify="right", style="magenta")
    table.add_column("Entry", justify="right", style="green")
    table.add_column("Exit", justify="right", style="red")
    table.add_column("P&L", justify="right", style="bold")
    table.add_column("Result", justify="center")

    total_pnl = 0
    wins = 0
    losses = 0

    # Sort all trades by entry time
    sorted_trades = sorted(all_trades, key=lambda x: x.entry_time)

    # Deduplicate across symbols (unlikely but safe)
    seen_trades = set()
    unique_trades = []
    for t in sorted_trades:
        trade_id = (t.entry_time, t.option_type, getattr(t, 'symbol', ''))
        if trade_id not in seen_trades:
            seen_trades.add(trade_id)
            unique_trades.append(t)
    sorted_trades = unique_trades

    for t in sorted_trades:
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
        
        # Format times for display
        try:
            e_t = t.entry_time.split('T')[0] + " " + t.entry_time.split('T')[1][:5]
            x_t = t.exit_time.split('T')[0] + " " + t.exit_time.split('T')[1][:5]
        except:
            e_t = t.entry_time
            x_t = t.exit_time

        table.add_row(
            getattr(t, 'symbol', 'N/A'),
            t.option_type,
            e_t,
            x_t,
            str(getattr(t, 'quantity', 'N/A')),
            f"{t.entry_price:.2f}",
            f"{t.exit_price:.2f}",
            f"[{pnl_style}]{total_trade_pnl:.2f}[/{pnl_style}]",
            result_text
        )

    console.print("\n")
    console.print(table)
    
    # Performance Metrics
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    console.print(f"\n[bold]Combined Performance Metrics:[/bold]")
    console.print(f"Total Trades: {total_trades} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    console.print(f"Cumulative Net P&L: [bold {'green' if total_pnl > 0 else 'red'}]{total_pnl:.2f}[/bold {'green' if total_pnl > 0 else 'red'}]")
    console.print("-" * 50 + "\n")

def process_symbol(symbol, backtest_config, options, indices_config, args):
    # Priority: Command line > backtest.yaml > options.yaml indices > default
    backtest_lower = backtest_config.get('lower_interval')
    backtest_upper = backtest_config.get('upper_interval')
    
    # Get intervals from options.yaml indices
    index_options = indices_config.get(symbol.lower(), {})
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
    
    # Fallback to defaults if still None
    if not from_date:
        from_date = "20250101"
    if not to_date:
        to_date = datetime.now().strftime('%Y%m%d')
    
    with print_lock:
        print(f"Target date range for {symbol}: {from_date} to {to_date}")
    
    downloader = BacktestDataDownloader(
        backtest_config_path=args.config,
        options_config_path=args.options
    )
    
    token = downloader.INDEX_TOKENS.get(symbol.upper())
    if not token:
        with print_lock:
            print(f"Token not found for {symbol}. Cannot load data.")
        return []
    
    try:
        f_dt = datetime.strptime(from_date + "0915", "%Y%m%d%H%M")
        t_dt = datetime.strptime(to_date + "1530", "%Y%m%d%H%M")
    except Exception as e:
        with print_lock:
            print(f"Error parsing date range: {e}. Using config default.")
        f_dt, t_dt = downloader.get_date_range()

    with print_lock:
        print(f"Fetching {lower_interval} data for {symbol}...")
    df_lower = downloader.historical_fetcher.fetch_historical_data(
        instrument_token=token,
        interval=lower_interval,
        from_date=f_dt,
        to_date=t_dt,
        index_name=symbol.lower()
    )
    
    with print_lock:
        print(f"Fetching {upper_interval} data for {symbol}...")
    df_upper = downloader.historical_fetcher.fetch_historical_data(
        instrument_token=token,
        interval=upper_interval,
        from_date=f_dt,
        to_date=t_dt,
        index_name=symbol.lower()
    )

    if df_lower is None or df_lower.empty or df_upper is None or df_upper.empty:
        with print_lock:
            print(f"Unable to resolve data for {symbol} ({lower_interval}, {upper_interval})")
        return []

    # Reset index to match run_backtest_wrapper expectations if needed
    if 'date' not in df_lower.columns:
        df_lower = df_lower.reset_index()
    if 'date' not in df_upper.columns:
        df_upper = df_upper.reset_index()

    return run_backtest_wrapper(df_lower, df_upper, symbol, lower_interval, upper_interval, options, args.strategy, from_date, to_date)

def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    parser = argparse.ArgumentParser(description='Backtest candlestick patterns on historical data')
    parser.add_argument('--symbol', type=str, help='Symbol (e.g., nifty50, banknifty)')
    parser.add_argument('--lower-interval', type=str, help='Lower Interval (e.g., 5minute)')
    parser.add_argument('--upper-interval', type=str, help='Upper Interval (e.g., 15minute)')
    parser.add_argument('--from-date', type=str, help='From date (YYYYMMDD)')
    parser.add_argument('--to-date', type=str, help='To date (YYYYMMDD)')
    parser.add_argument('--config', type=str, default='config/backtest.yaml', help='Path to backtest config')
    parser.add_argument('--options', type=str, default='config/options.yaml', help='Path to options config')
    parser.add_argument('--strategy', type=str, default='option', choices=['option', 'trend_momentum', 'market_structure'], help='Strategy to use')
    
    args = parser.parse_args()
    
    config = load_config(Path(args.config))
    options = load_config(Path(args.options))
    backtest_config = config.get('backtest', {})
    
    indices_config = options.get('indices', {})
    
    if args.symbol:
        symbol_key = args.symbol.lower()
        if symbol_key not in indices_config or not indices_config[symbol_key].get('enabled', False):
            print(f"Symbol {args.symbol} is not enabled in config. Skipping.")
            return
        symbols_to_run = [args.symbol]
    else:
        symbols_to_run = [s for s, cfg in indices_config.items() if cfg.get('enabled', False)]
        if not symbols_to_run:
            print("No enabled indices found in config.")
            return
    
    all_trades = []
    
    with ThreadPoolExecutor(max_workers=len(symbols_to_run)) as executor:
        future_to_symbol = {executor.submit(process_symbol, symbol, backtest_config, options, indices_config, args): symbol for symbol in symbols_to_run}
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                symbol_trades = future.result()
                if symbol_trades:
                    all_trades.extend(symbol_trades)
            except Exception as exc:
                print(f'{symbol} generated an exception: {exc}')
                import traceback
                traceback.print_exc()
            
    if len(symbols_to_run) > 1:
        display_combined_summary(all_trades)

if __name__ == "__main__":
    main()
