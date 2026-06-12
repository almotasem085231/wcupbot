"""
main.py - نقطة دخول البوت الرئيسية
==============================================
World Cup 2026 Schedule Bot - بوت جدول كأس العالم 2026 (متوافق مع aiogram v2.25.1)
"""

import sys
import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database import init_db

# استيراد معالجات الموديولات ونظام الإشعارات
from handlers import start, today, schedule, search, settings, predict
from handlers.notifications import check_and_send_notifications

logger = logging.getLogger(__name__)


# إعداد التسجيل (Logging)
def setup_logging():
    """إعداد نظام التسجيل لعرض الأخطاء والعمليات."""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # تقليل سجلات المكتبات المزعجة
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


# التحقق من التهيئة
def validate_config():
    """التحقق من توكن البوت."""
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_telegram_bot_token_here":
        print("\n" + "═" * 50)
        print("⚠️  خطأ: BOT_TOKEN غير محدد في ملف .env!")
        print("═" * 50 + "\n")
        sys.exit(1)


# تهيئة البوت والموزع مع التخزين في الذاكرة لـ FSM
validate_config()
setup_logging()

bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# تسجيل وسيط التحقق من الهوية والتوثيق
from middlewares import AuthMiddleware
dp.middleware.setup(AuthMiddleware())

# إعداد مجدول المهام الخلفية لإرسال الإشعارات
scheduler = AsyncIOScheduler()
scheduler.add_job(
    check_and_send_notifications,
    "interval",
    minutes=1,
    args=[bot]
)


async def on_startup(dispatcher: Dispatcher):
    """الدالة التي تنفذ عند بدء تشغيل البوت."""
    logger.info("🚀 بدء تشغيل World Cup 2026 Schedule Bot...")

    # تهيئة قاعدة البيانات SQLite
    await init_db()
    
    # تسجيل معالجات الرسائل والأزرار لكل موديول
    start.register_start_handlers(dispatcher)
    today.register_today_handlers(dispatcher)
    schedule.register_schedule_handlers(dispatcher)
    search.register_search_handlers(dispatcher)
    settings.register_settings_handlers(dispatcher)
    predict.register_predict_handlers(dispatcher)
    
    logger.info("✅ تم تسجيل كافة المعالجات بنجاح")

    # تشغيل مجدول إشعارات المباريات بالخلفية
    scheduler.start()
    logger.info("⏰ تم تشغيل مجدول إشعارات المباريات بالخلفية (يفحص كل دقيقة)")

    # الحصول على معلومات البوت
    bot_info = await dispatcher.bot.get_me()
    logger.info(f"🤖 البوت يعمل الآن باسم: @{bot_info.username}")

    print("\n" + "═" * 50)
    print(f"  🏆 World Cup 2026 Schedule Bot")
    print(f"  🤖 @{bot_info.username}")
    print(f"  ✅ يعمل الآن بنجاح (aiogram v2)...")
    print("═" * 50 + "\n")


async def on_shutdown(dispatcher: Dispatcher):
    """الدالة التي تنفذ عند إغلاق البوت."""
    logger.info("⏹️ جاري إيقاف البوت...")
    
    # إيقاف مجدول المهام
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏰ تم إيقاف مجدول الإشعارات")
        
    # إغلاق اتصالات البوت والتخزين
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()
    await dispatcher.bot.close()
    logger.info("👋 تم إغلاق اتصالات البوت بنجاح")


if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
