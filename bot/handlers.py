# bot/handlers.py - Oddiy foydalanuvchilar uchun handlerlar
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime

from database.models import User, Button
from database.db import AsyncSessionLocal
from bot.keyboards import get_main_keyboard, find_button_by_text, has_children

router = Router()

# ─────────────────────────────────────────────
#  Foydalanuvchini saqlash / yangilash
# ─────────────────────────────────────────────
async def save_user(msg: Message):
    async with AsyncSessionLocal() as s:
        try:
            r = await s.execute(select(User).where(User.user_id == msg.from_user.id))
            user = r.scalar_one_or_none()
            if not user:
                user = User(
                    user_id=msg.from_user.id,
                    username=msg.from_user.username,
                    first_name=msg.from_user.first_name,
                    last_name=msg.from_user.last_name,
                )
                s.add(user)
                await s.commit()
            else:
                user.last_active = datetime.now()
                user.username = msg.from_user.username
                user.first_name = msg.from_user.first_name
                await s.commit()
            return user
        except Exception:
            await s.rollback()
            r = await s.execute(select(User).where(User.user_id == msg.from_user.id))
            return r.scalar_one_or_none()


# ─────────────────────────────────────────────
#  Navigation stack — FSMContext orqali (memory leak yo'q)
# ─────────────────────────────────────────────
async def get_nav_stack(state: FSMContext) -> list:
    data = await state.get_data()
    return data.get("nav_stack", [])

async def set_nav_stack(state: FSMContext, stack: list):
    await state.update_data(nav_stack=stack)


# ─────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    user = await save_user(msg)
    # user None bo'lsa ham xavfsiz tekshirish
    if not user or user.is_blocked:
        await msg.answer("❌ Siz bloklandingiz.")
        return

    # Navni tozalash
    await set_nav_stack(state, [])

    kb = await get_main_keyboard(parent_id=None)
    text = (
        f"👋 Salom, <b>{msg.from_user.first_name}</b>!\n\n"
        "📌 Quyidagi bo'limlardan birini tanlang:"
    )
    if kb:
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg.answer(text + "\n\n⚠️ Hozircha bo'limlar qo'shilmagan.", parse_mode="HTML")


# ─────────────────────────────────────────────
#  🏠 Asosiy Menyu
# ─────────────────────────────────────────────
@router.message(F.text == "🏠 Asosiy Menyu")
async def go_home(msg: Message, state: FSMContext):
    await set_nav_stack(state, [])
    kb = await get_main_keyboard(parent_id=None)
    await msg.answer("🏠 Asosiy menyu", reply_markup=kb)


# ─────────────────────────────────────────────
#  ⬅️ Orqaga
# ─────────────────────────────────────────────
@router.message(F.text == "⬅️ Orqaga")
async def go_back(msg: Message, state: FSMContext):
    stack = await get_nav_stack(state)
    if stack:
        stack.pop()
    await set_nav_stack(state, stack)
    parent_id = stack[-1] if stack else None
    kb = await get_main_keyboard(parent_id=parent_id)
    await msg.answer("⬅️ Orqaga qaytdingiz", reply_markup=kb)


# ─────────────────────────────────────────────
#  Matnli xabar — tugma bosilishi
# ─────────────────────────────────────────────
@router.message(F.text)
async def handle_text(msg: Message, state: FSMContext):
    user = await save_user(msg)
    if not user or user.is_blocked:
        await msg.answer("❌ Siz bloklandingiz.")
        return

    button = await find_button_by_text(msg.text)
    if not button:
        return

    if await has_children(button.id):
        stack = await get_nav_stack(state)
        stack.append(button.id)
        await set_nav_stack(state, stack)
        kb = await get_main_keyboard(parent_id=button.id)
        name = f"{button.emoji} {button.name}".strip() if button.emoji else button.name
        await msg.answer(f"📂 <b>{name}</b>", reply_markup=kb, parse_mode="HTML")
    else:
        await send_content(msg, button)


# ─────────────────────────────────────────────
#  Kontent yuborish
# ─────────────────────────────────────────────
async def send_content(msg: Message, btn: Button):
    """Tugma contentini yuborish"""
    if btn.content_type == "text":
        await msg.answer(btn.content_text or "ℹ️ Bo'lim hozircha bo'sh.", parse_mode="HTML")

    elif btn.content_type == "photo" and btn.content_file_id:
        await msg.answer_photo(
            btn.content_file_id,
            caption=btn.content_text or "",
            parse_mode="HTML",
            protect_content=True
        )

    elif btn.content_type == "video" and btn.content_file_id:
        await msg.answer_video(
            btn.content_file_id,
            caption=btn.content_text or "",
            parse_mode="HTML",
            protect_content=True
        )

    elif btn.content_type == "file" and btn.content_file_id:
        await msg.answer_document(
            btn.content_file_id,
            caption=btn.content_text or "",
            parse_mode="HTML",
            protect_content=True
        )

    elif btn.content_type == "submenu":
        pass

    else:
        await msg.answer(btn.content_text or "ℹ️ Bo'lim hozircha bo'sh.", parse_mode="HTML")
