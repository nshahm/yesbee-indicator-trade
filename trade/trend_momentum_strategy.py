from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import candlestick
from candlestick import Candle, is_bullish_engulfing, is_hammer
from indicators import calculate_ema, calculate_rsi, calculate_atr, calculate_supertrend

@dataclass
class Trade:
    option_type: str
    pattern: str
    confirmation: str
    entry_time: str
    entry_price: float
    quantity: int = 0
    rsi: Optional[float] = None
    rsi_upper: Optional[float] = None
    stop_loss: Optional[float] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None

class TrendMomentumStrategy:
    def __init__(self, options: Dict, symbol: str):
        self.options = options
        self.symbol = symbol
        
        # Risk Management from system.md
        risk_config = options.get('risk_management', {})
        self.capital = risk_config.get('capital', 100000)
        self.risk_per_trade_percent = risk_config.get('risk_per_trade', 1.0) / 100.0
        self.max_open_trades = risk_config.get('max_open_trades', 3)
        self.max_trades_per_day = risk_config.get('max_trades_per_day', 0)
        self.max_consecutive_losses_per_day = risk_config.get('max_consecutive_losses_per_day', 0)
        
        self.trading_style = options.get('trading_style', 'intraday')
        
        # Indicator thresholds
        indicator_config = options.get('indicators', {})
        rsi_config = indicator_config.get('rsi', {})
        self.rsi_call_threshold = rsi_config.get('call_threshold', 50)
        self.rsi_put_threshold = rsi_config.get('put_threshold', 50)
        
        # Multipliers from system.md
        if self.trading_style == 'intraday':
            self.sl_multiplier = 1.2
            self.trail_multiplier = 1.0
        else: # swing
            self.sl_multiplier = 2.0 # 1.5 - 2.0 as per system.md
            self.trail_multiplier = 1.5 # 1.0 - 1.5 as per system.md

    def calculate_quantity(self, entry_price: float, stop_loss: float) -> int:
        risk_amount = self.capital * self.risk_per_trade_percent
        price_risk = abs(entry_price - stop_loss)
        if price_risk == 0:
            return 0
        return int(risk_amount / price_risk)

    def df_to_candles(self, df: pd.DataFrame) -> List[Candle]:
        candles = []
        for idx, row in df.iterrows():
            dt = row['date']
            candles.append(Candle(
                date=dt.isoformat() if isinstance(dt, datetime) else str(dt),
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close']
            ))
        return candles

    def is_bullish_pattern(self, candles: List[Candle]) -> bool:
        # Check for common bullish patterns mentioned in system.md
        # Engulfing / Hammer / Pullback (simplified to bullish candle)
        if not candles:
            return False
        
        last_candle = candles[-1]
        # Basic bullish candle
        is_bullish_candle = last_candle.close > last_candle.open
        
        # Check specific patterns
        if is_bullish_engulfing(candles) or is_hammer(candles):
            return True
            
        return is_bullish_candle

    def is_bearish_pattern(self, candles: List[Candle]) -> bool:
        if not candles:
            return False
        
        last_candle = candles[-1]
        is_bearish_candle = last_candle.close < last_candle.open
        
        from candlestick import is_bearish_engulfing, is_shooting_star
        if is_bearish_engulfing(candles) or is_shooting_star(candles):
            return True
            
        return is_bearish_candle

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
            
            # Get latest available upper timeframe data
            upper_data = df_upper_indexed[df_upper_indexed.index <= current_time]
            if upper_data.empty:
                continue
            last_upper = upper_data.iloc[-1]

            if active_trade:
                if active_trade.option_type == 'CALL':
                    # Update highest price for trailing SL
                    highest_price_since_entry = max(highest_price_since_entry, row['high'])
                    
                    # Update Trailing SL
                    trail_sl = highest_price_since_entry - (row['atr'] * self.trail_multiplier)
                    if trail_sl > active_trade.stop_loss:
                        active_trade.stop_loss = trail_sl
                    
                    # Check Exit Conditions
                    exit_reason = None
                    if row['low'] <= active_trade.stop_loss:
                        exit_reason = "SL/TSL Hit"
                        exit_price = active_trade.stop_loss
                    elif row['rsi'] < 40:
                        exit_reason = "RSI Reversal"
                        exit_price = row['close']
                    elif row['close'] < row['ema50']:
                        exit_reason = "Trend Breakdown"
                        exit_price = row['close']
                else: # PUT / SHORT
                    # Update lowest price for trailing SL
                    lowest_price_since_entry = min(lowest_price_since_entry, row['low'])
                    
                    # Update Trailing SL
                    trail_sl = lowest_price_since_entry + (row['atr'] * self.trail_multiplier)
                    if trail_sl < active_trade.stop_loss:
                        active_trade.stop_loss = trail_sl
                    
                    # Check Exit Conditions
                    exit_reason = None
                    if row['high'] >= active_trade.stop_loss:
                        exit_reason = "SL/TSL Hit"
                        exit_price = active_trade.stop_loss
                    elif row['rsi'] > 60: # Bearish RSI reversal
                        exit_reason = "RSI Reversal"
                        exit_price = row['close']
                    elif row['close'] > row['ema50']:
                        exit_reason = "Trend Breakdown"
                        exit_price = row['close']

                # Time-based exit (Intraday only)
                if not exit_reason and self.trading_style == 'intraday' and current_time.hour == 15 and current_time.minute >= 15:
                    exit_reason = "EOD Exit"
                    exit_price = row['close']
                
                if exit_reason:
                    active_trade.exit_time = current_time.isoformat()
                    active_trade.exit_price = exit_price
                    active_trade.pnl = (active_trade.exit_price - active_trade.entry_price) if active_trade.option_type == 'CALL' else (active_trade.entry_price - active_trade.exit_price)
                    completed_trades.append(active_trade)
                    
                    # Update Risk Management: Consecutive Losses
                    if active_trade.pnl < 0:
                        consecutive_losses_today += 1
                    else:
                        consecutive_losses_today = 0
                        
                    active_trade = None
                    continue

            else:
                # Check Risk Management Limits
                can_enter = True
                if self.max_trades_per_day > 0 and trades_today >= self.max_trades_per_day:
                    can_enter = False
                if self.max_consecutive_losses_per_day > 0 and consecutive_losses_today >= self.max_consecutive_losses_per_day:
                    can_enter = False
                
                if not can_enter:
                    continue

                # Check Entry Conditions
                
                # 1. LONG Entry Conditions
                trend_long_ok = (
                    row['close'] > row['ema50'] and 
                    row['ema20'] > row['ema50'] and 
                    row['close'] > row.get('ema200', 0)
                )
                rsi_long_ok = row['rsi'] > self.rsi_call_threshold and row['rsi'] > prev_row['rsi']
                htf_long_ok = (
                    last_upper['close'] > last_upper['ema50'] and 
                    last_upper['close'] > last_upper.get('ema200', 0)
                )
                
                # 2. SHORT Entry Conditions (Optional as per system.md)
                trend_short_ok = (
                    row['close'] < row['ema50'] and 
                    row['ema20'] < row['ema50'] and 
                    row['close'] < row.get('ema200', 999999)
                )
                rsi_short_ok = row['rsi'] < self.rsi_put_threshold and row['rsi'] < prev_row['rsi']
                htf_short_ok = (
                    last_upper['close'] < last_upper['ema50'] and 
                    last_upper['close'] < last_upper.get('ema200', 999999)
                )

                candles_window = self.df_to_candles(df_lower.iloc[i-5:i+1])
                
                if trend_long_ok and rsi_long_ok and htf_long_ok and self.is_bullish_pattern(candles_window):
                    entry_price = row['close']
                    initial_sl = entry_price - (row['atr'] * self.sl_multiplier)
                    quantity = self.calculate_quantity(entry_price, initial_sl)
                    
                    active_trade = Trade(
                        option_type='CALL',
                        pattern='TrendMomentum',
                        confirmation='EMA+RSI+HTF',
                        entry_time=current_time.isoformat(),
                        entry_price=entry_price,
                        quantity=quantity,
                        rsi=row['rsi'],
                        rsi_upper=last_upper['rsi'],
                        stop_loss=initial_sl
                    )
                    trades_today += 1
                    highest_price_since_entry = entry_price
                
                elif trend_short_ok and rsi_short_ok and htf_short_ok and self.is_bearish_pattern(candles_window):
                    entry_price = row['close']
                    initial_sl = entry_price + (row['atr'] * self.sl_multiplier)
                    quantity = self.calculate_quantity(entry_price, initial_sl)
                    
                    active_trade = Trade(
                        option_type='PUT',
                        pattern='TrendMomentum',
                        confirmation='EMA+RSI+HTF',
                        entry_time=current_time.isoformat(),
                        entry_price=entry_price,
                        quantity=quantity,
                        rsi=row['rsi'],
                        rsi_upper=last_upper['rsi'],
                        stop_loss=initial_sl
                    )
                    trades_today += 1
                    lowest_price_since_entry = entry_price
        
        return completed_trades
