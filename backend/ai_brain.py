"""
StockPulse AI — Autonomous Prediction Brain
24/7 multi-strategy AI that scans markets, detects patterns,
scores momentum, and generates autonomous buy/sell signals.

This is NOT a toy. This engine runs real technical analysis:
─────────────────────────────────────────────────────────────
│ Module              │ What it does                        │
├─────────────────────┼─────────────────────────────────────┤
│ TechnicalAnalyzer   │ RSI, MACD, Bollinger, EMA, SMA,    │
│                     │ VWAP, ATR, Stochastic, OBV         │
│ PatternDetector     │ Candlestick + chart pattern recog   │
│ MomentumScanner     │ Breakout detection, volume surge    │
│ SentimentAnalyzer   │ News sentiment scoring              │
│ StrategyEngine      │ Multi-strategy signal aggregation   │
│ AutoPilot           │ 24/7 scanner loop with trade exec   │
─────────────────────────────────────────────────────────────

Strategies:
  1. Momentum — Buy breakouts, ride trends
  2. Mean Reversion — Buy oversold, sell overbought
  3. Trend Following — EMA crossovers, MACD signals
  4. Volatility Breakout — Bollinger squeeze breakouts
  5. Volume Spike — Unusual volume with price action
"""

import asyncio
import math
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import pandas as pd

from strategies.indicators import add_trend_duration_forecast, add_macd_support_resistance, add_volume_profile_pivots


# ============================================================================
# Technical Analysis Engine
# ============================================================================
class TechnicalAnalyzer:
    """Calculate real technical indicators from price history."""

    @staticmethod
    def sma(closes: List[float], period: int) -> List[float]:
        """Simple Moving Average."""
        if len(closes) < period:
            return [sum(closes) / len(closes)] * len(closes)
        result = [None] * (period - 1)
        for i in range(period - 1, len(closes)):
            result.append(sum(closes[i - period + 1:i + 1]) / period)
        return result

    @staticmethod
    def ema(closes: List[float], period: int) -> List[float]:
        """Exponential Moving Average."""
        if not closes:
            return []
        multiplier = 2 / (period + 1)
        ema_vals = [closes[0]]
        for i in range(1, len(closes)):
            val = (closes[i] - ema_vals[-1]) * multiplier + ema_vals[-1]
            ema_vals.append(val)
        return ema_vals

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> float:
        """Relative Strength Index (0-100)."""
        if len(closes) < period + 1:
            return 50.0

        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        # Use last `period` values
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    @staticmethod
    def macd(
        closes: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Dict[str, float]:
        """MACD with signal line and histogram."""
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0}

        ta = TechnicalAnalyzer
        ema_fast = ta.ema(closes, fast)
        ema_slow = ta.ema(closes, slow)

        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = ta.ema(macd_line, signal)

        return {
            "macd": round(macd_line[-1], 4),
            "signal": round(signal_line[-1], 4),
            "histogram": round(macd_line[-1] - signal_line[-1], 4),
        }

    @staticmethod
    def bollinger_bands(
        closes: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, float]:
        """Bollinger Bands."""
        if len(closes) < period:
            price = closes[-1] if closes else 0
            return {"upper": price, "middle": price, "lower": price, "width": 0, "position": 0.5}

        window = closes[-period:]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / period
        std = math.sqrt(variance)

        upper = sma + std_dev * std
        lower = sma - std_dev * std
        width = (upper - lower) / sma if sma else 0

        current = closes[-1]
        position = (current - lower) / (upper - lower) if (upper - lower) else 0.5

        return {
            "upper": round(upper, 2),
            "middle": round(sma, 2),
            "lower": round(lower, 2),
            "width": round(width, 4),
            "position": round(max(0, min(1, position)), 4),
        }

    @staticmethod
    def stochastic(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        k_period: int = 14,
        d_period: int = 3,
    ) -> Dict[str, float]:
        """Stochastic Oscillator (%K and %D)."""
        if len(closes) < k_period:
            return {"k": 50, "d": 50}

        highest = max(highs[-k_period:])
        lowest = min(lows[-k_period:])

        if highest == lowest:
            k = 50
        else:
            k = ((closes[-1] - lowest) / (highest - lowest)) * 100

        # Simple %D (SMA of %K) — approximate with current value
        d = k  # In production, track K history for proper D calculation

        return {"k": round(k, 2), "d": round(d, 2)}

    @staticmethod
    def atr(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> float:
        """Average True Range — measures volatility."""
        if len(closes) < 2:
            return 0

        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0

        return round(sum(true_ranges[-period:]) / period, 4)

    @staticmethod
    def obv(closes: List[float], volumes: List[int]) -> List[float]:
        """On-Balance Volume — confirms price trends with volume."""
        if not closes or not volumes:
            return []

        obv_vals = [0]
        for i in range(1, min(len(closes), len(volumes))):
            if closes[i] > closes[i - 1]:
                obv_vals.append(obv_vals[-1] + volumes[i])
            elif closes[i] < closes[i - 1]:
                obv_vals.append(obv_vals[-1] - volumes[i])
            else:
                obv_vals.append(obv_vals[-1])

        return obv_vals

    @staticmethod
    def vwap(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[int],
    ) -> float:
        """Volume Weighted Average Price."""
        if not closes or not volumes:
            return 0

        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        cum_tp_vol = sum(tp * v for tp, v in zip(typical_prices, volumes))
        cum_vol = sum(volumes)

        return round(cum_tp_vol / cum_vol, 2) if cum_vol else 0

    def full_analysis(
        self,
        closes: List[float],
        highs: List[float] = None,
        lows: List[float] = None,
        volumes: List[int] = None,
    ) -> Dict:
        """Run complete technical analysis suite."""
        if not closes:
            return {}

        highs = highs or closes
        lows = lows or closes
        volumes = volumes or [0] * len(closes)

        current = closes[-1]
        sma_20 = self.sma(closes, 20)
        sma_50 = self.sma(closes, 50)
        ema_12 = self.ema(closes, 12)
        ema_26 = self.ema(closes, 26)
        
        # Calculate custom ChartPrime strategies using pandas
        df = pd.DataFrame({
            "open": opens if opens else closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes
        })
        
        df = add_trend_duration_forecast(df)
        df = add_macd_support_resistance(df)
        df = add_volume_profile_pivots(df)
        
        last_row = df.iloc[-1]

        return {
            "price": current,
            "rsi": self.rsi(closes),
            "macd": self.macd(closes),
            "bollinger": self.bollinger_bands(closes),
            "stochastic": self.stochastic(highs, lows, closes),
            "atr": self.atr(highs, lows, closes),
            "vwap": self.vwap(highs, lows, closes, volumes),
            "obv_trend": self._obv_trend(closes, volumes),
            "sma_20": round(sma_20[-1], 2) if sma_20[-1] else current,
            "sma_50": round(sma_50[-1], 2) if sma_50[-1] else current,
            "ema_12": round(ema_12[-1], 2),
            "ema_26": round(ema_26[-1], 2),
            "above_sma_20": current > (sma_20[-1] or 0),
            "above_sma_50": current > (sma_50[-1] or 0),
            "ema_bullish_cross": ema_12[-1] > ema_26[-1],
            "volume_surge": self._detect_volume_surge(volumes),
            "trend": self._determine_trend(closes),
            "cp_trend_duration": {
                "bullish": bool(last_row.get("tf_trend_bullish", False)),
                "probable_length": float(last_row.get("tf_probable_length", 0.0)),
                "current_count": int(last_row.get("tf_trend_count", 0)),
            },
            "cp_macd_sr": {
                "support": float(last_row.get("macd_sr_support", 0.0)),
                "resistance": float(last_row.get("macd_sr_resistance", 0.0)),
            },
            "cp_vol_profile": {
                "poc": float(last_row.get("vol_profile_poc", 0.0)),
                "delta": float(last_row.get("vol_profile_delta", 0.0)),
            }
        }

    def _obv_trend(self, closes: List[float], volumes: List[int]) -> str:
        """Is OBV confirming the price trend?"""
        obv = self.obv(closes, volumes)
        if len(obv) < 5:
            return "neutral"
        recent = obv[-5:]
        if all(recent[i] >= recent[i - 1] for i in range(1, len(recent))):
            return "bullish"
        elif all(recent[i] <= recent[i - 1] for i in range(1, len(recent))):
            return "bearish"
        return "neutral"

    @staticmethod
    def _detect_volume_surge(volumes: List[int], threshold: float = 2.0) -> bool:
        """Detect unusual volume spike."""
        if len(volumes) < 10:
            return False
        avg_vol = sum(volumes[-20:-1]) / min(19, len(volumes) - 1)
        return volumes[-1] > avg_vol * threshold if avg_vol else False

    @staticmethod
    def _determine_trend(closes: List[float]) -> str:
        """Determine price trend direction."""
        if len(closes) < 10:
            return "neutral"
        short_avg = sum(closes[-5:]) / 5
        long_avg = sum(closes[-20:]) / min(20, len(closes))

        pct_diff = ((short_avg - long_avg) / long_avg) * 100 if long_avg else 0

        if pct_diff > 2:
            return "strong_uptrend"
        elif pct_diff > 0.5:
            return "uptrend"
        elif pct_diff < -2:
            return "strong_downtrend"
        elif pct_diff < -0.5:
            return "downtrend"
        return "sideways"


# ============================================================================
# Pattern Detection
# ============================================================================
class PatternDetector:
    """Detect candlestick and chart patterns."""

    @staticmethod
    def detect_candlestick(
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
    ) -> List[str]:
        """Detect candlestick patterns in recent bars."""
        if len(closes) < 3:
            return []

        patterns = []
        o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
        body = abs(c - o)
        total_range = h - l if h != l else 0.01
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # Doji — indecision
        if body < total_range * 0.1:
            patterns.append("Doji")

        # Hammer — bullish reversal at bottom
        if lower_wick > body * 2 and upper_wick < body * 0.5 and c > o:
            patterns.append("Hammer")

        # Shooting Star — bearish reversal at top
        if upper_wick > body * 2 and lower_wick < body * 0.5 and o > c:
            patterns.append("Shooting Star")

        # Engulfing patterns (2-bar)
        if len(closes) >= 2:
            prev_body = abs(closes[-2] - opens[-2])
            # Bullish Engulfing
            if (
                opens[-2] > closes[-2]  # Previous was bearish
                and closes[-1] > opens[-1]  # Current is bullish
                and closes[-1] > opens[-2]  # Current close > prev open
                and opens[-1] < closes[-2]  # Current open < prev close
                and body > prev_body
            ):
                patterns.append("Bullish Engulfing")
            # Bearish Engulfing
            elif (
                closes[-2] > opens[-2]  # Previous was bullish
                and opens[-1] > closes[-1]  # Current is bearish
                and opens[-1] > closes[-2]  # Current open > prev close
                and closes[-1] < opens[-2]  # Current close < prev open
                and body > prev_body
            ):
                patterns.append("Bearish Engulfing")

        # Three White Soldiers
        if len(closes) >= 3:
            if (
                all(closes[-i] > opens[-i] for i in range(1, 4))
                and closes[-1] > closes[-2] > closes[-3]
            ):
                patterns.append("Three White Soldiers")

            # Three Black Crows
            if (
                all(opens[-i] > closes[-i] for i in range(1, 4))
                and closes[-1] < closes[-2] < closes[-3]
            ):
                patterns.append("Three Black Crows")

        return patterns

    @staticmethod
    def detect_chart_patterns(closes: List[float]) -> List[str]:
        """Detect higher-level chart patterns."""
        if len(closes) < 20:
            return []

        patterns = []

        # Double Bottom — W shape
        mid = len(closes) // 2
        left_min = min(closes[:mid])
        right_min = min(closes[mid:])
        left_min_idx = closes[:mid].index(left_min)
        right_min_idx = mid + closes[mid:].index(right_min)

        if abs(left_min - right_min) / left_min < 0.03:  # Within 3%
            peak_between = max(closes[left_min_idx:right_min_idx])
            if peak_between > left_min * 1.03:
                if closes[-1] > peak_between:
                    patterns.append("Double Bottom Breakout")
                else:
                    patterns.append("Double Bottom Forming")

        # Double Top — M shape
        left_max = max(closes[:mid])
        right_max = max(closes[mid:])
        if abs(left_max - right_max) / left_max < 0.03:
            trough = min(closes[closes[:mid].index(left_max):mid + closes[mid:].index(right_max)])
            if trough < left_max * 0.97:
                if closes[-1] < trough:
                    patterns.append("Double Top Breakdown")
                else:
                    patterns.append("Double Top Forming")

        # Ascending/Descending Triangle — higher lows / lower highs
        recent = closes[-10:]
        lows_trend = all(recent[i] >= recent[i-2] for i in range(2, len(recent), 2) if i < len(recent))
        highs_trend = all(recent[i] <= recent[i-2] for i in range(2, len(recent), 2) if i < len(recent))

        if lows_trend and not highs_trend:
            patterns.append("Ascending Triangle")
        elif highs_trend and not lows_trend:
            patterns.append("Descending Triangle")

        # Breakout — price above 20-day high
        high_20 = max(closes[-20:])
        if closes[-1] >= high_20 and closes[-2] < high_20:
            patterns.append("20-Day Breakout")

        # Breakdown — price below 20-day low
        low_20 = min(closes[-20:])
        if closes[-1] <= low_20 and closes[-2] > low_20:
            patterns.append("20-Day Breakdown")

        return patterns


# ============================================================================
# Trading Signal
# ============================================================================
class SignalStrength(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    HOLD = "hold"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class TradingSignal:
    """Composite trading signal from all strategies."""
    symbol: str
    action: str               # buy, sell, hold
    strength: str             # strong_buy → strong_sell
    confidence: float         # 0.0 — 1.0
    target_price: float
    stop_loss: float
    strategies_bullish: int
    strategies_bearish: int
    strategies_neutral: int
    reasons: List[str]
    indicators: Dict
    patterns: List[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ============================================================================
# Multi-Strategy Signal Aggregator
# ============================================================================
class StrategyEngine:
    """
    Runs multiple trading strategies and aggregates signals.
    Each strategy votes bullish/bearish/neutral with a weight.
    The composite signal determines the final action.
    """

    def __init__(self):
        self.ta = TechnicalAnalyzer()
        self.pd = PatternDetector()

    def generate_signal(
        self,
        symbol: str,
        closes: List[float],
        highs: List[float] = None,
        lows: List[float] = None,
        opens: List[float] = None,
        volumes: List[int] = None,
    ) -> TradingSignal:
        """Generate composite trading signal from all strategies."""
        if not closes or len(closes) < 5:
            return self._neutral_signal(symbol)

        highs = highs or closes
        lows = lows or closes
        opens = opens or closes
        volumes = volumes or [0] * len(closes)

        # Run full technical analysis
        indicators = self.ta.full_analysis(closes, highs, lows, volumes)

        # Detect patterns
        candlestick_patterns = self.pd.detect_candlestick(opens, highs, lows, closes)
        chart_patterns = self.pd.detect_chart_patterns(closes)
        all_patterns = candlestick_patterns + chart_patterns

        # Run each strategy
        votes = []
        reasons = []

        # Strategy 1: RSI Mean Reversion (weight: 20%)
        v, r = self._strategy_rsi(indicators)
        votes.append(("RSI", v, 0.20, r))

        # Strategy 2: MACD Trend (weight: 20%)
        v, r = self._strategy_macd(indicators)
        votes.append(("MACD", v, 0.20, r))

        # Strategy 3: Bollinger Breakout (weight: 15%)
        v, r = self._strategy_bollinger(indicators)
        votes.append(("Bollinger", v, 0.15, r))

        # Strategy 4: EMA Crossover (weight: 15%)
        v, r = self._strategy_ema_cross(indicators)
        votes.append(("EMA Cross", v, 0.15, r))

        # Strategy 5: Volume + Momentum (weight: 15%)
        v, r = self._strategy_volume_momentum(indicators)
        votes.append(("Volume", v, 0.15, r))

        # Strategy 6: Pattern Recognition (weight: 15%)
        v, r = self._strategy_patterns(all_patterns, indicators)
        votes.append(("Patterns", v, 0.15, r))
        
        # Strategy 7: ChartPrime PineScript Translations (weight: 25%)
        v, r = self._strategy_chartprime(indicators)
        votes.append(("ChartPrime", v, 0.25, r))

        # Aggregate votes
        weighted_score = sum(v * w for _, v, w, _ in votes)
        reasons = [r for _, _, _, r in votes if r]

        bullish = sum(1 for _, v, _, _ in votes if v > 0.2)
        bearish = sum(1 for _, v, _, _ in votes if v < -0.2)
        neutral = len(votes) - bullish - bearish

        # Determine action and confidence
        action, strength, confidence = self._score_to_action(weighted_score, bullish, bearish)

        # Calculate targets
        current = closes[-1]
        atr = indicators.get("atr", current * 0.02)
        target_price = round(current + (atr * 2 if action == "buy" else -atr * 2 if action == "sell" else 0), 2)
        stop_loss = round(current - atr * 1.5 if action == "buy" else current + atr * 1.5 if action == "sell" else current, 2)

        return TradingSignal(
            symbol=symbol,
            action=action,
            strength=strength,
            confidence=round(confidence, 4),
            target_price=target_price,
            stop_loss=stop_loss,
            strategies_bullish=bullish,
            strategies_bearish=bearish,
            strategies_neutral=neutral,
            reasons=reasons,
            indicators=indicators,
            patterns=all_patterns,
        )

    # ── Individual Strategies ─────────────────────────────────

    def _strategy_rsi(self, ind: Dict) -> Tuple[float, str]:
        """RSI Mean Reversion: buy oversold, sell overbought."""
        rsi = ind.get("rsi", 50)
        if rsi < 25:
            return (0.9, f"RSI extremely oversold ({rsi:.0f})")
        elif rsi < 30:
            return (0.7, f"RSI oversold ({rsi:.0f})")
        elif rsi < 40:
            return (0.3, f"RSI approaching oversold ({rsi:.0f})")
        elif rsi > 80:
            return (-0.9, f"RSI extremely overbought ({rsi:.0f})")
        elif rsi > 70:
            return (-0.7, f"RSI overbought ({rsi:.0f})")
        elif rsi > 60:
            return (-0.2, f"RSI elevated ({rsi:.0f})")
        return (0.0, "")

    def _strategy_macd(self, ind: Dict) -> Tuple[float, str]:
        """MACD Trend Following."""
        macd = ind.get("macd", {})
        hist = macd.get("histogram", 0)
        macd_val = macd.get("macd", 0)
        signal = macd.get("signal", 0)

        if macd_val > signal and hist > 0:
            strength = min(0.8, abs(hist) * 10)
            return (strength, f"MACD bullish crossover (hist: {hist:.4f})")
        elif macd_val < signal and hist < 0:
            strength = min(0.8, abs(hist) * 10)
            return (-strength, f"MACD bearish crossover (hist: {hist:.4f})")
        return (0.0, "")

    def _strategy_bollinger(self, ind: Dict) -> Tuple[float, str]:
        """Bollinger Band Breakout/Reversal."""
        bb = ind.get("bollinger", {})
        pos = bb.get("position", 0.5)
        width = bb.get("width", 0)

        # Squeeze breakout (low width + price at band)
        if width < 0.03 and pos > 0.9:
            return (0.7, f"Bollinger squeeze breakout (width: {width:.4f})")
        elif width < 0.03 and pos < 0.1:
            return (-0.7, f"Bollinger squeeze breakdown (width: {width:.4f})")
        # Mean reversion at extremes
        elif pos > 0.95:
            return (-0.5, f"Price at upper Bollinger Band ({pos:.2f})")
        elif pos < 0.05:
            return (0.5, f"Price at lower Bollinger Band ({pos:.2f})")
        return (0.0, "")

    def _strategy_ema_cross(self, ind: Dict) -> Tuple[float, str]:
        """EMA 12/26 Crossover."""
        ema_12 = ind.get("ema_12", 0)
        ema_26 = ind.get("ema_26", 0)
        bullish = ind.get("ema_bullish_cross", False)
        above_50 = ind.get("above_sma_50", False)

        if bullish and above_50:
            return (0.7, "EMA bullish cross + above SMA 50")
        elif bullish:
            return (0.4, "EMA 12 crossed above EMA 26")
        elif not bullish and not above_50:
            return (-0.7, "EMA bearish cross + below SMA 50")
        elif not bullish:
            return (-0.4, "EMA 12 below EMA 26")
        return (0.0, "")

    def _strategy_volume_momentum(self, ind: Dict) -> Tuple[float, str]:
        """Volume surge + price momentum."""
        volume_surge = ind.get("volume_surge", False)
        trend = ind.get("trend", "sideways")
        obv = ind.get("obv_trend", "neutral")

        score = 0.0
        reason = ""

        if volume_surge and trend in ("uptrend", "strong_uptrend"):
            score = 0.8
            reason = f"Volume surge + {trend} — institutional buying"
        elif volume_surge and trend in ("downtrend", "strong_downtrend"):
            score = -0.8
            reason = f"Volume surge + {trend} — institutional selling"
        elif obv == "bullish" and trend in ("uptrend", "strong_uptrend"):
            score = 0.4
            reason = "OBV confirms bullish trend"
        elif obv == "bearish" and trend in ("downtrend", "strong_downtrend"):
            score = -0.4
            reason = "OBV confirms bearish trend"

        return (score, reason)

    def _strategy_patterns(
        self, patterns: List[str], ind: Dict
    ) -> Tuple[float, str]:
        """Pattern-based signals."""
        if not patterns:
            return (0.0, "")

        bullish_patterns = {
            "Hammer": 0.5, "Bullish Engulfing": 0.7,
            "Three White Soldiers": 0.8, "Double Bottom Breakout": 0.9,
            "Ascending Triangle": 0.6, "20-Day Breakout": 0.8,
            "Double Bottom Forming": 0.3,
        }
        bearish_patterns = {
            "Shooting Star": -0.5, "Bearish Engulfing": -0.7,
            "Three Black Crows": -0.8, "Double Top Breakdown": -0.9,
            "Descending Triangle": -0.6, "20-Day Breakdown": -0.8,
            "Double Top Forming": -0.3,
        }

        total = 0.0
        detected = []
        for p in patterns:
            if p in bullish_patterns:
                total += bullish_patterns[p]
                detected.append(f"📈 {p}")
            elif p in bearish_patterns:
                total += bearish_patterns[p]
                detected.append(f"📉 {p}")

        avg = total / len(patterns) if patterns else 0
        reason = f"Patterns: {', '.join(detected)}" if detected else ""
        return (max(-1, min(1, avg)), reason)

    def _strategy_chartprime(self, ind: Dict) -> Tuple[float, str]:
        """ChartPrime custom strategies signal generation."""
        # 1. Trend Duration
        trend = ind.get("cp_trend_duration", {})
        is_bullish = trend.get("bullish", False)
        current_dur = trend.get("current_count", 0)
        prob_len = trend.get("probable_length", 0.0)
        
        # 2. MACD Support/Resistance
        sr = ind.get("cp_macd_sr", {})
        support = sr.get("support", 0.0)
        resistance = sr.get("resistance", 0.0)
        
        # 3. Volume Profile & Pivots
        vp = ind.get("cp_vol_profile", {})
        poc = vp.get("poc", 0.0)
        delta = vp.get("delta", 0.0)
        
        price = ind.get("price", 0.0)
        
        score = 0.0
        reasons = []
        
        # Add score for Trend Duration
        if is_bullish:
            if current_dur < prob_len * 0.8: # Still room to run
                score += 0.4
                reasons.append(f"Early bullish trend ({current_dur}/{prob_len:.1f} bars)")
            elif current_dur > prob_len * 1.2:
                score -= 0.2 # Extended trend
        else:
            if current_dur < prob_len * 0.8:
                score -= 0.4
                reasons.append(f"Early bearish trend ({current_dur}/{prob_len:.1f} bars)")
            elif current_dur > prob_len * 1.2:
                score += 0.2 # Extended trend
                
        # Add score for MACD S/R bounces
        if support > 0 and price > support and (price - support) / support < 0.02:
            score += 0.5
            reasons.append(f"Bouncing off MACD Support ({support:.2f})")
        if resistance > 0 and price < resistance and (resistance - price) / price < 0.02:
            score -= 0.5
            reasons.append(f"Rejection at MACD Resistance ({resistance:.2f})")
            
        # Add score for Volume Profile Delta
        if delta > 0 and price > poc:
            score += 0.3
            reasons.append(f"Strong Buy Delta above PoC ({poc:.2f})")
        elif delta < 0 and price < poc:
            score -= 0.3
            reasons.append(f"Strong Sell Delta below PoC ({poc:.2f})")
            
        score = max(-1.0, min(1.0, score))
        final_reason = " | ".join(reasons) if reasons else ""
        return (score, final_reason)

    # ── Signal Scoring ────────────────────────────────────────

    def _score_to_action(
        self, score: float, bullish: int, bearish: int
    ) -> Tuple[str, str, float]:
        """Convert weighted score to action, strength, and confidence."""
        confidence = abs(score)

        if score > 0.5:
            return ("buy", "strong_buy", min(0.95, confidence))
        elif score > 0.25:
            return ("buy", "buy", confidence)
        elif score > 0.1:
            return ("buy", "weak_buy", confidence)
        elif score < -0.5:
            return ("sell", "strong_sell", min(0.95, confidence))
        elif score < -0.25:
            return ("sell", "sell", confidence)
        elif score < -0.1:
            return ("sell", "weak_sell", confidence)
        else:
            return ("hold", "hold", 0.5)

    def _neutral_signal(self, symbol: str) -> TradingSignal:
        """Return a neutral/no-data signal."""
        return TradingSignal(
            symbol=symbol,
            action="hold",
            strength="hold",
            confidence=0.0,
            target_price=0,
            stop_loss=0,
            strategies_bullish=0,
            strategies_bearish=0,
            strategies_neutral=6,
            reasons=["Insufficient data"],
            indicators={},
            patterns=[],
        )


# ============================================================================
# AutoPilot — 24/7 Autonomous Scanner
# ============================================================================
class AutoPilot:
    """
    24/7 autonomous market scanner that:
    1. Continuously monitors all tracked stocks
    2. Runs technical analysis on each
    3. Generates trading signals
    4. Executes trades via the TradingEngine
    5. Manages positions (stop loss / take profit)
    """

    def __init__(self, strategy_engine: StrategyEngine = None):
        self.strategy = strategy_engine or StrategyEngine()
        self.is_running = False
        self._scan_interval = 60        # Scan every 60 seconds
        self._last_scan: Dict[str, dict] = {}
        self._signal_history: List[dict] = []
        self._scan_count = 0
        self._start_time: Optional[datetime] = None

    async def start(
        self,
        market_engine,           # MarketDataEngine instance
        trading_engine=None,     # TradingEngine instance (optional)
        tickers: List[str] = None,
    ):
        """Start the 24/7 scanning loop."""
        if self.is_running:
            print("[AUTOPILOT] Already running")
            return

        self.is_running = True
        self._start_time = datetime.now()
        print(f"[AUTOPILOT] 🚀 ENGAGED — scanning {len(tickers or [])} stocks")
        print(f"[AUTOPILOT] Scan interval: {self._scan_interval}s")
        print(f"[AUTOPILOT] Auto-trade: {'ENABLED' if trading_engine else 'DISABLED (signals only)'}")

        while self.is_running:
            try:
                await self._scan_cycle(market_engine, trading_engine, tickers)
                self._scan_count += 1
            except Exception as e:
                print(f"[AUTOPILOT] Scan error: {e}")

            await asyncio.sleep(self._scan_interval)

    def stop(self):
        """Stop the autopilot."""
        self.is_running = False
        runtime = datetime.now() - self._start_time if self._start_time else timedelta(0)
        print(f"[AUTOPILOT] 🛑 DISENGAGED — {self._scan_count} scans in {runtime}")

    async def scan_once(
        self,
        market_engine,
        tickers: List[str],
    ) -> List[TradingSignal]:
        """Run a single scan without the loop (for API calls)."""
        signals = []
        for ticker in tickers:
            try:
                history = await market_engine.get_history(ticker, period="3mo", interval="1d")
                if not history:
                    continue

                closes = [b.close for b in history]
                highs = [b.high for b in history]
                lows = [b.low for b in history]
                opens = [b.open for b in history]
                volumes = [b.volume for b in history]

                signal = self.strategy.generate_signal(
                    symbol=ticker,
                    closes=closes,
                    highs=highs,
                    lows=lows,
                    opens=opens,
                    volumes=volumes,
                )
                signals.append(signal)

                self._last_scan[ticker] = asdict(signal)
            except Exception as e:
                print(f"[AUTOPILOT] Scan error for {ticker}: {e}")

        # Sort by confidence (strongest signals first)
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals

    async def _scan_cycle(self, market_engine, trading_engine, tickers):
        """Single scan cycle — analyze all stocks."""
        if not tickers:
            return

        signals = await self.scan_once(market_engine, tickers)

        # Log actionable signals
        actionable = [s for s in signals if s.action != "hold" and s.confidence >= 0.5]
        if actionable:
            print(f"\n[AUTOPILOT] ── Scan #{self._scan_count + 1} ─────────────────")
            for sig in actionable[:5]:  # Top 5
                icon = "🟢" if sig.action == "buy" else "🔴"
                print(
                    f"  {icon} {sig.symbol}: {sig.strength.upper()} "
                    f"({sig.confidence*100:.0f}%) — {sig.reasons[0] if sig.reasons else ''}"
                )

        # Execute trades if trading engine is available
        if trading_engine:
            for signal in actionable:
                if signal.confidence >= trading_engine.risk.min_confidence:
                    await trading_engine.execute_signal(
                        symbol=signal.symbol,
                        signal=signal.action,
                        confidence=signal.confidence,
                        current_price=signal.indicators.get("price", 0),
                        reason="; ".join(signal.reasons[:2]),
                    )

            # Check stop loss / take profit on existing positions
            for pos in list(trading_engine._positions.values()):
                quote = await market_engine.get_quote(pos.symbol)
                if quote:
                    await trading_engine.check_stop_loss_take_profit(
                        pos.symbol, quote.price
                    )

        # Store signal history (keep last 500)
        for sig in signals:
            self._signal_history.append(asdict(sig))
        self._signal_history = self._signal_history[-500:]

    def get_status(self) -> dict:
        """Get autopilot status."""
        uptime = str(datetime.now() - self._start_time) if self._start_time else "0:00:00"

        # Find top opportunities
        top_buys = sorted(
            [s for s in self._last_scan.values() if s.get("action") == "buy"],
            key=lambda x: x.get("confidence", 0),
            reverse=True,
        )[:5]

        top_sells = sorted(
            [s for s in self._last_scan.values() if s.get("action") == "sell"],
            key=lambda x: x.get("confidence", 0),
            reverse=True,
        )[:5]

        return {
            "is_running": self.is_running,
            "uptime": uptime,
            "scan_count": self._scan_count,
            "scan_interval_seconds": self._scan_interval,
            "stocks_tracked": len(self._last_scan),
            "top_buy_signals": top_buys,
            "top_sell_signals": top_sells,
            "recent_signals": self._signal_history[-20:],
        }

    def get_signal(self, symbol: str) -> Optional[dict]:
        """Get the latest signal for a specific stock."""
        return self._last_scan.get(symbol)
