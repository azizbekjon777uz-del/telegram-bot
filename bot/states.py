# bot/states.py - FSM holatlari
from aiogram.fsm.state import State, StatesGroup

class AdminCreateButton(StatesGroup):
    waiting_emoji        = State()
    waiting_name         = State()
    waiting_cols         = State()
    waiting_content_type = State()
    waiting_content      = State()
    waiting_caption      = State()  # Fayl/rasm/video uchun alohida caption


class AdminEditButton(StatesGroup):
    waiting_field     = State()
    waiting_value     = State()

class AdminBroadcast(StatesGroup):
    waiting_message   = State()
    waiting_confirm   = State()

class AdminManage(StatesGroup):
    waiting_admin_id  = State()

class ChannelManage(StatesGroup):
    waiting_channel_id   = State()
    waiting_channel_name = State()
    waiting_channel_link = State()
