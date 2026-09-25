"""Allow python -m src to run bot"""
from .bot import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
