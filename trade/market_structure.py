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
        self.reset_state()

    def reset_state(self):
        super().reset_state()
        self.ms = MarketStructure(n=self.options.get('market_structure', {}).get('n', 2))
        self.has_hh = False
        self.has_lh = False
        self.hh_price = None
        self.lh_price = None
        self.hl_price = None
        self.has_ll = False
        self.has_lh_after_ll = False
        self.ll_price = None

    def run_backtest(self, df_lower: pd.DataFrame, df_upper: pd.DataFrame) -> List[Trade]:
        self.reset_state()
        df_upper_indexed = df_upper.set_index('date')
        
        for i in range(50, len(df_lower)):
            row = df_lower.iloc[i]
            prev_row = df_lower.iloc[i-1]
            current_time = row['date']
            
            # Daily Reset for Risk Management
            trade_date = current_time.date()
            if self.current_day != trade_date:
                self.current_day = trade_date
                self.trades_today = 0
                self.consecutive_losses_today = 0
                # Optionally reset pattern state daily
                self.has_hh = False
                self.has_lh = False
                self.has_ll = False
                self.has_lh_after_ll = False
            
            # Update Market Structure
            candles_so_far = self.df_to_candles(df_lower.iloc[:i+1])
            ms_result = self.ms.update(candles_so_far)
            
            if ms_result:
                if ms_result['is_hh']:
                    self.has_hh = True
                    self.has_lh = False # Reset LH when new HH formed
                    self.hh_price = ms_result['hh_price']
                elif ms_result['is_lh']:
                    if self.has_hh:
                        self.has_lh = True
                        self.lh_price = ms_result['lh_price']
                    if self.has_ll:
                        self.has_lh_after_ll = True
                        self.lh_price = ms_result['lh_price']
                
                if ms_result['is_ll']:
                    self.has_ll = True
                    self.has_lh_after_ll = False # Reset LH when new LL formed
                    self.ll_price = ms_result['ll_price']
                
                if ms_result['is_hl']:
                    self.hl_price = ms_result['hl_price']

            # Get latest available upper timeframe data
            upper_data = df_upper_indexed[df_upper_indexed.index <= current_time]
            if upper_data.empty:
                continue
            last_upper = upper_data.iloc[-1]

            if self.active_trade:
                # Reuse exit logic from base class
                if self.active_trade.option_type == 'CALL':
                    self.highest_price_since_entry = max(self.highest_price_since_entry, row['high'])
                    current_profit = row['close'] - self.active_trade.entry_price
                    profit_r = current_profit / self.active_trade.initial_risk if self.active_trade.initial_risk > 0 else 0
                    
                    if self.trailing_enabled:
                        new_sl = self.active_trade.stop_loss
                        # Step Trailing
                        if self.trailing_config.get('step_trailing', {}).get('enabled', False):
                            levels = self.trailing_config['step_trailing'].get('levels', [])
                            for level in levels:
                                if profit_r >= level['profit_r']:
                                    locked_sl = self.active_trade.entry_price + (level['lock_r'] * self.active_trade.initial_risk)
                                    new_sl = max(new_sl, locked_sl) if new_sl is not None else locked_sl
                        
                        # Tighten SL to previous candle low if in profit
                        if row['close'] > self.active_trade.entry_price:
                            new_sl = max(new_sl, prev_row['low']) if new_sl is not None else prev_row['low']
                        
                        self.active_trade.stop_loss = new_sl
                    
                    exit_reason = None
                    if self.active_trade.stop_loss is not None and row['low'] <= self.active_trade.stop_loss:
                        exit_reason = "SL/TSL Hit"
                        exit_price = self.active_trade.stop_loss
                    elif row['rsi'] < 40:
                        exit_reason = "RSI Reversal"
                        exit_price = row['close']
                    
                else: # PUT
                    self.lowest_price_since_entry = min(self.lowest_price_since_entry, row['low'])
                    current_profit = self.active_trade.entry_price - row['close']
                    profit_r = current_profit / self.active_trade.initial_risk if self.active_trade.initial_risk > 0 else 0
                    
                    if self.trailing_enabled:
                        new_sl = self.active_trade.stop_loss
                        if self.trailing_config.get('step_trailing', {}).get('enabled', False):
                            levels = self.trailing_config['step_trailing'].get('levels', [])
                            for level in levels:
                                if profit_r >= level['profit_r']:
                                    locked_sl = self.active_trade.entry_price - (level['lock_r'] * self.active_trade.initial_risk)
                                    new_sl = min(new_sl, locked_sl) if new_sl is not None else locked_sl
                        
                        if row['close'] < self.active_trade.entry_price:
                            new_sl = min(new_sl, prev_row['high']) if new_sl is not None else prev_row['high']
                            
                        self.active_trade.stop_loss = new_sl
                    
                    exit_reason = None
                    if self.active_trade.stop_loss is not None and row['high'] >= self.active_trade.stop_loss:
                        exit_reason = "SL/TSL Hit"
                        exit_price = self.active_trade.stop_loss
                    elif row['rsi'] > 60:
                        exit_reason = "RSI Reversal"
                        exit_price = row['close']

                if not exit_reason and self.trading_style == 'intraday' and current_time.hour == 15 and current_time.minute >= 15:
                    exit_reason = "EOD Exit"
                    exit_price = row['close']
                
                if exit_reason:
                    self.active_trade.exit_time = current_time.isoformat()
                    self.active_trade.exit_price = exit_price
                    self.active_trade.pnl = (self.active_trade.exit_price - self.active_trade.entry_price) if self.active_trade.option_type == 'CALL' else (self.active_trade.entry_price - self.active_trade.exit_price)
                    self.completed_trades.append(self.active_trade)
                    if self.active_trade.pnl < 0:
                        self.consecutive_losses_today += 1
                    else:
                        self.consecutive_losses_today = 0
                    self.active_trade = None
                    continue
            else:
                # Check Risk Management
                if self.max_trades_per_day > 0 and self.trades_today >= self.max_trades_per_day: continue
                if self.max_consecutive_losses_per_day > 0 and self.consecutive_losses_today >= self.max_consecutive_losses_per_day: continue

                # Manual Exit check
                if current_time.isoformat() in self.manual_exits:
                    continue

                # HHLL Logic
                avg_volume = df_lower['volume'].iloc[max(0, i-20):i].mean()
                volume_ok = row['volume'] > avg_volume if not np.isnan(avg_volume) and avg_volume > 0 else True
                
                # ADX Trend Strength Filter
                adx_value = row.get('ADX', 0)
                dmp_value = row.get('DMP', 0)
                dmn_value = row.get('DMN', 0)
                adx_ok = adx_value > self.adx_threshold if self.adx_enabled else True
                dx_ok_call = dmp_value > dmn_value if self.adx_enabled and self.dx_enabled else True
                dx_ok_put = dmn_value > dmp_value if self.adx_enabled and self.dx_enabled else True

                # 1. PUT Trade: HH -> LH -> Breakdown (Close < HL)
                if self.has_hh and self.has_lh and self.hl_price is not None:
                    if row['close'] < self.hl_price:
                        # MTF RSI Confirmation
                        rsi_upper = last_upper.get('rsi')
                        neutral_rsi = self.options.get('indicators', {}).get('rsi', {}).get('neutral_threshold', 50)
                        rsi_ok = row['rsi'] <= self.rsi_put_threshold
                        htf_rsi_ok = rsi_upper <= neutral_rsi if rsi_upper is not None else True
                        
                        if rsi_ok and htf_rsi_ok and row['close'] < row[f'ema{self.short_ema}'] and volume_ok and adx_ok and dx_ok_put:
                            self.active_trade = Trade(
                                option_type='PUT',
                                pattern='HH-LH-Breakdown',
                                confirmation='RSI+MTF',
                                entry_time=current_time.isoformat(),
                                entry_price=row['close'],
                                rsi=row['rsi'],
                                rsi_upper=rsi_upper,
                                adx=adx_value,
                                stop_loss=self.lh_price + (row['atr'] * 0.3) if self.lh_price else None,
                                initial_risk=self._get_initial_risk(row['atr'])
                            )
                            # Reset pattern state after entry
                            self.has_hh = False
                            self.has_lh = False
                            self.lowest_price_since_entry = row['low']
                            self.trades_today += 1
                            continue

                # 2. CALL Trade: LL -> LH -> Breakout (Close > LH)
                if self.has_ll and self.has_lh_after_ll and self.lh_price is not None:
                    if row['close'] > self.lh_price:
                        # MTF RSI Confirmation
                        rsi_upper = last_upper.get('rsi')
                        neutral_rsi = self.options.get('indicators', {}).get('rsi', {}).get('neutral_threshold', 50)
                        rsi_ok = row['rsi'] >= self.rsi_call_threshold
                        htf_rsi_ok = rsi_upper >= neutral_rsi if rsi_upper is not None else True

                        if rsi_ok and htf_rsi_ok and row['close'] > row[f'ema{self.short_ema}'] and volume_ok and adx_ok and dx_ok_call:
                            self.active_trade = Trade(
                                option_type='CALL',
                                pattern='LL-LH-Breakout',
                                confirmation='RSI+MTF',
                                entry_time=current_time.isoformat(),
                                entry_price=row['close'],
                                rsi=row['rsi'],
                                rsi_upper=rsi_upper,
                                adx=adx_value,
                                stop_loss=self.ll_price - (row['atr'] * 0.3) if self.ll_price else None,
                                initial_risk=self._get_initial_risk(row['atr'])
                            )
                            self.has_ll = False
                            self.highest_price_since_entry = row['high']
                            self.trades_today += 1
                            continue

        return self.completed_trades
