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
    """تهيئة قاعدة البيانات وإنشاء جدول المستخدمين وجدول سجل الإشعارات والتوقعات."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                timezone TEXT DEFAULT 'Asia/Riyadh',
                join_date TEXT,
                is_authorized INTEGER DEFAULT 0
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                match_id INTEGER,
                predicted_winner TEXT,
                predicted_score TEXT,
                is_resolved INTEGER DEFAULT 0
            );
        """)
        await db.commit()
        
        # إضافة عمود raaw_points لجدول users إذا لم يكن موجوداً
        try:
            await db.execute("ALTER TABLE users ADD COLUMN raaw_points INTEGER DEFAULT 0;")
            await db.commit()
        except Exception:
            pass

        # إضافة عمود is_authorized لجدول users إذا لم يكن موجوداً
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_authorized INTEGER DEFAULT 0;")
            await db.commit()
        except Exception:
            pass

        # إضافة عمود full_name لجدول users إذا لم يكن موجوداً
        try:
            await db.execute("ALTER TABLE users ADD COLUMN full_name TEXT;")
            await db.commit()
        except Exception:
            pass
            
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
    username: str = None,
    full_name: str = None
) -> bool:
    """إنشاء مستخدم جديد أو تحديث بياناته."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(telegram_id)
        if user:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE telegram_id = ?",
                (username, full_name, telegram_id)
            )
        else:
            await db.execute(
                "INSERT INTO users (telegram_id, username, full_name, timezone, join_date) VALUES (?, ?, ?, 'Asia/Riyadh', ?)",
                (telegram_id, username, full_name, now)
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


async def get_user_points(telegram_id: int) -> int:
    """جلب نقاط RAAW لمستخدم معين."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT raaw_points FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row["raaw_points"] if row else 0


async def add_prediction(user_id: int, match_id: int, predicted_winner: str, predicted_score: str) -> bool:
    """إضافة أو تحديث توقع للمباراة."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM predictions WHERE user_id = ? AND match_id = ?",
            (user_id, match_id)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE predictions SET predicted_winner = ?, predicted_score = ?, is_resolved = 0 WHERE id = ?",
                (predicted_winner, predicted_score, row[0])
            )
        else:
            await db.execute(
                "INSERT INTO predictions (user_id, match_id, predicted_winner, predicted_score, is_resolved) VALUES (?, ?, ?, ?, 0)",
                (user_id, match_id, predicted_winner, predicted_score)
            )
        await db.commit()
        return True


async def has_user_predicted(user_id: int, match_id: int) -> bool:
    """التحقق مما إذا كان المستخدم قد توقع نتيجة المباراة بالفعل."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM predictions WHERE user_id = ? AND match_id = ?",
            (user_id, match_id)
        )
        row = await cursor.fetchone()
        return row is not None


async def get_unresolved_predictions() -> List[Dict[str, Any]]:
    """جلب كافة التوقعات غير المحسوبة بعد."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, user_id, match_id, predicted_winner, predicted_score FROM predictions WHERE is_resolved = 0") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def resolve_prediction_db(pred_id: int, user_id: int, points: int) -> bool:
    """تحديث نقاط المستخدم وتحديد التوقع كمعالَج."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET raaw_points = raaw_points + ? WHERE telegram_id = ?",
            (points, user_id)
        )
        await db.execute(
            "UPDATE predictions SET is_resolved = 1 WHERE id = ?",
            (pred_id,)
        )
        await db.commit()
        return True


async def get_leaderboard_db() -> List[Dict[str, Any]]:
    """جلب أفضل 10 مستخدمين حسب نقاط RAAW."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT telegram_id, username, full_name, raaw_points FROM users ORDER BY raaw_points DESC, username ASC LIMIT 10"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def is_user_authorized(telegram_id: int) -> bool:
    """التحقق مما إذا كان المستخدم موثقاً."""
    user = await get_user(telegram_id)
    return (user is not None) and (user.get("is_authorized", 0) == 1)


async def set_user_authorized(telegram_id: int, is_authorized: int = 1) -> bool:
    """تحديث حالة توثيق المستخدم."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_authorized = ? WHERE telegram_id = ?",
            (is_authorized, telegram_id)
        )
        await db.commit()
        return True


async def get_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """البحث عن مستخدم بواسطة المعرف (Telegram ID أو اسم المستخدم)."""
    identifier = identifier.strip()
    if identifier.startswith("@"):
        identifier = identifier[1:]
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # إذا كان المعرف عبارة عن رقم، نبحث أولاً بالـ telegram_id
        if identifier.isdigit():
            async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (int(identifier),)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                    
        # ثم نبحث باسم المستخدم (تطابق غير حساس لحالة الأحرف)
        async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (identifier,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
                
        return None


async def add_user_points(telegram_id: int, points: int) -> int:
    """إضافة/خصم نقاط RAAW لمستخدم وتحديث رصيده."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET raaw_points = raaw_points + ? WHERE telegram_id = ?",
            (points, telegram_id)
        )
        await db.commit()
        
        # جلب الرصيد الجديد
        async with db.execute("SELECT raaw_points FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


