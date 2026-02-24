# 🚀 StockPulse AI - Deployment Guide

Complete guide for deploying StockPulse AI to various platforms.

## 📦 Option 1: Windows Executable (Easiest for Non-Technical Users)

### Build the Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Navigate to backend folder
cd c:\APEX_NEXUS_SYSTEM\04_PROJECTS\EQUITY_AI_PLATFORM\backend

# Create executable
pyinstaller --onefile ^
  --name "StockPulse-AI" ^
  --add-data "../data;data" ^
  --add-data "../stockpulse;stockpulse" ^
  --icon=../assets/icon.ico ^
  --noconsole ^
  server.py
```

### Package for Distribution

Create a folder structure:

```
StockPulse-AI/
├── StockPulse-AI.exe
├── data/
│   └── stocks.json
├── stockpulse/
│   └── index.html
└── START.bat
```

**START.bat:**

```batch
@echo off
echo Starting StockPulse AI Server...
start "" "StockPulse-AI.exe"
timeout /t 3
start http://localhost:8000/dashboard
```

### Share as ZIP

1. Compress the `StockPulse-AI` folder
2. Share the ZIP file
3. User extracts and double-clicks `START.bat`

---

## 🌐 Option 2: Deploy to Heroku (Free Cloud Hosting)

### Prerequisites

- Heroku account (free)
- Git installed

### Steps

1. **Create `Procfile`:**

```bash
cd c:\APEX_NEXUS_SYSTEM\04_PROJECTS\EQUITY_AI_PLATFORM
echo web: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT > Procfile
```

1. **Create `runtime.txt`:**

```bash
echo python-3.11.0 > runtime.txt
```

1. **Update `requirements.txt`:**

```bash
cd backend
echo gunicorn >> requirements.txt
```

1. **Initialize Git:**

```bash
git init
git add .
git commit -m "Initial commit"
```

1. **Deploy to Heroku:**

```bash
heroku login
heroku create stockpulse-ai
git push heroku main
heroku open
```

Your app will be live at: `https://stockpulse-ai.herokuapp.com/dashboard`

---

## 🐳 Option 3: Docker Container

### Create Dockerfile

```dockerfile
# c:\APEX_NEXUS_SYSTEM\04_PROJECTS\EQUITY_AI_PLATFORM\Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY data/ ./data/
COPY stockpulse/ ./stockpulse/

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "server.py"]
```

### Build and Run

```bash
# Build image
docker build -t stockpulse-ai .

# Run container
docker run -d -p 8000:8000 --name stockpulse stockpulse-ai

# Open browser
start http://localhost:8000/dashboard
```

### Share Docker Image

```bash
# Save image
docker save stockpulse-ai > stockpulse-ai.tar

# Share the .tar file
# Recipient loads it:
docker load < stockpulse-ai.tar
docker run -p 8000:8000 stockpulse-ai
```

---

## ☁️ Option 4: Deploy to Railway (Easiest Cloud Option)

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account
5. Push your code to GitHub
6. Railway auto-detects Python and deploys
7. Get your live URL: `https://stockpulse-ai.up.railway.app`

**No configuration needed!** Railway auto-detects everything.

---

## 🌊 Option 5: Deploy to Render

1. Go to [render.com](https://render.com)
2. Create new "Web Service"
3. Connect GitHub repo
4. Configure:
   - **Build Command:** `cd backend && pip install -r requirements.txt`
   - **Start Command:** `cd backend && python server.py`
5. Deploy!

Free tier available with auto-sleep after inactivity.

---

## 💻 Option 6: Deploy to DigitalOcean ($5/month)

### Create Droplet

1. Create Ubuntu 22.04 droplet ($5/month)
2. SSH into server:

```bash
ssh root@your-server-ip
```

1. Install dependencies:

```bash
# Update system
apt update && apt upgrade -y

# Install Python
apt install python3 python3-pip -y

# Install nginx
apt install nginx -y
```

1. Upload your app:

```bash
# On your local machine
scp -r c:\APEX_NEXUS_SYSTEM\04_PROJECTS\EQUITY_AI_PLATFORM root@your-server-ip:/var/www/
```

1. Install Python packages:

```bash
cd /var/www/EQUITY_AI_PLATFORM/backend
pip3 install -r requirements.txt
```

1. Create systemd service:

```bash
nano /etc/systemd/system/stockpulse.service
```

```ini
[Unit]
Description=StockPulse AI Server
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/EQUITY_AI_PLATFORM/backend
ExecStart=/usr/bin/python3 server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

1. Start service:

```bash
systemctl enable stockpulse
systemctl start stockpulse
```

1. Configure Nginx:

```bash
nano /etc/nginx/sites-available/stockpulse
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/stockpulse /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

Your app is now live at: `http://your-domain.com`

---

## 📱 Option 7: Share as Web App (GitHub Pages + Backend Elsewhere)

### Frontend Only (Static)

1. Push `stockpulse/index.html` to GitHub
2. Enable GitHub Pages
3. Frontend works with simulated data
4. No backend needed!

### Frontend + Backend

1. Deploy backend to Heroku/Railway/Render
2. Update `index.html` API_URL to your backend URL
3. Host frontend on GitHub Pages/Netlify/Vercel

---

## 🎁 Option 8: USB Drive Distribution

Create a portable version:

```
StockPulse-Portable/
├── python-3.11-embed/     # Embedded Python
├── backend/
├── data/
├── stockpulse/
└── RUN.bat
```

**RUN.bat:**

```batch
@echo off
cd /d %~dp0
python-3.11-embed\python.exe backend\server.py
```

Users just plug in USB and run `RUN.bat` - no installation needed!

---

## 🔒 Production Security Checklist

Before deploying to production:

- [ ] Add authentication (JWT/OAuth)
- [ ] Enable HTTPS/WSS
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Add logging and monitoring
- [ ] Set up backups
- [ ] Add error tracking (Sentry)
- [ ] Implement API key rotation
- [ ] Add DDoS protection (Cloudflare)

---

## 📊 Monitoring & Analytics

### Add Google Analytics

In `stockpulse/index.html`, add before `</head>`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Server Monitoring

Use services like:

- **UptimeRobot** - Free uptime monitoring
- **Sentry** - Error tracking
- **LogRocket** - Session replay
- **Datadog** - Full observability

---

## 💡 Tips for Distribution

### For Non-Technical Users

✅ Use Windows Executable + START.bat
✅ Include screenshots in README
✅ Create video tutorial
✅ Provide support email

### For Developers

✅ Share GitHub repo
✅ Include Docker setup
✅ Provide API documentation
✅ Add contribution guidelines

### For Clients/Businesses

✅ Deploy to cloud (Railway/Render)
✅ Custom domain
✅ SSL certificate
✅ Professional email support

---

## 🆘 Troubleshooting

**Port already in use:**

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Change port in server.py
uvicorn.run("server:app", host="0.0.0.0", port=8080)
```

**WebSocket connection failed:**

- Check firewall settings
- Ensure server is running
- Verify correct URL (ws:// not wss:// for local)

**Stocks not loading:**

- Verify `data/stocks.json` path
- Check file permissions
- Review server logs

---

**Need help?** Check the [main README](README.md) or server logs for details.
