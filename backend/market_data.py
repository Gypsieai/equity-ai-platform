"""
StockPulse AI — Live Market Data Engine
Fetches real-time prices, historical data, and market news from free APIs.

Data Sources (all free tier):
──────────────────────────────────────────────────
│ Provider      │ Rate Limit        │ Data                     │
│ yfinance      │ Unlimited*        │ Price, history, fundamentals │
│ Finnhub       │ 60 req/min        │ Real-time quotes, news   │
│ Alpha Vantage │ 25 req/day        │ Intraday, technicals     │
│ Twelve Data   │ 800 req/day       │ Time series, indicators  │
──────────────────────────────────────────────────
* yfinance uses Yahoo Finance (unofficial, no key)
"""

import os
import json
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

import httpx

# ── Optional imports (graceful degradation) ──────────────────
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("[MARKET] ⚠️ yfinance not installed. Run: pip install yfinance")


# ============================================================================
# Configuration
# ============================================================================
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY", "")

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting
_last_finnhub_call = 0.0
_FINNHUB_MIN_INTERVAL = 1.1  # 60 req/min → ~1 req/sec


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class LiveQuote:
    """Real-time stock quote."""
    ticker: str
    price: float
    change_1d: float          # percent
    change_1w: float
    change_1m: float
    open: float
    high: float
    low: float
    volume: int
    market_cap: str
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    avg_volume: Optional[int] = None
    timestamp: str = ""
    source: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class HistoricalBar:
    """Single OHLCV bar."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class MarketNews:
    """News article."""
    headline: str
    summary: str
    source: str
    url: str
    symbol: str
    sentiment: str  # positive, negative, neutral
    published_at: str


# ============================================================================
# Market Data Engine
# ============================================================================
class MarketDataEngine:
    """
    Unified interface to real market data.
    Falls back gracefully: yfinance → Finnhub → Alpha Vantage → cached data.
    """

    def __init__(self):
        self._quote_cache: Dict[str, dict] = {}
        self._history_cache: Dict[str, list] = {}
        self._cache_ttl = 30  # seconds for quote cache
        self._load_disk_cache()

        sources = []
        if HAS_YFINANCE:
            sources.append("yfinance ✅")
        if FINNHUB_API_KEY:
            sources.append("Finnhub ✅")
        if ALPHA_VANTAGE_KEY:
            sources.append("Alpha Vantage ✅")
        if TWELVE_DATA_KEY:
            sources.append("Twelve Data ✅")
        if not sources:
            sources.append("⚠️ No live sources — using cached/demo data")

        print(f"[MARKET] Data sources: {', '.join(sources)}")

    # ── Public API ───────────────────────────────────────────

    async def get_quote(self, ticker: str) -> Optional[LiveQuote]:
        """Get real-time quote for a single ticker."""
        ticker = ticker.upper()

        # Check memory cache
        cached = self._quote_cache.get(ticker)
        if cached and time.time() - cached["_ts"] < self._cache_ttl:
            return LiveQuote(**{k: v for k, v in cached.items() if k != "_ts"})

        # Try providers in order
        quote = None

        if HAS_YFINANCE:
            quote = await self._yf_quote(ticker)

        if not quote and FINNHUB_API_KEY:
            quote = await self._finnhub_quote(ticker)

        if quote:
            self._cache_quote(ticker, quote)
            return quote

        # Fallback to disk cache
        return self._get_disk_cached_quote(ticker)

    async def get_bulk_quotes(self, tickers: List[str]) -> List[LiveQuote]:
        """Get quotes for multiple tickers efficiently."""
        tickers = [t.upper() for t in tickers]

        if HAS_YFINANCE:
            quotes = await self._yf_bulk_quotes(tickers)
            if quotes:
                for q in quotes:
                    self._cache_quote(q.ticker, q)
                return quotes

        # Fallback: fetch one by one
        results = []
        for ticker in tickers:
            quote = await self.get_quote(ticker)
            if quote:
                results.append(quote)
            await asyncio.sleep(0.1)  # Small delay between calls
        return results

    async def get_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> List[HistoricalBar]:
        """Get historical OHLCV data."""
        ticker = ticker.upper()
        cache_key = f"{ticker}_{period}_{interval}"

        # Check cache (history cached for 5 minutes)
        if cache_key in self._history_cache:
            cached = self._history_cache[cache_key]
            if time.time() - cached["_ts"] < 300:
                return [HistoricalBar(**b) for b in cached["bars"]]

        bars = []

        if HAS_YFINANCE:
            bars = await self._yf_history(ticker, period, interval)

        if not bars and TWELVE_DATA_KEY:
            bars = await self._twelve_data_history(ticker, interval)

        if bars:
            self._history_cache[cache_key] = {
                "bars": [asdict(b) for b in bars],
                "_ts": time.time(),
            }

        return bars

    async def get_news(self, ticker: str = "", limit: int = 10) -> List[MarketNews]:
        """Get market news, optionally for a specific ticker."""
        if FINNHUB_API_KEY:
            return await self._finnhub_news(ticker, limit)
        return []

    async def get_market_summary(self) -> dict:
        """Get overall market summary (indices)."""
        indices = ["^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX"]
        summary = {}

        if HAS_YFINANCE:
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, self._yf_indices, indices)
                summary = data
            except Exception as e:
                print(f"[MARKET] Market summary error: {e}")

        return summary

    async def update_stocks_data(self, stocks_data: List[Dict]) -> List[Dict]:
        """
        Update the existing stocks_data list with live prices.
        This is the main integration point with server.py.
        """
        tickers = [s["ticker"] for s in stocks_data]
        quotes = await self.get_bulk_quotes(tickers)

        quote_map = {q.ticker: q for q in quotes}

        updated = 0
        for stock in stocks_data:
            ticker = stock["ticker"]
            if ticker in quote_map:
                q = quote_map[ticker]
                stock["price"] = q.price
                stock["change1D"] = q.change_1d
                stock["change1W"] = q.change_1w
                stock["change1M"] = q.change_1m
                stock["marketCap"] = q.market_cap
                # Derive sentiment from momentum
                momentum = q.change_1d + q.change_1w / 5
                if momentum > 1.5:
                    stock["sentiment"] = "Bullish"
                elif momentum < -1.5:
                    stock["sentiment"] = "Bearish"
                else:
                    stock["sentiment"] = "Neutral"
                updated += 1

        print(f"[MARKET] Updated {updated}/{len(stocks_data)} stocks with live data")
        self._save_disk_cache()
        return stocks_data

    # ── yfinance Provider ────────────────────────────────────

    async def _yf_quote(self, ticker: str) -> Optional[LiveQuote]:
        """Fetch a single quote via yfinance."""
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self._yf_fetch_info, ticker)
            if not info or "currentPrice" not in info:
                return None

            price = info.get("currentPrice", info.get("regularMarketPrice", 0))
            prev_close = info.get("previousClose", price)
            change_1d = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0

            # Calculate weekly/monthly change from history
            week_change, month_change = await self._yf_period_changes(ticker, price)

            return LiveQuote(
                ticker=ticker,
                price=round(price, 2),
                change_1d=change_1d,
                change_1w=week_change,
                change_1m=month_change,
                open=round(info.get("open", info.get("regularMarketOpen", 0)), 2),
                high=round(info.get("dayHigh", info.get("regularMarketDayHigh", 0)), 2),
                low=round(info.get("dayLow", info.get("regularMarketDayLow", 0)), 2),
                volume=info.get("volume", info.get("regularMarketVolume", 0)) or 0,
                market_cap=self._format_market_cap(info.get("marketCap", 0)),
                pe_ratio=info.get("trailingPE"),
                dividend_yield=info.get("dividendYield"),
                week_52_high=info.get("fiftyTwoWeekHigh"),
                week_52_low=info.get("fiftyTwoWeekLow"),
                avg_volume=info.get("averageVolume"),
                source="yfinance",
            )
        except Exception as e:
            print(f"[MARKET] yfinance error for {ticker}: {e}")
            return None

    def _yf_fetch_info(self, ticker: str) -> dict:
        """Synchronous yfinance fetch (runs in executor)."""
        stock = yf.Ticker(ticker)
        return stock.info

    async def _yf_period_changes(self, ticker: str, current_price: float) -> tuple:
        """Calculate 1W and 1M percentage changes."""
        try:
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(
                None, lambda: yf.Ticker(ticker).history(period="1mo")
            )
            if hist.empty:
                return (0.0, 0.0)

            closes = hist["Close"].tolist()
            month_ago_price = closes[0] if closes else current_price
            week_ago_price = closes[-5] if len(closes) >= 5 else closes[0]

            week_change = round(
                ((current_price - week_ago_price) / week_ago_price) * 100, 2
            ) if week_ago_price else 0.0

            month_change = round(
                ((current_price - month_ago_price) / month_ago_price) * 100, 2
            ) if month_ago_price else 0.0

            return (week_change, month_change)
        except Exception:
            return (0.0, 0.0)

    async def _yf_bulk_quotes(self, tickers: List[str]) -> List[LiveQuote]:
        """Bulk fetch via yfinance (more efficient)."""
        try:
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, self._yf_bulk_fetch, tickers)
            return raw
        except Exception as e:
            print(f"[MARKET] yfinance bulk error: {e}")
            return []

    def _yf_bulk_fetch(self, tickers: List[str]) -> List[LiveQuote]:
        """Synchronous bulk fetch."""
        results = []
        ticker_str = " ".join(tickers)

        data = yf.download(
            ticker_str,
            period="1mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
        )

        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker] if ticker in data.columns.get_level_values(0) else None

                if df is None or df.empty:
                    continue

                closes = df["Close"].dropna().tolist()
                if not closes:
                    continue

                current_price = round(closes[-1], 2)
                prev_close = closes[-2] if len(closes) >= 2 else current_price
                week_ago = closes[-5] if len(closes) >= 5 else closes[0]
                month_ago = closes[0]

                change_1d = round(((current_price - prev_close) / prev_close) * 100, 2) if prev_close else 0
                change_1w = round(((current_price - week_ago) / week_ago) * 100, 2) if week_ago else 0
                change_1m = round(((current_price - month_ago) / month_ago) * 100, 2) if month_ago else 0

                volumes = df["Volume"].dropna().tolist()
                opens = df["Open"].dropna().tolist()
                highs = df["High"].dropna().tolist()
                lows = df["Low"].dropna().tolist()

                # Get market cap from info (fast_info is faster)
                try:
                    info = yf.Ticker(ticker).fast_info
                    market_cap = self._format_market_cap(getattr(info, "market_cap", 0) or 0)
                except Exception:
                    market_cap = "N/A"

                results.append(LiveQuote(
                    ticker=ticker,
                    price=current_price,
                    change_1d=change_1d,
                    change_1w=change_1w,
                    change_1m=change_1m,
                    open=round(opens[-1], 2) if opens else 0,
                    high=round(highs[-1], 2) if highs else 0,
                    low=round(lows[-1], 2) if lows else 0,
                    volume=int(volumes[-1]) if volumes else 0,
                    market_cap=market_cap,
                    source="yfinance",
                ))
            except Exception as e:
                print(f"[MARKET] Bulk parse error for {ticker}: {e}")
                continue

        return results

    async def _yf_history(
        self, ticker: str, period: str, interval: str
    ) -> List[HistoricalBar]:
        """Fetch historical bars via yfinance."""
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: yf.Ticker(ticker).history(period=period, interval=interval),
            )
            bars = []
            for idx, row in df.iterrows():
                bars.append(HistoricalBar(
                    date=idx.strftime("%Y-%m-%d"),
                    open=round(row["Open"], 2),
                    high=round(row["High"], 2),
                    low=round(row["Low"], 2),
                    close=round(row["Close"], 2),
                    volume=int(row["Volume"]),
                ))
            return bars
        except Exception as e:
            print(f"[MARKET] yfinance history error for {ticker}: {e}")
            return []

    def _yf_indices(self, symbols: List[str]) -> dict:
        """Fetch market index data."""
        result = {}
        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                info = t.fast_info
                name_map = {
                    "^GSPC": "S&P 500",
                    "^DJI": "Dow Jones",
                    "^IXIC": "NASDAQ",
                    "^RUT": "Russell 2000",
                    "^VIX": "VIX",
                }
                price = getattr(info, "last_price", 0) or 0
                prev = getattr(info, "previous_close", price) or price
                change = round(((price - prev) / prev) * 100, 2) if prev else 0
                result[sym] = {
                    "name": name_map.get(sym, sym),
                    "price": round(price, 2),
                    "change": change,
                }
            except Exception:
                continue
        return result

    # ── Finnhub Provider ─────────────────────────────────────

    async def _finnhub_quote(self, ticker: str) -> Optional[LiveQuote]:
        """Fetch from Finnhub real-time API."""
        global _last_finnhub_call

        # Rate limit
        now = time.time()
        elapsed = now - _last_finnhub_call
        if elapsed < _FINNHUB_MIN_INTERVAL:
            await asyncio.sleep(_FINNHUB_MIN_INTERVAL - elapsed)
        _last_finnhub_call = time.time()

        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                data = resp.json()

            if not data or data.get("c", 0) == 0:
                return None

            price = data["c"]
            prev_close = data["pc"]
            change_1d = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0

            return LiveQuote(
                ticker=ticker,
                price=round(price, 2),
                change_1d=change_1d,
                change_1w=0.0,
                change_1m=0.0,
                open=round(data.get("o", 0), 2),
                high=round(data.get("h", 0), 2),
                low=round(data.get("l", 0), 2),
                volume=0,
                market_cap="N/A",
                source="finnhub",
            )
        except Exception as e:
            print(f"[MARKET] Finnhub error for {ticker}: {e}")
            return None

    async def _finnhub_news(self, ticker: str, limit: int) -> List[MarketNews]:
        """Fetch news from Finnhub."""
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        category = "general" if not ticker else ""
        if ticker:
            url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={week_ago}&to={today}&token={FINNHUB_API_KEY}"
        else:
            url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_API_KEY}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                articles = resp.json()

            news = []
            for article in articles[:limit]:
                # Simple sentiment from headline
                headline = article.get("headline", "")
                sentiment = "neutral"
                positive_words = ["surge", "rally", "gain", "rise", "up", "beat", "strong", "record", "bull"]
                negative_words = ["crash", "fall", "drop", "decline", "down", "miss", "weak", "bear", "loss"]
                hl_lower = headline.lower()
                if any(w in hl_lower for w in positive_words):
                    sentiment = "positive"
                elif any(w in hl_lower for w in negative_words):
                    sentiment = "negative"

                news.append(MarketNews(
                    headline=headline,
                    summary=article.get("summary", "")[:200],
                    source=article.get("source", "Unknown"),
                    url=article.get("url", ""),
                    symbol=ticker or "MARKET",
                    sentiment=sentiment,
                    published_at=datetime.fromtimestamp(
                        article.get("datetime", 0)
                    ).isoformat() if article.get("datetime") else "",
                ))
            return news
        except Exception as e:
            print(f"[MARKET] Finnhub news error: {e}")
            return []

    # ── Twelve Data Provider ─────────────────────────────────

    async def _twelve_data_history(
        self, ticker: str, interval: str = "1day"
    ) -> List[HistoricalBar]:
        """Fetch historical data from Twelve Data."""
        interval_map = {"1d": "1day", "1h": "1h", "5m": "5min", "1m": "1min"}
        td_interval = interval_map.get(interval, interval)

        url = (
            f"https://api.twelvedata.com/time_series"
            f"?symbol={ticker}&interval={td_interval}&outputsize=30"
            f"&apikey={TWELVE_DATA_KEY}"
        )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                data = resp.json()

            values = data.get("values", [])
            bars = []
            for v in reversed(values):  # Oldest first
                bars.append(HistoricalBar(
                    date=v["datetime"],
                    open=float(v["open"]),
                    high=float(v["high"]),
                    low=float(v["low"]),
                    close=float(v["close"]),
                    volume=int(v["volume"]),
                ))
            return bars
        except Exception as e:
            print(f"[MARKET] Twelve Data error for {ticker}: {e}")
            return []

    # ── Caching ──────────────────────────────────────────────

    def _cache_quote(self, ticker: str, quote: LiveQuote):
        """Cache a quote in memory."""
        data = asdict(quote)
        data["_ts"] = time.time()
        self._quote_cache[ticker] = data

    def _get_disk_cached_quote(self, ticker: str) -> Optional[LiveQuote]:
        """Get a quote from disk cache."""
        cache_file = CACHE_DIR / "quotes.json"
        try:
            if cache_file.exists():
                all_quotes = json.loads(cache_file.read_text(encoding="utf-8"))
                if ticker in all_quotes:
                    data = all_quotes[ticker]
                    data.pop("_ts", None)
                    return LiveQuote(**data)
        except Exception:
            pass
        return None

    def _save_disk_cache(self):
        """Persist quote cache to disk."""
        try:
            cache_file = CACHE_DIR / "quotes.json"
            # Remove _ts from saved data
            clean = {}
            for ticker, data in self._quote_cache.items():
                clean[ticker] = {k: v for k, v in data.items() if k != "_ts"}
            cache_file.write_text(
                json.dumps(clean, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            print(f"[MARKET] Cache save error: {e}")

    def _load_disk_cache(self):
        """Load cached quotes from disk."""
        cache_file = CACHE_DIR / "quotes.json"
        try:
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                for ticker, quote_data in data.items():
                    quote_data["_ts"] = 0  # Expired — will refresh
                    self._quote_cache[ticker] = quote_data
                print(f"[MARKET] Loaded {len(data)} cached quotes from disk")
        except Exception:
            pass

    # ── Utilities ────────────────────────────────────────────

    @staticmethod
    def _format_market_cap(cap: int) -> str:
        """Format market cap as human-readable string."""
        if not cap:
            return "N/A"
        if cap >= 1_000_000_000_000:
            return f"{cap / 1_000_000_000_000:.2f}T"
        elif cap >= 1_000_000_000:
            return f"{cap / 1_000_000_000:.0f}B"
        elif cap >= 1_000_000:
            return f"{cap / 1_000_000:.0f}M"
        return str(cap)
