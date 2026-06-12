"""
handlers/start.py - معالج أمر /start والمساعدة
==============================================
يعرض القائمة الرئيسية ويسجل المستخدمين الجدد (متوافق مع aiogram v2).
"""

import logging
from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from database import create_or_update_user
from keyboards.main_menu import get_main_menu, get_back_to_menu

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """
🏆 <b>مرحباً بك في بوت جدول كأس العالم 2026</b> 🏆

هذا البوت مخصص لعرض جدول مباريات كأس العالم 2026 بالكامل وتواقيت المباريات حسب دولتك المحلية.
🇺🇸 الولايات المتحدة | 🇲🇽 المكسيك | 🇨🇦 كندا

يرجى اختيار أحد الخيارات من القائمة أدناه:
"""

HELP_MESSAGE = """
ℹ️ <b>دليل استخدام البوت</b>

هذا البوت يتيح لك الاطلاع على جدول مباريات كأس العالم 2026 بالكامل:
• 🏆 <b>مباريات اليوم:</b> يعرض المباريات التي تقام اليوم بتوقيت بلدك المختار.
• 📅 <b>جميع المباريات:</b> يتصفح جدول البطولة كاملاً بصفحات منظمة.
• 🔍 <b>البحث عن منتخب:</b> يتيح لك كتابة اسم أي منتخب لعرض مبارياته فقط.
• 🌍 <b>تغيير التوقيت:</b> يتيح لك ضبط توقيت عرض المباريات حسب بلدك العربي.

<b>الأوامر المتاحة:</b>
/start - القائمة الرئيسية
/help - دليل المساعدة
"""


async def cmd_start(message: Message):
    """معالج أمر /start."""
    user = message.from_user
    logger.info(f"👤 مستخدم جديد/عائد: {user.id} (@{user.username})")

    # تسجيل أو تحديث المستخدم في قاعدة البيانات
    await create_or_update_user(
        telegram_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


async def cmd_help(message: Message):
    """معالج أمر /help."""
    await message.answer(
        HELP_MESSAGE,
        reply_markup=get_back_to_menu(),
        parse_mode="HTML"
    )


async def callback_main_menu(callback: CallbackQuery):
    """العودة للقائمة الرئيسية."""
    await callback.message.edit_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


async def callback_help(callback: CallbackQuery):
    """عرض المساعدة عبر الأزرار."""
    await callback.message.edit_text(
        HELP_MESSAGE,
        reply_markup=get_back_to_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


def register_start_handlers(dp: Dispatcher):
    """تسجيل معالجات start في موزع المهام."""
    dp.register_message_handler(cmd_start, commands=["start"])
    dp.register_message_handler(cmd_help, commands=["help"])
    dp.register_callback_query_handler(callback_main_menu, text="main_menu")
    dp.register_callback_query_handler(callback_help, text="help")
