# bot/keyboards.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from sqlalchemy import select
from database.models import Button
from database.db import AsyncSessionLocal


# ─────────────────────────────────────────────
#  USER KLAVIATURASI
# ─────────────────────────────────────────────
async def get_main_keyboard(parent_id=None):
    """DBdan tugmalarni o'qib, reply keyboard qaytaradi"""
    async with AsyncSessionLocal() as session:
        q = select(Button).where(
            Button.parent_id == parent_id,
            Button.is_active == True
        ).order_by(Button.order_num)
        result = await session.execute(q)
        buttons = result.scalars().all()

    if not buttons:
        if parent_id is not None:
            return ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="⬅️ Orqaga"),
                           KeyboardButton(text="🏠 Asosiy Menyu")]],
                resize_keyboard=True
            )
        return None

    keyboard, row = [], []
    cols = 2  # default
    for btn in buttons:
        cols = btn.cols
        label = f"{btn.emoji} {btn.name}".strip() if btn.emoji else btn.name
        row.append(KeyboardButton(text=label))
        if len(row) >= cols:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    if parent_id is not None:
        keyboard.append([
            KeyboardButton(text="⬅️ Orqaga"),
            KeyboardButton(text="🏠 Asosiy Menyu")
        ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def find_button_by_text(text: str):
    """Tugmani matn bo'yicha topish"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Button).where(Button.is_active == True)
        )
        for btn in result.scalars().all():
            label = f"{btn.emoji} {btn.name}".strip() if btn.emoji else btn.name
            if label == text.strip() or btn.name == text.strip():
                return btn
    return None


async def has_children(button_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        q = select(Button).where(
            Button.parent_id == button_id,
            Button.is_active == True
        )
        r = await session.execute(q)
        return bool(r.scalars().first())


# ─────────────────────────────────────────────
#  ADMIN INLINE KLAVIATURALARI
# ─────────────────────────────────────────────
def admin_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Tugmalar", callback_data="adm:buttons:null"),
                InlineKeyboardButton(text="➕ Tugma qo'sh", callback_data="adm:add_btn:null")
            ],
            [
                InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users"),
                InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")
            ],
            [
                InlineKeyboardButton(text="👮 Adminlar", callback_data="adm:admins"),
                InlineKeyboardButton(text="📢 Kanallar", callback_data="adm:channels")
            ],
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")
            ]
        ]
    )


async def admin_buttons_kb(parent_id=None):
    """Admin uchun tugmalar ro'yxati inline keyboard"""
    async with AsyncSessionLocal() as session:
        q = select(Button).where(
            Button.parent_id == parent_id
        ).order_by(Button.order_num)
        r = await session.execute(q)
        buttons = r.scalars().all()

    rows = []
    for btn in buttons:
        label = f"{btn.emoji} {btn.name}".strip() if btn.emoji else btn.name
        status = "✅" if btn.is_active else "❌"
        rows.append([
            InlineKeyboardButton(
                text=f"{status} {label}",
                callback_data=f"adm:btn_info:{btn.id}"
            )
        ])

    nav = []
    if parent_id:
        # parent ni topib, uning parent_id sini olamiz
        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Button).where(Button.id == parent_id))
            p = r.scalar_one_or_none()
            grandparent = p.parent_id if p else None
        nav.append(InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"adm:buttons:{grandparent or 'null'}"
        ))
    nav.append(InlineKeyboardButton(
        text="➕ Bu yerga qo'shish",
        callback_data=f"adm:add_btn:{parent_id or 'null'}"
    ))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Admin Menyu", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_btn_info_kb(btn_id: int, parent_id: int = None):
    pid = parent_id if parent_id is not None else "null"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"adm:edit:{btn_id}"),
                InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"adm:delete:{btn_id}")
            ],
            [
                InlineKeyboardButton(text="⬆️ Yuqoriga", callback_data=f"adm:reorder:up:{btn_id}"),
                InlineKeyboardButton(text="⬇️ Pastga", callback_data=f"adm:reorder:down:{btn_id}")
            ],
            [
                InlineKeyboardButton(text="🟢/🔴 Holat (Yoqish/O'chirish)", callback_data=f"adm:toggle:{btn_id}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"adm:buttons:{pid}")
            ]
        ]
    )


def admin_edit_fields_kb(btn_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nom", callback_data=f"adm:editf:{btn_id}:name"),
         InlineKeyboardButton(text="😀 Emoji", callback_data=f"adm:editf:{btn_id}:emoji")],
        [InlineKeyboardButton(text="📝 Content", callback_data=f"adm:editf:{btn_id}:content"),
         InlineKeyboardButton(text="📐 Ustunlar", callback_data=f"adm:editf:{btn_id}:cols")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"adm:btn_info:{btn_id}")],
    ])


def admin_cols_kb(btn_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ 1 ustun", callback_data=f"adm:setcols:{btn_id}:1"),
         InlineKeyboardButton(text="2️⃣ 2 ustun", callback_data=f"adm:setcols:{btn_id}:2")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"adm:edit:{btn_id}")],
    ])


def admin_content_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Matn", callback_data="ctype:text"),
         InlineKeyboardButton(text="🖼️ Rasm", callback_data="ctype:photo")],
        [InlineKeyboardButton(text="🎥 Video", callback_data="ctype:video"),
         InlineKeyboardButton(text="📁 Fayl", callback_data="ctype:file")],
        [InlineKeyboardButton(text="📂 Faqat Bo'lim", callback_data="ctype:submenu")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm:cancel")],
    ])


def confirm_broadcast_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="bc:confirm"),
         InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc:cancel")],
    ])

def admin_admins_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="adm:add_admin")],
        [InlineKeyboardButton(text="🏠 Admin Menyu", callback_data="adm:main")],
    ])

def admin_channels_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="adm:add_channel")],
        [InlineKeyboardButton(text="🏠 Admin Menyu", callback_data="adm:main")],
    ])

def sub_check_kb(channels: list):
    """Majburiy obuna uchun klaviatura"""
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch.channel_name}", url=ch.channel_link)])
    
    buttons.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="sub_check")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
