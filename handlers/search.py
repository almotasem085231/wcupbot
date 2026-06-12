"""
handlers/search.py - معالج البحث عن منتخب
==============================================
يتيح للمستخدم البحث عن مباريات منتخب معين عبر إدخال اسمه.
"""

import json
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import MATCHES_JSON_PATH
from database import get_user_timezone, convert_match_time
from keyboards.main_menu import get_back_to_menu

logger = logging.getLogger(__name__)
router = Router()


class SearchStates(StatesGroup):
    """حالات FSM للبحث عن منتخب."""
    waiting_for_team_name = State()


def load_matches() -> list:
    """تحميل مباريات كأس العالم من ملف JSON."""
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
    city = match.get("city", "مدينة غير حددة")
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


@router.message(Command("team"))
async def cmd_team(message: Message, state: FSMContext):
    """معالج أمر /team للبحث عن منتخب."""
    await message.answer(
        "🔍 <b>البحث عن منتخب</b>\n\n"
        "أرسل اسم المنتخب الذي تريد البحث عن مبارياته (مثال: الأرجنتين، فرنسا، المغرب، البرازيل):",
        parse_mode="HTML"
    )
    await state.set_state(SearchStates.waiting_for_team_name)


@router.callback_query(F.data == "search_team")
async def callback_search(callback: CallbackQuery, state: FSMContext):
    """معالج زر البحث عن منتخب من القائمة."""
    await callback.message.edit_text(
        "🔍 <b>البحث عن منتخب</b>\n\n"
        "أرسل اسم المنتخب الذي تريد البحث عن مبارياته (مثال: الأرجنتين، فرنسا، المغرب، البرازيل):",
        reply_markup=get_back_to_menu(),
        parse_mode="HTML"
    )
    await state.set_state(SearchStates.waiting_for_team_name)
    await callback.answer()


@router.message(SearchStates.waiting_for_team_name)
async def process_team_name(message: Message, state: FSMContext):
    """معالجة الاسم المرسل والبحث في ملف JSON."""
    team_query = message.text.strip()
    
    if not team_query:
        await message.answer("❌ يرجى إدخال اسم منتخب صحيح للبحث.")
        return

    user_tz_str = await get_user_timezone(message.from_user.id)
    matches = load_matches()
    found_matches = []

    for match in matches:
        home = match.get("home_team", "").lower()
        away = match.get("away_team", "").lower()
        query = team_query.lower()
        
        # البحث في الاسم العربي أو الإنجليزي للمنتخب
        if query in home or query in away:
            formatted_date, formatted_time, _ = convert_match_time(match["date"], match["time"], user_tz_str)
            found_matches.append((match, formatted_date, formatted_time))

    if not found_matches:
        await message.answer(
            f"❌ لم يتم العثور على مباريات للمنتخب <b>\"{team_query}\"</b>.\n"
            f"يرجى التأكد من كتابة الاسم بشكل صحيح أو البحث عن منتخب آخر.",
            reply_markup=get_back_to_menu(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    # ترتيب النتائج زمنياً
    found_matches.sort(key=lambda item: (item[0].get("date", ""), item[0].get("time", "")))

    # تنسيق النتائج
    cards = []
    for match, f_date, f_time in found_matches:
        cards.append(format_match_card(match, f_date, f_time))

    separator = "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    response_text = (
        f"🔍 <b>نتائج البحث عن: \"{team_query}\"</b>\n"
        f"📊 عدد المباريات المكتشفة: {len(found_matches)}\n\n"
        + separator.join(cards)
    )

    await message.answer(
        response_text,
        reply_markup=get_back_to_menu(),
        parse_mode="HTML"
    )
    await state.clear()
