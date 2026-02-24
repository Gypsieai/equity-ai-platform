"""
StockPulse AI — Autonomous Trading Engine
24/7 automated stock trading with AI-driven buy/sell decisions.

Broker: Alpaca Markets (https://alpaca.markets/)
  - Commission-free stock & crypto trading
  - Paper trading mode for testing (no real money)
  - RESTful API + WebSocket streaming
  - Supports market, limit, stop, and bracket orders

Setup:
  1. Sign up at https://alpaca.markets/ (free)
  2. Get API keys from dashboard (paper + live)
  3. Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env
  4. Set ALPACA_PAPER=true for paper trading (default)
"""

import os
import json
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# ============================================================================
# Configuration
# ============================================================================
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

# Alpaca base URLs
ALPACA_BASE = (
    "https://paper-api.alpaca.markets" if ALPACA_PAPER
    else "https://api.alpaca.markets"
)
ALPACA_DATA_BASE = "https://data.alpaca.markets"

DATA_DIR = Path(__file__).parent.parent / "data"
TRADES_LOG = DATA_DIR / "trades.json"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"

# ── Risk Management Defaults ────────────────────────────────
DEFAULT_MAX_POSITION_SIZE = 0.10      # Max 10% of portfolio per stock
DEFAULT_STOP_LOSS_PCT = 0.05          # 5% stop loss
DEFAULT_TAKE_PROFIT_PCT = 0.15        # 15% take profit
DEFAULT_MAX_DAILY_TRADES = 10         # Max trades per day
DEFAULT_MIN_CONFIDENCE = 0.70         # Minimum AI confidence to trade
COOLDOWN_AFTER_LOSS_MINUTES = 30      # Wait after a losing trade


# ============================================================================
# Data Models
# ============================================================================
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    SIMULATED = "simulated"

@dataclass
class TradeOrder:
    """Represents a buy/sell order."""
    id: str
    symbol: str
    side: str           # buy / sell
    order_type: str     # market / limit / stop
    qty: float
    price: Optional[float] = None      # For limit orders
    stop_price: Optional[float] = None # For stop orders
    status: str = "pending"
    filled_price: float = 0.0
    filled_at: str = ""
    reason: str = ""                   # Why the AI made this trade
    confidence: float = 0.0
    created_at: str = ""
    broker_order_id: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Position:
    """Active stock position."""
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    opened_at: str = ""


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_position_pct: float = DEFAULT_MAX_POSITION_SIZE
    stop_loss_pct: float = DEFAULT_STOP_LOSS_PCT
    take_profit_pct: float = DEFAULT_TAKE_PROFIT_PCT
    max_daily_trades: int = DEFAULT_MAX_DAILY_TRADES
    min_confidence: float = DEFAULT_MIN_CONFIDENCE
    cooldown_minutes: int = COOLDOWN_AFTER_LOSS_MINUTES
    # Capital allocation
    total_capital: float = 0.0    # Set from Alpaca account
    available_cash: float = 0.0


# ============================================================================
# Trading Engine
# ============================================================================
class TradingEngine:
    """
    Autonomous trading engine with risk management.
    Integrates with Alpaca for real/paper trading.
    Falls back to simulated trading if no API keys.
    """

    def __init__(self):
        self.risk = RiskConfig()
        self._trades: List[dict] = []
        self._positions: Dict[str, Position] = {}
        self._daily_trade_count = 0
        self._last_loss_time: Optional[datetime] = None
        self._is_live = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)
        self._trading_client = None
        self._data_client = None

        if self._is_live:
            self._trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=ALPACA_PAPER)
            self._data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
            mode = "PAPER" if ALPACA_PAPER else "🔴 LIVE"
            print(f"[TRADE] Alpaca connected ({mode} mode)")
        else:
            print("[TRADE] ⚠️ No Alpaca keys — running in SIMULATION mode")
            print("[TRADE]    Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env")

        self._load_trade_log()

    # ── Public API ───────────────────────────────────────────

    async def initialize(self):
        """Fetch account info and sync positions from broker."""
        if self._is_live:
            account = await self._get_account()
            if account:
                self.risk.total_capital = float(account.get("portfolio_value", 0))
                self.risk.available_cash = float(account.get("buying_power", 0))
                print(f"[TRADE] Portfolio: ${self.risk.total_capital:,.2f}")
                print(f"[TRADE] Buying power: ${self.risk.available_cash:,.2f}")

            # Sync positions
            await self._sync_positions()
        else:
            # Simulation defaults
            self.risk.total_capital = 100_000.00  # $100K paper money
            self.risk.available_cash = 100_000.00
            print(f"[TRADE] Simulated capital: ${self.risk.total_capital:,.2f}")

    async def execute_signal(
        self,
        symbol: str,
        signal: Literal["buy", "sell", "hold"],
        confidence: float,
        current_price: float,
        reason: str = "",
    ) -> Optional[TradeOrder]:
        """
        Execute a trading signal from the AI predictor.
        Returns the order if executed, None if rejected by risk checks.
        """
        # ── Risk Checks ─────────────────────────────────────
        if signal == "hold":
            return None

        if confidence < self.risk.min_confidence:
            return None  # Not confident enough

        if self._daily_trade_count >= self.risk.max_daily_trades:
            print(f"[TRADE] Daily limit reached ({self.risk.max_daily_trades})")
            return None

        # Cooldown after loss
        if self._last_loss_time:
            elapsed = (datetime.now() - self._last_loss_time).total_seconds() / 60
            if elapsed < self.risk.cooldown_minutes:
                return None

        # ── BUY Logic ────────────────────────────────────────
        if signal == "buy":
            # Check if already holding
            if symbol in self._positions:
                return None  # Already in position

            # Calculate position size
            max_spend = self.risk.available_cash * self.risk.max_position_pct
            qty = int(max_spend / current_price) if current_price > 0 else 0
            if qty <= 0:
                return None  # Not enough capital

            # Calculate stop loss and take profit
            stop_loss = round(current_price * (1 - self.risk.stop_loss_pct), 2)
            take_profit = round(current_price * (1 + self.risk.take_profit_pct), 2)

            order = await self.place_order(
                symbol=symbol,
                side="buy",
                qty=qty,
                order_type="market",
                reason=reason or f"AI BUY signal ({confidence*100:.0f}% confidence)",
                confidence=confidence,
            )

            if order and order.status in ("filled", "simulated"):
                # Track position
                self._positions[symbol] = Position(
                    symbol=symbol,
                    qty=qty,
                    avg_entry_price=order.filled_price or current_price,
                    current_price=current_price,
                    market_value=qty * current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    opened_at=datetime.now().isoformat(),
                )
                self.risk.available_cash -= qty * current_price

            return order

        # ── SELL Logic ───────────────────────────────────────
        elif signal == "sell":
            if symbol not in self._positions:
                return None  # Nothing to sell

            position = self._positions[symbol]
            order = await self.place_order(
                symbol=symbol,
                side="sell",
                qty=position.qty,
                order_type="market",
                reason=reason or f"AI SELL signal ({confidence*100:.0f}% confidence)",
                confidence=confidence,
            )

            if order and order.status in ("filled", "simulated"):
                # Calculate P&L
                sell_price = order.filled_price or current_price
                pl = (sell_price - position.avg_entry_price) * position.qty
                self.risk.available_cash += position.qty * sell_price

                if pl < 0:
                    self._last_loss_time = datetime.now()

                del self._positions[symbol]

            return order

        return None

    async def check_stop_loss_take_profit(self, symbol: str, current_price: float):
        """Check if any position hits stop loss or take profit."""
        if symbol not in self._positions:
            return

        pos = self._positions[symbol]
        pos.current_price = current_price
        pos.market_value = pos.qty * current_price
        pos.unrealized_pl = (current_price - pos.avg_entry_price) * pos.qty
        pos.unrealized_pl_pct = ((current_price - pos.avg_entry_price) / pos.avg_entry_price) * 100

        # Stop Loss
        if current_price <= pos.stop_loss:
            print(f"[TRADE] 🛑 STOP LOSS triggered for {symbol} at ${current_price:.2f}")
            await self.execute_signal(
                symbol, "sell", 1.0, current_price,
                reason=f"Stop loss triggered (${pos.stop_loss:.2f})"
            )

        # Take Profit
        elif current_price >= pos.take_profit:
            print(f"[TRADE] 🎯 TAKE PROFIT triggered for {symbol} at ${current_price:.2f}")
            await self.execute_signal(
                symbol, "sell", 1.0, current_price,
                reason=f"Take profit triggered (${pos.take_profit:.2f})"
            )

    async def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        limit_price: float = None,
        stop_price: float = None,
        reason: str = "",
        confidence: float = 0.0,
    ) -> TradeOrder:
        """Place an order via Alpaca or simulate."""
        order_id = f"ord_{int(time.time())}_{symbol}"

        order = TradeOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            price=limit_price,
            stop_price=stop_price,
            reason=reason,
            confidence=confidence,
        )

        if self._is_live:
            result = await self._alpaca_place_order(order)
            order.broker_order_id = result.get("id", "")
            order.status = result.get("status", "rejected")
            if order.status == "filled":
                order.filled_price = float(result.get("filled_avg_price", 0))
                order.filled_at = result.get("filled_at", datetime.now().isoformat())
        else:
            # Simulate
            order.status = "simulated"
            order.filled_price = limit_price or 0  # Will be set by caller
            order.filled_at = datetime.now().isoformat()

        # Log trade
        self._daily_trade_count += 1
        self._log_trade(order)

        action = "🟢 BUY" if side == "buy" else "🔴 SELL"
        mode = "LIVE" if self._is_live else "SIM"
        print(
            f"[TRADE] {action} {qty}x {symbol} @ ${order.filled_price:.2f} "
            f"({mode}) — {reason}"
        )

        return order

    # ── Account & Position Methods ────────────────────────────

    def get_portfolio_summary(self) -> dict:
        """Get current portfolio state."""
        total_positions_value = sum(
            p.market_value for p in self._positions.values()
        )
        total_unrealized_pl = sum(
            p.unrealized_pl for p in self._positions.values()
        )

        return {
            "total_capital": round(self.risk.total_capital, 2),
            "available_cash": round(self.risk.available_cash, 2),
            "positions_value": round(total_positions_value, 2),
            "unrealized_pl": round(total_unrealized_pl, 2),
            "positions_count": len(self._positions),
            "daily_trades": self._daily_trade_count,
            "max_daily_trades": self.risk.max_daily_trades,
            "mode": "paper" if ALPACA_PAPER else "live" if self._is_live else "simulation",
            "positions": [asdict(p) for p in self._positions.values()],
            "risk_config": asdict(self.risk),
        }

    def get_trade_history(self, limit: int = 50) -> List[dict]:
        """Get recent trade history."""
        return self._trades[-limit:]

    def get_positions(self) -> List[dict]:
        """Get all open positions."""
        return [asdict(p) for p in self._positions.values()]

    def update_risk_config(self, **kwargs):
        """Update risk management parameters."""
        for key, value in kwargs.items():
            if hasattr(self.risk, key):
                setattr(self.risk, key, value)
                print(f"[TRADE] Risk config updated: {key} = {value}")

    # ── Alpaca API Methods ────────────────────────────────────

    async def _get_account(self) -> dict:
        """Get Alpaca account info."""
        try:
            if not self._trading_client:
                return {}
            account = await asyncio.to_thread(self._trading_client.get_account)
            return {
                "portfolio_value": account.portfolio_value,
                "buying_power": account.buying_power
            }
        except Exception as e:
            print(f"[TRADE] Account fetch error: {e}")
            return {}

    async def _sync_positions(self):
        """Sync positions from Alpaca."""
        try:
            if not self._trading_client:
                return
            positions = await asyncio.to_thread(self._trading_client.get_all_positions)

            for pos in positions:
                symbol = pos.symbol
                self._positions[symbol] = Position(
                    symbol=symbol,
                    qty=float(pos.qty),
                    avg_entry_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price) if pos.current_price else 0.0,
                    market_value=float(pos.market_value) if pos.market_value else 0.0,
                    unrealized_pl=float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                    unrealized_pl_pct=float(pos.unrealized_plpc) * 100 if pos.unrealized_plpc else 0.0,
                )
            print(f"[TRADE] Synced {len(positions)} positions from Alpaca")
        except Exception as e:
            print(f"[TRADE] Position sync error: {e}")

    async def _alpaca_place_order(self, order: TradeOrder) -> dict:
        """Place an order via Alpaca trading client."""
        if not self._trading_client:
            return {"status": "rejected", "error": "No trading client"}
            
        try:
            req_kwargs = {
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": AlpacaOrderSide.BUY if order.side.lower() == "buy" else AlpacaOrderSide.SELL,
                "time_in_force": TimeInForce.DAY,
            }

            if order.order_type == "market":
                req = MarketOrderRequest(**req_kwargs)
            elif order.order_type == "limit":
                req = LimitOrderRequest(limit_price=float(order.price) if order.price else 1.0, **req_kwargs)
            elif order.order_type in ("stop", "stop_limit"):
                req = StopOrderRequest(stop_price=float(order.stop_price) if order.stop_price else 1.0, **req_kwargs)
            else:
                return {"status": "rejected", "error": f"Unsupported order type: {order.order_type}"}

            submitted_order = await asyncio.to_thread(self._trading_client.submit_order, req)

            return {
                "id": str(submitted_order.id),
                "status": str(submitted_order.status.value),
                "filled_avg_price": float(submitted_order.filled_avg_price) if submitted_order.filled_avg_price else 0.0,
                "filled_at": submitted_order.filled_at.isoformat() if submitted_order.filled_at else ""
            }
        except Exception as e:
            print(f"[TRADE] Order error: {e}")
            return {"status": "rejected", "error": str(e)}

    async def _get_alpaca_bars(self, symbol: str, timeframe: str = "1Day", limit: int = 30) -> list:
        """Get historical bars from Alpaca Data API."""
        if not self._data_client:
            return []
        try:
            tf_map = {"1Day": TimeFrame.Day, "1Min": TimeFrame.Minute, "1Hour": TimeFrame.Hour}
            tf = tf_map.get(timeframe, TimeFrame.Day)
            
            req = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=tf,
                limit=limit
            )
            bars = await asyncio.to_thread(self._data_client.get_stock_bars, req)
            
            if symbol not in bars.data:
                return []
                
            raw_bars = bars.data[symbol]
            return [
                {
                    "t": bar.timestamp.isoformat(),
                    "o": float(bar.open),
                    "h": float(bar.high),
                    "l": float(bar.low),
                    "c": float(bar.close),
                    "v": float(bar.volume),
                }
                for bar in raw_bars
            ]
        except Exception as e:
            print(f"[TRADE] Bars error for {symbol}: {e}")
            return []

    # ── Trade Logging ─────────────────────────────────────────

    def _log_trade(self, order: TradeOrder):
        """Log a trade to history."""
        self._trades.append(asdict(order))
        self._save_trade_log()

    def _load_trade_log(self):
        """Load trade history from disk."""
        try:
            if TRADES_LOG.exists():
                self._trades = json.loads(
                    TRADES_LOG.read_text(encoding="utf-8")
                )
                print(f"[TRADE] Loaded {len(self._trades)} historical trades")
        except Exception:
            self._trades = []

    def _save_trade_log(self):
        """Persist trade history to disk."""
        try:
            TRADES_LOG.parent.mkdir(parents=True, exist_ok=True)
            TRADES_LOG.write_text(
                json.dumps(self._trades, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[TRADE] Save error: {e}")
