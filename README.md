# 🚀 StockPulse AI - Neural Market Intelligence Platform

A premium AI-powered stock prediction dashboard with real-time WebSocket streaming, technical analysis, and intelligent alerting.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

- **Real-time WebSocket Streaming** - Live market data and AI predictions
- **AI-Powered Predictions** - Technical analysis with confidence scores
- **Pattern Recognition** - Detects chart patterns (Head & Shoulders, Breakouts, etc.)
- **Smart Alerts** - Price thresholds, confidence triggers, pattern detection
- **Premium UI** - Glassmorphic design with neon accents and smooth animations
- **40+ Stock Coverage** - Pre-loaded with major market stocks

## 🎯 Quick Start

### Option 1: Run Locally (Recommended for Development)

```bash
# 1. Install Python dependencies
cd backend
pip install -r requirements.txt

# 2. Start the server
python server.py

# 3. Open browser
# Navigate to: http://localhost:8000/dashboard
```

### Option 2: Standalone Executable (Windows)

```bash
# Build the executable
cd backend
pip install pyinstaller
pyinstaller --onefile --add-data "../data/stocks.json;data" --add-data "../stockpulse;stockpulse" server.py

# Run the executable
dist\server.exe

# Open: http://localhost:8000/dashboard
```

### Option 3: Docker Container

```bash
# Build the image
docker build -t stockpulse-ai .

# Run the container
docker run -p 8000:8000 stockpulse-ai

# Open: http://localhost:8000/dashboard
```

### Option 4: Deploy to Cloud (Heroku/Railway/Render)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed cloud deployment instructions.

## 📁 Project Structure

```
EQUITY_AI_PLATFORM/
├── backend/
│   ├── server.py           # FastAPI WebSocket server
│   └── requirements.txt    # Python dependencies
├── stockpulse/
│   └── index.html         # Premium dashboard UI
├── data/
│   └── stocks.json        # Stock data (40 stocks)
└── README.md
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status |
| `/dashboard` | GET | Dashboard UI |
| `/docs` | GET | Interactive API docs |
| `/api/stocks` | GET | All stocks |
| `/api/stocks/{symbol}` | GET | Single stock |
| `/api/predict/{symbol}` | GET | AI prediction |
| `/api/alerts` | GET/POST | Manage alerts |
| `/ws/stream` | WebSocket | Market updates stream |
| `/ws/predict/{symbol}` | WebSocket | Symbol predictions |

## 🎨 Tech Stack

**Backend:**

- FastAPI - Modern Python web framework
- Uvicorn - ASGI server
- WebSockets - Real-time communication
- Pydantic - Data validation

**Frontend:**

- Tailwind CSS - Utility-first styling
- Chart.js - Interactive charts
- Vanilla JavaScript - No framework overhead
- Font Awesome - Icons

## 🔧 Configuration

Edit `backend/server.py` to customize:

```python
UPDATE_INTERVAL = 2.0  # Prediction update frequency (seconds)
STOCKS_FILE = "path/to/stocks.json"  # Stock data location
```

## 📊 Adding Your Own Stocks

Edit `data/stocks.json`:

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "price": 178.50,
  "change1D": 2.34,
  "change1W": 5.67,
  "change1M": 12.45,
  "aiScore": 85,
  "sentiment": "Bullish",
  "marketCap": "$2.8T"
}
```

## 🚀 Deployment Options

### 1. **Share as ZIP File**

Package the entire folder and share. Recipient needs Python installed.

### 2. **Windows Executable**

Use PyInstaller to create a standalone `.exe` - no Python required for end users.

### 3. **Web Hosting**

Deploy to:

- **Heroku** (Free tier available)
- **Railway** (Easy deployment)
- **Render** (Free tier)
- **DigitalOcean** ($5/month)
- **AWS/Azure/GCP** (Production scale)

### 4. **Docker**

Containerized deployment - works anywhere Docker runs.

## 🔐 Security Notes

⚠️ **For Production:**

- Add authentication (JWT tokens)
- Use HTTPS/WSS instead of HTTP/WS
- Implement rate limiting
- Add CORS restrictions
- Use environment variables for secrets
- Add input validation

## 📝 License

MIT License - Feel free to use for personal or commercial projects.

## 🤝 Support

For issues or questions:

1. Check the [API docs](http://localhost:8000/docs)
2. Review server logs
3. Verify WebSocket connection status

## 🎯 Roadmap

- [ ] Real ML model integration (TensorFlow/PyTorch)
- [ ] Live market data API integration
- [ ] User authentication system
- [ ] Portfolio tracking
- [ ] Mobile app (React Native)
- [ ] Advanced charting (TradingView integration)

---

**Built with ⚡ by the StockPulse Team**
