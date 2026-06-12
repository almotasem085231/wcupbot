"""
handlers/schedule.py - معالج جدول البطولة كاملاً
==============================================
يعرض جدول مباريات كأس العالم 2026 كاملاً مع إمكانية التصفح بصفحات متتالية (متوافق مع aiogram v2).
"""

import json
import logging
from math import ceil
from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import MATCHES_JSON_PATH
from database import get_user_timezone, convert_match_time, get_match_status

logger = logging.getLogger(__name__)

PAGE_SIZE = 4  # عدد المباريات في الصفحة الواحدة


def load_sorted_matches() -> list:
    """تحميل المباريات وترتيبها زمنياً."""
    try:
        with open(MATCHES_JSON_PATH, "r", encoding="utf-8") as f:
            matches = json.load(f)
            # ترتيب حسب التاريخ والوقت
            matches.sort(key=lambda m: (m.get("date", ""), m.get("time", "")))
            return matches
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

    status = get_match_status(match.get("date", ""), match.get("time", ""))

    card = (
        f"📌 <b>الحالة:</b> {status}\n"
        f"{home_flag} {home_team} × {away_flag} {away_team}\n"
        f"📅 {formatted_date}\n"
        f"🕒 {formatted_time}\n"
        f"🏟 {stadium}\n"
        f"📍 {city}"
    )
    if stage:
        card += f"\n🏆 {stage}"
    
    return card


def get_schedule_keyboard(page_index: int, total_pages: int) -> InlineKeyboardMarkup:
    """إنشاء أزرار التصفح لجدول البطولة."""
    markup = InlineKeyboardMarkup()
    
    nav_row = []
    # زر السابق
    if page_index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅ السابق", callback_data=f"all_matches_page:{page_index - 1}"))
    
    # زر التالي
    if page_index < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡ التالي", callback_data=f"all_matches_page:{page_index + 1}"))
        
    if nav_row:
        markup.row(*nav_row)
        
    markup.add(InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu"))
    return markup


async def get_schedule_page_message(user_id: int, page_index: int) -> tuple[str, InlineKeyboardMarkup]:
    """تجهيز نص الصفحة الحالية وأزرار التصفح."""
    user_tz_str = await get_user_timezone(user_id)
    matches = load_sorted_matches()
    total_matches = len(matches)
    
    if total_matches == 0:
        return "📅 <b>جدول البطولة</b>\n\nلا توجد مباريات مضافة في الجدول حالياً.", get_schedule_keyboard(0, 0)
        
    total_pages = ceil(total_matches / PAGE_SIZE)
    
    # تصحيح مؤشر الصفحة إذا خرج عن الحدود
    if page_index < 0:
        page_index = 0
    elif page_index >= total_pages:
        page_index = total_pages - 1
        
    start_idx = page_index * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_matches = matches[start_idx:end_idx]
    
    cards = []
    for match in page_matches:
        formatted_date, formatted_time, _ = convert_match_time(match["date"], match["time"], user_tz_str)
        cards.append(format_match_card(match, formatted_date, formatted_time))
        
    separator = "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    header = (
        f"📅 <b>جدول كأس العالم 2026</b>\n"
        f"📄 الصفحة {page_index + 1} من {total_pages} (مجموع المباريات: {total_matches})\n\n"
    )
    
    text = header + separator.join(cards) + "\n\n━━━━━━━━━━━━━━━━━━━━━━"
    markup = get_schedule_keyboard(page_index, total_pages)
    
    return text, markup


async def cmd_schedule(message: Message):
    """معالج أمر /schedule."""
    text, markup = await get_schedule_page_message(message.from_user.id, 0)
    await message.answer(
        text,
        reply_markup=markup,
        parse_mode="HTML"
    )


async def callback_schedule_page(callback: CallbackQuery):
    """معالج التصفح بين صفحات جدول البطولة."""
    page_index = int(callback.data.split(":")[1])
    text, markup = await get_schedule_page_message(callback.from_user.id, page_index)
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        # لتجنب حدوث خطأ إذا لم تتغير الرسالة
        logger.debug(f"Edit message ignore: {e}")
        
    await callback.answer()


def register_schedule_handlers(dp: Dispatcher):
    """تسجيل معالجات الجدول في موزع المهام."""
    dp.register_message_handler(cmd_schedule, commands=["schedule"])
    dp.register_callback_query_handler(callback_schedule_page, text_startswith="all_matches_page:")
