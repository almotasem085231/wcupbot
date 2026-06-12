"""
config.py - إعدادات البوت المركزية
==============================================
يحتوي على المسارات، الإعدادات الأساسية، والمناطق الزمنية.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# المسارات الأساسية
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = str(DATA_DIR / "worldcup.db")
MATCHES_JSON_PATH = str(BASE_DIR / "matches.json")

# إنشاء مجلد البيانات إذا لم يكن موجوداً
DATA_DIR.mkdir(exist_ok=True)

# إعدادات Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# إعدادات التسجيل
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# الدول العربية والمناطق الزمنية المتاحة في البوت
ARABIC_TIMEZONES = {
    "🇱🇾 ليبيا": "Africa/Tripoli",
    "🇪🇬 مصر": "Africa/Cairo",
    "🇸🇦 خنازير ": "Asia/Riyadh",
    "🇸🇾 سوريا": "Asia/Damascus",
    "🇩🇿 الجزائر": "Africa/Algiers",
    "🇹🇳 تونس": "Africa/Tunis",
    "🇲🇦 المغرب": "Africa/Casablanca",
    "🇦🇪 الإمارات": "Asia/Dubai"
}
