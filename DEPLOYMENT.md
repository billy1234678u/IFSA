# 🚀 Deployment Guide - IFSA Market Monitor

This guide covers both **Netlify** (serverless) and **Hostinger** (VPS/Docker) deployments in detail.

---

## 📋 Prerequisites

- GitHub account (for CI/CD)
- Telegram Bot Token (optional but recommended)
- Discord Webhook URL (optional)
- Netlify account (for Netlify deployment)
- Hostinger VPS account (for Hostinger deployment)

---

## Option 1: Netlify Deployment (Serverless)

### Why Netlify?
- ✅ Free tier includes 125k function invocations/month
- ✅ Scheduled functions (cron) for automated monitoring
- ✅ Global CDN for dashboard
- ✅ No server maintenance
- ✅ Automatic HTTPS
- ✅ Git-based deploys

### Step-by-Step

#### 1. Prepare Repository

```bash
git clone https://github.com/billy1234678u/IFSA.git
cd IFSA

# Ensure netlify.toml exists (already included)
cat netlify.toml
```

#### 2. Install Netlify CLI (Local Testing)

```bash
npm install -g netlify-cli
netlify --version
```

#### 3. Create Netlify Site

**Via UI (Recommended):**
1. Go to https://app.netlify.com
2. "Add new site" → "Import an existing project"
3. Connect GitHub → Select `billy1234678u/IFSA`
4. Build settings:
   - Build command: `pip install -r requirements.txt`
   - Publish directory: `dashboard`
   - Functions directory: `netlify/functions`
5. Click Deploy

**Via CLI:**
```bash
netlify login
netlify init
# Follow prompts: Create & configure new site
# Team: your team
# Site name: ifsa-market-monitor (or custom)
```

#### 4. Configure Environment Variables

In Netlify UI: Site Settings → Environment Variables → Add:

```
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-YourBotToken
TELEGRAM_CHAT_ID=123456789
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
MONITORED_ASSETS=XAUUSD:FOREX, BTCUSDT:CRYPTO:BINANCE, ETHUSDT:CRYPTO:BINANCE
POLL_INTERVAL_SECONDS=300
ALERT_COOLDOWN_SECONDS=900
API_SECRET_KEY=your-random-secret-key
ENVIRONMENT=production
PYTHON_VERSION=3.11
```

Or via CLI:
```bash
netlify env:set TELEGRAM_BOT_TOKEN "your_token"
netlify env:set TELEGRAM_CHAT_ID "your_chat_id"
netlify env:set DISCORD_WEBHOOK_URL "your_webhook_url"
netlify env:set TELEGRAM_ENABLED "true"
netlify env:set DISCORD_ENABLED "true"
```

#### 5. Deploy

```bash
# Manual deploy
netlify deploy --prod

# Or push to main branch (auto-deploy if GitHub connected)
git push origin main
```

#### 6. Verify Deployment

- Dashboard: `https://your-site.netlify.app/dashboard`
- Health: `https://your-site.netlify.app/health`
- API Status: `https://your-site.netlify.app/api/status`
- Trigger manually: `curl -X POST https://your-site.netlify.app/api/trigger`

#### 7. Check Scheduled Function Logs

Netlify UI → Functions → `monitor` → Logs

You should see logs every 5 minutes:
```
🚀 IFSA Monitor triggered
Starting monitoring cycle...
Fetched 4/4 assets
...
✅ Monitor cycle completed
```

#### 8. (Optional) Custom Domain

Netlify UI → Domain Settings → Add custom domain → Follow DNS instructions

---

### Netlify Deployment Architecture

- **Scheduled Function** (`netlify/functions/monitor.py`): Runs every 5 min via cron `*/5 * * * *`
- **API Function** (`netlify/functions/api.py`): Handles `/api/*` routes
- **Health Function** (`netlify/functions/health.py`): Lightweight health check
- **Static Dashboard** (`dashboard/`): Served via Netlify CDN

**Limitations & Workarounds:**
- Functions timeout: 10s (free) / 26s (pro). Bot uses concurrent fetching to stay under limit.
- No persistent filesystem: Use Netlify Blobs or external storage for state. Currently uses file + falls back to memory.
- For higher frequency (e.g., every 1 min), upgrade to Pro or use Hostinger.

---

## Option 2: Hostinger VPS Deployment

### Why Hostinger VPS?
- ✅ Full control, persistent storage
- ✅ No function timeout limits
- ✅ Can run continuous loop (real-time, not just every 5 min)
- ✅ Docker support
- ✅ Cheaper for high-frequency polling
- ✅ Can host API + Bot + Dashboard together

### Prerequisites

- Hostinger VPS plan (KVM 1 or higher recommended)
- SSH access
- Domain (optional, for HTTPS)

### Step-by-Step - Docker (Recommended)

#### 1. SSH into VPS

```bash
ssh root@YOUR_VPS_IP
# or
ssh username@YOUR_VPS_IP
```

Get IP from Hostinger hPanel → VPS → Overview

#### 2. Install Docker (if not pre-installed)

```bash
# Check
docker --version
docker-compose --version

# If not installed:
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo apt install docker-compose -y
sudo systemctl enable docker
sudo systemctl start docker
```

#### 3. Clone & Configure

```bash
git clone https://github.com/billy1234678u/IFSA.git
cd IFSA

cp .env.example .env
nano .env
# Add your Telegram/Discord credentials
```

#### 4. Run with Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
```

This will:
- Build image
- Start API on port 8000
- Start bot loop in background
- Persist data in `./data`

#### 5. Open Firewall

Via Hostinger hPanel:
- VPS → Firewall → Add Rule → 8000/tcp → Allow
- Or via SSH:
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

#### 6. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/status

# From your local machine:
curl http://YOUR_VPS_IP:8000/health
# Open in browser: http://YOUR_VPS_IP:8000/dashboard
```

#### 7. Setup Nginx Reverse Proxy + HTTPS (Optional but Recommended)

```bash
sudo apt install nginx certbot python3-certbot-nginx -y

# Create Nginx config
sudo nano /etc/nginx/sites-available/ifsa-monitor

# Add:
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

sudo ln -s /etc/nginx/sites-available/ifsa-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# HTTPS with Let's Encrypt
sudo certbot --nginx -d yourdomain.com
```

Now dashboard at `https://yourdomain.com/dashboard`

#### 8. Setup Auto-Restart & Monitoring

Docker Compose already has `restart: unless-stopped`.

For extra monitoring, add to crontab:
```bash
crontab -e
# Add:
*/5 * * * * curl -f http://localhost:8000/health || docker-compose -f /opt/IFSA/docker-compose.yml restart
```

---

### Step-by-Step - Native Python (No Docker)

If you prefer not to use Docker:

```bash
# On Hostinger VPS
sudo apt update
sudo apt install python3.11 python3.11-venv git -y

git clone https://github.com/billy1234678u/IFSA.git
cd IFSA

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env

# Create systemd services
sudo nano /etc/systemd/system/ifsa-monitor.service
```

Paste:
```ini
[Unit]
Description=IFSA Market Monitor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/IFSA
Environment=PATH=/root/IFSA/venv/bin
ExecStart=/root/IFSA/venv/bin/python -m src.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/ifsa-api.service
[Unit]
Description=IFSA Market Monitor API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/IFSA
Environment=PATH=/root/IFSA/venv/bin
ExecStart=/root/IFSA/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ifsa-monitor ifsa-api
sudo systemctl start ifsa-monitor ifsa-api
sudo systemctl status ifsa-monitor
sudo journalctl -u ifsa-monitor -f
```

---

### Hostinger Shared Hosting Workaround

Hostinger shared hosting doesn't support long-running Python processes. Options:

1. **Use Netlify for bot + Shared for dashboard:**
   - Upload `dashboard/` via FTP to `public_html/dashboard`
   - Bot runs on Netlify scheduled functions

2. **Use Hostinger's Cron Jobs:**
   - hPanel → Advanced → Cron Jobs
   - Add cron: `*/5 * * * * /usr/bin/python3 /home/username/IFSA/netlify/functions/monitor.py`
   - Limited, not recommended

3. **Upgrade to VPS:** Recommended for full functionality

---

## 🔐 Security Checklist

- [ ] `.env` never committed (in `.gitignore`)
- [ ] `API_SECRET_KEY` set to random strong value in production
- [ ] Telegram bot token kept secret
- [ ] Discord webhook URL kept secret
- [ ] Firewall only opens needed ports (80, 443, 8000)
- [ ] HTTPS enabled via Let's Encrypt or Netlify auto-HTTPS
- [ ] `ENVIRONMENT=production` in prod
- [ ] Regular updates: `docker-compose pull && docker-compose up -d`

---

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Local
curl http://localhost:8000/health

# Netlify
curl https://your-site.netlify.app/health

# Hostinger VPS
curl http://YOUR_VPS_IP:8000/health
```

Setup UptimeRobot (free) to monitor `/health` every 5 min.

### Logs

```bash
# Docker
docker-compose logs -f
docker-compose logs -f market-monitor | grep ALERT

# Systemd
journalctl -u ifsa-monitor -f
journalctl -u ifsa-api -f

# Netlify
Netlify UI → Functions → Logs
```

### Updating

```bash
# Docker
git pull
docker-compose build
docker-compose up -d

# Native
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ifsa-monitor ifsa-api
```

---

## 🆘 Troubleshooting

See README.md Troubleshooting section + check logs.

Common issues:

**Netlify function timeout:**
- Reduce assets or increase polling interval
- Check function logs for slow provider

**Hostinger VPS OOM:**
- Use KVM 2+ for more RAM
- Reduce workers in `docker-compose.yml`

**Telegram not working:**
- Verify token via `curl https://api.telegram.org/bot<TOKEN>/getMe`

**Dashboard blank:**
- Check API URL in `dashboard/app.js` - should auto-detect Netlify vs VPS
- Check browser console for errors

---

## 📞 Need Help?

- GitHub Issues: https://github.com/billy1234678u/IFSA/issues
- Hostinger Support: hPanel → Help
- Netlify Support: https://answers.netlify.com
