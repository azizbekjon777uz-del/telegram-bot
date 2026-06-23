# =============================================
# config.py - Bot va Admin panel sozlamalari
# =============================================
import os
from dotenv import load_dotenv

load_dotenv()

# @BotFather dan olingan bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin foydalanuvchilar (Telegram user_id) — vergul bilan ajrating: 123,456
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()]

# Admin panel
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "supersecretkey2024")

# Server
ADMIN_HOST = os.getenv("ADMIN_HOST", "0.0.0.0")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8000"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot_database.db")
