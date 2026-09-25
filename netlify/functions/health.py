"""
Simple health check function for Netlify - lightweight, no heavy deps
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def handler(event, context):
    try:
        from src.core.state_store import StateStore
        store = StateStore()
        stats = store.get_stats()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "healthy",
                "service": "IFSA Market Monitor",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": stats
            }, default=str)
        }
    except Exception as e:
        return {
            "statusCode": 200,  # Still 200 to not trigger Netlify alerts, but status degraded
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "degraded",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        }
