"""
keyboards/main_menu.py - لوحة المفاتيح الرئيسية
==============================================
أزرار القائمة الرئيسية والتنقل الأساسية (متوافق مع aiogram v2).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    """القائمة الرئيسية للبوت."""
    markup = InlineKeyboardMarkup(row_width=2)
    
    # إضافة الأزرار الثنائية
    markup.row(
        InlineKeyboardButton(text="🏆 مباريات اليوم", callback_data="today_matches"),
        InlineKeyboardButton(text="📅 جميع المباريات", callback_data="all_matches_page:0")
    )
    markup.row(
        InlineKeyboardButton(text="🔍 البحث عن منتخب", callback_data="search_team"),
        InlineKeyboardButton(text="🌍 تغيير التوقيت", callback_data="change_timezone")
    )
    markup.row(
        InlineKeyboardButton(text="🎯 توقع المباريات", callback_data="pred_start"),
        InlineKeyboardButton(text="📊 المتصدرين", callback_data="pred_leaderboard")
    )
    
    # زر المساعدة المنفرد
    markup.row(
        InlineKeyboardButton(text="ℹ️ المساعدة", callback_data="help")
    )

    return markup


def get_back_to_menu() -> InlineKeyboardMarkup:
    """زر العودة للقائمة الرئيسية."""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")
    )
    return markup
