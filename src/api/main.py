"""
FastAPI application - Health, status, manual triggers, dashboard API
Designed for both Hostinger VPS and Netlify Functions adapter
"""
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import os

from ..config import settings, get_assets_config, yaml_config
from ..core.state_store import StateStore
from ..bot import MarketMonitorBot

logger = logging.getLogger(__name__)

app = FastAPI(
    title="IFSA Market Monitor",
    description="Automated, event-driven market monitoring bot for XAUUSD, Crypto, Forex with RSI & MA crossovers, Telegram/Discord alerts",
    version="1.0.0",
    docs_url="/docs" if yaml_config.get('api', {}).get('enable_docs', True) else None
)

# CORS
origins = yaml_config.get('api', {}).get('cors_origins', ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (lazy)
_state_store = None
_bot = None

def get_state_store() -> StateStore:
    global _state_store
    if _state_store is None:
        _state_store = StateStore()
    return _state_store

def get_bot() -> MarketMonitorBot:
    global _bot
    if _bot is None:
        _bot = MarketMonitorBot()
    return _bot

def verify_api_key(x_api_key: str = Header(None)):
    """Optional API key protection"""
    expected = settings.api_secret_key or yaml_config.get('api', {}).get('secret_key')
    if expected and expected != "change-me" and expected != "change-me-in-production":
        if x_api_key != expected:
            # Allow if no key provided and in dev mode
            if settings.environment == "production" and x_api_key is None:
                # For public health endpoints, don't require key
                pass
            elif x_api_key != expected:
                raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@app.get("/")
async def root():
    return {
        "name": "IFSA Market Monitor",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "dashboard": "/dashboard"
    }

@app.get("/health")
async def health_check():
    """Health check for load balancers, Netlify, uptime monitors"""
    store = get_state_store()
    stats = store.get_stats()
    return {
        "status": "healthy",
        "timestamp": stats.get("last_update"),
        "uptime": stats.get("uptime_human"),
        "tracked_symbols": stats.get("tracked_symbols"),
        "total_alerts_sent": stats.get("total_alerts_sent")
    }

@app.get("/status")
async def get_status(store: StateStore = Depends(get_state_store)):
    """Detailed bot status"""
    state = store.get_state()
    assets_cfg = get_assets_config()

    # Build asset status
    asset_status = []
    for asset in assets_cfg:
        symbol = asset['symbol']
        last_price = store.get_last_price(symbol)
        last_ind = store.get_last_indicator(symbol)
        asset_status.append({
            "symbol": symbol,
            "name": asset.get('name', symbol),
            "type": asset.get('type'),
            "enabled": asset.get('enabled', True),
            "last_price": last_price,
            "last_indicator": last_ind.model_dump() if last_ind else None,
            "last_update": last_ind.timestamp.isoformat() if last_ind and last_ind.timestamp else None
        })

    return {
        "stats": store.get_stats(),
        "assets": asset_status,
        "config": {
            "poll_interval": yaml_config.get('app', {}).get('poll_interval_seconds', settings.poll_interval_seconds),
            "indicators": yaml_config.get('indicators', {}),
            "telegram_enabled": bool(settings.telegram_enabled),
            "discord_enabled": bool(settings.discord_enabled)
        }
    }

@app.post("/trigger")
async def trigger_monitoring(bot: MarketMonitorBot = Depends(get_bot), authorized: bool = Depends(verify_api_key)):
    """Manually trigger a monitoring cycle - used by Netlify scheduled functions & dashboard"""
    try:
        result = await bot.run_once()
        return result
    except Exception as e:
        logger.error(f"Trigger failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets")
async def list_assets():
    """List configured assets"""
    return {"assets": get_assets_config()}

@app.get("/indicators/{symbol}")
async def get_indicator(symbol: str, store: StateStore = Depends(get_state_store)):
    """Get latest indicator for symbol"""
    ind = store.get_last_indicator(symbol.upper())
    if not ind:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return ind.model_dump()

@app.get("/alerts/history")
async def get_alert_history(limit: int = 50, store: StateStore = Depends(get_state_store)):
    """Get alert history"""
    import json
    from pathlib import Path
    history_file = Path(store.history_file)
    if not history_file.exists():
        return {"history": [], "count": 0}

    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
        # Return most recent
        history = history[-limit:][::-1]
        return {"history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/test")
async def test_alert(symbol: str = "BTCUSDT", bot: MarketMonitorBot = Depends(get_bot), authorized: bool = Depends(verify_api_key)):
    """Send test alert to verify Telegram/Discord"""
    try:
        success = await bot.alert_manager.send_test_alert(symbol)
        if success:
            return {"status": "success", "message": f"Test alert sent for {symbol}"}
        else:
            return {"status": "partial", "message": "Test alert attempted but some notifiers may have failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config(authorized: bool = Depends(verify_api_key)):
    """Get sanitized config (no secrets)"""
    return {
        "app": yaml_config.get('app', {}),
        "assets": get_assets_config(),
        "indicators": yaml_config.get('indicators', {}),
        "alerts": {
            "cooldown_seconds": yaml_config.get('alerts', {}).get('cooldown_seconds'),
            "channels": {
                "telegram": {"enabled": bool(settings.telegram_enabled)},
                "discord": {"enabled": bool(settings.discord_enabled)},
                "console": {"enabled": True}
            }
        },
        "scheduling": yaml_config.get('scheduling', {})
    }

# Mount dashboard static files if exists
dashboard_path = Path(__file__).parent.parent.parent / "dashboard"
if dashboard_path.exists():
    try:
        app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")
    except Exception as e:
        logger.warning(f"Failed to mount dashboard: {e}")

# For Netlify Functions adapter - export handler
# Netlify will use this via mangum or similar, but we also provide direct function files
