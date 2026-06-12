"""
main.py - نقطة دخول البوت الرئيسية
==============================================
World Cup 2026 Schedule Bot - بوت جدول كأس العالم 2026
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database import init_db

# استيراد معالجات الراوتر ونظام الإشعارات
from handlers import start, today, schedule, search, settings
from handlers.notifications import check_and_send_notifications


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
    return logging.getLogger(__name__)


# التحقق من التهيئة
def validate_config():
    """التحقق من توكن البوت."""
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_telegram_bot_token_here":
        print("\n" + "═" * 50)
        print("⚠️  خطأ: BOT_TOKEN غير محدد في ملف .env!")
        print("═" * 50 + "\n")
        sys.exit(1)


async def main():
    """الدالة الرئيسية لبدء تشغيل البوت."""
    logger = setup_logging()
    logger.info("🚀 بدء تشغيل World Cup 2026 Schedule Bot...")

    validate_config()

    # تهيئة قاعدة البيانات SQLite
    await init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات")

    # إنشاء البوت والـ Dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # تسجيل الموجهات (Routers)
    dp.include_router(start.router)
    dp.include_router(today.router)
    dp.include_router(schedule.router)
    dp.include_router(search.router)
    dp.include_router(settings.router)

    # إعداد مجدول المهام الخلفية لإرسال الإشعارات
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_send_notifications,
        "interval",
        minutes=1,
        args=[bot]
    )
    scheduler.start()
    logger.info("⏰ تم تشغيل مجدول إشعارات المباريات بالخلفية (يفحص كل دقيقة)")

    # الحصول على معلومات البوت
    bot_info = await bot.get_me()
    logger.info(f"🤖 البوت يعمل الآن باسم: @{bot_info.username}")

    print("\n" + "═" * 50)
    print(f"  🏆 World Cup 2026 Schedule Bot")
    print(f"  🤖 @{bot_info.username}")
    print(f"  ✅ يعمل الآن بنجاح...")
    print("═" * 50 + "\n")

    # تشغيل Polling
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.critical(f"💥 خطأ غير متوقع: {e}", exc_info=True)
    finally:
        # إيقاف مجدول المهام
        if scheduler.running:
            scheduler.shutdown()
            logger.info("⏰ تم إيقاف مجدول الإشعارات")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 تم إيقاف البوت. مع السلامة!")
