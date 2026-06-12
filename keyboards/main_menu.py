"""
keyboards/main_menu.py - لوحة المفاتيح الرئيسية
==============================================
أزرار القائمة الرئيسية والتنقل الأساسية (متوافق مع aiogram v2).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


import config


def get_main_menu(user_id: int = None) -> InlineKeyboardMarkup:
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

    # إذا كان المستخدم هو المشرف، نعرض له زر لوحة التحكم
    if user_id is not None and user_id == config.ADMIN_ID:
        markup.row(
            InlineKeyboardButton(text="🛠 لوحة المشرف", callback_data="admin_panel")
        )

    return markup



def get_back_to_menu() -> InlineKeyboardMarkup:
    """زر العودة للقائمة الرئيسية."""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")
    )
    return markup
