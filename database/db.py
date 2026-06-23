# database/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
import sys, os

# Bot papkasining mutlaq yo'li — PythonAnywhere da ham to'g'ri ishlaydi
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from config import DATABASE_URL

# Agar yo'l nisbiy bo'lsa, uni mutlaqqa o'zgartirish
# "sqlite+aiosqlite:///./bot_database.db" -> "sqlite+aiosqlite:////absolute/path/bot_database.db"
if DATABASE_URL.startswith("sqlite") and "///./" in DATABASE_URL:
    db_filename = DATABASE_URL.split("///./")[-1]
    abs_db_path = os.path.join(BASE_DIR, db_filename)
    DATABASE_URL = f"sqlite+aiosqlite:///{abs_db_path}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
