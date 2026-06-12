"""
handlers/today.py - معالج مباريات اليوم
==============================================
يعرض مباريات اليوم بناءً على المنطقة الزمنية المحددة للمستخدم.
"""

import json
import logging
import pytz
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from config import MATCHES_JSON_PATH
from database import get_user_timezone, convert_match_time
from keyboards.main_menu import get_back_to_menu

logger = logging.getLogger(__name__)
router = Router()


def load_matches() -> list:
    """تحميل المباريات من ملف JSON المحلي."""
    try:
        with open(MATCHES_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading matches.json: {e}")
        return []


def format_match_card(match: dict, formatted_date: str, formatted_time: str) -> str:
    """تنسيق بطاقة المباراة حسب النموذج المطلوب."""
    home_flag = match.get("home_flag", "🏳️")
    home_team = match.get("home_team", "غير معروف")
    away_flag = match.get("away_flag", "🏳️")
    away_team = match.get("away_team", "غير معروف")
    stadium = match.get("stadium", "ملعب غير محدد")
    city = match.get("city", "مدينة غير محددة")
    stage = match.get("stage", "")

    card = (
        f"{home_flag} {home_team} × {away_flag} {away_team}\n"
        f"📅 {formatted_date}\n"
        f"🕒 {formatted_time}\n"
        f"🏟 {stadium}\n"
        f"📍 {city}"
    )
    if stage:
        card += f"\n🏆 {stage}"
    
    return card


async def get_today_matches_message(user_id: int) -> str:
    """البحث عن مباريات اليوم وتنسيق الرسالة."""
    user_tz_str = await get_user_timezone(user_id)
    user_tz = pytz.timezone(user_tz_str)
    
    # الحصول على تاريخ اليوم الحالي في توقيت المستخدم
    user_now = datetime.now(user_tz)
    today_str = user_now.strftime("%Y-%m-%d")
    
    matches = load_matches()
    today_matches = []

    for match in matches:
        # تحويل وقت المباراة إلى توقيت المستخدم لمعرفة تاريخها المحلي
        _, _, local_dt = convert_match_time(match["date"], match["time"], user_tz_str)
        if local_dt:
            match_local_date = local_dt.strftime("%Y-%m-%d")
            if match_local_date == today_str:
                formatted_date, formatted_time, _ = convert_match_time(match["date"], match["time"], user_tz_str)
                today_matches.append((match, formatted_date, formatted_time))

    if not today_matches:
        # عرض اسم البلد للتوضيح للمستخدم
        from config import ARABIC_TIMEZONES
        country_name = "توقيتك"
        for name, tz in ARABIC_TIMEZONES.items():
            if tz == user_tz_str:
                country_name = name
                break
        return f"📅 <b>مباريات اليوم ({country_name})</b>\n\nلا توجد مباريات مجدولة اليوم حسب توقيت بلدك المختار ⚽"

    # تنسيق الرسالة
    cards = []
    for match, f_date, f_time in today_matches:
        cards.append(format_match_card(match, f_date, f_time))

    # دمج البطاقات بفاصل خطوط
    separator = "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    message_text = "🏆 <b>مباريات اليوم</b> 🏆\n\n" + separator.join(cards)
    return message_text


@router.message(Command("today"))
async def cmd_today(message: Message):
    """معالج أمر /today."""
    text = await get_today_matches_message(message.from_user.id)
    await message.answer(
        text,
        reply_markup=get_back_to_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "today_matches")
async def callback_today(callback: CallbackQuery):
    """معالج زر مباريات اليوم من القائمة."""
    text = await get_today_matches_message(callback.from_user.id)
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_menu(),
        parse_mode="HTML"
    )
    await callback.answer()
