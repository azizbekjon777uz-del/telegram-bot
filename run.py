# run.py
import asyncio
import sys
import os

# Windows uchun UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import main

if __name__ == "__main__":
    print("=" * 50)
    print("  Telegram Bot ishga tushmoqda...")
    print("  Admin panel: /admin buyrug'ini yuboring")
    print("=" * 50)
    asyncio.run(main())
