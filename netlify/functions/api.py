"""
Netlify Function - API Adapter
Exposes FastAPI via Netlify Functions using Mangum adapter pattern
Simplified version without Mangum dependency for portability
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# We will implement a simple router that mirrors FastAPI endpoints
# For full FastAPI support, you can use mangum library

def handler(event, context):
    """
    Main API handler for Netlify
    Routes:
    - /api/health
    - /api/status
    - /api/trigger
    - /api/assets
    - /api/alerts/history
    """
    import asyncio
    from src.core.state_store import StateStore
    from src.bot import MarketMonitorBot
    from src.config import get_assets_config
    from datetime import datetime

    path = event.get('path', '')
    http_method = event.get('httpMethod', 'GET')
    query_params = event.get('queryStringParameters') or {}

    print(f"API called: {http_method} {path}")

    # Normalize path - Netlify may prefix with /.netlify/functions/api
    # We strip that prefix
    if '/.netlify/functions/api' in path:
        path = path.split('/.netlify/functions/api')[-1]
    if not path.startswith('/'):
        path = '/' + path

    # Remove /api prefix if present
    if path.startswith('/api'):
        path = path[3:]  # Remove /api
    if not path:
        path = '/'

    async def handle_async():
        store = StateStore()
        bot = MarketMonitorBot()

        if path in ('/', ''):
            return {
                "name": "IFSA Market Monitor API",
                "version": "1.0.0",
                "endpoints": [
                    "/health",
                    "/status",
                    "/trigger (POST)",
                    "/assets",
                    "/indicators/{symbol}",
                    "/alerts/history",
                    "/alerts/test (POST)"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }

        elif path == '/health':
            stats = store.get_stats()
            return {
                "status": "healthy",
                "timestamp": stats.get("last_update"),
                "uptime": stats.get("uptime_human"),
                "tracked_symbols": stats.get("tracked_symbols"),
                "total_alerts_sent": stats.get("total_alerts_sent")
            }

        elif path == '/status':
            assets_cfg = get_assets_config()
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
                    "last_indicator": last_ind.model_dump() if last_ind else None
                })
            return {
                "stats": store.get_stats(),
                "assets": asset_status
            }

        elif path == '/assets':
            return {"assets": get_assets_config()}

        elif path.startswith('/indicators/'):
            symbol = path.split('/')[-1].upper()
            ind = store.get_last_indicator(symbol)
            if not ind:
                raise Exception(f"No data for {symbol}")
            return ind.model_dump()

        elif path == '/alerts/history':
            import json as js
            from pathlib import Path as P
            history_file = P(store.history_file)
            if not history_file.exists():
                return {"history": [], "count": 0}
            with open(history_file, 'r') as f:
                history = js.load(f)
            limit = int(query_params.get('limit', 50))
            history = history[-limit:][::-1]
            return {"history": history, "count": len(history)}

        elif path == '/trigger' and http_method == 'POST':
            result = await bot.run_once()
            await bot.price_fetcher.close()
            return result

        elif path == '/alerts/test' and http_method == 'POST':
            symbol = query_params.get('symbol', 'BTCUSDT')
            success = await bot.alert_manager.send_test_alert(symbol)
            await bot.price_fetcher.close()
            return {"status": "success" if success else "partial", "message": f"Test alert for {symbol}"}

        else:
            raise Exception(f"Endpoint not found: {path}")

    try:
        result = asyncio.run(handle_async())
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, X-API-KEY",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
            },
            "body": json.dumps(result, default=str)
        }
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        status = 404 if "not found" in str(e).lower() else 500
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e), "path": path})
        }
