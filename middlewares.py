"""
middlewares.py - وسيط التحقق من الهوية والتوثيق
==============================================
يتحقق من حالة توثيق المستخدم قبل معالجة أي أمر أو زر.
"""

import logging
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.types import Message, CallbackQuery
from database import is_user_authorized, set_user_authorized, create_or_update_user
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

PASSWORD = "TH_2001"


class AuthMiddleware(BaseMiddleware):
    """وسيط للتحقق من إدخال كلمة المرور الصحيحة قبل السماح بالوصول لأوامر وأزرار البوت."""

    async def on_pre_process_message(self, message: Message, data: dict):
        # تجاهل الرسائل التي ليست في المحادثات الخاصة
        if message.chat.type != "private":
            return

        user_id = message.from_user.id
        username = message.from_user.username

        # التحقق مما إذا كان المستخدم موثقاً بالفعل
        authorized = await is_user_authorized(user_id)
        if authorized:
            return

        text = message.text.strip() if message.text else ""

        # إذا أدخل المستخدم كلمة المرور الصحيحة
        if text == PASSWORD:
            # تسجيل المستخدم وتوثيقه
            await create_or_update_user(telegram_id=user_id, username=username)
            await set_user_authorized(user_id, 1)

            # استيراد رسالة الترحيب من معالج البداية
            from handlers.start import WELCOME_MESSAGE

            await message.answer(
                "✅ تم التوثيق بنجاح! يمكنك الآن استخدام البوت بالكامل.",
                parse_mode="HTML"
            )
            await message.answer(
                WELCOME_MESSAGE,
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            # إلغاء مرور الرسالة للمعالجات الأخرى
            raise CancelHandler()

        # إذا حاول المستخدم استخدام الأمر /start
        if text.startswith("/start"):
            await create_or_update_user(telegram_id=user_id, username=username)
            await message.answer(
                "🔐 يرجى إدخال كلمة المرور للوصول إلى البوت:",
                parse_mode="HTML"
            )
            raise CancelHandler()

        # إذا أرسل المستخدم أي شيء آخر وهو غير موثق
        await create_or_update_user(telegram_id=user_id, username=username)
        await message.answer(
            "❌ كلمة المرور غير صحيحة.\nيرجى المحاولة مرة أخرى:",
            parse_mode="HTML"
        )
        raise CancelHandler()

    async def on_pre_process_callback_query(self, callback_query: CallbackQuery, data: dict):
        user_id = callback_query.from_user.id

        # التحقق مما إذا كان المستخدم موثقاً
        authorized = await is_user_authorized(user_id)
        if not authorized:
            await callback_query.answer(
                "⚠️ يجب التوثيق أولاً عن طريق إدخال كلمة المرور الصحيحة.",
                show_alert=True
            )
            # إلغاء مرور الكولباك للمعالجات الأخرى
            raise CancelHandler()
