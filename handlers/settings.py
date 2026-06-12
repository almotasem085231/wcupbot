"""
handlers/settings.py - معالج تغيير المنطقة الزمنية
==============================================
يتيح للمستخدم تحديد المنطقة الزمنية لبلده العربي لتعديل أوقات المباريات تلقائياً.
"""

import logging
import pytz
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import update_user_timezone, get_user_timezone
from keyboards.timezone import get_timezone_keyboard
from keyboards.main_menu import get_main_menu, get_back_to_menu
from config import ARABIC_TIMEZONES

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("timezone"))
async def cmd_timezone(message: Message):
    """معالج أمر /timezone."""
    current_tz = await get_user_timezone(message.from_user.id)
    
    # البحث عن الاسم العربي للمنطقة الحالية
    country_name = "غير محدد"
    for name, tz in ARABIC_TIMEZONES.items():
        if tz == current_tz:
            country_name = name
            break

    await message.answer(
        f"🌍 <b>تغيير المنطقة الزمنية</b>\n\n"
        f"بلدك الحالي: <b>{country_name}</b>\n\n"
        f"اختر بلدك من القائمة لتعديل مواعيد المباريات تلقائياً حسب توقيتك المحلي:",
        reply_markup=get_timezone_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "change_timezone")
async def callback_change_timezone(callback: CallbackQuery):
    """معالج زر تغيير التوقيت."""
    current_tz = await get_user_timezone(callback.from_user.id)
    
    country_name = "غير محدد"
    for name, tz in ARABIC_TIMEZONES.items():
        if tz == current_tz:
            country_name = name
            break

    await callback.message.edit_text(
        f"🌍 <b>تغيير المنطقة الزمنية</b>\n\n"
        f"بلدك الحالي: <b>{country_name}</b>\n\n"
        f"اختر بلدك من القائمة لتعديل مواعيد المباريات تلقائياً حسب توقيتك المحلي:",
        reply_markup=get_timezone_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_tz:"))
async def callback_set_timezone(callback: CallbackQuery):
    """حفظ المنطقة الزمنية المختارة في قاعدة البيانات."""
    tz_value = callback.data.split(":", 1)[1]

    # التحقق من صحة التوقيت
    try:
        pytz.timezone(tz_value)
    except pytz.exceptions.UnknownTimeZoneError:
        await callback.answer("❌ المنطقة الزمنية المحددة غير صالحة")
        return

    await update_user_timezone(callback.from_user.id, tz_value)

    # جلب الاسم العربي للبلد
    country_name = tz_value
    for name, tz in ARABIC_TIMEZONES.items():
        if tz == tz_value:
            country_name = name
            break

    await callback.message.edit_text(
        f"✅ <b>تم ضبط التوقيت بنجاح!</b>\n\n"
        f"🌍 البلد المحدد: <b>{country_name}</b>\n"
        f"🕒 التوقيت المعتمد: <b>{tz_value}</b>\n\n"
        f"ستظهر جميع مواعيد المباريات الآن متطابقة مع توقيت هذا البلد.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ تم حفظ التوقيت: {country_name}")
    logger.info(f"👤 المستخدم {callback.from_user.id} قام بتغيير المنطقة الزمنية إلى {tz_value}")
