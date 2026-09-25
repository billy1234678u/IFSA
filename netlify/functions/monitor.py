"""
Netlify Scheduled Function - Market Monitor
Runs every 5 minutes via cron in netlify.toml
This is the main event-driven entry point for Netlify deployment

Netlify Scheduled Functions: https://docs.netlify.com/functions/scheduled-functions/
"""
import json
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bot import MarketMonitorBot
from src.config import settings

def handler(event, context):
    """
    Netlify Function handler
    event: contains cron info if scheduled
    context: Netlify context
    """
    print(f"🚀 IFSA Monitor triggered - Event: {event.get('httpMethod', 'scheduled')}")

    # For scheduled functions, event may have different shape
    is_scheduled = event.get('headers', {}).get('x-nf-scheduled') or 'scheduled' in str(event).lower() or event.get('httpMethod') is None

    async def run():
        bot = MarketMonitorBot()
        result = await bot.run_once()
        await bot.price_fetcher.close()
        return result

    try:
        result = asyncio.run(run())
        print(f"✅ Monitor cycle completed: {result.get('status')}")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Market monitor executed successfully",
                "result": result,
                "trigger": "scheduled" if is_scheduled else "http"
            }, default=str)
        }
    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "message": "Market monitor failed"
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {"httpMethod": "GET", "headers": {}}
    test_context = {}
    response = handler(test_event, test_context)
    print(json.dumps(response, indent=2))
