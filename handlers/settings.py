"""
handlers/settings.py - معالج تغيير المنطقة الزمنية
==============================================
يتيح للمستخدم تحديد المنطقة الزمنية لبلده العربي لتعديل أوقات المباريات تلقائياً (متوافق مع aiogram v2).
"""

import logging
import pytz
from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from database import update_user_timezone, get_user_timezone
from keyboards.timezone import get_timezone_keyboard
from keyboards.main_menu import get_main_menu
from config import ARABIC_TIMEZONES

logger = logging.getLogger(__name__)


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
        reply_markup=get_main_menu(callback.from_user.id),
        parse_mode="HTML"
    )
    await callback.answer(f"✅ تم حفظ التوقيت: {country_name}")
    logger.info(f"👤 المستخدم {callback.from_user.id} قام بتغيير المنطقة الزمنية إلى {tz_value}")


def register_settings_handlers(dp: Dispatcher):
    """تسجيل معالجات الإعدادات في موزع المهام."""
    dp.register_message_handler(cmd_timezone, commands=["timezone"])
    dp.register_callback_query_handler(callback_change_timezone, text="change_timezone")
    dp.register_callback_query_handler(callback_set_timezone, text_startswith="set_tz:")
