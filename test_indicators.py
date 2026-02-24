import pandas as pd
import numpy as np

# Create dummy OHLCV data
np.random.seed(42)
days = 300
dates = pd.date_range("2023-01-01", periods=days)
close_prices = np.cumsum(np.random.randn(days)) + 100
open_prices = close_prices + np.random.randn(days) * 2
high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.randn(days)) * 2
low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.randn(days)) * 2
volumes = np.random.randint(1000, 100000, size=days)

df = pd.DataFrame({
    "open": open_prices,
    "high": high_prices,
    "low": low_prices,
    "close": close_prices,
    "volume": volumes
}, index=dates)

from backend.strategies.indicators import add_trend_duration_forecast, add_macd_support_resistance, add_volume_profile_pivots

print("Testing Trend Duration Forecast...")
df = add_trend_duration_forecast(df, length=50, trend_length=3, samples=10)
print(f"Columns added: {[c for c in df.columns if c.startswith('tf_')]}")

print("Testing MACD Support & Resistance...")
df = add_macd_support_resistance(df)
print(f"Columns added: {[c for c in df.columns if c.startswith('macd_sr_')]}")

print("Testing Volume Profile & Pivots...")
df = add_volume_profile_pivots(df)
print(f"Columns added: {[c for c in df.columns if c.startswith('vol_profile_')]}")

print("\nLast Row Sample Data:")
print(df.iloc[-1][['close', 'tf_trend_bullish', 'tf_probable_length', 'macd_sr_support', 'macd_sr_resistance', 'vol_profile_poc']])
print("SUCCESS!")
