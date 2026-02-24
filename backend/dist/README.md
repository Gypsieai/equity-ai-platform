# 🚀 StockPulse AI - Portable Edition

## Quick Start

1. **Double-click `RUN.bat`**
2. Dashboard opens automatically at <http://localhost:8000/dashboard>
3. That's it! No installation required.

## What's Included

- ✅ **StockPulse-AI.exe** - Standalone server (no Python needed)
- ✅ **40 Stock Dataset** - Pre-loaded market data
- ✅ **Premium Dashboard** - Neural AI interface
- ✅ **WebSocket Streaming** - Real-time predictions
- ✅ **Alert System** - Smart notifications

## System Requirements

- **OS:** Windows 10/11 (64-bit)
- **RAM:** 512 MB minimum
- **Disk:** 50 MB free space
- **Network:** Internet connection (optional, for updates)

## Features

### 🧠 AI Predictions

- Technical analysis with confidence scores
- Pattern recognition (Head & Shoulders, Breakouts, etc.)
- 7-day price forecasts
- Real-time sentiment analysis

### 📊 Live Dashboard

- Interactive Chart.js visualizations
- WebSocket streaming (2-second updates)
- Sector filtering and sorting
- Mini trend charts

### 🔔 Smart Alerts

- Price threshold triggers
- Confidence-based alerts
- Pattern detection notifications
- Priority levels (Low → Critical)

## Usage

### Access Points

- **Dashboard:** <http://localhost:8000/dashboard>
- **API Docs:** <http://localhost:8000/docs>
- **Health Check:** <http://localhost:8000/>

### Creating Alerts

1. Click the bell icon (top right)
2. Enter stock symbol (e.g., AAPL)
3. Set condition (Price Above/Below, Confidence %, Pattern)
4. Choose priority level
5. Click "Create Alert"

### Viewing Predictions

- Click any stock in the watchlist
- View AI forecast panel (bottom right of chart)
- Check confidence score and pattern detection
- See 7-day price target

## Troubleshooting

### Port Already in Use

If you see "Address already in use" error:

1. Close other programs using port 8000
2. Or edit the executable to use a different port

### Firewall Warning

Windows may show a firewall prompt:

- Click "Allow access"
- This is normal for server applications

### Antivirus False Positive

Some antivirus software may flag the .exe:

- This is a false positive (PyInstaller executables are sometimes flagged)
- Add exception in your antivirus settings
- Or run from the source code instead (see main README.md)

### Dashboard Not Loading

1. Wait 5 seconds for server to start
2. Manually open: <http://localhost:8000/dashboard>
3. Check if StockPulse-AI.exe is running in Task Manager

## Advanced

### Command Line Options

```bash
# Run on different port (requires editing server.py and rebuilding)
StockPulse-AI.exe --port 8080
```

### API Endpoints

```bash
# Get all stocks
curl http://localhost:8000/api/stocks

# Get prediction for NVDA
curl http://localhost:8000/api/predict/NVDA

# WebSocket stream
ws://localhost:8000/ws/stream
```

## Sharing This App

You can share this entire folder with others:

1. Compress the `dist` folder to ZIP
2. Share via email/drive/USB
3. Recipient extracts and runs `RUN.bat`

**No Python installation required!**

## File Size

- **Executable:** ~25 MB (includes Python runtime + dependencies)
- **Total Package:** ~26 MB (with data files)

## Security Notes

⚠️ **For Local Use Only**

- This version has no authentication
- Don't expose to public internet
- Use only on trusted networks

For production deployment, see the main DEPLOYMENT.md guide.

## Updates

To update stock data:

1. Edit `data/stocks.json` (in parent folder)
2. Rebuild executable with PyInstaller
3. Or use the source code version for easier updates

## Support

**Issues?**

- Check server logs in the console window
- Verify firewall/antivirus settings
- Review main README.md for detailed docs

**Want to modify?**

- See the source code in the parent `backend` folder
- Edit `server.py` for backend changes
- Edit `stockpulse/index.html` for UI changes
- Rebuild with: `pyinstaller --onefile server.py`

---

**Built with ⚡ by StockPulse AI**

Version: 1.0.0 | License: MIT
