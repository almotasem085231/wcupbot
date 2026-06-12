"""
handlers/admin.py - لوحة تحكم المشرف والعمليات الإدارية
======================================================
يحتوي على معالجات لوحة التحكم للمسؤول (تعديل النقاط وتعديل نتائج المباريات).
متوافق بالكامل مع aiogram v2.25.1.
"""

import logging
import json
import re
from math import ceil
from typing import Optional

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
from database import get_user_by_identifier, add_user_points
from keyboards.admin import (
    get_admin_panel_keyboard,
    get_admin_matches_keyboard,
    get_admin_cancel_keyboard
)
from keyboards.main_menu import get_main_menu
from handlers.schedule import load_sorted_matches
from handlers.notifications import resolve_predictions

logger = logging.getLogger(__name__)

# حجم الصفحة للمباريات في لوحة الإدارة
ADMIN_PAGE_SIZE = 5


class AdminStates(StatesGroup):
    waiting_for_user_identifier = State()
    waiting_for_points = State()
    waiting_for_match_result = State()


def is_admin(user_id: int) -> bool:
    """التحقق من أن المستخدم هو المسؤول."""
    return user_id == config.ADMIN_ID


# --- لوحة التحكم الرئيسية ---

async def callback_admin_panel(callback: CallbackQuery, state: FSMContext):
    """عرض لوحة التحكم الرئيسية للمشرف."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح لك بالوصول إلى لوحة المشرف.", show_alert=True)
        return

    await state.finish()  # تنظيف أي حالة FSM جارية
    
    await callback.message.edit_text(
        "🛠 <b>لوحة تحكم المشرف (Admin Panel)</b>\n\n"
        "مرحباً بك في لوحة الإدارة. يرجى اختيار العملية التي تريد القيام بها:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# --- تعديل نقاط RAAW ---

async def callback_admin_add_points(callback: CallbackQuery, state: FSMContext):
    """البدء في عملية تعديل النقاط لمستخدم."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح لك بالوصول إلى لوحة المشرف.", show_alert=True)
        return

    await AdminStates.waiting_for_user_identifier.set()
    
    await callback.message.edit_text(
        "👤 <b>إضافة أو خصم نقاط RAAW لمستخدم</b>\n\n"
        "يرجى كتابة <b>معرف المستخدم (Telegram ID)</b> أو <b>اسم المستخدم (Username)</b>:\n"
        "<i>مثال: 123456789 أو @username</i>",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


async def process_user_identifier(message: Message, state: FSMContext):
    """معالجة معرف المستخدم والتحقق من وجوده في قاعدة البيانات."""
    if not is_admin(message.from_user.id):
        return

    identifier = message.text.strip()
    user = await get_user_by_identifier(identifier)
    
    if not user:
        await message.reply(
            "❌ <b>لم يتم العثور على المستخدم في قاعدة البيانات!</b>\n\n"
            "يرجى التأكد من كتابة الـ Telegram ID بشكل صحيح، أو أن المستخدم قد تفاعل مع البوت وسجل فيه سابقاً.\n\n"
            "أرسل المعرف مجدداً، أو اضغط إلغاء للعودة:",
            reply_markup=get_admin_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    # حفظ بيانات المستخدم المستهدف في حالة FSM
    await state.update_data(
        target_user_id=user["telegram_id"],
        target_full_name=user["full_name"],
        target_username=user["username"],
        target_current_points=user["raaw_points"]
    )
    
    await AdminStates.waiting_for_points.set()
    
    username_display = f"@{user['username']}" if user["username"] else "لا يوجد"
    await message.reply(
        f"✅ <b>تم العثور على المستخدم بنجاح!</b>\n\n"
        f"👤 الاسم: <b>{user['full_name']}</b>\n"
        f"🏷 اليوزرنيم: <b>{username_display}</b>\n"
        f"🆔 معرف التليجرام: <code>{user['telegram_id']}</code>\n"
        f"🎮 رصيد النقاط الحالي: <b>{user['raaw_points']} RAAW Points</b>\n\n"
        f"🪙 <b>يرجى إرسال عدد النقاط المراد إضافتها أو خصمها:</b>\n"
        f"<i>مثال: لإضافة 10 نقاط اكتب 10، ولخصم 5 نقاط اكتب -5</i>",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode="HTML"
    )


async def process_points(message: Message, state: FSMContext):
    """معالجة عدد النقاط المدخلة وتحديث رصيد المستخدم."""
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()
    
    try:
        points = int(text)
    except ValueError:
        await message.reply(
            "❌ <b>صيغة غير صحيحة!</b>\n"
            "يرجى إرسال رقم صحيح (مثال: 10 أو -5):",
            reply_markup=get_admin_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    target_full_name = data["target_full_name"]
    
    # تحديث النقاط في قاعدة البيانات
    new_points = await add_user_points(target_user_id, points)
    
    action_text = f"إضافة {points}" if points >= 0 else f"خصم {abs(points)}"
    
    await message.reply(
        f"✅ <b>تم تعديل النقاط بنجاح!</b>\n\n"
        f"👤 المستخدم: <b>{target_full_name}</b>\n"
        f"⚙️ العملية: <b>{action_text} نقطة</b>\n"
        f"🏆 الرصيد الجديد: <b>{new_points} RAAW Points</b>",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )

    # إرسال إشعار للمستخدم المستهدف
    try:
        # تحديد صياغة الإشعار للمستخدم
        if points >= 0:
            user_notif_text = f"🎁 <b>قام المسؤول بإضافة {points} من نقاط RAAW إلى رصيدك!</b>\n\n"
        else:
            user_notif_text = f"⚠️ <b>قام المسؤول بخصم {abs(points)} من نقاط RAAW من رصيدك!</b>\n\n"
            
        user_notif_text += f"🎮 رصيدك الحالي هو: <b>{new_points} RAAW Points</b> 🏆"
        
        await message.bot.send_message(
            chat_id=target_user_id,
            text=user_notif_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Failed to send points update notification to user {target_user_id}: {e}")

    await state.finish()


# --- تعديل نتائج المباريات ---

async def callback_admin_edit_results(callback: CallbackQuery, state: FSMContext):
    """عرض قائمة المباريات بشكل مجدول للتعديل."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح لك بالوصول إلى لوحة المشرف.", show_alert=True)
        return

    await state.finish()  # تنظيف أي حالة FSM
    
    # استخراج رقم الصفحة
    page_index = int(callback.data.split(":")[1])
    
    matches = load_sorted_matches()
    total_matches = len(matches)
    
    if total_matches == 0:
        await callback.message.edit_text(
            "⚠️ لا توجد مباريات مضافة في الجدول حالياً.",
            reply_markup=get_admin_panel_keyboard()
        )
        await callback.answer()
        return
        
    total_pages = ceil(total_matches / ADMIN_PAGE_SIZE)
    
    if page_index < 0:
        page_index = 0
    elif page_index >= total_pages:
        page_index = total_pages - 1
        
    start_idx = page_index * ADMIN_PAGE_SIZE
    end_idx = start_idx + ADMIN_PAGE_SIZE
    page_matches = matches[start_idx:end_idx]
    
    await callback.message.edit_text(
        f"✏️ <b>تعديل نتائج مباريات كأس العالم 2026</b>\n"
        f"📄 الصفحة {page_index + 1} من {total_pages} (مجموع المباريات: {total_matches})\n\n"
        f"اختر اللقاء المراد إدخال أو تعديل نتيجته من الأزرار التالية:",
        reply_markup=get_admin_matches_keyboard(page_matches, page_index, total_pages),
        parse_mode="HTML"
    )
    await callback.answer()


async def callback_admin_edit_match(callback: CallbackQuery, state: FSMContext):
    """طلب النتيجة الجديدة للمباراة المحددة."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح لك بالوصول إلى لوحة المشرف.", show_alert=True)
        return

    parts = callback.data.split(":")
    match_id = int(parts[1])
    page_index = int(parts[2])
    
    matches = load_sorted_matches()
    match_detail = next((m for m in matches if m["id"] == match_id), None)
    
    if not match_detail:
        await callback.answer("⚠️ تعذر العثور على تفاصيل المباراة.", show_alert=True)
        return

    await state.update_data(
        edit_match_id=match_id,
        edit_page_index=page_index,
        edit_match_details=match_detail
    )
    
    await AdminStates.waiting_for_match_result.set()
    
    home_score = match_detail.get("home_score")
    away_score = match_detail.get("away_score")
    score_display = f"<b>{home_score} - {away_score}</b>" if home_score is not None else "<i>لا توجد نتيجة</i>"
    
    await callback.message.edit_text(
        f"✏️ <b>تعديل نتيجة اللقاء:</b>\n"
        f"{match_detail['home_flag']} {match_detail['home_team']} × {match_detail['away_team']} {match_detail['away_flag']}\n\n"
        f"النتيجة الحالية للمباراة: {score_display}\n\n"
        f"⚙️ <b>يرجى كتابة النتيجة الجديدة وإرسالها:</b>\n"
        f"• بالصيغة: <code>2-1</code> (يسار للمضيف، يمين للضيف)\n"
        f"• أو اكتب <code>null</code> أو <code>-</code> لإلغاء النتيجة الحالية وجعلها غير مبرمة.",
        reply_markup=get_admin_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


async def process_match_result(message: Message, state: FSMContext):
    """حفظ نتيجة المباراة الجديدة وتفعيل نظام احتساب النقاط التلقائي."""
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip().lower()
    
    home_score = None
    away_score = None
    
    is_cleared = False
    
    if text in ["null", "-", "إلغاء", "clear"]:
        is_cleared = True
    else:
        # التحقق من الصيغة (رقم-رقم) مع السماح بوجود مسافات
        match_pattern = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", text)
        if not match_pattern:
            await message.reply(
                "❌ <b>صيغة النتيجة غير صحيحة!</b>\n"
                "يرجى إرسال النتيجة بالصيغة <b>رقم-رقم</b> (مثال: 2-1) أو اكتب <code>null</code> لإلغائها:",
                reply_markup=get_admin_cancel_keyboard(),
                parse_mode="HTML"
            )
            return
            
        home_score = int(match_pattern.group(1))
        away_score = int(match_pattern.group(2))

    data = await state.get_data()
    match_id = data["edit_match_id"]
    page_index = data["edit_page_index"]
    match_detail = data["edit_match_details"]
    
    # تحديث ملف matches.json
    success = False
    try:
        with open(config.MATCHES_JSON_PATH, "r", encoding="utf-8") as f:
            matches_data = json.load(f)
            
        for m in matches_data:
            if m["id"] == match_id:
                m["home_score"] = home_score
                m["away_score"] = away_score
                success = True
                break
                
        if success:
            with open(config.MATCHES_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(matches_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error writing to matches.json: {e}")
        await message.reply(f"❌ حدث خطأ أثناء تعديل الملف: {e}")
        await state.finish()
        return

    if not success:
        await message.reply("❌ تعذر العثور على المباراة في ملف البيانات.")
        await state.finish()
        return

    # التنسيق لتأكيد الحفظ
    if is_cleared:
        result_display = "تم إلغاء النتيجة"
    else:
        result_display = f"<b>{home_score} - {away_score}</b>"
        
    await message.reply(
        f"✅ <b>تم تحديث النتيجة بنجاح!</b>\n\n"
        f"⚽ اللقاء: {match_detail['home_flag']} {match_detail['home_team']} × {match_detail['away_team']} {match_detail['away_flag']}\n"
        f"📊 النتيجة المعتمدة: {result_display}\n\n"
        f"⚙️ جاري التحقق من التوقعات وتوزيع نقاط RAAW على الفائزين...",
        parse_mode="HTML"
    )

    # تشغيل عملية التحقق وتوزيع النقاط للتوقعات غير المحسوبة تلقائياً
    if not is_cleared:
        try:
            await resolve_predictions(message.bot)
        except Exception as e:
            logger.error(f"Error auto-resolving predictions after admin edit: {e}")
            await message.answer(f"⚠️ حدث خطأ أثناء توزيع نقاط التوقعات تلقائياً: {e}")

    # العودة لصفحة المباريات السابقة في لوحة الإدارة
    # محاكاة كولباك لاستدعاء العرض مجدداً
    fake_callback = CallbackQuery(
        id="fake",
        from_user=message.from_user,
        chat_instance="fake",
        message=message,
        data=f"admin_edit_results:{page_index}"
    )
    fake_callback.message.edit_text = message.answer  # تحويل التعديل إلى إرسال رسالة جديدة
    await callback_admin_edit_results(fake_callback, state)


# --- تسجيل معالجات المشرف ---

def register_admin_handlers(dp: Dispatcher):
    """تسجيل معالجات لوحة تحكم المشرف في موزع المهام."""
    # أزرار التنقل الرئيسية واللوحة
    dp.register_callback_query_handler(callback_admin_panel, text="admin_panel", state="*")
    dp.register_callback_query_handler(callback_admin_panel, text="admin_cancel", state="*")
    
    # معالجات تعديل النقاط
    dp.register_callback_query_handler(callback_admin_add_points, text="admin_add_points", state="*")
    dp.register_message_handler(process_user_identifier, state=AdminStates.waiting_for_user_identifier)
    dp.register_message_handler(process_points, state=AdminStates.waiting_for_points)
    
    # معالجات تعديل نتائج المباريات
    dp.register_callback_query_handler(callback_admin_edit_results, text_startswith="admin_edit_results:", state="*")
    dp.register_callback_query_handler(callback_admin_edit_match, text_startswith="admin_edit_match:", state="*")
    dp.register_message_handler(process_match_result, state=AdminStates.waiting_for_match_result)
