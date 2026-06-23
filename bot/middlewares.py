# bot/middlewares.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Channel, Admin
from bot.keyboards import sub_check_kb
from config import ADMIN_IDS

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:

        # from_user bo'lmasa o'tkazib yuborish
        if not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id

        # Asosiy adminlarni tekshirmasdan o'tkazish
        if user_id in ADMIN_IDS:
            return await handler(event, data)

        # DB da qo'shimcha adminlarni ham tekshirish
        async with AsyncSessionLocal() as s:
            adm_r = await s.execute(select(Admin).where(Admin.user_id == user_id))
            if adm_r.scalar_one_or_none() is not None:
                return await handler(event, data)

        # Faol kanallarni olish
        async with AsyncSessionLocal() as s:
            r = await s.execute(select(Channel).where(Channel.is_active == True))
            channels = r.scalars().all()

        if not channels:
            return await handler(event, data)

        bot = data["bot"]

        not_subscribed = []
        for ch in channels:
            try:
                member = await bot.get_chat_member(chat_id=ch.channel_id, user_id=user_id)
                if member.status in ["left", "kicked", "banned"]:
                    not_subscribed.append(ch)
            except Exception:
                # Bot kanalga qo'shilmagan yoki admin emas — o'tkazib yuborish
                pass

        if not_subscribed:
            text = "❌ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz shart!</b>"
            kb = sub_check_kb(not_subscribed)

            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                if event.data == "sub_check":
                    await event.answer("Siz hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
                else:
                    await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
            return  # Handlerga o'tishni to'xtatish

        # Obuna tasdiqlash tugmasi
        if isinstance(event, CallbackQuery) and event.data == "sub_check":
            try:
                await event.message.delete()
            except Exception:
                pass
            await event.message.answer("✅ Rahmat! Endi botdan foydalanishingiz mumkin. Boshlash uchun /start bosing.")
            return

        return await handler(event, data)
