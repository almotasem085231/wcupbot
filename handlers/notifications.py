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
from aiogram.utils.exceptions import TelegramAPIError
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

    # تشغيل التحقق من التوقعات تلقائياً
    try:
        await resolve_predictions(bot)
    except Exception as e:
        logger.error(f"Error resolving predictions in scheduler: {e}")


async def resolve_predictions(bot: Bot):
    """التحقق من نتائج المباريات وحساب نقاط توقعات المستخدمين."""
    from database import get_unresolved_predictions, resolve_prediction_db
    
    matches = load_matches()
    if not matches:
        return

    unresolved = await get_unresolved_predictions()
    if not unresolved:
        return

    matches_map = {m["id"]: m for m in matches}

    for pred in unresolved:
        match_id = pred["match_id"]
        user_id = pred["user_id"]
        pred_winner = pred["predicted_winner"]
        pred_score = pred["predicted_score"]

        match = matches_map.get(match_id)
        if not match:
            continue

        home_score = match.get("home_score")
        away_score = match.get("away_score")

        # إذا كانت النتيجة متوفرة (ليست null وليست None)
        if home_score is not None and away_score is not None:
            if home_score > away_score:
                actual_winner = "home"
            elif away_score > home_score:
                actual_winner = "away"
            else:
                actual_winner = "draw"

            points = 0
            try:
                pred_home, pred_away = map(int, pred_score.split("-"))
                if pred_home == home_score and pred_away == away_score:
                    points = 10
                elif pred_winner == actual_winner:
                    points = 5
            except Exception:
                if pred_winner == actual_winner:
                    points = 5

            await resolve_prediction_db(pred["id"], user_id, points)

            home_team = match.get("home_team", "غير معروف")
            away_team = match.get("away_team", "غير معروف")
            home_flag = match.get("home_flag", "🏳️")
            away_flag = match.get("away_flag", "🏳️")

            if points == 10:
                result_text = f"🔥 <b>توقع خارق! نتيجة صحيحة تماماً!</b>\n\nحصلت على: <b>+10 RAAW Points</b> 🏆"
            elif points == 5:
                result_text = f"✅ <b>توقع صحيح للفائز باللقاء!</b>\n\nحصلت على: <b>+5 RAAW Points</b> ⭐️"
            else:
                result_text = f"❌ <b>توقع غير صحيح للمباراة.</b>\n\nحصلت على: <b>0 نقاط RAAW</b>"

            message_text = (
                f"🔔 <b>تم احتساب توقعك للمباراة!</b>\n\n"
                f"{home_flag} {home_team} <b>{home_score} - {away_score}</b> {away_team} {away_flag}\n"
                f"🎯 توقعك: <b>{pred_score}</b>\n\n"
                f"{result_text}"
            )

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
                logger.info(f"📨 تم إرسال نتيجة التوقع للمستخدم {user_id} للمباراة {match_id}")
            except TelegramAPIError as e:
                logger.warning(f"⚠️ فشل إرسال نتيجة التوقع للمستخدم {user_id}: {e}")
