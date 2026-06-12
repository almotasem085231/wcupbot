"""
keyboards/timezone.py - لوحة اختيار المنطقة الزمنية
==============================================
أزرار اختيار المنطقة الزمنية للبلدان العربية المحددة (متوافق مع aiogram v2).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ARABIC_TIMEZONES


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """لوحة اختيار المنطقة الزمنية."""
    markup = InlineKeyboardMarkup(row_width=1)

    # إضافة أزرار الدول العربية
    for display_name, tz_value in ARABIC_TIMEZONES.items():
        markup.add(
            InlineKeyboardButton(
                text=display_name,
                callback_data=f"set_tz:{tz_value}"
            )
        )

    # زر العودة للقائمة الرئيسية
    markup.add(
        InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")
    )
    return markup
