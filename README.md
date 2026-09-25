# 📈 IFSA Market Monitor Bot

> **Automated, event-driven market monitoring bot** that tracks real-time price action & key technical indicators (RSI, MA crossovers, MACD) for **XAUUSD (Gold)**, **Crypto (BTC, ETH)**, and **Forex**, delivering instant alerts via **Telegram** and **Discord Webhooks**. Deployable on **Netlify** (serverless) or **Hostinger VPS** (Docker).

[![CI](https://github.com/billy1234678u/IFSA/actions/workflows/ci.yml/badge.svg)](https://github.com/billy1234678u/IFSA/actions/workflows/ci.yml)
[![Netlify](https://img.shields.io/badge/Deploy-Netlify-00C7B7?logo=netlify)](https://app.netlify.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)

---

## ✨ Features

### 🎯 Core Monitoring
- **Real-time price tracking** for:
  - **XAUUSD** - Gold Spot (via Yahoo Finance `GC=F`)
  - **Crypto** - BTCUSDT, ETHUSDT, etc. (via Binance public API)
  - **Forex** - EURUSD, GBPUSD, etc.
- **Multi-provider fallback**: Binance → Yahoo Finance → TwelveData
- **Event-driven architecture**: Polling + webhook triggers + scheduled jobs

### 📊 Technical Indicators
- **RSI (14)**: Overbought (>70) / Oversold (<30) detection with crossover alerts
- **Moving Averages**: SMA 50/200 (Golden Cross / Death Cross), EMA 9/21
- **MACD**: Bullish/Bearish crossover detection
- **Bollinger Bands**: Breakout detection
- **Price Action**: % change, threshold breakouts, support/resistance

### 🔔 Alert Channels
- **Telegram Bot**: Rich Markdown alerts with emojis
- **Discord Webhook**: Embedded alerts with color coding
- **Console**: Structured logging
- **Cooldown system**: Prevents spam (configurable, default 15min per alert type)

### 🚀 Deployment Ready
- **Netlify**: Serverless Functions + Scheduled Functions (every 5 min) + Static Dashboard
- **Hostinger**: Docker Compose + Native Python + systemd services
- **DevOps**: CI/CD, health checks, structured logging, state persistence

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Event Sources                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Binance  │  │  Yahoo   │  │ Netlify Cron │  │   API    │ │
│  │  Crypto  │  │ XAUUSD   │  │  */5 * * * * │  │ /trigger │ │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └────┬─────┘ │
└───────┼─────────────┼───────────────┼───────────────┼───────┘
        └─────────────┴───────┬───────┴───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   MarketMonitorBot                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ PriceFetcher │→ │ Indicators   │→ │ StrategyEngine   │  │
│  │ (multi-prov) │  │ RSI, MA, MACD│  │ Crossover detect │  │
│  └──────────────┘  └──────────────┘  └────────┬─────────┘  │
│                                               ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ StateStore   │← │ AlertManager │← │ Alerts Generated │  │
│  │ JSON/Blobs   │  │ Cooldown     │  │                  │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────┘  │
└───────────────────────────┼─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Notification Channels                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Telegram   │  │   Discord    │  │    Dashboard     │  │
│  │  Bot API     │  │  Webhook     │  │  Real-time UI    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure
```
IFSA/
├── src/
│   ├── core/               # Core engine
│   │   ├── price_fetcher.py    # Multi-provider price aggregator
│   │   ├── indicators.py       # RSI, SMA, EMA, MACD, Bollinger
│   │   ├── strategy_engine.py  # Event detection logic
│   │   ├── alert_manager.py    # Dispatch + cooldown
│   │   └── state_store.py      # Persistence layer
│   ├── notifiers/          # Alert channels
│   │   ├── telegram.py
│   │   ├── discord.py
│   │   └── base.py
│   ├── api/                # FastAPI server
│   │   └── main.py
│   ├── bot.py              # Main loop
│   ├── config.py           # 12-factor config
│   └── models.py           # Pydantic models
├── netlify/
│   └── functions/          # Netlify serverless functions
│       ├── monitor.py          # Scheduled every 5 min
│       ├── api.py              # API adapter
│       └── health.py
├── dashboard/              # Static frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
├── scripts/
│   ├── setup.sh
│   └── deploy_hostinger.sh
├── .github/workflows/      # CI/CD
├── config.yaml             # Main config
├── Dockerfile
├── docker-compose.yml
├── netlify.toml
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Local Development

```bash
# Clone
git clone https://github.com/billy1234678u/IFSA.git
cd IFSA

# Setup (creates venv, installs deps, creates .env)
bash scripts/setup.sh
# or
make setup

# Edit .env with your credentials
nano .env

# Run bot (continuous loop)
make bot
# or
python -m src.bot

# In another terminal, run API + dashboard
make dev
# Open http://localhost:8000/dashboard
# API Docs at http://localhost:8000/docs
```

### 2. Environment Variables

Create `.env` from `.env.example`:

```ini
# Telegram (get token from @BotFather)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# Discord (create webhook in channel settings)
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Assets (optional override)
MONITORED_ASSETS=XAUUSD:FOREX, BTCUSDT:CRYPTO:BINANCE, ETHUSDT:CRYPTO:BINANCE

# Indicators
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30
ALERT_COOLDOWN_SECONDS=900
```

**How to get Telegram credentials:**
1. Message `@BotFather` on Telegram → `/newbot` → get token
2. Message `@userinfobot` → get your chat ID
3. Or: Add bot to channel, send message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`

**How to get Discord webhook:**
1. Discord Channel → Edit Channel → Integrations → Webhooks → New Webhook → Copy URL

---

## 🌐 Deployment

### Option A: Netlify (Serverless - Recommended for low cost)

**Why Netlify?** Free tier, scheduled functions, global CDN for dashboard, no server management.

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Link site (or create new)
netlify link
# or
netlify init

# Set env vars in Netlify UI or via CLI
netlify env:set TELEGRAM_BOT_TOKEN "your_token"
netlify env:set TELEGRAM_CHAT_ID "your_chat_id"
netlify env:set DISCORD_WEBHOOK_URL "your_webhook"
netlify env:set TELEGRAM_ENABLED "true"
netlify env:set DISCORD_ENABLED "true"

# Deploy
netlify deploy --prod
```

**Netlify Config (`netlify.toml`) already includes:**
- Scheduled function: `*/5 * * * *` (every 5 minutes)
- API redirects: `/api/*` → `/.netlify/functions/api`
- Dashboard publish: `dashboard/` folder
- Python runtime: 3.11

**After deploy:**
- Dashboard: `https://your-site.netlify.app/dashboard`
- Health: `https://your-site.netlify.app/health`
- API: `https://your-site.netlify.app/api/status`
- Manual trigger: `POST https://your-site.netlify.app/api/trigger`

**Netlify Blobs (optional persistence):**
Enable in Netlify UI → Functions → Blobs to persist state across invocations.

---

### Option B: Hostinger VPS (Docker - Recommended for 24/7)

**Why Hostinger VPS?** Full control, Docker support, persistent storage, cheaper for high-frequency polling.

#### B1: Docker (Easiest)

```bash
# On your local machine or SSH into Hostinger VPS
# Hostinger VPS comes with Ubuntu, Docker pre-installed on higher plans

# Clone
git clone https://github.com/billy1234678u/IFSA.git
cd IFSA

# Configure
cp .env.example .env
nano .env  # Add Telegram/Discord creds

# Run
docker-compose up -d

# Check logs
docker-compose logs -f

# Dashboard
# http://YOUR_VPS_IP:8000/dashboard
# http://YOUR_VPS_IP:8000/docs
```

**Hostinger hPanel steps:**
1. VPS → Access → SSH
2. `docker --version` (install if needed: `curl -fsSL https://get.docker.com | sh`)
3. `docker-compose --version` (install: `sudo apt install docker-compose`)
4. Clone repo and run as above
5. Open firewall: hPanel → Firewall → Add rule → 8000/tcp
6. (Optional) Setup domain: hPanel → Domains → Point to VPS IP → Use Nginx reverse proxy

#### B2: Native Python + systemd (No Docker)

```bash
# On Hostinger VPS (Ubuntu)
sudo apt update && sudo apt install python3.11 python3-venv git -y

git clone https://github.com/billy1234678u/IFSA.git
cd IFSA
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env

# Create systemd services (see scripts/deploy_hostinger.sh)
sudo nano /etc/systemd/system/ifsa-monitor.service
# [paste from scripts/deploy_hostinger.sh]

sudo systemctl daemon-reload
sudo systemctl enable ifsa-monitor ifsa-api
sudo systemctl start ifsa-monitor ifsa-api
sudo systemctl status ifsa-monitor
```

#### B3: Hostinger Shared Hosting (Node.js workaround)

Hostinger shared hosting doesn't support Python long-running processes. Use this workaround:

1. Deploy dashboard to shared hosting via FTP (upload `dashboard/` folder)
2. Use Netlify for bot logic (scheduled functions)
3. Or: Convert bot to Node.js cron job (contact for Node version)

---

## 📊 Configuration (`config.yaml`)

```yaml
assets:
  - symbol: "XAUUSD"
    name: "Gold Spot / US Dollar"
    type: "FOREX"
    provider: "yahoo"
    yahoo_symbol: "GC=F"
    alerts:
      price_thresholds:
        - level: 2000
          direction: "above"
      percent_change: 1.5

indicators:
  rsi:
    enabled: true
    period: 14
    overbought: 70
    oversold: 30
  moving_averages:
    enabled: true
    sma_fast: 50
    sma_slow: 200
    ema_fast: 9
    ema_slow: 21
    alert_on_crossover: true

alerts:
  cooldown_seconds: 900
  channels:
    telegram: {enabled: true}
    discord: {enabled: true}
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root info |
| `/health` | GET | Health check (for uptime monitors) |
| `/status` | GET | Detailed bot status + asset indicators |
| `/trigger` | POST | Manually trigger monitoring cycle |
| `/assets` | GET | List configured assets |
| `/indicators/{symbol}` | GET | Latest indicators for symbol |
| `/alerts/history?limit=50` | GET | Recent alerts |
| `/alerts/test?symbol=BTCUSDT` | POST | Send test alert |
| `/docs` | GET | Swagger UI |
| `/dashboard` | GET | Frontend dashboard |

**Example:**
```bash
curl https://your-site.netlify.app/api/status
curl -X POST https://your-site.netlify.app/api/trigger -H "X-API-KEY: your_secret"
```

---

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v
make test

# Test indicators
python -m pytest tests/test_indicators.py -v

# Test bot import
python -c "from src.bot import MarketMonitorBot; print('OK')"

# Test alert
curl -X POST http://localhost:8000/alerts/test?symbol=XAUUSD
```

---

## 🛡️ DevOps Best Practices Implemented

- **12-Factor Config**: ENV + YAML with overrides
- **Resilient Fetching**: Retry with exponential backoff (tenacity), multi-provider fallback
- **Cooldown & Deduplication**: Prevents alert spam
- **State Persistence**: JSON file + Netlify Blobs ready + Redis optional
- **Health Checks**: Docker HEALTHCHECK, `/health` endpoint, uptime monitoring ready
- **Structured Logging**: JSON logs, log levels via ENV
- **CI/CD**: GitHub Actions for test, lint, Docker build, Netlify deploy
- **Security**: API key auth, CORS, security headers, secrets via ENV (not in repo)
- **Monitoring**: Stats endpoint, Prometheus-ready, Grafana compatible

---

## 🗺️ Roadmap

- [ ] Add TradingView webhook support
- [ ] Add email alerts via SendGrid
- [ ] Add SMS via Twilio
- [ ] Add more indicators: Stochastic, ADX, Ichimoku
- [ ] Add backtesting engine
- [ ] Add WebSocket for real-time dashboard updates
- [ ] Add Redis for distributed locking
- [ ] Add Prometheus metrics endpoint

---

## 🤝 Contributing

PRs welcome! Please run `make test` before submitting.

---

## 📄 License

MIT - See LICENSE

---

## 🆘 Troubleshooting

**Telegram not sending?**
- Check bot token and chat ID in `.env`
- Send `/start` to your bot first
- Check logs: `docker-compose logs -f | grep Telegram`

**Discord not sending?**
- Verify webhook URL (should start with `https://discord.com/api/webhooks/`)
- Check Discord channel permissions

**XAUUSD price not fetching?**
- Yahoo Finance sometimes rate-limits. Bot falls back to alternative symbols.
- Check `yahoo_symbol` in config: try `GC=F`, `XAUUSD=X`, `GOLD`

**Netlify function timeout?**
- Netlify Functions have 10s timeout (26s for pro). Bot is optimized to fetch concurrently.
- Reduce assets in `MONITORED_ASSETS` or increase timeout in `netlify.toml`

**Hostinger VPS can't access dashboard?**
- Check firewall: `sudo ufw allow 8000`
- Check Docker: `docker ps`, `docker-compose logs`
- Try `curl localhost:8000/health` from VPS

---

## 📞 Support

- Issues: https://github.com/billy1234678u/IFSA/issues
- Email: via GitHub profile

---

**Built with ❤️ for traders who need instant alerts on Gold and Crypto moves.**
