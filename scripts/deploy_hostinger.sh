#!/bin/bash
# Hostinger VPS Deployment Script for IFSA Market Monitor
# Supports both Docker and native Python deployment

set -e

echo "🚀 Deploying IFSA Market Monitor to Hostinger..."

# Config
REMOTE_USER=${HOSTINGER_USER:-root}
REMOTE_HOST=${HOSTINGER_HOST:-}
REMOTE_PATH=${HOSTINGER_PATH:-/opt/ifsa-monitor}
USE_DOCKER=${USE_DOCKER:-true}

if [ -z "$REMOTE_HOST" ]; then
    echo "⚠️  HOSTINGER_HOST not set, running local Docker deployment (for VPS you are already SSH'd in)"
    echo "📦 Building and running Docker..."
    docker-compose down || true
    docker-compose build
    docker-compose up -d
    echo "✅ Deployed locally via Docker"
    docker-compose logs --tail=50
    exit 0
fi

echo "📡 Deploying to $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"

# Create remote directory
ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_PATH"

# Rsync files (excluding sensitive and unnecessary)
rsync -avz --progress \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '.git/' \
    --exclude 'node_modules/' \
    --exclude 'data/' \
    --exclude 'logs/' \
    --exclude '.env' \
    ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/

# Copy .env.example as .env if not exists on remote
ssh $REMOTE_USER@$REMOTE_HOST "
    cd $REMOTE_PATH
    if [ ! -f .env ]; then
        cp .env.example .env
        echo '⚠️  Created .env from example - please edit it on server!'
    fi
    mkdir -p data logs
"

if [ "$USE_DOCKER" = "true" ]; then
    echo "🐳 Deploying via Docker..."
    ssh $REMOTE_USER@$REMOTE_HOST "
        cd $REMOTE_PATH
        docker-compose down || true
        docker-compose build
        docker-compose up -d
        docker-compose logs --tail=30
    "
else
    echo "🐍 Deploying via native Python + systemd..."
    ssh $REMOTE_USER@$REMOTE_HOST "
        cd $REMOTE_PATH
        python3 -m venv venv || true
        source venv/bin/activate
        pip install -r requirements.txt

        # Create systemd service
        cat > /etc/systemd/system/ifsa-monitor.service << 'EOF'
[Unit]
Description=IFSA Market Monitor Bot
After=network.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=$REMOTE_PATH
Environment=PATH=$REMOTE_PATH/venv/bin
ExecStart=$REMOTE_PATH/venv/bin/python -m src.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        cat > /etc/systemd/system/ifsa-api.service << 'EOF'
[Unit]
Description=IFSA Market Monitor API
After=network.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=$REMOTE_PATH
Environment=PATH=$REMOTE_PATH/venv/bin
ExecStart=$REMOTE_PATH/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable ifsa-monitor ifsa-api
        systemctl restart ifsa-monitor ifsa-api
        systemctl status ifsa-monitor --no-pager
        systemctl status ifsa-api --no-pager
    "
fi

echo "✅ Deployment to Hostinger completed!"
echo "🌐 API should be available at http://$REMOTE_HOST:8000"
echo "📊 Dashboard at http://$REMOTE_HOST:8000/dashboard"
