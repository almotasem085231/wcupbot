"""
handlers/notifications.py - نظام إرسال الإشعارات التلقائي
=========================================================
يتحقق كل دقيقة من اقتراب موعد المباريات ويرسل تنبيهات للمستخدمين.
"""

import json
import logging
import pytz
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from config import MATCHES_JSON_PATH
from database import (
    get_all_users, 
    is_notification_sent, 
    mark_notification_sent, 
    convert_match_time
)

logger = logging.getLogger(__name__)


def load_matches() -> list:
    """تحميل المباريات من ملف JSON المحلي."""
    try:
        with open(MATCHES_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading matches in scheduler: {e}")
        return []


def format_notification_message(match: dict, f_date: str, f_time: str, notif_type: str) -> str:
    """تنسيق رسالة الإشعار بناءً على نوعه."""
    home_flag = match.get("home_flag", "🏳️")
    home_team = match.get("home_team", "غير معروف")
    away_flag = match.get("away_flag", "🏳️")
    away_team = match.get("away_team", "غير معروف")
    stadium = match.get("stadium", "ملعب غير محدد")
    city = match.get("city", "مدينة غير محددة")
    stage = match.get("stage", "")

    # تحديد عنوان الإشعار
    if notif_type == "1h":
        title = "⏰ <b>تبدأ المباراة بعد ساعة واحدة!</b>"
    elif notif_type == "10m":
        title = "⏳ <b>تبدأ المباراة بعد 10 دقائق!</b>"
    else:
        title = "🏁 <b>انطلقت المباراة الآن! بالتوفيق للمنتخبين ⚽</b>"

    message = (
        f"{title}\n\n"
        f"{home_flag} {home_team} × {away_flag} {away_team}\n"
        f"📅 {f_date}\n"
        f"🕒 {f_time}\n"
        f"🏟 {stadium}\n"
        f"📍 {city}"
    )
    if stage:
        message += f"\n🏆 {stage}"
        
    return message


async def check_and_send_notifications(bot: Bot):
    """التحقق من مواعيد المباريات وإرسال الإشعارات للمستخدمين."""
    matches = load_matches()
    if not matches:
        return

    users = await get_all_users()
    if not users:
        return

    now_utc = datetime.now(pytz.UTC)
    logger.debug(f"⏰ بدء فحص إشعارات المباريات (التوقيت الحالي UTC: {now_utc})")

    for match in matches:
        match_id = match.get("id")
        if not match_id:
            continue

        try:
            # تحليل موعد المباراة بالـ UTC
            match_dt_utc = datetime.strptime(
                f"{match['date']} {match['time']}", 
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=pytz.UTC)
        except Exception as e:
            logger.error(f"Error parsing date/time for match {match_id}: {e}")
            continue

        # فارق الوقت بالثواني
        diff_seconds = (match_dt_utc - now_utc).total_seconds()

        # تحديد نوع الإشعار المستحق
        notif_type = None
        if 0 < diff_seconds <= 3600:
            notif_type = "1h"
        
        # إذا كانت المباراة أقرب من 10 دقائق، تعطى الأولوية لإشعار 10m
        if 0 < diff_seconds <= 600:
            notif_type = "10m"
            
        # إذا انطلقت المباراة بالفعل ولم يمر عليها أكثر من 30 دقيقة
        if -1800 <= diff_seconds <= 0:
            notif_type = "start"

        if not notif_type:
            continue

        # إرسال التنبيه للمستخدمين الذين لم يتلقوه بعد
        for user in users:
            user_id = user["telegram_id"]
            user_tz = user["timezone"]

            # التحقق مما إذا كان الإشعار قد أرسل مسبقاً
            already_sent = await is_notification_sent(user_id, match_id, notif_type)
            if already_sent:
                continue

            # تحويل الموعد لتوقيت المستخدم المحلي
            f_date, f_time, _ = convert_match_time(match["date"], match["time"], user_tz)
            msg_text = format_notification_message(match, f_date, f_time, notif_type)

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=msg_text,
                    parse_mode="HTML"
                )
                logger.info(f"📨 تم إرسال إشعار ({notif_type}) للمباراة {match_id} إلى المستخدم {user_id}")
            except TelegramAPIError as e:
                # إذا قام المستخدم بحظر البوت أو حدث خطأ، نسجل ذلك لمنع المحاولة مرة أخرى وتفادي تجميد البوت
                logger.warning(f"⚠️ فشل إرسال الإشعار للمستخدم {user_id}: {e}")
            
            # تسجيل التنبيه كمرسل لتفادي تكراره
            await mark_notification_sent(user_id, match_id, notif_type)
