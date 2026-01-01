from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
from .trend_momentum_strategy import TrendMomentumStrategy, Trade
from indicators import MarketStructure, calculate_atr, calculate_rsi
from candlestick import Candle

class MarketStructureStrategy(TrendMomentumStrategy):
    def __init__(self, options: Dict, symbol: str):
        super().__init__(options, symbol)
        self.ms = MarketStructure(n=options.get('market_structure', {}).get('n', 2))
        
    def run_backtest(self, df_lower: pd.DataFrame, df_upper: pd.DataFrame) -> List[Trade]:
        completed_trades: List[Trade] = []
        active_trade: Optional[Trade] = None
        highest_price_since_entry = 0.0
        lowest_price_since_entry = 0.0
        
        # Risk Management Tracking
        trades_today = 0
        consecutive_losses_today = 0
        current_day = None
        
        df_upper_indexed = df_upper.set_index('date')
        
        # Reset Market Structure
        self.ms = MarketStructure(n=self.options.get('market_structure', {}).get('n', 2))
        
        # State for HHLL patterns
        has_hh = False
        has_lh = False
        hh_price = None
        lh_price = None
        hl_price = None
        
        has_ll = False
        ll_price = None

        for i in range(50, len(df_lower)):
            row = df_lower.iloc[i]
            prev_row = df_lower.iloc[i-1]
            current_time = row['date']
            
            # Daily Reset for Risk Management
            trade_date = current_time.date()
            if current_day != trade_date:
                current_day = trade_date
                trades_today = 0
                consecutive_losses_today = 0
                # Optionally reset pattern state daily
                has_hh = False
                has_lh = False
                has_ll = False
            
            # Update Market Structure
            candles_so_far = self.df_to_candles(df_lower.iloc[:i+1])
            ms_result = self.ms.update(candles_so_far)
            
            if ms_result:
                if ms_result['is_hh']:
                    has_hh = True
                    has_lh = False # Reset LH when new HH formed
                    hh_price = ms_result['hh_price']
                elif ms_result['is_lh']:
                    if has_hh:
                        has_lh = True
                        lh_price = ms_result['lh_price']
                
                if ms_result['is_ll']:
                    has_ll = True
                    ll_price = ms_result['ll_price']
                
                if ms_result['is_hl']:
                    hl_price = ms_result['hl_price']

            # Get latest available upper timeframe data
            upper_data = df_upper_indexed[df_upper_indexed.index <= current_time]
            if upper_data.empty:
                continue
            last_upper = upper_data.iloc[-1]

            if active_trade:
                # Reuse exit logic from base class
                # (Copied from TrendMomentumStrategy because it's tightly coupled in run_backtest)
                if active_trade.option_type == 'CALL':
                    highest_price_since_entry = max(highest_price_since_entry, row['high'])
                    current_profit = row['close'] - active_trade.entry_price
                    profit_r = current_profit / active_trade.initial_risk if active_trade.initial_risk > 0 else 0
                    
                    if self.trailing_enabled:
                        new_sl = active_trade.stop_loss
                        # Step Trailing
                        if self.trailing_config.get('step_trailing', {}).get('enabled', False):
                            levels = self.trailing_config['step_trailing'].get('levels', [])
                            for level in levels:
                                if profit_r >= level['profit_r']:
                                    locked_sl = active_trade.entry_price + (level['lock_r'] * active_trade.initial_risk)
                                    new_sl = max(new_sl, locked_sl) if new_sl is not None else locked_sl
                        
                        # Tighten SL to previous candle low if in profit
                        if row['close'] > active_trade.entry_price:
                            new_sl = max(new_sl, prev_row['low']) if new_sl is not None else prev_row['low']
                        
                        active_trade.stop_loss = new_sl
                    
                    exit_reason = None
                    if active_trade.stop_loss is not None and row['low'] <= active_trade.stop_loss:
                        exit_reason = "SL/TSL Hit"
                        exit_price = active_trade.stop_loss
                    elif row['rsi'] < 40:
                        exit_reason = "RSI Reversal"
                        exit_price = row['close']
                    
                else: # PUT
                    lowest_price_since_entry = min(lowest_price_since_entry, row['low'])
                    current_profit = active_trade.entry_price - row['close']
                    profit_r = current_profit / active_trade.initial_risk if active_trade.initial_risk > 0 else 0
                    
                    if self.trailing_enabled:
                        new_sl = active_trade.stop_loss
                        if self.trailing_config.get('step_trailing', {}).get('enabled', False):
                            levels = self.trailing_config['step_trailing'].get('levels', [])
                            for level in levels:
                                if profit_r >= level['profit_r']:
                                    locked_sl = active_trade.entry_price - (level['lock_r'] * active_trade.initial_risk)
                                    new_sl = min(new_sl, locked_sl) if new_sl is not None else locked_sl
                        
                        if row['close'] < active_trade.entry_price:
                            new_sl = min(new_sl, prev_row['high']) if new_sl is not None else prev_row['high']
                            
                        active_trade.stop_loss = new_sl
                    
                    exit_reason = None
                    if active_trade.stop_loss is not None and row['high'] >= active_trade.stop_loss:
                        exit_reason = "SL/TSL Hit"
                        exit_price = active_trade.stop_loss
                    elif row['rsi'] > 60:
                        exit_reason = "RSI Reversal"
                        exit_price = row['close']

                if not exit_reason and self.trading_style == 'intraday' and current_time.hour == 15 and current_time.minute >= 15:
                    exit_reason = "EOD Exit"
                    exit_price = row['close']
                
                if exit_reason:
                    active_trade.exit_time = current_time.isoformat()
                    active_trade.exit_price = exit_price
                    active_trade.pnl = (active_trade.exit_price - active_trade.entry_price) if active_trade.option_type == 'CALL' else (active_trade.entry_price - active_trade.exit_price)
                    completed_trades.append(active_trade)
                    if active_trade.pnl < 0:
                        consecutive_losses_today += 1
                    else:
                        consecutive_losses_today = 0
                    active_trade = None
                    continue
            else:
                # Check Risk Management
                if self.max_trades_per_day > 0 and trades_today >= self.max_trades_per_day: continue
                if self.max_consecutive_losses_per_day > 0 and consecutive_losses_today >= self.max_consecutive_losses_per_day: continue

                # HHLL Logic
                avg_volume = df_lower['volume'].iloc[max(0, i-20):i].mean()
                volume_ok = row['volume'] > avg_volume if not np.isnan(avg_volume) and avg_volume > 0 else True
                
                # 1. PUT Trade: HH -> LH -> Breakdown (Close < HL)
                if has_hh and has_lh and hl_price is not None:
                    if row['close'] < hl_price:
                        # Extra conditions from hhll.md
                        if row['rsi'] < 50 and row['close'] < row['ema20'] and volume_ok:
                            active_trade = Trade(
                                option_type='PUT',
                                pattern='HH-LH-Breakdown',
                                confirmation='RSI < 50',
                                entry_time=current_time.isoformat(),
                                entry_price=row['close'],
                                rsi=row['rsi'],
                                stop_loss=lh_price + (row['atr'] * 0.3) if lh_price else None,
                                initial_risk=self._get_initial_risk(row['atr'])
                            )
                            # Reset pattern state after entry
                            has_hh = False
                            has_lh = False
                            lowest_price_since_entry = row['low']
                            trades_today += 1
                            continue

                # 2. CALL Trade: LL -> LH -> Breakout (Close > LH)
                if has_ll and ms_result.get('lh_price') is not None:
                    lh_val = ms_result['lh_price']
                    if row['close'] > lh_val:
                        if row['rsi'] > 50 and row['close'] > row['ema20'] and volume_ok:
                            active_trade = Trade(
                                option_type='CALL',
                                pattern='LL-LH-Breakout',
                                confirmation='RSI > 50',
                                entry_time=current_time.isoformat(),
                                entry_price=row['close'],
                                rsi=row['rsi'],
                                stop_loss=ll_price - (row['atr'] * 0.3) if ll_price else None,
                                initial_risk=self._get_initial_risk(row['atr'])
                            )
                            has_ll = False
                            highest_price_since_entry = row['high']
                            trades_today += 1
                            continue

        return completed_trades
