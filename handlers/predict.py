"""
handlers/predict.py - نظام التوقعات (Bet System) RAAW Points
============================================================
يتيح للمستخدمين توقع نتائج مباريات كأس العالم 2026 وجمع نقاط RAAW.
متوافق بالكامل مع aiogram v2.25.1.
"""

import logging
import json
import re
import pytz
from datetime import datetime
from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import MATCHES_JSON_PATH
from database import (
    get_user_timezone,
    convert_match_time,
    get_user_points,
    add_prediction,
    has_user_predicted,
    get_leaderboard_db
)

logger = logging.getLogger(__name__)


class PredictStates(StatesGroup):
    waiting_for_match = State()
    waiting_for_winner = State()
    waiting_for_score = State()


def load_upcoming_matches() -> list:
    """تحميل المباريات التي لم تبدأ بعد من ملف JSON."""
    try:
        with open(MATCHES_JSON_PATH, "r", encoding="utf-8") as f:
            matches = json.load(f)
            
        now_utc = datetime.now(pytz.UTC)
        upcoming = []
        
        for m in matches:
            try:
                match_dt = datetime.strptime(
                    f"{m.get('date', '')} {m.get('time', '')}", 
                    "%Y-%m-%d %H:%M"
                ).replace(tzinfo=pytz.UTC)
                
                # إظهار فقط المباريات التي لم تبدأ بعد
                if match_dt > now_utc:
                    upcoming.append((m, match_dt))
            except Exception:
                continue
                
        # ترتيب حسب موعد البداية تصاعدياً
        upcoming.sort(key=lambda x: x[1])
        return [x[0] for x in upcoming]
    except Exception as e:
        logger.error(f"Error loading upcoming matches: {e}")
        return []


async def cmd_predict(message: Message, state: FSMContext):
    """بدء التوقع واختيار المباراة."""
    await state.finish()  # تنظيف أي حالة سابقة
    
    upcoming = load_upcoming_matches()
    if not upcoming:
        await message.answer("⚠️ لا توجد مباريات قادمة متاحة للتوقع حالياً.")
        return

    # عرض أول 6 مباريات قادمة لتجنب ازدحام الأزرار
    upcoming_limit = upcoming[:6]
    user_tz = await get_user_timezone(message.from_user.id)
    
    markup = InlineKeyboardMarkup(row_width=1)
    for m in upcoming_limit:
        # تحويل وقت المباراة لتوقيت المستخدم
        date_str, time_str, _ = convert_match_time(m["date"], m["time"], user_tz)
        
        btn_text = f"{m['home_flag']} {m['home_team']} × {m['away_team']} {m['away_flag']} ({time_str})"
        markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"pred_match:{m['id']}"))
        
    markup.add(InlineKeyboardButton(text="❌ إلغاء", callback_data="pred_cancel"))
    
    await message.answer(
        "⚽ <b>اختر مباراة لتوقع نتيجتها من القائمة التالية:</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await PredictStates.waiting_for_match.set()


async def callback_match_selected(callback: CallbackQuery, state: FSMContext):
    """معالجة اختيار المباراة وتحديد خيار الفائز."""
    match_id = int(callback.data.split(":")[1])
    
    # تحميل تفاصيل المباراة
    upcoming = load_upcoming_matches()
    selected_match = next((m for m in upcoming if m["id"] == match_id), None)
    
    if not selected_match:
        await callback.answer("⚠️ هذه المباراة بدأت بالفعل أو غير متاحة للتوقع حالياً.", show_alert=True)
        await state.finish()
        return

    # حفظ معرّف المباراة في FSM
    await state.update_data(match_id=match_id, match_details=selected_match)
    
    home_name = selected_match["home_team"]
    home_flag = selected_match["home_flag"]
    away_name = selected_match["away_team"]
    away_flag = selected_match["away_flag"]
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text=f"{home_flag} فوز {home_name}", callback_data="pred_winner:home"),
        InlineKeyboardButton(text=f"{away_flag} فوز {away_name}", callback_data="pred_winner:away"),
        InlineKeyboardButton(text="🤝 تعادل الفريقين", callback_data="pred_winner:draw"),
        InlineKeyboardButton(text="❌ إلغاء", callback_data="pred_cancel")
    )
    
    await callback.message.edit_text(
        f"🎯 <b>توقع مباراة:</b>\n"
        f"{home_flag} {home_name} × {away_name} {away_flag}\n\n"
        f"اختر توقعك لنتيجة المباراة الرئيسية:",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await PredictStates.waiting_for_winner.set()
    await callback.answer()


async def callback_winner_selected(callback: CallbackQuery, state: FSMContext):
    """حفظ خيار الفائز وطلب النتيجة الرقمية."""
    winner = callback.data.split(":")[1]
    await state.update_data(predicted_winner=winner)
    
    data = await state.get_data()
    match = data["match_details"]
    
    await callback.message.edit_text(
        f"🎯 <b>الخطوة الأخيرة:</b>\n"
        f"مباراة: {match['home_flag']} {match['home_team']} × {match['away_team']} {match['away_flag']}\n\n"
        f"يرجى كتابة النتيجة المتوقعة للمباراة وإرسالها كنص في الدردشة.\n"
        f"⚠️ <b>تنبيه:</b> يجب كتابة النتيجة بصيغة (الأهداف على اليسار للمضيف، وعلى اليمين للضيف)\n"
        f"مثال: <code>2-1</code> (فوز {match['home_team']}) أو <code>0-0</code> (تعادل) أو <code>1-2</code> (فوز {match['away_team']})",
        parse_mode="HTML"
    )
    await PredictStates.waiting_for_score.set()
    await callback.answer()


async def msg_score_received(message: Message, state: FSMContext):
    """استلام النتيجة والتحقق منها وحفظ التوقع."""
    score_text = message.text.strip()
    
    # التحقق من الصيغة (رقم-رقم)
    if not re.match(r"^\d+-\d+$", score_text):
        await message.reply(
            "❌ صيغة النتيجة غير صحيحة!\n"
            "يرجى إرسال النتيجة بالشكل التالي: <b>رقم-رقم</b>\n"
            "مثال: <code>2-1</code> أو <code>1-1</code>",
            parse_mode="HTML"
        )
        return
        
    data = await state.get_data()
    match_id = data["match_id"]
    predicted_winner = data["predicted_winner"]
    match = data["match_details"]
    
    # التحقق المنطقي من توافق النتيجة مع الفائز المختار
    try:
        home_score, away_score = map(int, score_text.split("-"))
        if predicted_winner == "home" and home_score <= away_score:
            await message.reply("⚠️ لقد اخترت فوز الفريق المضيف سابقاً، ولكن النتيجة المدخلة تشير للتعادل أو فوز الضيف! يرجى إدخال نتيجة متوافقة (مثال: 2-1).")
            return
        elif predicted_winner == "away" and away_score <= home_score:
            await message.reply("⚠️ لقد اخترت فوز الفريق الضيف سابقاً، ولكن النتيجة المدخلة تشير للتعادل أو فوز المضيف! يرجى إدخال نتيجة متوافقة (مثال: 1-2).")
            return
        elif predicted_winner == "draw" and home_score != away_score:
            await message.reply("⚠️ لقد اخترت التعادل سابقاً، ولكن النتيجة المدخلة تشير إلى فوز أحد الطرفين! يرجى إدخال نتيجة تعادل (مثال: 1-1).")
            return
    except Exception:
        await message.reply("❌ حدث خطأ في معالجة الأرقام، حاول مجدداً بصيغة صحيحة مثل 2-1.")
        return

    # حفظ التوقع بقاعدة البيانات
    await add_prediction(
        user_id=message.from_user.id,
        match_id=match_id,
        predicted_winner=predicted_winner,
        predicted_score=score_text
    )
    
    await message.answer(
        f"✅ <b>تم تسجيل توقعك بنجاح!</b>\n\n"
        f"⚽ المباراة: {match['home_flag']} {match['home_team']} × {match['away_team']} {match['away_flag']}\n"
        f"🎯 توقعك: {score_text}\n\n"
        f"سيتم احتساب النقاط تلقائياً عند تحديث نتيجة المباراة ونهايتها! بالتوفيق 🏆",
        parse_mode="HTML"
    )
    await state.finish()


async def callback_pred_cancel(callback: CallbackQuery, state: FSMContext):
    """إلغاء عملية التوقع."""
    await state.finish()
    await callback.message.edit_text("❌ تم إلغاء عملية التوقع.")
    await callback.answer()


async def cmd_points(message: Message):
    """عرض نقاط RAAW للمستخدم."""
    points = await get_user_points(message.from_user.id)
    await message.answer(
        f"👤 <b>نقاطك الحالية:</b>\n\n"
        f"🎮 الرصيد: <b>{points} RAAW Points</b> 🏆\n\n"
        f"توقع نتائج المباريات القادمة عبر أمر /predict لزيادة نقاطك!",
        parse_mode="HTML"
    )


async def cmd_leaderboard(message: Message):
    """عرض جدول ترتيب المتوقعين."""
    top_users = await get_leaderboard_db()
    if not top_users:
        await message.answer("📊 جدول الترتيب فارغ حالياً. كن أول من يتوقع ويجمع النقاط!")
        return
        
    text = "📊 <b>جدول ترتيب النقاط (RAAW Points)</b> 🏆\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for idx, user in enumerate(top_users):
        rank = medals[idx] if idx < 3 else f"{idx + 1}."
        username = f"@{user['username']}" if user['username'] else f"مستخدم {user['telegram_id']}"
        text += f"{rank} {username} ── <b>{user['raaw_points']} نقطة</b>\n"
        
    await message.answer(text, parse_mode="HTML")


async def callback_predict_start(callback: CallbackQuery, state: FSMContext):
    """بدء التوقع من الزر المباشر."""
    # تمرير callback.message ولكن مع الحفاظ على معلومات المستخدم الفعلي
    callback.message.from_user = callback.from_user
    await cmd_predict(callback.message, state)
    await callback.answer()


async def callback_predict_leaderboard(callback: CallbackQuery):
    """عرض المتصدرين من الزر المباشر."""
    await cmd_leaderboard(callback.message)
    await callback.answer()


def register_predict_handlers(dp: Dispatcher):
    """تسجيل معالجات نظام التوقعات."""
    # الأوامر العامة
    dp.register_message_handler(cmd_predict, commands=["predict"], state="*")
    dp.register_message_handler(cmd_points, commands=["points"])
    dp.register_message_handler(cmd_leaderboard, commands=["leaderboard"])
    
    # معالجات الأزرار والـ FSM
    dp.register_callback_query_handler(callback_pred_cancel, text="pred_cancel", state="*")
    dp.register_callback_query_handler(callback_predict_start, text="pred_start", state="*")
    dp.register_callback_query_handler(callback_predict_leaderboard, text="pred_leaderboard")
    dp.register_callback_query_handler(callback_match_selected, text_startswith="pred_match:", state=PredictStates.waiting_for_match)
    dp.register_callback_query_handler(callback_winner_selected, text_startswith="pred_winner:", state=PredictStates.waiting_for_winner)
    dp.register_message_handler(msg_score_received, state=PredictStates.waiting_for_score)
