"""
StockPulse AI — Email Alert Engine
Scheduled notifications for Dusty (Tuesday + Wednesday)

Features:
  - HTML email reports with pattern recognition results
  - AI signal summaries with confidence scores
  - Portfolio performance snapshots
  - Configurable schedule via .env
  - APScheduler integration for cron-based dispatch

Email providers supported:
  - Gmail (app password)
  - SendGrid
  - Any SMTP server
"""

import os
import smtplib
import asyncio
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False
    print("[EMAIL] ⚠️ APScheduler not installed. Run: pip install apscheduler")


# ============================================================================
# Configuration
# ============================================================================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")  # Dusty's email
ALERT_DAYS = os.getenv("ALERT_DAYS", "tue,wed")  # Cron day-of-week
ALERT_TIME = os.getenv("ALERT_TIME", "07:00")  # Local time (AEST)
SENDER_NAME = os.getenv("SENDER_NAME", "StockPulse AI")

DATA_DIR = Path(__file__).parent.parent / "data"
EMAIL_LOG = DATA_DIR / "email_log.json"


# ============================================================================
# Data Models
# ============================================================================
@dataclass
class AlertReport:
    """Complete market report for email dispatch."""
    generated_at: str = ""
    market_summary: Dict = field(default_factory=dict)
    top_signals: List[Dict] = field(default_factory=list)
    pattern_detections: List[Dict] = field(default_factory=list)
    risk_alerts: List[Dict] = field(default_factory=list)
    portfolio_snapshot: Dict = field(default_factory=dict)
    watchlist_movers: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


# ============================================================================
# Email Alert Engine
# ============================================================================
class EmailAlertEngine:
    """Handles email composition, sending, and scheduling."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._email_log: List[Dict] = []
        self._load_log()

    # ── Scheduler ───────────────────────────────────────────────
    def start_scheduler(self):
        """Start the APScheduler for Tue/Wed alerts."""
        if not HAS_SCHEDULER:
            print("[EMAIL] ❌ Cannot start scheduler — APScheduler not installed")
            return False

        if self.scheduler and self.scheduler.running:
            print("[EMAIL] ⚡ Scheduler already running")
            return True

        self.scheduler = AsyncIOScheduler()

        # Parse alert days (e.g., "tue,wed")
        days = ALERT_DAYS.strip().lower()
        hour, minute = ALERT_TIME.split(":")

        self.scheduler.add_job(
            self._scheduled_alert,
            CronTrigger(
                day_of_week=days,
                hour=int(hour),
                minute=int(minute),
                timezone="Australia/Brisbane"
            ),
            id="stockpulse_email_alert",
            name="StockPulse Tuesday/Wednesday Email Alert",
            replace_existing=True,
        )

        self.scheduler.start()
        print(f"[EMAIL] ✅ Scheduler started — alerts on [{days.upper()}] at {ALERT_TIME} AEST")
        return True

    def stop_scheduler(self):
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            print("[EMAIL] 🛑 Scheduler stopped")

    async def _scheduled_alert(self):
        """Called by APScheduler on Tue/Wed."""
        print(f"[EMAIL] 🔔 Scheduled alert triggered at {datetime.now()}")
        try:
            # Import here to avoid circular imports
            from ai_brain import StrategyEngine, TechnicalAnalyzer, PatternDetector
            from market_data import MarketDataEngine

            market = MarketDataEngine()
            analyzer = TechnicalAnalyzer()
            detector = PatternDetector()
            strategy = StrategyEngine()

            report = await self.generate_report(market, analyzer, detector, strategy)
            success = self.send_alert(report)

            if success:
                print(f"[EMAIL] ✅ Alert sent to {ALERT_EMAIL}")
            else:
                print(f"[EMAIL] ❌ Failed to send alert")
        except Exception as e:
            print(f"[EMAIL] ❌ Scheduled alert error: {e}")

    # ── Report Generation ───────────────────────────────────────
    async def generate_report(
        self,
        market_engine=None,
        analyzer=None,
        detector=None,
        strategy_engine=None,
        stocks_data: List[Dict] = None,
    ) -> AlertReport:
        """Generate a comprehensive market report."""
        report = AlertReport()

        # Load stocks if not provided
        if not stocks_data:
            stocks_file = DATA_DIR / "stocks.json"
            if stocks_file.exists():
                with open(stocks_file) as f:
                    stocks_data = json.load(f)

        if not stocks_data:
            return report

        # Refresh live prices
        if market_engine:
            try:
                await market_engine.update_stocks_data(stocks_data)
            except Exception as e:
                print(f"[EMAIL] ⚠️ Price refresh failed: {e}")

        # Generate signals for each stock
        for stock in stocks_data:
            ticker = stock.get("ticker", "")
            try:
                # Get history for analysis
                if market_engine:
                    history = await market_engine.get_history(ticker, period="3mo")
                    if history:
                        closes = [bar.close for bar in history]
                        highs = [bar.high for bar in history]
                        lows = [bar.low for bar in history]
                        opens = [bar.open for bar in history]
                        volumes = [bar.volume for bar in history]

                        # Technical analysis
                        if analyzer and len(closes) >= 30:
                            analysis = analyzer.full_analysis(
                                closes, highs, lows, volumes
                            )

                            # Pattern detection
                            if detector and len(opens) >= 5:
                                candle_patterns = detector.detect_candlestick(
                                    opens[-20:], highs[-20:], lows[-20:], closes[-20:]
                                )
                                chart_patterns = detector.detect_chart_patterns(closes)

                                if candle_patterns or chart_patterns:
                                    report.pattern_detections.append({
                                        "symbol": ticker,
                                        "name": stock.get("name", ticker),
                                        "price": stock.get("price", 0),
                                        "candlestick": candle_patterns,
                                        "chart": chart_patterns,
                                    })

                            # AI signal generation
                            if strategy_engine:
                                signal = strategy_engine.evaluate(
                                    ticker, analysis,
                                    current_price=stock.get("price", 0)
                                )
                                if signal and signal.get("action") != "hold":
                                    report.top_signals.append({
                                        "symbol": ticker,
                                        "name": stock.get("name", ticker),
                                        "price": stock.get("price", 0),
                                        "action": signal.get("action", "hold"),
                                        "confidence": signal.get("confidence", 0),
                                        "reason": signal.get("reason", ""),
                                        "target": signal.get("target_price", 0),
                                    })

                # Risk check
                change = stock.get("change1D", 0)
                if abs(change) > 5:
                    report.risk_alerts.append({
                        "symbol": ticker,
                        "name": stock.get("name", ticker),
                        "change": change,
                        "alert": f"{'📈 Surging' if change > 0 else '📉 Dropping'} {abs(change):.1f}% today",
                    })

                # Watchlist movers
                report.watchlist_movers.append({
                    "symbol": ticker,
                    "name": stock.get("name", ticker),
                    "price": stock.get("price", 0),
                    "change_1d": stock.get("change1D", 0),
                    "change_1w": stock.get("change1W", 0),
                    "ai_score": stock.get("aiScore", 50),
                    "sentiment": stock.get("sentiment", "neutral"),
                })

            except Exception as e:
                print(f"[EMAIL] ⚠️ Analysis failed for {ticker}: {e}")

        # Sort signals by confidence
        report.top_signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)
        report.watchlist_movers.sort(key=lambda s: abs(s.get("change_1d", 0)), reverse=True)

        return report

    def generate_preview(self, stocks_data: List[Dict] = None) -> AlertReport:
        """Generate a FAST preview report using cached stock data only (no API calls).
        Used by /api/email/preview to avoid timeouts."""
        report = AlertReport()

        if not stocks_data:
            stocks_file = DATA_DIR / "stocks.json"
            if stocks_file.exists():
                with open(stocks_file) as f:
                    stocks_data = json.load(f)

        if not stocks_data:
            return report

        for stock in stocks_data:
            ticker = stock.get("ticker", "")
            change = stock.get("change1D", 0)
            ai_score = stock.get("aiScore", 50)

            # Simulate signals from AI score
            if ai_score >= 80:
                report.top_signals.append({
                    "symbol": ticker,
                    "name": stock.get("name", ticker),
                    "price": stock.get("price", 0),
                    "action": "buy" if change > 0 else "sell",
                    "confidence": ai_score / 100,
                    "reason": f"AI Score {ai_score}/100 — {'strong momentum' if change > 0 else 'reversal expected'}",
                    "target": stock.get("price", 0) * (1.05 if change > 0 else 0.95),
                })

            # Risk alerts
            if abs(change) > 5:
                report.risk_alerts.append({
                    "symbol": ticker,
                    "name": stock.get("name", ticker),
                    "change": change,
                    "alert": f"{'📈 Surging' if change > 0 else '📉 Dropping'} {abs(change):.1f}% today",
                })

            # Watchlist
            report.watchlist_movers.append({
                "symbol": ticker,
                "name": stock.get("name", ticker),
                "price": stock.get("price", 0),
                "change_1d": change,
                "change_1w": stock.get("change1W", 0),
                "ai_score": ai_score,
                "sentiment": stock.get("sentiment", "neutral"),
            })

        report.top_signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)
        report.watchlist_movers.sort(key=lambda s: abs(s.get("change_1d", 0)), reverse=True)

        return report

    # ── Email Sending ───────────────────────────────────────────
    def send_alert(self, report: AlertReport, recipient: str = None) -> bool:
        """Send the alert email."""
        to_email = recipient or ALERT_EMAIL
        if not to_email:
            print("[EMAIL] ❌ No recipient email configured. Set ALERT_EMAIL in .env")
            return False

        if not SMTP_USER or not SMTP_PASSWORD:
            print("[EMAIL] ❌ SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._build_subject(report)
            msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
            msg["To"] = to_email

            # Plain text fallback
            text_body = self._build_text(report)
            msg.attach(MIMEText(text_body, "plain"))

            # HTML body
            html_body = self._build_html(report)
            msg.attach(MIMEText(html_body, "html"))

            # Send
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, msg.as_string())

            # Log
            self._log_email(to_email, report)
            print(f"[EMAIL] ✅ Alert sent to {to_email}")
            return True

        except Exception as e:
            print(f"[EMAIL] ❌ Send failed: {e}")
            return False

    # ── Email Subject ───────────────────────────────────────────
    def _build_subject(self, report: AlertReport) -> str:
        day_name = datetime.now().strftime("%A")
        signal_count = len(report.top_signals)
        alert_count = len(report.risk_alerts)
        pattern_count = len(report.pattern_detections)

        parts = []
        if signal_count:
            parts.append(f"{signal_count} Signal{'s' if signal_count > 1 else ''}")
        if pattern_count:
            parts.append(f"{pattern_count} Pattern{'s' if pattern_count > 1 else ''}")
        if alert_count:
            parts.append(f"{alert_count} Alert{'s' if alert_count > 1 else ''}")

        summary = " · ".join(parts) if parts else "Market Update"
        return f"⚡ StockPulse {day_name}: {summary}"

    # ── Plain Text ──────────────────────────────────────────────
    def _build_text(self, report: AlertReport) -> str:
        lines = [
            "═══════════════════════════════════════",
            "  STOCKPULSE AI — MARKET INTELLIGENCE  ",
            "═══════════════════════════════════════",
            f"  Generated: {datetime.now().strftime('%A %d %B %Y, %I:%M %p AEST')}",
            "",
        ]

        if report.top_signals:
            lines.append("── TOP AI SIGNALS ──")
            for s in report.top_signals[:5]:
                emoji = "🟢" if s["action"] == "buy" else "🔴"
                lines.append(
                    f"  {emoji} {s['symbol']} — {s['action'].upper()} "
                    f"(Confidence: {s['confidence']:.0%}) ${s['price']:.2f}"
                )
                if s.get("reason"):
                    lines.append(f"     → {s['reason']}")
            lines.append("")

        if report.pattern_detections:
            lines.append("── PATTERN DETECTIONS ──")
            for p in report.pattern_detections:
                patterns = []
                if p.get("candlestick"):
                    patterns.extend(p["candlestick"])
                if p.get("chart"):
                    patterns.extend(p["chart"])
                lines.append(f"  {p['symbol']}: {', '.join(patterns)}")
            lines.append("")

        if report.risk_alerts:
            lines.append("── ⚠️ RISK ALERTS ──")
            for r in report.risk_alerts:
                lines.append(f"  {r['alert']} — {r['symbol']}")
            lines.append("")

        if report.watchlist_movers:
            lines.append("── WATCHLIST ──")
            for m in report.watchlist_movers[:10]:
                arrow = "↑" if m["change_1d"] > 0 else "↓" if m["change_1d"] < 0 else "→"
                lines.append(
                    f"  {m['symbol']:6s} ${m['price']:>8.2f}  {arrow} {m['change_1d']:+.1f}%  "
                    f"AI: {m['ai_score']}/100"
                )

        lines.extend(["", "— StockPulse AI 🤖", "   Powered by APEX NEXUS"])
        return "\n".join(lines)

    # ── HTML Email ──────────────────────────────────────────────
    def _build_html(self, report: AlertReport) -> str:
        date_str = datetime.now().strftime("%A %d %B %Y, %I:%M %p AEST")

        # Signal rows
        signal_rows = ""
        for s in report.top_signals[:8]:
            color = "#22c55e" if s["action"] in ("buy", "strong_buy") else "#ef4444"
            conf_pct = int(s.get("confidence", 0) * 100)
            conf_color = "#22c55e" if conf_pct >= 70 else "#f59e0b" if conf_pct >= 50 else "#ef4444"
            signal_rows += f"""
            <tr style="border-bottom:1px solid #1e1e3a;">
              <td style="padding:12px;font-weight:700;color:#a78bfa;font-family:monospace;">{s['symbol']}</td>
              <td style="padding:12px;color:#aaa;">{s.get('name', s['symbol'])}</td>
              <td style="padding:12px;text-align:center;">
                <span style="display:inline-block;padding:4px 12px;border-radius:6px;font-weight:700;font-size:12px;
                  background:{color}22;color:{color};text-transform:uppercase;">{s['action']}</span>
              </td>
              <td style="padding:12px;text-align:center;font-weight:700;color:{conf_color};">{conf_pct}%</td>
              <td style="padding:12px;text-align:right;font-family:monospace;font-weight:700;">${s['price']:.2f}</td>
              <td style="padding:12px;color:#888;font-size:12px;">{s.get('reason', '')[:60]}</td>
            </tr>"""

        # Pattern rows
        pattern_rows = ""
        for p in report.pattern_detections[:6]:
            all_patterns = []
            if p.get("candlestick"):
                all_patterns.extend(p["candlestick"])
            if p.get("chart"):
                all_patterns.extend(p["chart"])
            badges = "".join(
                f'<span style="display:inline-block;padding:3px 8px;border-radius:4px;'
                f'background:rgba(99,102,241,0.15);color:#a78bfa;font-size:11px;'
                f'font-weight:600;margin:2px 4px 2px 0;">{pat}</span>'
                for pat in all_patterns[:4]
            )
            pattern_rows += f"""
            <tr style="border-bottom:1px solid #1e1e3a;">
              <td style="padding:12px;font-weight:700;color:#a78bfa;font-family:monospace;">{p['symbol']}</td>
              <td style="padding:12px;font-family:monospace;font-weight:700;">${p['price']:.2f}</td>
              <td style="padding:12px;">{badges}</td>
            </tr>"""

        # Risk alerts
        risk_section = ""
        if report.risk_alerts:
            risk_items = "".join(
                f'<div style="padding:10px 16px;margin-bottom:6px;border-radius:8px;'
                f'background:{"rgba(239,68,68,0.08)" if r["change"] < 0 else "rgba(34,197,94,0.08)"};">'
                f'<span style="font-weight:700;color:#fff;">{r["symbol"]}</span> '
                f'<span style="color:{"#ef4444" if r["change"] < 0 else "#22c55e"};font-weight:700;">'
                f'{r["change"]:+.1f}%</span> — '
                f'<span style="color:#aaa;">{r["alert"]}</span></div>'
                for r in report.risk_alerts
            )
            risk_section = f"""
            <div style="margin-bottom:28px;">
              <h2 style="font-size:16px;color:#f59e0b;margin-bottom:12px;">⚠️ Risk Alerts</h2>
              {risk_items}
            </div>"""

        # Watchlist table
        watchlist_rows = ""
        for m in report.watchlist_movers[:12]:
            change_color = "#22c55e" if m["change_1d"] > 0 else "#ef4444" if m["change_1d"] < 0 else "#888"
            score_color = "#22c55e" if m["ai_score"] >= 75 else "#f59e0b" if m["ai_score"] >= 50 else "#ef4444"
            watchlist_rows += f"""
            <tr style="border-bottom:1px solid #1e1e3a;">
              <td style="padding:10px;font-weight:700;color:#a78bfa;font-family:monospace;font-size:13px;">{m['symbol']}</td>
              <td style="padding:10px;font-family:monospace;font-weight:600;">${m['price']:.2f}</td>
              <td style="padding:10px;text-align:center;font-weight:700;color:{change_color};">{m['change_1d']:+.1f}%</td>
              <td style="padding:10px;text-align:center;font-weight:700;color:{change_color};">{m.get('change_1w', 0):+.1f}%</td>
              <td style="padding:10px;text-align:center;">
                <span style="font-weight:700;color:{score_color};">{m['ai_score']}</span>
                <span style="color:#555;">/100</span>
              </td>
            </tr>"""

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0a14;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e0e0f0;">
  <div style="max-width:680px;margin:0 auto;padding:20px;">

    <!-- Header -->
    <div style="text-align:center;padding:32px 20px;border-bottom:1px solid #1e1e3a;">
      <div style="font-size:28px;margin-bottom:8px;">⚡</div>
      <h1 style="font-size:22px;font-weight:900;margin:0;letter-spacing:-0.5px;">
        <span style="color:#fff;">Stock</span><span style="color:#6366f1;">Pulse</span>
        <span style="color:#a78bfa;"> AI</span>
      </h1>
      <p style="color:#888;font-size:13px;margin-top:6px;">Neural Market Intelligence Report</p>
      <p style="color:#555;font-size:12px;margin-top:4px;">{date_str}</p>
    </div>

    <div style="padding:24px 0;">

      <!-- Top AI Signals -->
      {"" if not signal_rows else f'''
      <div style="margin-bottom:28px;">
        <h2 style="font-size:16px;color:#6366f1;margin-bottom:12px;">🎯 Top AI Signals</h2>
        <div style="border-radius:12px;overflow:hidden;border:1px solid #1e1e3a;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="background:#12122a;">
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Symbol</th>
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Name</th>
                <th style="padding:10px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">Action</th>
                <th style="padding:10px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">Confidence</th>
                <th style="padding:10px;text-align:right;color:#555;font-size:11px;text-transform:uppercase;">Price</th>
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Reason</th>
              </tr>
            </thead>
            <tbody>{signal_rows}</tbody>
          </table>
        </div>
      </div>
      '''}

      <!-- Pattern Detections -->
      {"" if not pattern_rows else f'''
      <div style="margin-bottom:28px;">
        <h2 style="font-size:16px;color:#a78bfa;margin-bottom:12px;">🔍 Pattern Detections</h2>
        <div style="border-radius:12px;overflow:hidden;border:1px solid #1e1e3a;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="background:#12122a;">
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Symbol</th>
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Price</th>
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Patterns Found</th>
              </tr>
            </thead>
            <tbody>{pattern_rows}</tbody>
          </table>
        </div>
      </div>
      '''}

      <!-- Risk Alerts -->
      {risk_section}

      <!-- Watchlist -->
      {"" if not watchlist_rows else f'''
      <div style="margin-bottom:28px;">
        <h2 style="font-size:16px;color:#fff;margin-bottom:12px;">📊 Watchlist</h2>
        <div style="border-radius:12px;overflow:hidden;border:1px solid #1e1e3a;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="background:#12122a;">
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Symbol</th>
                <th style="padding:10px;text-align:left;color:#555;font-size:11px;text-transform:uppercase;">Price</th>
                <th style="padding:10px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">1D</th>
                <th style="padding:10px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">1W</th>
                <th style="padding:10px;text-align:center;color:#555;font-size:11px;text-transform:uppercase;">AI Score</th>
              </tr>
            </thead>
            <tbody>{watchlist_rows}</tbody>
          </table>
        </div>
      </div>
      '''}

    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:24px 20px;border-top:1px solid #1e1e3a;color:#555;font-size:12px;">
      <p>Powered by <strong style="color:#6366f1;">StockPulse AI</strong> · APEX NEXUS</p>
      <p style="margin-top:4px;color:#444;">
        This report is AI-generated analysis, not financial advice.
        Always do your own research before trading.
      </p>
    </div>

  </div>
</body>
</html>"""

        return html

    # ── Logging ─────────────────────────────────────────────────
    def _log_email(self, recipient: str, report: AlertReport):
        self._email_log.append({
            "sent_at": datetime.now().isoformat(),
            "recipient": recipient,
            "signals": len(report.top_signals),
            "patterns": len(report.pattern_detections),
            "alerts": len(report.risk_alerts),
        })
        # Keep last 100
        self._email_log = self._email_log[-100:]
        self._save_log()

    def _load_log(self):
        try:
            if EMAIL_LOG.exists():
                with open(EMAIL_LOG) as f:
                    self._email_log = json.load(f)
        except Exception:
            self._email_log = []

    def _save_log(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(EMAIL_LOG, "w") as f:
                json.dump(self._email_log, f, indent=2)
        except Exception as e:
            print(f"[EMAIL] ⚠️ Log save failed: {e}")

    def get_log(self, limit: int = 20) -> List[Dict]:
        return self._email_log[-limit:]

    def get_config(self) -> Dict:
        return {
            "smtp_host": SMTP_HOST,
            "smtp_port": SMTP_PORT,
            "smtp_user": SMTP_USER,
            "smtp_configured": bool(SMTP_USER and SMTP_PASSWORD),
            "alert_email": ALERT_EMAIL,
            "alert_days": ALERT_DAYS,
            "alert_time": ALERT_TIME,
            "scheduler_running": bool(self.scheduler and self.scheduler.running),
        }


# Singleton
email_engine = EmailAlertEngine()
