"""
keyboards/timezone.py - لوحة اختيار المنطقة الزمنية
==============================================
أزرار اختيار المنطقة الزمنية للبلدان العربية السبعة المحددة.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ARABIC_TIMEZONES


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """لوحة اختيار المنطقة الزمنية."""
    builder = InlineKeyboardBuilder()

    # أزرار الدول العربية السبعة
    for display_name, tz_value in ARABIC_TIMEZONES.items():
        builder.row(
            InlineKeyboardButton(
                text=display_name,
                callback_data=f"set_tz:{tz_value}"
            )
        )

    # زر العودة للقائمة الرئيسية
    builder.row(
        InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")
    )
    return builder.as_markup()
