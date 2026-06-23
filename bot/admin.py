# bot/admin.py - Bot ichidagi admin panel
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, delete
from datetime import datetime

from config import ADMIN_IDS
from database.models import Button, User, BroadcastLog, Admin, Channel
from database.db import AsyncSessionLocal
from bot.states import AdminCreateButton, AdminEditButton, AdminBroadcast, AdminManage, ChannelManage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards import (
    admin_main_kb, admin_buttons_kb, admin_btn_info_kb,
    admin_edit_fields_kb, admin_cols_kb, admin_content_type_kb,
    confirm_broadcast_kb, admin_admins_kb, admin_channels_kb
)

router = Router()


async def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Admin).where(Admin.user_id == user_id))
        return r.scalar_one_or_none() is not None


# ═══════════════════════════════════════
#  /admin — Asosiy admin menyu
# ═══════════════════════════════════════
@router.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await msg.answer("❌ Sizda ruxsat yo'q!")
        return
    await state.clear()
    await msg.answer(
        "🛠️ <b>Admin Panel</b>\n\nNimani boshqarmoqchisiz?",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
#  Callback: adm:main
# ═══════════════════════════════════════
@router.callback_query(F.data == "adm:main")
async def cb_main(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)
    await state.clear()
    await cb.message.edit_text(
        "🛠️ <b>Admin Panel</b>\n\nNimani boshqarmoqchisiz?",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
#  Callback: adm:buttons:<parent_id>
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:buttons:"))
async def cb_buttons(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    pid_str = cb.data.split(":")[-1]
    parent_id = None if pid_str == "null" else int(pid_str)

    kb = await admin_buttons_kb(parent_id)

    # Bo'lim nomini olish
    title = "📋 <b>Asosiy bo'lim tugmalari</b>"
    if parent_id:
        async with AsyncSessionLocal() as s:
            r = await s.execute(select(Button).where(Button.id == parent_id))
            p = r.scalar_one_or_none()
            if p:
                name = f"{p.emoji} {p.name}".strip() if p.emoji else p.name
                title = f"📂 <b>{name}</b> ichidagi tugmalar"

    try:
        await cb.message.edit_text(title, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await cb.answer()


# ═══════════════════════════════════════
#  Callback: adm:btn_info:<id>
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:btn_info:"))
async def cb_btn_info(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    btn_id = int(cb.data.split(":")[-1])
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Button).where(Button.id == btn_id))
        btn = r.scalar_one_or_none()

    if not btn:
        return await cb.answer("Topilmadi!", show_alert=True)

    name = f"{btn.emoji} {btn.name}".strip() if btn.emoji else btn.name
    status = "✅ Faol" if btn.is_active else "❌ O'chirilgan"
    content_preview = (btn.content_text or "")[:100]

    text = (
        f"🔹 <b>{name}</b>\n\n"
        f"📌 Status: {status}\n"
        f"🗂 Content turi: <code>{btn.content_type}</code>\n"
        f"📐 Ustunlar: {btn.cols}\n"
        f"📝 Content: {content_preview or '—'}"
    )

    await cb.message.edit_text(
        text,
        reply_markup=admin_btn_info_kb(btn.id, btn.parent_id),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
#  TUGMA QO'SHISH
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:add_btn:"))
async def cb_add_btn_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    pid_str = cb.data.split(":")[-1]
    parent_id = None if pid_str == "null" else int(pid_str)
    await state.update_data(parent_id=parent_id)

    await cb.message.edit_text(
        "➕ <b>Yangi tugma qo'shish</b>\n\n"
        "😀 Emoji kiriting (yoki — bosing agar kerak bo'lmasa):\n\n"
        "<i>Misol: 🏠 yoki 📚</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminCreateButton.waiting_emoji)


@router.message(AdminCreateButton.waiting_emoji)
async def cb_add_emoji(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    # msg.text None bo'lishi mumkin (rasm yoki fayl yuborilsa)
    if not msg.text:
        await msg.answer("❌ Iltimos faqat matn yuboring (yoki — belgisi):")
        return
    emoji = "" if msg.text.strip() == "—" else msg.text.strip()
    await state.update_data(emoji=emoji)
    await msg.answer("✏️ Tugma <b>nomini</b> kiriting:", parse_mode="HTML")
    await state.set_state(AdminCreateButton.waiting_name)


@router.message(AdminCreateButton.waiting_name)
async def cb_add_name(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.update_data(name=msg.text.strip(), cols=2)
    await msg.answer(
        "📦 Content turini tanlang:",
        reply_markup=admin_content_type_kb()
    )
    await state.set_state(AdminCreateButton.waiting_content_type)


@router.callback_query(F.data.startswith("ctype:"), AdminCreateButton.waiting_content_type)
async def cb_add_content_type(cb: CallbackQuery, state: FSMContext):
    ctype = cb.data.split(":")[-1]
    await state.update_data(content_type=ctype)

    if ctype == "submenu":
        # To'g'ridan-to'g'ri saqlash
        await save_new_button(cb.message, state)
        await cb.message.answer(
            "✅ Bo'lim tugmasi yaratildi! Endi bu tugma ichiga boshqa tugmalar qo'shishingiz mumkin.",
            reply_markup=admin_main_kb()
        )
        return

    hints = {
        "text":  "📝 Xabar matnini kiriting (HTML format mumkin):\n\n<i>Misol: &lt;b&gt;Salom&lt;/b&gt; dunyo!</i>",
        "photo": "📷 Bot ga rasm yuboring (yoki file_id kiriting):",
        "video": "🎥 Bot ga video yuboring (yoki file_id kiriting):",
        "file":  "📁 Bot ga fayl yuboring (yoki file_id kiriting):",
    }
    await cb.message.edit_text(hints.get(ctype, "Matnni kiriting:"), parse_mode="HTML")
    await state.set_state(AdminCreateButton.waiting_content)


@router.message(AdminCreateButton.waiting_content)
async def cb_add_content(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return

    data = await state.get_data()
    ctype = data.get("content_type", "text")

    if ctype == "text":
        # Matn uchun to'g'ridan saqlash
        await state.update_data(content_text=msg.text, content_file_id=None)
        await save_new_button(msg, state)
        await msg.answer(
            "✅ <b>Tugma muvaffaqiyatli yaratildi!</b>",
            reply_markup=admin_main_kb(),
            parse_mode="HTML"
        )
        return

    # Fayl/rasm/video — file_id saqlash, caption alohida so'rash
    if ctype == "photo" and msg.photo:
        await state.update_data(content_file_id=msg.photo[-1].file_id)
    elif ctype == "video" and msg.video:
        await state.update_data(content_file_id=msg.video.file_id)
    elif ctype == "file" and msg.document:
        await state.update_data(content_file_id=msg.document.file_id)
    else:
        # Noto'g'ri format
        await msg.answer("❌ Noto'g'ri format. Qayta yuboring:")
        return

    # Caption alohida so'rash (forwarded caption ishlatilmaydi!)
    await msg.answer(
        "✏️ Endi <b>caption (tavsif)</b> yozing:\n"
        "(Yoki manbasiz matn kiriting. Forwarded matn avtomatik olinmaydi!)\n\n"
        "<i>Bo'sh qoldirish uchun — yuboring</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminCreateButton.waiting_caption)


@router.message(AdminCreateButton.waiting_caption)
async def cb_add_caption(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    caption = "" if msg.text and msg.text.strip() == "—" else (msg.text or "")
    await state.update_data(content_text=caption)
    await save_new_button(msg, state)
    await msg.answer(
        "✅ <b>Tugma muvaffaqiyatli yaratildi!</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


async def save_new_button(msg_or_cb, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as s:
        # Order num
        pid = data.get("parent_id")
        r = await s.execute(
            select(func.count(Button.id)).where(Button.parent_id == pid)
        )
        order = r.scalar() or 0

        btn = Button(
            name=data.get("name", "Nomsiz"),
            emoji=data.get("emoji", ""),
            parent_id=pid,
            content_type=data.get("content_type", "text"),
            content_text=data.get("content_text"),
            content_file_id=data.get("content_file_id"),
            cols=data.get("cols", 2),
            order_num=order,
        )
        s.add(btn)
        await s.commit()
    await state.clear()


# ═══════════════════════════════════════
#  TAHRIRLASH
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:edit:"))
async def cb_edit(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    btn_id = int(cb.data.split(":")[-1])
    await state.update_data(edit_btn_id=btn_id)
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Button).where(Button.id == btn_id))
        btn = r.scalar_one_or_none()

    if not btn:
        return await cb.answer("Topilmadi!", show_alert=True)

    name = f"{btn.emoji} {btn.name}".strip() if btn.emoji else btn.name
    await cb.message.edit_text(
        f"✏️ <b>{name}</b> ni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?",
        reply_markup=admin_edit_fields_kb(btn_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm:editf:"))
async def cb_edit_field(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    parts = cb.data.split(":")
    btn_id = int(parts[2])
    field = parts[3]

    if field == "cols":
        await cb.message.edit_text(
            "📐 Ustunlar sonini tanlang:",
            reply_markup=admin_cols_kb(btn_id)
        )
        return

    await state.update_data(edit_btn_id=btn_id, edit_field=field)
    prompts = {
        "name":    "✏️ Yangi <b>nom</b> kiriting:",
        "emoji":   "😀 Yangi <b>emoji</b> kiriting (bo'sh qoldirish uchun — yuboring):",
        "content": "📝 Yangi <b>content</b> kiriting (matn, rasm, video, yoki fayl yuboring):",
    }
    await cb.message.edit_text(prompts.get(field, "Yangi qiymat kiriting:"), parse_mode="HTML")
    await state.set_state(AdminEditButton.waiting_value)


@router.callback_query(F.data.startswith("adm:setcols:"))
async def cb_set_cols(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    parts = cb.data.split(":")
    btn_id = int(parts[2])
    cols = int(parts[3])

    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Button).where(Button.id == btn_id))
        btn = r.scalar_one_or_none()
        if btn:
            btn.cols = cols
            await s.commit()

    await cb.answer(f"✅ {cols} ustun o'rnatildi!", show_alert=True)
    await cb.message.edit_text(
        f"✅ Ustunlar soni {cols} ga o'zgartirildi!",
        reply_markup=admin_edit_fields_kb(btn_id)
    )


@router.message(AdminEditButton.waiting_value)
async def cb_save_edit(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return

    data = await state.get_data()
    btn_id = data.get("edit_btn_id")
    field = data.get("edit_field")

    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Button).where(Button.id == btn_id))
        btn = r.scalar_one_or_none()
        if not btn:
            await msg.answer("Xato: Tugma topilmadi!")
            await state.clear()
            return

        if field == "name":
            btn.name = msg.text.strip()
        elif field == "emoji":
            btn.emoji = "" if msg.text.strip() == "—" else msg.text.strip()
        elif field == "content":
            if msg.text:
                btn.content_type = "text"
                btn.content_text = msg.text
            elif msg.photo:
                btn.content_type = "photo"
                btn.content_file_id = msg.photo[-1].file_id
                btn.content_text = msg.caption or ""
            elif msg.video:
                btn.content_type = "video"
                btn.content_file_id = msg.video.file_id
                btn.content_text = msg.caption or ""
            elif msg.document:
                btn.content_type = "file"
                btn.content_file_id = msg.document.file_id
                btn.content_text = msg.caption or ""

        await s.commit()

    await state.clear()
    await msg.answer("✅ Muvaffaqiyatli saqlandi!", reply_markup=admin_main_kb())


# ═══════════════════════════════════════
#  O'CHIRISH
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:delete:"))
async def cb_delete(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    btn_id = int(cb.data.split(":")[-1])

    async with AsyncSessionLocal() as s:
        # Rekursiv o'chirish
        async def delete_recursive(bid):
            children = (await s.execute(
                select(Button).where(Button.parent_id == bid)
            )).scalars().all()
            for child in children:
                await delete_recursive(child.id)
                await s.delete(child)
            r = await s.execute(select(Button).where(Button.id == bid))
            b = r.scalar_one_or_none()
            if b:
                await s.delete(b)

        await delete_recursive(btn_id)
        await s.commit()

    await cb.answer("🗑️ O'chirildi!", show_alert=True)
    await cb.message.edit_text(
        "🗑️ Tugma o'chirildi!",
        reply_markup=admin_main_kb()
    )


# ═══════════════════════════════════════
#  HOLAT (TOGGLE)
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:toggle:"))
async def cb_toggle(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    btn_id = int(cb.data.split(":")[-1])
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Button).where(Button.id == btn_id))
        btn = r.scalar_one_or_none()
        if btn:
            btn.is_active = not btn.is_active
            await s.commit()
            status = "✅ Faollashtirildi" if btn.is_active else "❌ O'chirildi"
            await cb.answer(status, show_alert=True)
            # Refresh
            name = f"{btn.emoji} {btn.name}".strip() if btn.emoji else btn.name
            s2 = "✅ Faol" if btn.is_active else "❌ O'chirilgan"
            await cb.message.edit_text(
                f"🔹 <b>{name}</b>\n📌 Status: {s2}\n🗂 Content: {btn.content_type}",
                reply_markup=admin_btn_info_kb(btn.id, btn.parent_id),
                parse_mode="HTML"
            )


# ═══════════════════════════════════════
#  FOYDALANUVCHILAR
# ═══════════════════════════════════════
@router.callback_query(F.data == "adm:users")
async def cb_users(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    async with AsyncSessionLocal() as s:
        total = (await s.execute(select(func.count(User.id)))).scalar()
        blocked = (await s.execute(
            select(func.count(User.id)).where(User.is_blocked == True)
        )).scalar()
        today = datetime.now().date()
        new_today = (await s.execute(
            select(func.count(User.id)).where(
                func.date(User.joined_at) == today
            )
        )).scalar()

        # So'ngi 10 user
        last_users = (await s.execute(
            select(User).order_by(User.joined_at.desc()).limit(10)
        )).scalars().all()

    lines = [f"👥 <b>Foydalanuvchilar</b>\n",
             f"📊 Jami: <b>{total}</b> ta",
             f"✅ Faol: <b>{total - blocked}</b> ta",
             f"🚫 Bloklangan: <b>{blocked}</b> ta",
             f"🆕 Bugun qo'shilgan: <b>{new_today}</b> ta\n",
             "━━━━━━━━━━━━━━\n<b>So'ngi 10 foydalanuvchi:</b>"]

    for u in last_users:
        name = u.first_name or "Nomsiz"
        uname = f"@{u.username}" if u.username else f"ID:{u.user_id}"
        block = "🚫" if u.is_blocked else ""
        lines.append(f"{block} <a href='tg://user?id={u.user_id}'>{name}</a> {uname}")

    await cb.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Admin Menyu", callback_data="adm:main")]
        ]),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════
#  BROADCAST
# ═══════════════════════════════════════
@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    async with AsyncSessionLocal() as s:
        count = (await s.execute(
            select(func.count(User.id)).where(User.is_blocked == False)
        )).scalar()

    await cb.message.edit_text(
        f"📢 <b>Broadcast</b>\n\n"
        f"Xabar <b>{count}</b> ta foydalanuvchiga yuboriladi.\n\n"
        f"📝 Yubormoqchi bo'lgan xabaringizni yozing\n"
        f"<i>(HTML formatda: &lt;b&gt;qalin&lt;/b&gt;, &lt;i&gt;kursiv&lt;/i&gt;, rasm, video ham yuborishingiz mumkin)</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminBroadcast.waiting_message)


@router.message(AdminBroadcast.waiting_message)
async def bc_get_message(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return

    # Xabar turini saqlash
    if msg.text:
        await state.update_data(bc_text=msg.text, bc_type="text")
    elif msg.photo:
        await state.update_data(
            bc_file_id=msg.photo[-1].file_id,
            bc_caption=msg.caption or "",
            bc_type="photo"
        )
    elif msg.video:
        await state.update_data(
            bc_file_id=msg.video.file_id,
            bc_caption=msg.caption or "",
            bc_type="video"
        )
    else:
        await state.update_data(bc_text=msg.text or "", bc_type="text")

    await msg.answer(
        "📤 Xabar tasdiqlang:\n\n"
        "Yuqoridagi xabar barcha foydalanuvchilarga yuboriladi.",
        reply_markup=confirm_broadcast_kb()
    )
    await state.set_state(AdminBroadcast.waiting_confirm)


@router.callback_query(F.data == "bc:confirm", AdminBroadcast.waiting_confirm)
async def bc_confirm(cb: CallbackQuery, state: FSMContext, bot: Bot):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    data = await state.get_data()
    await state.clear()

    await cb.message.edit_text("⏳ Xabar yuborilmoqda...")

    async with AsyncSessionLocal() as s:
        users = (await s.execute(
            select(User).where(User.is_blocked == False)
        )).scalars().all()

    success, failed = 0, 0
    bc_type = data.get("bc_type", "text")

    for user in users:
        try:
            if bc_type == "text":
                await bot.send_message(user.user_id, data["bc_text"], parse_mode="HTML")
            elif bc_type == "photo":
                await bot.send_photo(user.user_id, data["bc_file_id"], caption=data.get("bc_caption", ""), parse_mode="HTML")
            elif bc_type == "video":
                await bot.send_video(user.user_id, data["bc_file_id"], caption=data.get("bc_caption", ""), parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)  # Telegram: max 20 msg/sec, rate limit oldini olish
        except Exception:
            failed += 1

    async with AsyncSessionLocal() as s:
        log = BroadcastLog(
            message_text=data.get("bc_text") or data.get("bc_caption") or "",
            total_users=len(users),
            success_count=success,
            failed_count=failed,
        )
        s.add(log)
        await s.commit()

    await cb.message.edit_text(
        f"✅ <b>Broadcast tugadi!</b>\n\n"
        f"📤 Jami: {len(users)} ta\n"
        f"✅ Muvaffaqiyatli: {success} ta\n"
        f"❌ Xato: {failed} ta",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "bc:cancel")
async def bc_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "❌ Broadcast bekor qilindi.",
        reply_markup=admin_main_kb()
    )


# ═══════════════════════════════════════
#  STATISTIKA
# ═══════════════════════════════════════
@router.callback_query(F.data == "adm:stats")
async def cb_stats(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌ Ruxsat yo'q", show_alert=True)

    async with AsyncSessionLocal() as s:
        total_users = (await s.execute(select(func.count(User.id)))).scalar()
        total_buttons = (await s.execute(
            select(func.count(Button.id)).where(Button.is_active == True)
        )).scalar()
        all_buttons = (await s.execute(select(func.count(Button.id)))).scalar()
        blocked_users = (await s.execute(
            select(func.count(User.id)).where(User.is_blocked == True)
        )).scalar()
        broadcasts = (await s.execute(select(func.count(BroadcastLog.id)))).scalar()
        today = datetime.now().date()
        new_today = (await s.execute(
            select(func.count(User.id)).where(func.date(User.joined_at) == today)
        )).scalar()

    await cb.message.edit_text(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"🆕 Bugun qo'shilgan: <b>{new_today}</b>\n"
        f"🚫 Bloklangan: <b>{blocked_users}</b>\n\n"
        f"📋 Faol tugmalar: <b>{total_buttons}</b>\n"
        f"📦 Jami tugmalar: <b>{all_buttons}</b>\n\n"
        f"📢 Jami broadcastlar: <b>{broadcasts}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Admin Menyu", callback_data="adm:main")]
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm:cancel")
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ Bekor qilindi.", reply_markup=admin_main_kb())

# ═══════════════════════════════════════
#  TUGMA REORDER (TARTIB)
# ═══════════════════════════════════════
@router.callback_query(F.data.startswith("adm:reorder:"))
async def cb_reorder(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌", show_alert=True)
    
    parts = cb.data.split(":")
    direction = parts[2]
    btn_id = int(parts[3])

    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Button).where(Button.id == btn_id))
        btn = r.scalar_one_or_none()
        if not btn: return await cb.answer("Topilmadi!")

        # Qolgan tugmalarni olish
        r_all = await s.execute(
            select(Button).where(Button.parent_id == btn.parent_id).order_by(Button.order_num)
        )
        siblings = list(r_all.scalars().all())
        idx = next((i for i, b in enumerate(siblings) if b.id == btn_id), -1)

        if direction == "up" and idx > 0:
            siblings[idx].order_num, siblings[idx-1].order_num = siblings[idx-1].order_num, siblings[idx].order_num
            await s.commit()
            await cb.answer("⬆️ Yuqoriga ko'tarildi")
        elif direction == "down" and idx < len(siblings) - 1:
            siblings[idx].order_num, siblings[idx+1].order_num = siblings[idx+1].order_num, siblings[idx].order_num
            await s.commit()
            await cb.answer("⬇️ Pastga tushdi")
        else:
            await cb.answer("Harakatning iloji yo'q")
            return

    # Menyu yangilash — parent_id ni to'g'ri uzatish
    pid_str = str(btn.parent_id) if btn.parent_id is not None else "null"
    # cb.data ni vaqtincha almashtirish orqali cb_buttons ga to'g'ri parent_id beramiz
    import types
    fake_cb = types.SimpleNamespace(
        data=f"adm:buttons:{pid_str}",
        from_user=cb.from_user,
        message=cb.message,
        answer=cb.answer
    )
    await cb_buttons(fake_cb)


# ═══════════════════════════════════════
#  ADMINLAR BOSHQARUVI
# ═══════════════════════════════════════
@router.callback_query(F.data == "adm:admins")
async def cb_admins_list(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return await cb.answer("❌", show_alert=True)
    
    async with AsyncSessionLocal() as s:
        admins = (await s.execute(select(Admin))).scalars().all()
    
    text = "👮 <b>Adminlar ro'yxati:</b>\n\n"
    for a in ADMIN_IDS:
        text += f"👑 <b>{a}</b> (Asosiy Admin)\n"
    for a in admins:
        text += f"🔹 <code>{a.user_id}</code> - /del_admin_{a.id}\n"
    
    await cb.message.edit_text(text, reply_markup=admin_admins_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:add_admin")
async def cb_add_admin_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return
    await cb.message.edit_text("Yangi adminning <b>Telegram ID</b> raqamini yuboring:\n(Masalan: 123456789)", parse_mode="HTML")
    await state.set_state(AdminManage.waiting_admin_id)

@router.message(AdminManage.waiting_admin_id)
async def cb_add_admin_save(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id): return
    if not msg.text or not msg.text.strip().isdigit():
        return await msg.answer("❌ Faqat raqam yuboring!")

    new_user_id = int(msg.text.strip())
    async with AsyncSessionLocal() as s:
        # Avval mavjudligini tekshirish
        existing = (await s.execute(select(Admin).where(Admin.user_id == new_user_id))).scalar_one_or_none()
        if existing:
            await state.clear()
            return await msg.answer("⚠️ Bu foydalanuvchi allaqachon admin!", reply_markup=admin_admins_kb())
        if new_user_id in ADMIN_IDS:
            await state.clear()
            return await msg.answer("⚠️ Bu foydalanuvchi asosiy admin!", reply_markup=admin_admins_kb())
        new_adm = Admin(user_id=new_user_id)
        s.add(new_adm)
        await s.commit()

    await state.clear()
    await msg.answer("✅ Yangi admin qo'shildi!", reply_markup=admin_admins_kb())

@router.message(F.text.startswith("/del_admin_"))
async def del_admin_cmd(msg: Message):
    if not await is_admin(msg.from_user.id): return
    try:
        # /del_admin_123 -> "123"
        admin_pk = int(msg.text.split("/del_admin_")[-1].strip())
    except (ValueError, IndexError):
        return await msg.answer("❌ Noto'g'ri format!")
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Admin).where(Admin.id == admin_pk))
        adm = r.scalar_one_or_none()
        if adm:
            await s.delete(adm)
            await s.commit()
            await msg.answer("🗑️ Admin o'chirildi.")
        else:
            await msg.answer("❌ Admin topilmadi!")


# ═══════════════════════════════════════
#  KANALLAR BOSHQARUVI (Majburiy Obuna)
# ═══════════════════════════════════════
@router.callback_query(F.data == "adm:channels")
async def cb_channels_list(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return
    async with AsyncSessionLocal() as s:
        channels = (await s.execute(select(Channel))).scalars().all()
    
    text = "📢 <b>Majburiy obuna kanallari:</b>\n\n"
    if not channels:
        text += "Hozircha kanallar yo'q."
    for c in channels:
        text += f"🔹 <a href='{c.channel_link}'>{c.channel_name}</a> - /del_channel_{c.id}\n"
    
    await cb.message.edit_text(text, reply_markup=admin_channels_kb(), parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data == "adm:add_channel")
async def cb_add_channel_start(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return
    await cb.message.edit_text("Kanal ID sini yuboring (Masalan: @mychannel yoki -1001234567):")
    await state.set_state(ChannelManage.waiting_channel_id)

@router.message(ChannelManage.waiting_channel_id)
async def cb_add_ch_id(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id): return
    await state.update_data(ch_id=msg.text.strip())
    await msg.answer("Kanal uchun nom kiriting (Misol: Dasturchilar kanali):")
    await state.set_state(ChannelManage.waiting_channel_name)

@router.message(ChannelManage.waiting_channel_name)
async def cb_add_ch_name(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id): return
    await state.update_data(ch_name=msg.text.strip())
    await msg.answer("Kanal ssilkasini yuboring (Misol: https://t.me/mychannel):")
    await state.set_state(ChannelManage.waiting_channel_link)

@router.message(ChannelManage.waiting_channel_link)
async def cb_add_ch_save(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id): return
    data = await state.get_data()
    async with AsyncSessionLocal() as s:
        new_ch = Channel(
            channel_id=data['ch_id'],
            channel_name=data['ch_name'],
            channel_link=msg.text.strip()
        )
        s.add(new_ch)
        await s.commit()
    
    await state.clear()
    await msg.answer("✅ Kanal qo'shildi!", reply_markup=admin_channels_kb())

@router.message(F.text.startswith("/del_channel_"))
async def del_channel_cmd(msg: Message):
    if not await is_admin(msg.from_user.id): return
    try:
        ch_pk = int(msg.text.split("/del_channel_")[-1].strip())
    except (ValueError, IndexError):
        return await msg.answer("❌ Noto'g'ri format!")
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Channel).where(Channel.id == ch_pk))
        ch = r.scalar_one_or_none()
        if ch:
            await s.delete(ch)
            await s.commit()
            await msg.answer("🗑️ Kanal o'chirildi.")
        else:
            await msg.answer("❌ Kanal topilmadi!")


