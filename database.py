"""
database.py - إدارة قاعدة البيانات SQLite والبيانات
==============================================
يتضمن عمليات قاعدة البيانات لمستخدمي البوت بشكل غير متزامن
بالإضافة إلى وظائف مساعدة لمعالجة التوقيت والتواريخ وإشعارات المباريات.
"""

import aiosqlite
import logging
import pytz
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db():
    """تهيئة قاعدة البيانات وإنشاء جدول المستخدمين وجدول سجل الإشعارات."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                timezone TEXT DEFAULT 'Asia/Riyadh',
                join_date TEXT
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                user_id INTEGER,
                match_id INTEGER,
                notification_type TEXT, -- '1h', '10m', 'start'
                sent_at TEXT,
                PRIMARY KEY (user_id, match_id, notification_type)
            );
        """)
        await db.commit()
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")


async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """جلب بيانات مستخدم بواسطة Telegram ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_users() -> List[Dict[str, Any]]:
    """جلب جميع المستخدمين المسجلين في البوت."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT telegram_id, timezone FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def create_or_update_user(
    telegram_id: int,
    username: str = None
) -> bool:
    """إنشاء مستخدم جديد أو تحديث بياناته."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(telegram_id)
        if user:
            await db.execute(
                "UPDATE users SET username = ? WHERE telegram_id = ?",
                (username, telegram_id)
            )
        else:
            await db.execute(
                "INSERT INTO users (telegram_id, username, timezone, join_date) VALUES (?, ?, 'Asia/Riyadh', ?)",
                (telegram_id, username, now)
            )
        await db.commit()
        return True


async def update_user_timezone(telegram_id: int, timezone: str) -> bool:
    """تحديث المنطقة الزمنية للمستخدم."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET timezone = ? WHERE telegram_id = ?",
            (timezone, telegram_id),
        )
        await db.commit()
        return True


async def get_user_timezone(telegram_id: int) -> str:
    """جلب المنطقة الزمنية للمستخدم."""
    user = await get_user(telegram_id)
    return user["timezone"] if user else "Asia/Riyadh"


async def is_notification_sent(user_id: int, match_id: int, notification_type: str) -> bool:
    """التحقق مما إذا كان الإشعار قد أرسل للمستخدم سابقاً لمنع التكرار."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM sent_notifications WHERE user_id = ? AND match_id = ? AND notification_type = ?",
            (user_id, match_id, notification_type)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def mark_notification_sent(user_id: int, match_id: int, notification_type: str) -> bool:
    """تسجيل إرسال الإشعار بنجاح في قاعدة البيانات."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_notifications (user_id, match_id, notification_type, sent_at) VALUES (?, ?, ?, ?)",
            (user_id, match_id, notification_type, now)
        )
        await db.commit()
        return True


def convert_match_time(date_str: str, time_str: str, user_tz_str: str) -> Tuple[str, str, datetime]:
    """
    تحويل وقت وتاريخ المباراة من UTC إلى المنطقة الزمنية للمستخدم.
    تُرجع: (التاريخ المنسق بالعربية، الوقت المنسق، كائن datetime المحلي)
    """
    try:
        # إنشاء كائن datetime بالـ UTC
        utc_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC)
        # التحويل لمنطقة المستخدم
        user_tz = pytz.timezone(user_tz_str)
        local_dt = utc_dt.astimezone(user_tz)
        
        # التنسيق العربي للأشهر
        months_ar = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        
        formatted_date = f"{local_dt.day} {months_ar[local_dt.month]} {local_dt.year}"
        formatted_time = local_dt.strftime("%H:%M")
        
        return formatted_date, formatted_time, local_dt
    except Exception as e:
        logger.error(f"Error converting timezone: {e}")
        return date_str, time_str, datetime.now()


def get_match_status(date_str: str, time_str: str) -> str:
    """
    تحديد حالة المباراة بناءً على الوقت الحالي بالـ UTC.
    المخرجات:
    - "⏳ لم تبدأ"
    - "🟢 جارية الآن"
    - "🏁 انتهت"
    """
    try:
        match_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC)
        now_utc = datetime.now(pytz.UTC)
        diff = (now_utc - match_dt).total_seconds()
        
        if diff < 0:
            return "⏳ لم تبدأ"
        elif 0 <= diff <= 7200:  # ساعتان (120 دقيقة)
            return "🟢 جارية الآن"
        else:
            return "🏁 انتهت"
    except Exception:
        return "⏳ لم تبدأ"

