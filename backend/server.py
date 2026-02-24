"""
StockPulse AI — Autonomous Trading Terminal v3.0
──────────────────────────────────────────────────
Live market data • AI prediction brain • Autonomous trading
24/7 scanning • Multi-strategy signals • Risk management
──────────────────────────────────────────────────
"""
import asyncio
import json
import random
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import asdict

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from market_data import MarketDataEngine
from trading_engine import TradingEngine, Position as TradePosition
from ai_brain import StrategyEngine, AutoPilot, TechnicalAnalyzer, PatternDetector
from email_alerts import email_engine

# ============================================================================
# Configuration
# ============================================================================
STOCKS_FILE = Path(__file__).parent.parent / "data" / "stocks.json"
UPDATE_INTERVAL = 2.0  # Seconds between prediction updates

app = FastAPI(
    title="StockPulse AI API",
    description="Real-time stock predictions and alerts via WebSocket",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Data Models
# ============================================================================
class Stock(BaseModel):
    ticker: str
    name: str
    sector: str
    aiScore: int
    price: float
    change1D: float
    change1W: float
    change1M: float
    sentiment: str
    marketCap: str

class Prediction(BaseModel):
    symbol: str
    direction: str  # bullish, bearish, neutral
    confidence: float
    target_price: float
    support_level: float
    resistance_level: float
    pattern: Optional[str] = None
    timestamp: str

class Alert(BaseModel):
    id: str
    symbol: str
    type: str  # price_above, price_below, volume_spike, pattern, confidence
    condition: str
    value: float
    priority: str  # low, medium, high, critical
    triggered: bool = False
    created_at: str

class AlertTrigger(BaseModel):
    alert_id: str
    symbol: str
    message: str
    priority: str
    prediction: Optional[Prediction] = None
    timestamp: str

# ============================================================================
# In-Memory State
# ============================================================================
stocks_data: List[Dict] = []
active_alerts: List[Alert] = []
connected_clients: Dict[str, List[WebSocket]] = {}  # symbol -> [websockets]
global_clients: List[WebSocket] = []  # For broadcast alerts

# ── Engine Instances ──────────────────────────────────────────
market_engine = MarketDataEngine()
trading_engine = TradingEngine()
strategy_engine = StrategyEngine()
autopilot = AutoPilot(strategy_engine)
LIVE_DATA_ENABLED = True      # Toggle live vs simulated
AUTOTRADE_ENABLED = False     # Toggle autonomous trading (requires Alpaca keys)

def load_stocks():
    """Load stocks from JSON file"""
    global stocks_data
    try:
        with open(STOCKS_FILE, 'r') as f:
            stocks_data = json.load(f)
        print(f"[OK] Loaded {len(stocks_data)} stocks from {STOCKS_FILE}")
    except Exception as e:
        print(f"[!] Failed to load stocks: {e}")
        stocks_data = []

async def refresh_live_prices():
    """Refresh all stock prices from live sources."""
    global stocks_data
    if not LIVE_DATA_ENABLED:
        return
    try:
        stocks_data = await market_engine.update_stocks_data(stocks_data)
    except Exception as e:
        print(f"[!] Live data refresh failed: {e}")

# ============================================================================
# Technical Analysis (Simulated - Replace with real ML models)
# ============================================================================
def calculate_technical_indicators(stock: Dict) -> Dict:
    """Calculate technical indicators for a stock"""
    price = stock['price']
    change_1d = stock['change1D']
    ai_score = stock['aiScore']
    
    # Simulated technical indicators
    rsi = min(100, max(0, 50 + change_1d * 5 + random.uniform(-10, 10)))
    macd = change_1d * 0.5 + random.uniform(-0.5, 0.5)
    bollinger_position = random.uniform(-1, 1)  # -1 = lower band, 1 = upper band
    volume_ratio = 1 + random.uniform(-0.3, 0.5)
    
    return {
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd * 0.8,
        "bollinger_position": bollinger_position,
        "volume_ratio": volume_ratio,
        "sma_20": price * (1 - random.uniform(0, 0.05)),
        "sma_50": price * (1 - random.uniform(0, 0.1)),
        "ema_12": price * (1 + random.uniform(-0.02, 0.02)),
    }

def detect_patterns(stock: Dict, indicators: Dict) -> Optional[str]:
    """Detect chart patterns"""
    patterns = [
        ("Head & Shoulders", 0.08),
        ("Double Top", 0.1),
        ("Double Bottom", 0.1),
        ("Ascending Triangle", 0.12),
        ("Descending Triangle", 0.12),
        ("Bull Flag", 0.15),
        ("Bear Flag", 0.15),
        ("Cup and Handle", 0.05),
        ("Breakout", 0.2),
        ("Breakdown", 0.15),
    ]
    
    # Random pattern detection (replace with real pattern recognition)
    if random.random() < 0.3:  # 30% chance of detecting a pattern
        pattern, _ = random.choices(patterns, weights=[p[1] for p in patterns])[0]
        return pattern
    return None

def generate_prediction(stock: Dict) -> Prediction:
    """Generate AI prediction for a stock"""
    indicators = calculate_technical_indicators(stock)
    pattern = detect_patterns(stock, indicators)
    
    # Base prediction on AI score and momentum
    base_score = stock['aiScore'] / 100
    momentum = (stock['change1D'] + stock['change1W'] / 5 + stock['change1M'] / 20) / 3
    
    # Calculate confidence (0.0 - 1.0)
    confidence = min(0.99, max(0.3, base_score * 0.7 + abs(momentum) * 0.05 + random.uniform(-0.1, 0.1)))
    
    # Determine direction
    if momentum > 1 and indicators['rsi'] < 70:
        direction = "bullish"
    elif momentum < -1 and indicators['rsi'] > 30:
        direction = "bearish"
    else:
        direction = "neutral" if abs(momentum) < 0.5 else ("bullish" if momentum > 0 else "bearish")
    
    # Calculate price targets
    price = stock['price']
    volatility = abs(stock['change1D']) / 100 + 0.02
    
    if direction == "bullish":
        target = price * (1 + volatility * (1 + confidence))
        support = price * (1 - volatility * 0.5)
        resistance = price * (1 + volatility * 2)
    elif direction == "bearish":
        target = price * (1 - volatility * (1 + confidence))
        support = price * (1 - volatility * 2)
        resistance = price * (1 + volatility * 0.5)
    else:
        target = price
        support = price * (1 - volatility)
        resistance = price * (1 + volatility)
    
    return Prediction(
        symbol=stock['ticker'],
        direction=direction,
        confidence=round(confidence, 4),
        target_price=round(target, 2),
        support_level=round(support, 2),
        resistance_level=round(resistance, 2),
        pattern=pattern,
        timestamp=datetime.now().isoformat()
    )

# ============================================================================
# Alert System
# ============================================================================
def check_alerts(stock: Dict, prediction: Prediction) -> List[AlertTrigger]:
    """Check if any alerts should be triggered"""
    triggered = []
    
    for alert in active_alerts:
        if alert.triggered or alert.symbol != stock['ticker']:
            continue
        
        should_trigger = False
        message = ""
        
        if alert.type == "price_above" and stock['price'] >= alert.value:
            should_trigger = True
            message = f"{stock['ticker']} price ${stock['price']:.2f} exceeded ${alert.value:.2f}"
        
        elif alert.type == "price_below" and stock['price'] <= alert.value:
            should_trigger = True
            message = f"{stock['ticker']} price ${stock['price']:.2f} dropped below ${alert.value:.2f}"
        
        elif alert.type == "confidence" and prediction.confidence * 100 >= alert.value:
            should_trigger = True
            message = f"{stock['ticker']} AI confidence {prediction.confidence*100:.1f}% exceeded {alert.value}%"
        
        elif alert.type == "pattern" and prediction.pattern:
            should_trigger = True
            message = f"{stock['ticker']} pattern detected: {prediction.pattern}"
        
        if should_trigger:
            alert.triggered = True
            triggered.append(AlertTrigger(
                alert_id=alert.id,
                symbol=stock['ticker'],
                message=message,
                priority=alert.priority,
                prediction=prediction,
                timestamp=datetime.now().isoformat()
            ))
    
    return triggered

# ============================================================================
# WebSocket Connection Manager
# ============================================================================
class ConnectionManager:
    def __init__(self):
        self.symbol_connections: Dict[str, List[WebSocket]] = {}
        self.global_connections: List[WebSocket] = []
    
    async def connect_symbol(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.symbol_connections:
            self.symbol_connections[symbol] = []
        self.symbol_connections[symbol].append(websocket)
        print(f"[+] Client connected to {symbol} stream")
    
    async def connect_global(self, websocket: WebSocket):
        await websocket.accept()
        self.global_connections.append(websocket)
        print("[+] Client connected to global stream")
    
    def disconnect_symbol(self, websocket: WebSocket, symbol: str):
        if symbol in self.symbol_connections:
            self.symbol_connections[symbol].remove(websocket)
            print(f"[-] Client disconnected from {symbol} stream")
    
    def disconnect_global(self, websocket: WebSocket):
        self.global_connections.remove(websocket)
        print("[-] Client disconnected from global stream")
    
    async def broadcast_to_symbol(self, symbol: str, message: dict):
        if symbol in self.symbol_connections:
            for connection in self.symbol_connections[symbol]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast_global(self, message: dict):
        for connection in self.global_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ============================================================================
# API Endpoints
# ============================================================================
@app.on_event("startup")
async def startup():
    load_stocks()
    # Fetch live prices on startup
    await refresh_live_prices()
    # Initialize trading engine
    await trading_engine.initialize()
    # Start background price refresh (every 60 seconds)
    asyncio.create_task(background_price_refresh())
    # Start 24/7 AutoPilot scanner
    tickers = [s["ticker"] for s in stocks_data]
    trade_engine = trading_engine if AUTOTRADE_ENABLED else None
    asyncio.create_task(autopilot.start(market_engine, trade_engine, tickers))
    print(f"[AUTOPILOT] Scanning {len(tickers)} stocks")
    print(f"[AUTOTRADE] {'ENABLED — live execution' if AUTOTRADE_ENABLED else 'DISABLED — signals only'}")
    # Start email scheduler for Dusty (Tuesday + Wednesday alerts)
    email_engine.start_scheduler()

async def background_price_refresh():
    """Periodically refresh stock prices in the background."""
    while True:
        await asyncio.sleep(60)  # Refresh every 60 seconds
        try:
            await refresh_live_prices()
        except Exception as e:
            print(f"[!] Background refresh error: {e}")

@app.get("/")
async def root():
    return {
        "message": "StockPulse AI API",
        "version": "2.0.0",
        "stocks": len(stocks_data),
        "live_data": LIVE_DATA_ENABLED,
    }

@app.get("/api/stocks")
async def get_stocks():
    return stocks_data

@app.get("/api/stocks/{symbol}")
async def get_stock(symbol: str):
    stock = next((s for s in stocks_data if s['ticker'].upper() == symbol.upper()), None)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

@app.get("/api/predict/{symbol}")
async def get_prediction(symbol: str):
    stock = next((s for s in stocks_data if s['ticker'].upper() == symbol.upper()), None)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return generate_prediction(stock)

# ── Live Market Data Endpoints ───────────────────────────────

@app.get("/api/market/summary")
async def market_summary():
    """Get major indices (S&P 500, Dow, NASDAQ, etc.)."""
    return await market_engine.get_market_summary()

@app.get("/api/market/refresh")
async def force_refresh():
    """Force refresh all prices from live sources."""
    await refresh_live_prices()
    return {"status": "refreshed", "stocks": len(stocks_data), "timestamp": datetime.now().isoformat()}

@app.get("/api/history/{symbol}")
async def get_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    """Get historical OHLCV data for charting."""
    bars = await market_engine.get_history(symbol.upper(), period, interval)
    return [{"date": b.date, "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume} for b in bars]

@app.get("/api/news")
async def get_news(symbol: str = "", limit: int = 10):
    """Get market news (optionally filtered by symbol)."""
    articles = await market_engine.get_news(symbol.upper() if symbol else "", limit)
    return [asdict(a) for a in articles]

@app.get("/api/quote/{symbol}")
async def get_live_quote(symbol: str):
    """Get a single real-time quote with full details."""
    quote = await market_engine.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not available")
    return asdict(quote)

# ── Alert Endpoints ──────────────────────────────────────────

@app.post("/api/alerts")
async def create_alert(alert: Alert):
    active_alerts.append(alert)
    return {"status": "created", "alert": alert}

@app.get("/api/alerts")
async def get_alerts():
    return active_alerts

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    global active_alerts
    active_alerts = [a for a in active_alerts if a.id != alert_id]
    return {"status": "deleted"}

# ══════════════════════════════════════════════════════════════
# Trading & AutoPilot Endpoints
# ══════════════════════════════════════════════════════════════

@app.get("/api/portfolio")
async def get_portfolio():
    """Get full portfolio summary: capital, positions, P&L."""
    return trading_engine.get_portfolio_summary()

@app.get("/api/positions")
async def get_positions():
    """Get all open positions."""
    return trading_engine.get_positions()

@app.get("/api/trades")
async def get_trades(limit: int = 50):
    """Get trade history."""
    return trading_engine.get_trade_history(limit)

@app.post("/api/trade/buy/{symbol}")
async def manual_buy(symbol: str, qty: int = None):
    """Manually buy a stock."""
    quote = await market_engine.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not available")
    if qty is None:
        max_spend = trading_engine.risk.available_cash * 0.05
        qty = int(max_spend / quote.price) if quote.price > 0 else 0
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Insufficient capital")
    order = await trading_engine.place_order(
        symbol=symbol.upper(), side="buy", qty=qty,
        order_type="market", reason="Manual buy via API",
    )
    if order:
        order.filled_price = quote.price
        trading_engine._positions[symbol.upper()] = TradePosition(
            symbol=symbol.upper(), qty=qty,
            avg_entry_price=quote.price,
            current_price=quote.price,
            market_value=qty * quote.price,
            stop_loss=round(quote.price * 0.95, 2),
            take_profit=round(quote.price * 1.15, 2),
            opened_at=datetime.now().isoformat(),
        )
        trading_engine.risk.available_cash -= qty * quote.price
    return asdict(order) if order else {"error": "Order failed"}

@app.post("/api/trade/sell/{symbol}")
async def manual_sell(symbol: str):
    """Manually sell all shares of a stock."""
    pos = trading_engine._positions.get(symbol.upper())
    if not pos:
        raise HTTPException(status_code=404, detail="No position found")
    quote = await market_engine.get_quote(symbol.upper())
    price = quote.price if quote else pos.current_price
    order = await trading_engine.place_order(
        symbol=symbol.upper(), side="sell", qty=pos.qty,
        order_type="market", reason="Manual sell via API",
    )
    if order:
        order.filled_price = price
        trading_engine.risk.available_cash += pos.qty * price
        del trading_engine._positions[symbol.upper()]
    return asdict(order) if order else {"error": "Order failed"}

@app.get("/api/risk")
async def get_risk_config():
    """Get current risk management configuration."""
    return asdict(trading_engine.risk)

@app.post("/api/risk")
async def update_risk(
    max_position_pct: float = None,
    stop_loss_pct: float = None,
    take_profit_pct: float = None,
    max_daily_trades: int = None,
    min_confidence: float = None,
):
    """Update risk management parameters."""
    updates = {}
    if max_position_pct is not None:
        updates["max_position_pct"] = max_position_pct
    if stop_loss_pct is not None:
        updates["stop_loss_pct"] = stop_loss_pct
    if take_profit_pct is not None:
        updates["take_profit_pct"] = take_profit_pct
    if max_daily_trades is not None:
        updates["max_daily_trades"] = max_daily_trades
    if min_confidence is not None:
        updates["min_confidence"] = min_confidence
    trading_engine.update_risk_config(**updates)
    return asdict(trading_engine.risk)

# ── AutoPilot & AI Signal Endpoints ──────────────────────────

@app.get("/api/autopilot/status")
async def autopilot_status():
    """Get AutoPilot scanner status."""
    return autopilot.get_status()

@app.post("/api/autopilot/start")
async def autopilot_start():
    """Start the AutoPilot 24/7 scanner."""
    if autopilot.is_running:
        return {"status": "already_running"}
    tickers = [s["ticker"] for s in stocks_data]
    trade_engine = trading_engine if AUTOTRADE_ENABLED else None
    asyncio.create_task(autopilot.start(market_engine, trade_engine, tickers))
    return {"status": "started", "stocks": len(tickers)}

@app.post("/api/autopilot/stop")
async def autopilot_stop():
    """Stop the AutoPilot scanner."""
    autopilot.stop()
    return {"status": "stopped"}

@app.get("/api/signals")
async def get_all_signals():
    """Get latest AI signals for all tracked stocks."""
    return autopilot.get_status().get("recent_signals", [])

@app.get("/api/signals/{symbol}")
async def get_signal(symbol: str):
    """Get AI signal for a specific stock."""
    sig = autopilot.get_signal(symbol.upper())
    if sig:
        return sig
    # Generate on demand if not cached
    tickers = [symbol.upper()]
    signals = await autopilot.scan_once(market_engine, tickers)
    if signals:
        return asdict(signals[0])
    raise HTTPException(status_code=404, detail="No signal available")

@app.get("/api/scan")
async def scan_market():
    """Run a full market scan NOW and return all signals sorted by confidence."""
    tickers = [s["ticker"] for s in stocks_data]
    signals = await autopilot.scan_once(market_engine, tickers)
    return {
        "timestamp": datetime.now().isoformat(),
        "total": len(signals),
        "buy_signals": [asdict(s) for s in signals if s.action == "buy"],
        "sell_signals": [asdict(s) for s in signals if s.action == "sell"],
        "hold": [asdict(s) for s in signals if s.action == "hold"],
    }

@app.post("/api/autotrade/enable")
async def enable_autotrade():
    """Enable autonomous trading (requires Alpaca keys)."""
    global AUTOTRADE_ENABLED
    if not trading_engine._is_live:
        return {"error": "Alpaca API keys required. Set ALPACA_API_KEY in .env"}
    AUTOTRADE_ENABLED = True
    return {"status": "enabled", "mode": "paper" if __import__('os').getenv('ALPACA_PAPER', 'true').lower() == 'true' else "live"}

@app.post("/api/autotrade/disable")
async def disable_autotrade():
    """Disable autonomous trading (signals only)."""
    global AUTOTRADE_ENABLED
    AUTOTRADE_ENABLED = False
    return {"status": "disabled"}

@app.get("/api/analyze/{symbol}")
async def deep_analyze(symbol: str):
    """Run deep technical analysis on a single stock."""
    history = await market_engine.get_history(symbol.upper(), period="3mo", interval="1d")
    if not history:
        raise HTTPException(status_code=404, detail="No history available")
    closes = [b.close for b in history]
    highs = [b.high for b in history]
    lows = [b.low for b in history]
    opens = [b.open for b in history]
    volumes = [b.volume for b in history]
    signal = strategy_engine.generate_signal(
        symbol=symbol.upper(),
        closes=closes, highs=highs, lows=lows,
        opens=opens, volumes=volumes,
    )
    return asdict(signal)

# ============================================================================
# WebSocket Endpoints
# ============================================================================
@app.websocket("/ws/predict/{symbol}")
async def websocket_predict(websocket: WebSocket, symbol: str):
    """Stream real-time predictions for a specific symbol"""
    stock = next((s for s in stocks_data if s['ticker'].upper() == symbol.upper()), None)
    if not stock:
        await websocket.close(code=4004)
        return
    
    await manager.connect_symbol(websocket, symbol)
    
    try:
        while True:
            # Fetch live price (or simulate if live data is off)
            if LIVE_DATA_ENABLED:
                live = await market_engine.get_quote(symbol)
                if live:
                    stock['price'] = live.price
                    stock['change1D'] = live.change_1d
            else:
                stock['price'] *= (1 + random.uniform(-0.002, 0.002))
                stock['change1D'] += random.uniform(-0.1, 0.1)
            
            # Generate prediction
            prediction = generate_prediction(stock)
            
            # Check alerts
            triggers = check_alerts(stock, prediction)
            
            # Send prediction
            await websocket.send_json({
                "type": "prediction",
                "data": prediction.dict()
            })
            
            # Send triggered alerts
            for trigger in triggers:
                await manager.broadcast_global({
                    "type": "alert_trigger",
                    "data": trigger.dict()
                })
            
            await asyncio.sleep(UPDATE_INTERVAL)
    except WebSocketDisconnect:
        manager.disconnect_symbol(websocket, symbol)

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """Stream all stock updates and alerts"""
    await manager.connect_global(websocket)
    
    try:
        while True:
            updates = []
            
            # Refresh prices from live source periodically
            if LIVE_DATA_ENABLED:
                await refresh_live_prices()

            for stock in stocks_data[:20]:  # Top 20 stocks
                prediction = generate_prediction(stock)
                triggers = check_alerts(stock, prediction)
                
                updates.append({
                    "symbol": stock['ticker'],
                    "price": round(stock['price'], 2),
                    "change": round(stock['change1D'], 2),
                    "prediction": prediction.dict()
                })
                
                for trigger in triggers:
                    await websocket.send_json({
                        "type": "alert_trigger",
                        "data": trigger.dict()
                    })
            
            await websocket.send_json({
                "type": "market_update",
                "data": updates,
                "timestamp": datetime.now().isoformat()
            })
            
            await asyncio.sleep(UPDATE_INTERVAL)
    except WebSocketDisconnect:
        manager.disconnect_global(websocket)

# ============================================================================
# Email Alert Endpoints (Dusty's Tue/Wed Notifications)
# ============================================================================

@app.get("/api/email/config")
async def get_email_config():
    """Get email notification configuration."""
    return email_engine.get_config()

@app.post("/api/email/test")
async def send_test_email(recipient: str = None):
    """Send a test market report email NOW."""
    analyzer = TechnicalAnalyzer()
    detector = PatternDetector()
    report = await email_engine.generate_report(
        market_engine=market_engine,
        analyzer=analyzer,
        detector=detector,
        strategy_engine=strategy_engine,
        stocks_data=stocks_data,
    )
    success = email_engine.send_alert(report, recipient)
    return {
        "status": "sent" if success else "failed",
        "signals": len(report.top_signals),
        "patterns": len(report.pattern_detections),
        "alerts": len(report.risk_alerts),
        "watchlist": len(report.watchlist_movers),
    }

@app.get("/api/email/log")
async def get_email_log(limit: int = 20):
    """Get email dispatch history."""
    return email_engine.get_log(limit)

@app.post("/api/email/schedule/start")
async def start_email_schedule():
    """Start the Tuesday/Wednesday email scheduler."""
    success = email_engine.start_scheduler()
    return {"status": "started" if success else "failed", "config": email_engine.get_config()}

@app.post("/api/email/schedule/stop")
async def stop_email_schedule():
    """Stop the email scheduler."""
    email_engine.stop_scheduler()
    return {"status": "stopped"}

@app.get("/api/email/preview")
async def preview_email():
    """Generate and preview the email report (returns HTML). Uses cached data for speed."""
    from fastapi.responses import HTMLResponse
    report = email_engine.generate_preview(stocks_data)
    html = email_engine._build_html(report)
    return HTMLResponse(content=html)

# ============================================================================
# Static Files (Serve Frontend)
# ============================================================================
frontend_dir = Path(__file__).parent.parent / "stockpulse"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

@app.get("/dashboard")
async def serve_dashboard():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Dashboard not found")

# ============================================================================
# Run Server
# ============================================================================
if __name__ == "__main__":
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║         StockPulse AI — Autonomous Terminal v3.1        ║
    ╠══════════════════════════════════════════════════════════╣
    ║  LIVE MARKET DATA     ✅  yfinance + Finnhub            ║
    ║  AI PREDICTION BRAIN  ✅  6-strategy signal engine       ║
    ║  24/7 AUTOPILOT       ✅  Continuous market scanner      ║
    ║  TRADING ENGINE       ✅  Alpaca paper/live trading      ║
    ║  RISK MANAGEMENT      ✅  Stop loss, take profit, limits ║
    ║  EMAIL ALERTS         ✅  Tue/Wed scheduled reports      ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Dashboard:  http://localhost:8000/dashboard             ║
    ║  API Docs:   http://localhost:8000/docs                  ║
    ║  Email:      http://localhost:8000/api/email/preview     ║
    ╠══════════════════════════════════════════════════════════╣
    ║  📊 /api/stocks        — Live prices                     ║
    ║  📈 /api/signals       — AI buy/sell signals             ║
    ║  🤖 /api/autopilot/*   — 24/7 scanner control            ║
    ║  💰 /api/portfolio     — Portfolio & positions            ║
    ║  📉 /api/trade/buy/*   — Manual buy/sell                  ║
    ║  🔍 /api/analyze/*     — Deep technical analysis          ║
    ║  🔄 /api/scan          — Full market scan                 ║
    ║  📧 /api/email/*       — Email alert control             ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
