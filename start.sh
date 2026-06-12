#!/bin/bash
# ===================================================
# World Cup 2026 Schedule Bot - Termux Startup Script
# ===================================================
# طريقة الاستخدام في Termux:
# chmod +x start.sh && ./start.sh
# ===================================================

echo "╔════════════════════════════════════════════╗"
echo "║      🏆 World Cup 2026 Bot Installer       ║"
echo "║          تثبيت وتشغيل البوت في Termux      ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# تحديث الحزم في Termux
echo "📦 1. تحديث قائمة الحزم..."
pkg update -y

# تثبيت بايثون
echo "🐍 2. تثبيت بايثون..."
pkg install python -y

# ترقية أداة تثبيت الحزم pip
echo "⬆️ 3. ترقية pip..."
pip install --upgrade pip

# تثبيت المتطلبات من ملف requirements.txt
echo "📚 4. تثبيت مكتبات Python المطلوبة..."
pip install -r requirements.txt

# إنشاء مجلدات البيانات الأساسية
echo "📁 5. إنشاء مجلد قاعدة البيانات..."
mkdir -p data

# التحقق من وجود ملف الإعدادات .env
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  تنبيه: ملف .env غير موجود!"
    echo "📋 جاري نسخ .env.example لإنشاء ملف .env..."
    cp .env.example .env
    echo ""
    echo "🔑 تم إنشاء ملف .env بنجاح!"
    echo "يرجى تعديل ملف .env وكتابة رمز البوت (BOT_TOKEN) الخاص بك من @BotFather."
    echo "بعد إدخال الرمز، يمكنك تشغيل البوت عبر الأمر: python main.py"
    echo ""
else
    # قراءة التوكن والتأكد من أنه ليس القيمة الافتراضية
    token_val=$(grep "BOT_TOKEN" .env | cut -d'=' -f2)
    if [ "$token_val" = "your_telegram_bot_token_here" ] || [ -z "$token_val" ]; then
        echo "⚠️  تنبيه: يرجى فتح ملف .env وتعديل قيمة BOT_TOKEN برمز البوت الفعلي."
        exit 1
    fi
    
    echo "🚀 6. تشغيل البوت..."
    echo ""
    python main.py
fi
