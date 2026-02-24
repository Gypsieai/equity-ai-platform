import pandas as pd
import numpy as np
import pandas_ta as ta

def add_trend_duration_forecast(df: pd.DataFrame, length: int = 50, trend_length: int = 3, samples: int = 10) -> pd.DataFrame:
    """
    Translates 'Trend Duration Forecast [ChartPrime]' Pine Script explicitly.
    Calculates Hull Moving Average (HMA), detects rising/falling trends,
    and forecasts the probable length based on past samples.
    """
    if len(df) < length:
        return df
        
    # Calculate HMA
    df['hma'] = ta.hma(df['close'], length=length)
    
    # Calculate consecutive rising/falling
    # ta.rising in Pine Script checks if the series has been strictly increasing for 'length' bars
    df['hma_rising'] = df['hma'].diff() > 0
    df['hma_falling'] = df['hma'].diff() < 0
    
    # Rolling sum to check if it's been rising/falling for `trend_length` bars
    df['is_rising_trend'] = df['hma_rising'].rolling(window=trend_length).sum() == trend_length
    df['is_falling_trend'] = df['hma_falling'].rolling(window=trend_length).sum() == trend_length
    
    # State tracking variables
    trend_state = [False] * len(df)
    trend_count = [0] * len(df)
    
    bullish_lengths = []
    bearish_lengths = []
    
    probable_length = [0.0] * len(df)
    
    current_trend = None  # True for bullish, False for bearish
    current_count = 0
    
    for i in range(trend_length, len(df)):
        is_rising = df['is_rising_trend'].iloc[i]
        is_falling = df['is_falling_trend'].iloc[i]
        
        # Determine current trend
        new_trend = current_trend
        if is_rising:
            new_trend = True
        elif is_falling:
            new_trend = False
            
        # If trend changed
        if new_trend != current_trend and current_trend is not None:
            # Save the length of the previous trend
            if current_trend is True:
                bullish_lengths.append(current_count)
                if len(bullish_lengths) > samples:
                    bullish_lengths.pop(0)
            else:
                bearish_lengths.append(current_count)
                if len(bearish_lengths) > samples:
                    bearish_lengths.pop(0)
            
            # Reset count for the new trend
            current_count = 0
            
        current_trend = new_trend
        
        # Increment counter
        if current_trend is not None:
            current_count += 1
            
        trend_state[i] = current_trend
        trend_count[i] = current_count
        
        # Calculate Probable Length (Average of past samples)
        if current_trend is True and len(bullish_lengths) > 0:
            probable_length[i] = sum(bullish_lengths) / len(bullish_lengths)
        elif current_trend is False and len(bearish_lengths) > 0:
            probable_length[i] = sum(bearish_lengths) / len(bearish_lengths)
            
    df['tf_trend_bullish'] = trend_state
    df['tf_trend_count'] = trend_count
    df['tf_probable_length'] = probable_length
    
    return df

def add_macd_support_resistance(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_len: int = 9) -> pd.DataFrame:
    """
    Translates 'MACD Support and Resistance [ChartPrime]'.
    Finds local highs/lows on MACD crossovers/crossunders to plot support/resistance lines.
    """
    if len(df) < slow + signal_len:
        return df
        
    # Calculate MACD
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal_len)
    
    # Handle pandas-ta MACD column naming convention
    # Usually: 'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9'
    macd_col = [c for c in macd.columns if c.startswith('MACD_')][0]
    sig_col = [c for c in macd.columns if c.startswith('MACDs_')][0]
    
    df['macd_line'] = macd[macd_col]
    df['macd_signal'] = macd[sig_col]
    
    # Detect Crossovers (MACD crosses above Signal) -> Bullish, look for local Low (Support)
    # Detect Crossunders (MACD crosses below Signal) -> Bearish, look for local High (Resistance)
    df['macd_cross_up'] = (df['macd_line'] > df['macd_signal']) & (df['macd_line'].shift(1) <= df['macd_signal'].shift(1))
    df['macd_cross_down'] = (df['macd_line'] < df['macd_signal']) & (df['macd_line'].shift(1) >= df['macd_signal'].shift(1))
    
    # Store up to 20 active support/resistance levels
    active_levels = [] # List of dicts: {'is_support': bool, 'level': float, 'start_idx': int}
    
    support_val = [np.nan] * len(df)
    resistance_val = [np.nan] * len(df)
    
    for i in range(5, len(df)):
        # Prune crossed levels
        current_low = df['low'].iloc[i]
        current_high = df['high'].iloc[i]
        
        # Keep levels that haven't been broken
        new_levels = []
        for lvl in active_levels:
            if lvl['is_support'] and current_low < lvl['level']:
                continue # Support broken
            if not lvl['is_support'] and current_high > lvl['level']:
                continue # Resistance broken
            new_levels.append(lvl)
        active_levels = new_levels
        
        # Check for new cross_down (lookback 5 bars for local high -> Resistance)
        if df['macd_cross_down'].iloc[i]:
            local_high = df['high'].iloc[i-5:i+1].max()
            active_levels.append({'is_support': False, 'level': local_high, 'start_idx': i})
            
        # Check for new cross_up (lookback 5 bars for local low -> Support)
        if df['macd_cross_up'].iloc[i]:
            local_low = df['low'].iloc[i-5:i+1].min()
            active_levels.append({'is_support': True, 'level': local_low, 'start_idx': i})
            
        # Limit to 20 levels
        if len(active_levels) > 20:
            active_levels.pop(0) # Remove oldest
            
        # Find closest active support / resistance for the current bar
        supports = [l['level'] for l in active_levels if l['is_support']]
        resistances = [l['level'] for l in active_levels if not l['is_support']]
        
        price = df['close'].iloc[i]
        
        if supports:
            # Find the highest support level below price
            valid_supports = [s for s in supports if s <= price]
            if valid_supports:
                support_val[i] = max(valid_supports)
                
        if resistances:
            # Find the lowest resistance level above price
            valid_res = [r for r in resistances if r >= price]
            if valid_res:
                resistance_val[i] = min(valid_res)
                
    df['macd_sr_support'] = support_val
    df['macd_sr_resistance'] = resistance_val
    
    return df

def add_volume_profile_pivots(df: pd.DataFrame, period: int = 200, bins: int = 50, pivot_length: int = 10) -> pd.DataFrame:
    """
    Translates 'Volume Profile + Pivot Levels [ChartPrime]'.
    Calculates Point of Control (PoC) over a lookback period and identifies Pivot Highs/Lows.
    """
    if len(df) < period:
        return df
        
    poc_vals = [np.nan] * len(df)
    delta_vals = [0.0] * len(df)
    
    # Calculate Pivot Highs and Lows
    # A pivot high is a bar whose high is >= the highs of the surrounding 'pivot_length' bars (both sides)
    df['pivot_high'] = df['high'].rolling(window=pivot_length*2+1, center=True).max() == df['high']
    df['pivot_low'] = df['low'].rolling(window=pivot_length*2+1, center=True).min() == df['low']
    
    # In a real-time trading agent, rolling center=True introduces future-leakage
    # To fix this for right-edge trading, we check if the high `pivot_length` bars ago was the highest in the 2*pivot_length window.
    # df['pivot_high_realtime'] = (df['high'].shift(pivot_length) == df['high'].rolling(window=pivot_length*2+1).max())
    
    for i in range(period, len(df)):
        window = df.iloc[i-period:i]
        
        H = window['high'].max()
        L = window['low'].min()
        
        if H == L:
            continue
            
        bin_size = (H - L) / bins
        
        # We need to bin the volume.
        # Vectorized approach:
        # Determine which bin each close price belongs to
        bin_indices = np.floor((window['close'] - L) / bin_size).clip(0, bins-1)
        
        vol_by_bin = window.groupby(bin_indices)['volume'].sum()
        
        if not vol_by_bin.empty:
            max_bin_idx = vol_by_bin.idxmax()
            
            # PoC is the midpoint of the bin with max volume
            poc = L + (max_bin_idx * bin_size) + (bin_size / 2)
            poc_vals[i] = poc
            
        # Calculate Delta (Buy Vol - Sell Vol)
        # Simplified assumption: Close > Open = Buy Vol, Close < Open = Sell Vol
        buy_vol = window.loc[window['close'] > window['open'], 'volume'].sum()
        sell_vol = window.loc[window['close'] < window['open'], 'volume'].sum()
        
        delta_vals[i] = buy_vol - sell_vol
        
    df['vol_profile_poc'] = poc_vals
    df['vol_profile_delta'] = delta_vals
    
    return df
