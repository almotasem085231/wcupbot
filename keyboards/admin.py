"""
keyboards/admin.py - لوحة تحكم المشرف
==============================================
أزرار لوحة التحكم والإدارة للمسؤول (متوافق مع aiogram v2).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """لوحة التحكم الرئيسية للمشرف."""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="➕ إضافة / خصم نقاط RAAW", callback_data="admin_add_points"),
        InlineKeyboardButton(text="✏️ تعديل نتائج المباريات", callback_data="admin_edit_results:0"),
        InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")
    )
    return markup


def get_admin_matches_keyboard(page_matches: list, page_index: int, total_pages: int) -> InlineKeyboardMarkup:
    """أزرار تصفح واختيار المباريات للتعديل."""
    markup = InlineKeyboardMarkup(row_width=1)
    
    for m in page_matches:
        home_score = m.get("home_score")
        away_score = m.get("away_score")
        
        if home_score is not None and away_score is not None:
            score_str = f"({home_score} - {away_score})"
        else:
            score_str = "(لم تبدأ / لا توجد نتيجة)"
            
        btn_text = f"✏️ {m['home_flag']} {m['home_team']} × {m['away_team']} {m['away_flag']} {score_str}"
        markup.add(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"admin_edit_match:{m['id']}:{page_index}"
            )
        )
        
    # أزرار التنقل بين الصفحات
    nav_row = []
    if page_index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅ السابق", callback_data=f"admin_edit_results:{page_index - 1}"))
    if page_index < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡ التالي", callback_data=f"admin_edit_results:{page_index + 1}"))
        
    if nav_row:
        markup.row(*nav_row)
        
    markup.add(InlineKeyboardButton(text="🔙 لوحة التحكم", callback_data="admin_panel"))
    return markup


def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """زر إلغاء العملية الحالية والعودة للوحة المشرف."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="❌ إلغاء والعودة للوحة", callback_data="admin_panel"))
    return markup
