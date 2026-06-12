"""
keyboards/main_menu.py - لوحة المفاتيح الرئيسية
==============================================
أزرار القائمة الرئيسية والتنقل الأساسية.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """القائمة الرئيسية للبوت."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🏆 مباريات اليوم", callback_data="today_matches"),
        InlineKeyboardButton(text="📅 جميع المباريات", callback_data="all_matches_page:0")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 البحث عن منتخب", callback_data="search_team"),
        InlineKeyboardButton(text="🌍 تغيير التوقيت", callback_data="change_timezone")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ المساعدة", callback_data="help")
    )

    return builder.as_markup()


def get_back_to_menu() -> InlineKeyboardMarkup:
    """زر العودة للقائمة الرئيسية."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 الرئيسية", callback_data="main_menu")
    return builder.as_markup()
