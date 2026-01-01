from typing import Dict, List, Optional, Union
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
import candlestick
from candlestick import Candle
from candlestick.bullish import __all__ as bullish_patterns
from candlestick.bearish import __all__ as bearish_patterns
from candlestick.neutral import __all__ as neutral_patterns

@dataclass
class Trade:
    option_type: str
    pattern: str
    confirmation: str
    entry_time: str
    entry_price: float
    symbol: Optional[str] = None
    rsi: Optional[float] = None
    rsi_upper: Optional[float] = None
    stop_loss: Optional[float] = None
    initial_risk: Optional[float] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None

class OptionSignal:
    def __init__(self, action: str, option_type: str, pattern: str, rsi_value: Optional[float] = None, rsi_upper: Optional[float] = None, confirmation: str = "N/A"):
        self.action = action  # 'ENTRY' or 'EXIT'
        self.option_type = option_type  # 'CALL' or 'PUT'
        self.pattern = pattern
        self.rsi_value = rsi_value
        self.rsi_upper = rsi_upper
        self.confirmation = confirmation

    def __repr__(self):
        rsi_str = f", RSI: {self.rsi_value:.2f}" if self.rsi_value is not None else ""
        rsi_u_str = f", RSI_U: {self.rsi_upper:.2f}" if self.rsi_upper is not None else ""
        return f"{self.action} {self.option_type} (Pattern: {self.pattern}, Conf: {self.confirmation}{rsi_str}{rsi_u_str})"

PATTERN_CONFIRMATIONS = {
    # Single
    'is_hammer': 'Single',
    'is_inverted_hammer': 'Single',
    'is_dragonfly_doji': 'Single',
    'is_bullish_spinning_top': 'Single',
    'is_hanging_man': 'Single',
    'is_shooting_star': 'Single',
    'is_gravestone_doji': 'Single',
    'is_bearish_spinning_top': 'Single',
    'is_spinning_top': 'Single',
    'is_doji': 'Single',
    'is_marubozu': 'Single',
    # Double
    'is_bullish_kicker': 'Double',
    'is_bullish_engulfing': 'Double',
    'is_piercing_line': 'Double',
    'is_bullish_harami': 'Double',
    'is_tweezer_bottom': 'Double',
    'is_bearish_engulfing': 'Double',
    'is_bearish_kicker': 'Double',
    'is_dark_cloud_cover': 'Double',
    'is_bearish_harami': 'Double',
    'is_tweezer_top': 'Double',
    'is_harami': 'Double',
    # Triple
    'is_morning_doji_star': 'Triple',
    'is_three_white_soldiers': 'Triple',
    'is_morning_star': 'Triple',
    'is_evening_doji_star': 'Triple',
    'is_three_black_crows': 'Triple',
    'is_evening_star': 'Triple',
    'is_bullish_engulfing_sandwich': 'Triple',
    'is_bullish_abandoned_baby': 'Triple',
    'is_bearish_engulfing_sandwich': 'Triple',
    'is_bearish_abandoned_baby': 'Triple',
    'is_rising_three': 'Triple',
    'is_falling_three': 'Triple'
}

def df_to_candles(df: pd.DataFrame) -> List[Candle]:
    candles = []
    for idx, row in df.iterrows():
        if 'date' in row:
            dt = row['date']
        else:
            dt = idx
        
        candles.append(Candle(
            date=dt.isoformat() if isinstance(dt, datetime) else str(dt),
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close']
        ))
    return candles

def get_pattern_category(window_df: pd.DataFrame, patterns: Dict) -> Optional[str]:
    if len(window_df) < 5:
        return None
    candles = df_to_candles(window_df)
    for category, pats in patterns.items():
        for pattern_func in pats:
            if pattern_func(candles):
                return category
    return None

def get_option_signals(
    category: str, 
    pattern_name: str, 
    upper_category: Optional[str] = None, 
    current_position: Optional[str] = None,
    rsi_value: Optional[float] = None,
    rsi_upper: Optional[float] = None,
    rsi_config: Optional[Dict] = None,
    df: Optional[pd.DataFrame] = None,
    index: Optional[int] = None
) -> List[OptionSignal]:
    """
    Generates entry and exit signals based on candlestick pattern category.
    Strict MTF: Entry only if upper_category matches lower timeframe trend.
    """
    signals = []
    
    # Use value from DataFrame if provided and rsi_value is None
    if rsi_value is None and df is not None and index is not None and 'rsi' in df.columns:
        rsi_value = df.iloc[index]['rsi']
    
    confirmation = PATTERN_CONFIRMATIONS.get(pattern_name, "N/A")
    
    # 1. ENTRY LOGIC (Only if no active position)
    if current_position is None:
        # Check RSI thresholds
        rsi_call_ok = True
        rsi_put_ok = True
        
        if rsi_config:
            call_thresh = rsi_config.get('call_threshold')
            call_upper_thresh = rsi_config.get('call_upper_threshold')
            put_thresh = rsi_config.get('put_threshold')
            put_lower_thresh = rsi_config.get('put_lower_threshold')
            
            # Lower timeframe RSI checks
            if rsi_value is not None:
                if call_thresh is not None:
                    rsi_call_ok = rsi_value >= call_thresh
                if call_upper_thresh is not None:
                    rsi_call_ok = rsi_call_ok and rsi_value <= call_upper_thresh
                    
                if put_thresh is not None:
                    rsi_put_ok = rsi_value <= put_thresh
                if put_lower_thresh is not None:
                    rsi_put_ok = rsi_put_ok and rsi_value >= put_lower_thresh
            
            # Upper timeframe RSI checks (Optional alignment)
            if rsi_upper is not None:
                neutral_rsi = rsi_config.get('neutral_threshold', 50)
                if call_thresh is not None:
                    rsi_call_ok = rsi_call_ok and (rsi_upper >= neutral_rsi) # Basic trend confirmation
                if put_thresh is not None:
                    rsi_put_ok = rsi_put_ok and (rsi_upper <= neutral_rsi)

        # STRICT MTF: Only enter if upper timeframe confirms trend
        if upper_category:
            if category == 'Bullish' and upper_category == 'Bullish':
                if rsi_call_ok:
                    signals.append(OptionSignal('ENTRY', 'CALL', pattern_name, rsi_value, rsi_upper, confirmation))
            elif category == 'Bearish' and upper_category == 'Bearish':
                if rsi_put_ok:
                    signals.append(OptionSignal('ENTRY', 'PUT', pattern_name, rsi_value, rsi_upper, confirmation))
        # No entry if upper_category is not available (Strict MTF)
            
    # 2. EXIT LOGIC (Reversal patterns)
    # Only exit on strong patterns (Triple) OR if MTF trend is no longer aligned
    is_strong_pattern = confirmation == 'Triple'
    neutral_rsi = rsi_config.get('neutral_threshold', 50) if rsi_config else 50
    
    # Check if MTF trend is still aligned
    mtf_aligned = False
    if current_position == 'CALL' and upper_category == 'Bullish':
        mtf_aligned = True
    elif current_position == 'PUT' and upper_category == 'Bearish':
        mtf_aligned = True

    if current_position == 'CALL' and category == 'Bearish':
        # Exit if it's a strong reversal OR if upper timeframe is no longer bullish and RSI confirms
        if is_strong_pattern or (not mtf_aligned and (rsi_value is not None and rsi_value < neutral_rsi)):
            signals.append(OptionSignal('EXIT', 'CALL', pattern_name, rsi_value, rsi_upper, confirmation))
    elif current_position == 'PUT' and category == 'Bullish':
        if is_strong_pattern or (not mtf_aligned and (rsi_value is not None and rsi_value > neutral_rsi)):
            signals.append(OptionSignal('EXIT', 'PUT', pattern_name, rsi_value, rsi_upper, confirmation))

    # 3. Multi-timeframe Trend Change Exits
    # Only exit on actual trend reversal in MTF, not just Neutral
    if upper_category and current_position:
        if current_position == 'CALL' and upper_category == 'Bearish':
            signals.append(OptionSignal('EXIT', 'CALL', 'MTF_REVERSAL', rsi_value, rsi_upper, confirmation))
        elif current_position == 'PUT' and upper_category == 'Bullish':
            signals.append(OptionSignal('EXIT', 'PUT', 'MTF_REVERSAL', rsi_value, rsi_upper, confirmation))
        
    return signals

class OptionStrategy:
    def __init__(self, options: Dict, symbol: str):
        self.options = options
        self.symbol = symbol
        self.rsi_config = options.get('indicators', {}).get('rsi', {})
        self.atr_config = options.get('indicators', {}).get('atr', {})
        self.macd_config = options.get('indicators', {}).get('macd', {})
        self.stoch_config = options.get('indicators', {}).get('stochastic', {})
        self.pattern_config = options.get('patterns', {})
        self.trading_hours = options.get('trading_hours', {})
        index_config = options.get('indices', {}).get(symbol.lower(), {})
        self.max_concurrent_trades = index_config.get('max_concurrent_trades', 1)
        
        # Risk management from index config, fallback to global
        self.risk_management = index_config.get('risk_management', options.get('risk_management', {}))
        self.max_trades_per_day = self.risk_management.get('max_trades_per_day', 0)
        self.max_consecutive_losses_per_day = self.risk_management.get('max_consecutive_losses_per_day', 0)
        self.sl_config = self.risk_management.get('stop_loss', {})
        self.trailing_config = self.risk_management.get('trailing', {})
        self.sl_enabled = self.sl_config.get('enabled', True)
        self.atr_sl_config = self.sl_config.get('atr', {})
        self.fixed_sl_config = self.sl_config.get('fixed', {})
        self.trailing_enabled = self.trailing_config.get('enabled', True)
        
        self.patterns = self._get_enabled_patterns()
        
    def _get_initial_risk(self, current_atr: float) -> float:
        risks = []
        if self.atr_sl_config.get('enabled', True):
            multiplier = self.atr_sl_config.get('multiplier', 1.5)
            risks.append(multiplier * (current_atr if not pd.isna(current_atr) else 0))
        
        if self.fixed_sl_config.get('enabled', False):
            risks.append(self.fixed_sl_config.get('points', 0))
            
        if not risks:
            # Fallback to ATR if nothing is enabled but sl is enabled
            return 1.5 * (current_atr if not pd.isna(current_atr) else 0)
            
        # Use the tighter stop (minimum risk) if both are enabled
        return min(r for r in risks if r > 0) or 0
        
    def _get_enabled_patterns(self) -> Dict:
        def is_enabled(p_name, category):
            cat_config = self.pattern_config.get(category.lower(), {})
            return cat_config.get(p_name, False)

        return {
            'Bullish': [getattr(candlestick, p) for p in bullish_patterns if is_enabled(p, 'Bullish')],
            'Bearish': [getattr(candlestick, p) for p in bearish_patterns if is_enabled(p, 'Bearish')],
            'Neutral': [getattr(candlestick, p) for p in neutral_patterns if is_enabled(p, 'Neutral')]
        }

    def run_backtest(self, df_lower: pd.DataFrame, df_upper: pd.DataFrame) -> List[Trade]:
        if df_lower.empty or df_upper.empty:
            return []
            
        active_trades = {'CALL': None, 'PUT': None}
        completed_trades: List[Trade] = []
        last_exit_time: Optional[datetime] = None
        highest_price_since_entry = {'CALL': 0.0, 'PUT': 0.0}
        lowest_price_since_entry = {'CALL': 0.0, 'PUT': 0.0}
        
        # Risk Management Tracking
        trades_today = 0
        consecutive_losses_today = 0
        current_day = None
        
        df_upper_indexed = df_upper.set_index('date')

        def get_last_upper_window(lower_date: datetime) -> pd.DataFrame:
            relevant_upper = df_upper_indexed[df_upper_indexed.index <= lower_date]
            return relevant_upper.tail(5)

        for i in range(5, len(df_lower) + 1):
            window_df_lower = df_lower.iloc[i-5:i]
            current_row_lower = df_lower.iloc[i-1]
            prev_row_lower = df_lower.iloc[i-2] if i > 1 else None
            
            current_rsi = current_row_lower.get('rsi')
            current_atr = current_row_lower.get('atr')
            previous_rsi = prev_row_lower.get('rsi') if prev_row_lower is not None else None
            current_time = current_row_lower['date']
            
            # Double Cross Indicators
            f, s, sig = self.macd_config.get('fast', 12), self.macd_config.get('slow', 26), self.macd_config.get('signal', 9)
            k, d, sk = self.stoch_config.get('k', 14), self.stoch_config.get('d', 3), self.stoch_config.get('smooth_k', 3)
            
            macd_col = f"MACD_{f}_{s}_{sig}"
            hist_col = f"MACDh_{f}_{s}_{sig}"
            sig_col = f"MACDs_{f}_{s}_{sig}"
            stoch_k_col = f"STOCHk_{k}_{d}_{sk}"
            stoch_d_col = f"STOCHd_{k}_{d}_{sk}"
            
            curr_macd_h = current_row_lower.get(hist_col)
            curr_stoch_k = current_row_lower.get(stoch_k_col)
            curr_stoch_d = current_row_lower.get(stoch_d_col)
            
            prev_stoch_k = prev_row_lower.get(stoch_k_col) if prev_row_lower is not None else None
            prev_stoch_d = prev_row_lower.get(stoch_d_col) if prev_row_lower is not None else None
            
            # Double Cross Signal Logic
            double_cross_signal = None
            if self.macd_config.get('enabled', True) and self.stoch_config.get('enabled', True):
                oversold = self.stoch_config.get('oversold', 20)
                overbought = self.stoch_config.get('overbought', 80)
                
                if prev_stoch_k is not None and prev_stoch_d is not None and \
                   curr_stoch_k is not None and curr_stoch_d is not None and curr_macd_h is not None:
                    
                    # Bullish Cross: %K crosses above %D below oversold level AND MACD Histogram > 0
                    if prev_stoch_k < prev_stoch_d and curr_stoch_k > curr_stoch_d and \
                       curr_stoch_k < oversold and curr_macd_h > 0:
                        double_cross_signal = 'CALL'
                    
                    # Bearish Cross: %K crosses below %D above overbought level AND MACD Histogram < 0
                    elif prev_stoch_k > prev_stoch_d and curr_stoch_k < curr_stoch_d and \
                         curr_stoch_k > overbought and curr_macd_h < 0:
                        double_cross_signal = 'PUT'

            # Daily Reset for Risk Management
            trade_date = current_time.date()
            if current_day != trade_date:
                current_day = trade_date
                trades_today = 0
                consecutive_losses_today = 0
            
            # Trading Hours Check
            is_within_hours = True
            force_session_exit = False
            if self.trading_hours:
                start_str = self.trading_hours.get('start_time', '09:15')
                end_str = self.trading_hours.get('end_time', '15:30')
                
                # Create time objects for comparison
                start_time_obj = datetime.strptime(start_str, '%H:%M').time()
                end_time_obj = datetime.strptime(end_str, '%H:%M').time()
                current_time_only = current_time.time()
                
                if current_time_only < start_time_obj:
                    is_within_hours = False
                if current_time_only >= end_time_obj:
                    is_within_hours = False
                    force_session_exit = True

            if pd.isna(current_rsi) or pd.isna(previous_rsi):
                continue
            
            # RSI Trend Signal
            rsi_trend_signal = None
            call_thresh = self.rsi_config.get('call_threshold', 60)
            call_upper_thresh = self.rsi_config.get('call_upper_threshold', 80)
            put_thresh = self.rsi_config.get('put_threshold', 40)
            put_lower_thresh = self.rsi_config.get('put_lower_threshold', 20)
            
            if current_rsi > previous_rsi and call_thresh <= current_rsi <= call_upper_thresh:
                rsi_trend_signal = 'CALL'
            elif current_rsi < previous_rsi and put_lower_thresh <= current_rsi <= put_thresh:
                rsi_trend_signal = 'PUT'
            
            window_df_upper = get_last_upper_window(current_time)
            if len(window_df_upper) < 5:
                continue
                
            upper_category = get_pattern_category(window_df_upper, self.patterns)
            current_rsi_upper = window_df_upper.iloc[-1].get('rsi')
            candles_lower = df_to_candles(window_df_lower)

            # Handle EXITS
            current_pos = 'CALL' if active_trades['CALL'] else 'PUT' if active_trades['PUT'] else None
            
            # 1. Check Stop Loss and Force Session Exit
            if current_pos:
                trade = active_trades[current_pos]
                is_exit_triggered = False
                exit_price = current_row_lower['close']

                # Trailing Stop Loss Logic from stoploss.md
                if self.trailing_enabled:
                    if current_pos == 'CALL':
                        highest_price_since_entry['CALL'] = max(highest_price_since_entry['CALL'], current_row_lower['high'])
                        current_profit = current_row_lower['close'] - trade.entry_price
                        profit_r = current_profit / trade.initial_risk if trade.initial_risk > 0 else 0
                        
                        new_sl = trade.stop_loss
                        
                        # 1. Step Trailing
                        if self.trailing_config.get('step_trailing', {}).get('enabled', False):
                            levels = self.trailing_config['step_trailing'].get('levels', [])
                            for level in levels:
                                if profit_r >= level['profit_r']:
                                    locked_sl = trade.entry_price + (level['lock_r'] * trade.initial_risk)
                                    if new_sl is None:
                                        new_sl = locked_sl
                                    else:
                                        new_sl = max(new_sl, locked_sl)
                        
                        # 2. Candle-based trailing (Original requirement)
                        if i > 2:
                            prev_row = df_lower.iloc[i-2]
                            if current_row_lower['close'] > trade.entry_price:
                                if new_sl is None:
                                    new_sl = prev_row['low']
                                else:
                                    new_sl = max(new_sl, prev_row['low'])
                        
                        # 3. ATR-based trailing (Universal Setup)
                        activation_r = self.trailing_config.get('activation_r', 1.8)
                        if profit_r >= activation_r:
                            trail_multiplier = self.trailing_config.get('multiplier', 1.2)
                            atr_trail = highest_price_since_entry['CALL'] - (current_atr * trail_multiplier)
                            if new_sl is None:
                                new_sl = atr_trail
                            else:
                                new_sl = max(new_sl, atr_trail)
                        
                        trade.stop_loss = new_sl

                    else: # PUT
                        lowest_price_since_entry['PUT'] = min(lowest_price_since_entry['PUT'], current_row_lower['low'])
                        current_profit = trade.entry_price - current_row_lower['close']
                        profit_r = current_profit / trade.initial_risk if trade.initial_risk > 0 else 0
                        
                        new_sl = trade.stop_loss
                        
                        # 1. Step Trailing
                        if self.trailing_config.get('step_trailing', {}).get('enabled', False):
                            levels = self.trailing_config['step_trailing'].get('levels', [])
                            for level in levels:
                                if profit_r >= level['profit_r']:
                                    locked_sl = trade.entry_price - (level['lock_r'] * trade.initial_risk)
                                    if new_sl is None:
                                        new_sl = locked_sl
                                    else:
                                        new_sl = min(new_sl, locked_sl)
                        
                        # 2. Candle-based trailing
                        if i > 2:
                            prev_row = df_lower.iloc[i-2]
                            if current_row_lower['close'] < trade.entry_price:
                                if new_sl is None:
                                    new_sl = prev_row['high']
                                else:
                                    new_sl = min(new_sl, prev_row['high'])
                                
                        # 3. ATR-based trailing
                        activation_r = self.trailing_config.get('activation_r', 1.8)
                        if profit_r >= activation_r:
                            trail_multiplier = self.trailing_config.get('multiplier', 1.2)
                            atr_trail = lowest_price_since_entry['PUT'] + (current_atr * trail_multiplier)
                            if new_sl is None:
                                new_sl = atr_trail
                            else:
                                new_sl = min(new_sl, atr_trail)
                        
                        trade.stop_loss = new_sl

                # Check Stop Loss (Prioritized over session exit)
                if trade.stop_loss is not None:
                    if current_pos == 'CALL':
                        if current_row_lower['low'] <= trade.stop_loss:
                            is_exit_triggered = True
                            exit_price = trade.stop_loss
                    else: # PUT
                        if current_row_lower['high'] >= trade.stop_loss:
                            is_exit_triggered = True
                            exit_price = trade.stop_loss

                # Force Session Exit (if SL not hit)
                if not is_exit_triggered and force_session_exit:
                    is_exit_triggered = True
                    exit_price = current_row_lower['close']
                
                if is_exit_triggered:
                    trade.exit_time = current_row_lower['date'].isoformat()
                    trade.exit_price = exit_price
                    completed_trades.append(trade)
                    
                    # Update Risk Management: Consecutive Losses
                    is_loss = (trade.option_type == 'CALL' and trade.exit_price < trade.entry_price) or \
                              (trade.option_type == 'PUT' and trade.exit_price > trade.entry_price)
                    if is_loss:
                        consecutive_losses_today += 1
                    else:
                        consecutive_losses_today = 0
                        
                    active_trades[current_pos] = None
                    last_exit_time = current_time
                    current_pos = None

            # 2. Exit if RSI trend REVERSES or Double Cross Reversal
            if current_pos:
                is_reversal = (rsi_trend_signal and rsi_trend_signal != current_pos) or \
                              (double_cross_signal and double_cross_signal != current_pos)
                
                # Exit if stochastic exits extreme zone (Double Cross Exit)
                stoch_exit = False
                if self.stoch_config.get('enabled', True):
                    if current_pos == 'CALL' and curr_stoch_k > 70: # Standard exit for long
                         stoch_exit = True
                    elif current_pos == 'PUT' and curr_stoch_k < 30: # Standard exit for short
                         stoch_exit = True

                if is_reversal or stoch_exit:
                    # MTF Check for reversal
                    mtf_aligned = (current_pos == 'CALL' and upper_category == 'Bullish') or \
                                  (current_pos == 'PUT' and upper_category == 'Bearish')
                    
                    # Only exit if MTF is not aligned OR if the reversal signal is strong
                    if not mtf_aligned or stoch_exit:
                        trade = active_trades[current_pos]
                        if trade:
                            trade.exit_time = current_row_lower['date'].isoformat()
                            trade.exit_price = current_row_lower['close']
                            completed_trades.append(trade)
                            
                            # Update Risk Management: Consecutive Losses
                            is_loss = (trade.option_type == 'CALL' and trade.exit_price < trade.entry_price) or \
                                      (trade.option_type == 'PUT' and trade.exit_price > trade.entry_price)
                            if is_loss:
                                consecutive_losses_today += 1
                            else:
                                consecutive_losses_today = 0
                                
                            active_trades[current_pos] = None
                            last_exit_time = current_time
                            current_pos = None

            # 3. Exit based on patterns and UTF trend
            if current_pos:
                # Check for lower timeframe reversal patterns
                found_exit = False
                for category_lower, pats in self.patterns.items():
                    if found_exit: break
                    for pattern_func in pats:
                        if pattern_func(candles_lower):
                            pattern_name = pattern_func.__name__
                            signals = get_option_signals(
                                category_lower, 
                                pattern_name, 
                                upper_category, 
                                current_position=current_pos,
                                rsi_value=current_rsi,
                                rsi_upper=current_rsi_upper,
                                rsi_config=self.rsi_config,
                                df=df_lower,
                                index=i-1
                            )
                            
                            for signal in signals:
                                if signal.action == 'EXIT':
                                    trade = active_trades[signal.option_type]
                                    if trade:
                                        trade.exit_time = current_row_lower['date'].isoformat()
                                        trade.exit_price = current_row_lower['close']
                                        completed_trades.append(trade)
                                        
                                        # Update Risk Management: Consecutive Losses
                                        is_loss = (trade.option_type == 'CALL' and trade.exit_price < trade.entry_price) or \
                                                  (trade.option_type == 'PUT' and trade.exit_price > trade.entry_price)
                                        if is_loss:
                                            consecutive_losses_today += 1
                                        else:
                                            consecutive_losses_today = 0
                                            
                                        active_trades[signal.option_type] = None
                                        last_exit_time = current_time
                                        current_pos = None
                                        found_exit = True
                                        break
                        if found_exit: break

                # If no pattern exit, check for UTF trend change exit
                if current_pos:
                    utf_exit_signals = get_option_signals(
                        'Neutral', 
                        'UTF_TREND_CHANGE', 
                        upper_category, 
                        current_position=current_pos,
                        rsi_value=current_rsi,
                        rsi_upper=current_rsi_upper,
                        rsi_config=self.rsi_config
                    )
                    for signal in utf_exit_signals:
                        if signal.action == 'EXIT':
                            trade = active_trades[signal.option_type]
                            if trade:
                                trade.exit_time = current_row_lower['date'].isoformat()
                                trade.exit_price = current_row_lower['close']
                                completed_trades.append(trade)
                                
                                # Update Risk Management: Consecutive Losses
                                is_loss = (trade.option_type == 'CALL' and trade.exit_price < trade.entry_price) or \
                                          (trade.option_type == 'PUT' and trade.exit_price > trade.entry_price)
                                if is_loss:
                                    consecutive_losses_today += 1
                                else:
                                    consecutive_losses_today = 0
                                    
                                active_trades[signal.option_type] = None
                                last_exit_time = current_time
                                current_pos = None
                                break

            # Handle ENTRIES
            can_enter = is_within_hours
            if last_exit_time:
                diff = (current_time - last_exit_time).total_seconds()
                if diff < 60:
                    can_enter = False
            
            # Risk Management Checks
            if self.max_trades_per_day > 0 and trades_today >= self.max_trades_per_day:
                can_enter = False
            if self.max_consecutive_losses_per_day > 0 and consecutive_losses_today >= self.max_consecutive_losses_per_day:
                can_enter = False

            if can_enter:
                current_active_count = sum(1 for t in active_trades.values() if t is not None)
                if current_active_count < self.max_concurrent_trades:
                    current_pos = 'CALL' if active_trades['CALL'] else 'PUT' if active_trades['PUT'] else None
                    
                    # 1. Entry based on RSI Trend
                    if current_pos is None and rsi_trend_signal:
                        initial_risk = self._get_initial_risk(current_atr)
                        
                        if rsi_trend_signal == 'CALL':
                            sl_price = current_row_lower['close'] - initial_risk if self.sl_enabled else None
                            highest_price_since_entry['CALL'] = current_row_lower['high']
                        else:
                            sl_price = current_row_lower['close'] + initial_risk if self.sl_enabled else None
                            lowest_price_since_entry['PUT'] = current_row_lower['low']
                            
                        active_trades[rsi_trend_signal] = Trade(
                            option_type=rsi_trend_signal,
                            pattern='RSI_TREND',
                            confirmation='RSI_SMOOTH',
                            entry_time=current_row_lower['date'].isoformat(),
                            entry_price=current_row_lower['close'],
                            rsi=current_rsi,
                            rsi_upper=current_rsi_upper,
                            stop_loss=sl_price,
                            initial_risk=initial_risk
                        )
                        trades_today += 1
                        current_pos = rsi_trend_signal
                        current_active_count += 1

                    # 2. Entry based on Double Cross
                    if current_active_count < self.max_concurrent_trades and double_cross_signal:
                        if active_trades[double_cross_signal] is None:
                            initial_risk = self._get_initial_risk(current_atr)
                            
                            if double_cross_signal == 'CALL':
                                sl_price = current_row_lower['close'] - initial_risk if self.sl_enabled else None
                                highest_price_since_entry['CALL'] = current_row_lower['high']
                            else:
                                sl_price = current_row_lower['close'] + initial_risk if self.sl_enabled else None
                                lowest_price_since_entry['PUT'] = current_row_lower['low']
                                
                            active_trades[double_cross_signal] = Trade(
                                option_type=double_cross_signal,
                                pattern='DOUBLE_CROSS',
                                confirmation='MACD_STOCH',
                                entry_time=current_row_lower['date'].isoformat(),
                                entry_price=current_row_lower['close'],
                                rsi=current_rsi,
                                rsi_upper=current_rsi_upper,
                                stop_loss=sl_price,
                                initial_risk=initial_risk
                            )
                            trades_today += 1
                            current_pos = double_cross_signal
                            current_active_count += 1

                    # 3. Pattern entry logic (only if not already entered by RSI or Double Cross)
                    if current_active_count < self.max_concurrent_trades:
                        for category_lower, pats in self.patterns.items():
                            for pattern_func in pats:
                                if pattern_func(candles_lower):
                                    pattern_name = pattern_func.__name__
                                    signals = get_option_signals(
                                        category_lower, 
                                        pattern_name, 
                                        upper_category, 
                                        current_position=current_pos,
                                        rsi_value=current_rsi,
                                        rsi_upper=current_rsi_upper,
                                        rsi_config=self.rsi_config
                                    )
                                    
                                    for signal in signals:
                                        if signal.action == 'ENTRY':
                                            if active_trades[signal.option_type] is None:
                                                initial_risk = self._get_initial_risk(current_atr)
                                                
                                                if signal.option_type == 'CALL':
                                                    sl_price = current_row_lower['close'] - initial_risk if self.sl_enabled else None
                                                    highest_price_since_entry['CALL'] = current_row_lower['high']
                                                else:
                                                    sl_price = current_row_lower['close'] + initial_risk if self.sl_enabled else None
                                                    lowest_price_since_entry['PUT'] = current_row_lower['low']

                                                active_trades[signal.option_type] = Trade(
                                                    option_type=signal.option_type,
                                                    pattern=pattern_name,
                                                    confirmation=signal.confirmation,
                                                    entry_time=current_row_lower['date'].isoformat(),
                                                    entry_price=current_row_lower['close'],
                                                    rsi=current_rsi,
                                                    rsi_upper=current_rsi_upper,
                                                    stop_loss=sl_price,
                                                    initial_risk=initial_risk
                                                )
                                                trades_today += 1
                                                current_pos = signal.option_type
                                                current_active_count += 1
                                                if current_active_count >= self.max_concurrent_trades:
                                                    break
                                if current_active_count >= self.max_concurrent_trades:
                                    break
        
        # Close remaining
        last_row = df_lower.iloc[-1]
        for opt_type, trade in active_trades.items():
            if trade:
                trade.exit_time = last_row['date'].isoformat()
                trade.exit_price = last_row['close']
                completed_trades.append(trade)
                
        return completed_trades
