import asyncio
import logging
import os
import json
import random
import threading
import hmac
from datetime import datetime
import zoneinfo
import hashlib

from flask import Flask, request as flask_request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
from astronomy import get_sky_report, moon_phase_accurate

# ─── تنظیمات ───────────────────────────────────────────────
load_dotenv()

def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

TOKEN           = required_env("BOT_TOKEN")
ADMIN_ID        = int(required_env("ADMIN_ID"))
WEBHOOK_URL     = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET  = os.getenv("WEBHOOK_SECRET")
BACKUP_GROUP_ID = int(required_env("BACKUP_GROUP_ID"))
DB_FILE         = "db.json"
PORT            = int(os.environ.get("PORT", 8080))

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── تایم‌زون ───────────────────────────────────────────────
def today_ir():
    return str(datetime.now(zoneinfo.ZoneInfo("Asia/Tehran")).date())

def now_ir():
    return datetime.now(zoneinfo.ZoneInfo("Asia/Tehran"))

# ─── کد ناشناس ─────────────────────────────────────────────
def get_anon_code(user_id: int) -> str:
    return hashlib.md5(str(user_id).encode()).hexdigest()[:4].upper()

# ─── توابع نجومی (fallback) ─────────────────────────────────
def moon_phase(now) -> str:
    ref   = datetime(2000, 1, 6, tzinfo=zoneinfo.ZoneInfo("Asia/Tehran"))
    days  = (now - ref).total_seconds() / 86400
    cycle = days % 29.53
    if cycle < 1.85:   return "🌑 ماه نو (New Moon)"
    elif cycle < 7.38:  return "🌒 هلال رو به رشد (Waxing Crescent)"
    elif cycle < 9.22:  return "🌓 ربع اول (First Quarter)"
    elif cycle < 14.77: return "🌔 گیبوس رو به رشد (Waxing Gibbous)"
    elif cycle < 16.61: return "🌕 بدر — ماه کامل (Full Moon)"
    elif cycle < 22.15: return "🌖 گیبوس رو به کاهش (Waning Gibbous)"
    elif cycle < 23.99: return "🌗 ربع آخر (Last Quarter)"
    elif cycle < 29.53: return "🌘 هلال رو به کاهش (Waning Crescent)"
    return "🌑 ماه نو (New Moon)"

def zodiac_sign(month: int, day: int) -> str:
    signs = [
        (1, 20, "جدی (Capricorn) ♑"), (2, 19, "دلو (Aquarius) ♒"),
        (3, 21, "حوت (Pisces) ♓"),    (4, 20, "حمل (Aries) ♈"),
        (5, 21, "ثور (Taurus) ♉"),    (6, 21, "جوزا (Gemini) ♊"),
        (7, 23, "سرطان (Cancer) ♋"),  (8, 23, "اسد (Leo) ♌"),
        (9, 23, "سنبله (Virgo) ♍"),   (10, 23, "میزان (Libra) ♎"),
        (11, 22, "عقرب (Scorpio) ♏"), (12, 22, "قوس (Sagittarius) ♐"),
        (12, 31, "جدی (Capricorn) ♑"),
    ]
    for m, d, name in signs:
        if month < m or (month == m and day < d):
            return name
    return "جدی (Capricorn) ♑"

def get_season(month: int, day: int) -> str:
    if (month == 3 and day >= 20) or (3 < month < 6) or (month == 6 and day < 21):
        return "🌸 بهار (Spring)"
    elif (month == 6 and day >= 21) or (6 < month < 9) or (month == 9 and day < 23):
        return "☀️ تابستان (Summer)"
    elif (month == 9 and day >= 23) or (9 < month < 12) or (month == 12 and day < 22):
        return "🍂 پاییز (Autumn)"
    return "❄️ زمستان (Winter)"

def get_dates() -> str:
    now = now_ir()
    en_days   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    en_months = ["January","February","March","April","May","June",
                 "July","August","September","October","November","December"]
    miladi = f"{en_days[now.weekday()]}, {en_months[now.month-1]} {now.day} {now.year}"
    try:
        import jdatetime
        jdate     = jdatetime.datetime.fromgregorian(datetime=now)
        fa_days   = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یک‌شنبه"]
        fa_months = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                     "مهر","آبان","آذر","دی","بهمن","اسفند"]
        shamsi = f"{fa_days[now.weekday()]}، {jdate.day} {fa_months[jdate.month-1]} {jdate.year}"
    except ImportError:
        shamsi = "نیاز به نصب jdatetime"
    moon   = moon_phase_accurate(now) or moon_phase(now)
    zodiac = zodiac_sign(now.month, now.day)
    season = get_season(now.month, now.day)
    return (
        f"📅 تاریخ امروز:\n\n"
        f"🗓 شمسی: {shamsi}\n"
        f"🌍 میلادی: {miladi}\n\n"
        f"🌙 فاز ماه: {moon}\n"
        f"♈ برج زودیاک: {zodiac}\n"
        f"🍂 فصل: {season}"
    )

# ─── پایگاه داده ───────────────────────────────────────────
db_msg_id = None

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    try:
        asyncio.run_coroutine_threadsafe(backup_db(db), loop)
    except Exception:
        pass

async def backup_db(db: dict):
    global db_msg_id
    full = {k: v for k, v in db.items() if k != "anon_codes"}
    text = json.dumps(full, ensure_ascii=False)
    if len(text) > 4000:
        usage   = {k: v for k, v in full.items() if k in ("history_usage", "philosophy_usage")}
        mapping = {k: v for k, v in full.items() if k not in ("history_usage", "philosophy_usage")}
        trimmed = {**dict(list(mapping.items())[-100:]), **usage}
        text    = json.dumps(trimmed, ensure_ascii=False)
    try:
        if db_msg_id:
            await application.bot.edit_message_text(text, chat_id=BACKUP_GROUP_ID, message_id=db_msg_id)
        else:
            msg = await application.bot.send_message(BACKUP_GROUP_ID, text)
            db_msg_id = msg.message_id
            await application.bot.pin_chat_message(BACKUP_GROUP_ID, db_msg_id, disable_notification=True)
    except Exception as e:
        logger.error(f"خطا در بکاپ: {e}")

async def restore_db():
    global db_msg_id
    try:
        chat = await application.bot.get_chat(BACKUP_GROUP_ID)
        if chat.pinned_message and chat.pinned_message.text:
            mapping   = json.loads(chat.pinned_message.text)
            db_msg_id = chat.pinned_message.message_id
            db        = load_db()
            db.update(mapping)
            save_db(db)
            logger.info(f"✅ db بازیابی شد — {len(mapping)} رکورد")
    except Exception as e:
        logger.error(f"خطا در بازیابی db: {e}")

# ─── کیبوردها ──────────────────────────────────────────────
CANCEL_KB = ReplyKeyboardMarkup([["❌ لغو"]], resize_keyboard=True, one_time_keyboard=True)

def reply_btn(admin_msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ پاسخ به ادمین", callback_data=f"reply_{admin_msg_id}")
    ]])

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["🔭 آسمان امشب",   "📖 فال حافظ"],
        ["📅 تاریخ امروز",  "🧠 اندیشه روزانه"],
        ["📜 درس تاریخ",    "📨 ارسال پیام"],
    ], resize_keyboard=True)

def send_type_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✉️ پیام عادی",  callback_data="msg_normal"),
        InlineKeyboardButton("🎭 پیام ناشناس", callback_data="msg_anon"),
    ]])

# ─── هندلرها ───────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db   = load_db()
    db.setdefault("users", {})[str(user.id)] = user.full_name
    save_db(db)
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋 به ربات Black Pearl خوش اومدی.\n\n"
        "از منو زیر می‌تونی به همه امکانات دسترسی داشته باشی.\n"
        "برای راهنما از دستور /help استفاده کن.",
    )
    await update.message.reply_text("منو:", reply_markup=main_menu())

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 راهنمای بات Black Pearl\n\n"
        "📚 محتوای روزانه\n"
        "هر روز یه درس تاریخ و یه اندیشه فلسفی از بزرگان داری — روزی یه بار.\n\n"
        "📖 فال حافظ\n"
        "توی چتت «فال» بنویس یا از منو استفاده کن — از بین غزل های حافظ یه فال برات انتخاب می‌شه.\n\n"
        "📅 تاریخ امروز\n"
        "توی چتت «امروز» بنویس یا از منو استفاده کن — تاریخ شمسی، میلادی، فاز ماه، برج و فصل رو می‌بینی.\n\n"
        "🔭 آسمان امشب\n"
        "توی چتت «آسمان» بنویس یا از منو استفاده کن — وضعیت سیارات، صورت‌های فلکی و ستاره‌های ناوبری رو می‌بینی..\n\n"
        "📨 ارسال پیام به ادمین\n"
        "می‌تونی با اسم (پیام عادی) یا بدون هویت (پیام ناشناس) با ادمین در ارتباط باشی. "
        "وقتی ادمین جواب داد بهت اطلاع داده میشه.\n\n"
        "آیدی پشتیبانی: @TriuneGod"
    )

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db    = load_db()
    users = db.get("users", {})
    await update.message.reply_text(
        f"📊 آمار بات:\n\n"
        f"👤 کاربران یونیک: {len(users)}"
    )

async def invalid_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text("❔دستور نامعتبر.\nراهنمای استفاده از بات: /help")

async def cmd_sky(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔭 در حال محاسبه وضعیت آسمان...")
    try:
        report = get_sky_report(now_ir())
        await update.message.reply_text(report)
    except Exception as e:
        logger.error(f"خطای آسمان: {e}")
        await update.message.reply_text(f"⚠️ خطا: {e}")

async def cmd_hafez(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from hafez import HAFEZ_POEMS
    entry = random.choice(HAFEZ_POEMS)
    await update.message.reply_text(
        f"📖 فال حافظ\n\n{entry['poem']}\n\n✨ تعبیر:\n{entry['tafsir']}"
    )

async def _send_history(reply_fn, user_id: int):
    db = load_db()
    if db.get("history_usage", {}).get(str(user_id)) == today_ir():
        await reply_fn("📜 درس تاریخ امروزت رو گرفتی!\nفردا برگرد. 🗓")
        return
    from history import HISTORY_FACTS
    await reply_fn(f"📜 {random.choice(HISTORY_FACTS)}")
    db.setdefault("history_usage", {})[str(user_id)] = today_ir()
    save_db(db)

async def _send_philosophy(reply_fn, user_id: int):
    db = load_db()
    if db.get("philosophy_usage", {}).get(str(user_id)) == today_ir():
        await reply_fn("🧠 اندیشه امروزت رو گرفتی!\nفردا برگرد. 🗓")
        return
    from philosophy import PHILOSOPHY_QUOTES
    await reply_fn(f"🧠 {random.choice(PHILOSOPHY_QUOTES)}")
    db.setdefault("philosophy_usage", {})[str(user_id)] = today_ir()
    save_db(db)

# ─── callback ها ───────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    user  = query.from_user
    await query.answer()

    if data == "msg_choose":
        await query.message.reply_text(
            "پیامت رو چطور بفرستم؟\n\n"
            "✉️ پیام عادی — اسم و مشخصاتت برای ادمین نمایش داده میشه\n"
            "🎭 پیام ناشناس — هویتت مخفی میمونه",
            reply_markup=send_type_menu(),
        )

    elif data == "msg_normal":
        ctx.user_data["waiting"] = True
        ctx.user_data["anon"]    = False
        await query.message.reply_text("✏️ پیامت رو بنویس:", reply_markup=CANCEL_KB)

    elif data == "msg_anon":
        ctx.user_data["waiting"] = True
        ctx.user_data["anon"]    = True
        await query.message.reply_text("🎭 پیامت رو بنویس (ناشناس):", reply_markup=CANCEL_KB)

    elif data == "get_history":
        await _send_history(query.message.reply_text, user.id)

    elif data == "get_philosophy":
        await _send_philosophy(query.message.reply_text, user.id)

    elif data == "get_date":
        await query.message.reply_text(get_dates())

    elif data == "get_hafez":
        from hafez import HAFEZ_POEMS
        entry = random.choice(HAFEZ_POEMS)
        await query.message.reply_text(
            f"📖 فال حافظ\n\n{entry['poem']}\n\n✨ تعبیر:\n{entry['tafsir']}"
        )

    elif data == "get_sky":
        await query.message.reply_text("🔭 در حال محاسبه وضعیت آسمان...")
        try:
            report = get_sky_report(now_ir())
            await query.message.reply_text(report)
        except Exception as e:
            logger.error(f"خطای آسمان callback: {e}")
            await query.message.reply_text(f"⚠️ خطا: {e}")

    elif data.startswith("reply_"):
        admin_msg_id = int(data.split("_")[1])
        db    = load_db()
        entry = db.get(str(admin_msg_id))
        is_anon = entry[2] if (entry and len(entry) > 2) else False
        ctx.user_data["waiting"]        = True
        ctx.user_data["anon"]           = is_anon
        ctx.user_data["reply_to_admin"] = admin_msg_id
        prompt = "🎭 پیامت رو بنویس (ناشناس):" if is_anon else "✏️ پیامت رو بنویس:"
        await query.message.reply_text(prompt, reply_markup=CANCEL_KB)

# ─── ارسال پیام به ادمین ────────────────────────────────────
async def send_to_admin(ctx, msg, user, db, anon=False):
    sender = f"🎭 ناشناس #{get_anon_code(user.id)}" if anon \
             else f"{user.full_name} (@{user.username or '—'}) | آیدی: {user.id}"
    tag = await ctx.bot.send_message(ADMIN_ID, f"📩 پیام از {sender}")
    copied = await ctx.bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=msg.chat_id,
        message_id=msg.message_id,
        reply_to_message_id=tag.message_id,
    )
    db[str(copied.message_id)] = [user.id, msg.message_id, anon]
    save_db(db)

async def user_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    user = update.effective_user

    # کلمات کلیدی — همیشه اول
    if msg.text:
        txt = msg.text.strip()
        # دکمه‌های منو
        if txt == "🔭 آسمان امشب":
            await cmd_sky(update, ctx)
            return
        if txt == "📖 فال حافظ":
            await cmd_hafez(update, ctx)
            return
        if txt == "📅 تاریخ امروز":
            await msg.reply_text(get_dates())
            return
        if txt == "🧠 اندیشه روزانه":
            await _send_philosophy(msg.reply_text, user.id)
            return
        if txt == "📜 درس تاریخ":
            await _send_history(msg.reply_text, user.id)
            return
        if txt == "📨 ارسال پیام":
            await msg.reply_text(
                "پیامت رو چطور بفرستم؟\n\n"
                "✉️ پیام عادی — اسم و مشخصاتت برای ادمین نمایش داده میشه\n"
                "🎭 پیام ناشناس — هویتت مخفی میمونه",
                reply_markup=send_type_menu(),
            )
            return
        # کلمات کلیدی متنی
        if txt in ("فال", "فال حافظ", "🔮"):
            await cmd_hafez(update, ctx)
            return
        if txt in ("امروز", "تاریخ", "تاریخ امروز"):
            await msg.reply_text(get_dates())
            return
        if txt in ("آسمان", "نجوم", "ستاره"):
            await cmd_sky(update, ctx)
            return

    if msg.text == "❌ لغو":
        ctx.user_data["waiting"] = False
        ctx.user_data["anon"]    = False
        ctx.user_data.pop("reply_to_admin", None)
        await msg.reply_text("❌ لغو شد.", reply_markup=main_menu())
        return

    if not ctx.user_data.get("waiting"):
        if msg.chat.type != "private":
            return
        await msg.reply_text("❔دستور نامعتبر.\nراهنمای استفاده از بات: /help")
        return

    anon = ctx.user_data.pop("anon", False)
    ctx.user_data["waiting"] = False
    db = load_db()
    await send_to_admin(ctx, msg, user, db, anon=anon)
    if anon:
        await msg.reply_text("✅ پیام ناشناست ارسال شد.", reply_markup=main_menu())
    else:
        await msg.reply_text("✅ پیامت ارسال شد. منتظر جواب ادمین باش!", reply_markup=main_menu())

async def user_sticker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    user = update.effective_user
    if not ctx.user_data.get("waiting"):
        if msg.chat.type != "private":
            return
        await msg.reply_text("❔دستور نامعتبر.\nراهنمای استفاده از بات: /help")
        return
    anon = ctx.user_data.pop("anon", False)
    ctx.user_data["waiting"] = False
    db = load_db()
    await send_to_admin(ctx, msg, user, db, anon=anon)
    await msg.reply_text("✅ پیامت ارسال شد.", reply_markup=main_menu())

async def admin_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg   = update.message
    db    = load_db()
    entry = db.get(str(msg.reply_to_message.message_id))
    if not entry:
        return
    user_id, user_msg_id = entry[0], entry[1]
    try:
        await ctx.bot.copy_message(
            chat_id=user_id,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
            reply_to_message_id=user_msg_id,
        )
        await ctx.bot.send_message(
            user_id, "📬 ادمین جوابتو داد!",
            reply_markup=reply_btn(msg.reply_to_message.message_id),
        )
        await msg.reply_text("✅ پاسخ ارسال شد.")
    except Exception as e:
        logger.error(f"خطا: {e}")
        await msg.reply_text(f"⚠️ خطا: {e}")

# ─── فیلترها ───────────────────────────────────────────────
ALL_CONTENT = (
    filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO
    | filters.VOICE | filters.ANIMATION | filters.VIDEO_NOTE
    | filters.LOCATION | filters.CONTACT
)

# ─── ثبت هندلرها (مشترک) ───────────────────────────────────
def register_handlers(app):
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("stats",  cmd_stats))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        filters.Chat(ADMIN_ID) & filters.REPLY & (ALL_CONTENT | filters.Sticker.ALL), admin_reply))
    app.add_handler(MessageHandler(filters.COMMAND, invalid_command))
    app.add_handler(MessageHandler(
        ~filters.COMMAND & ALL_CONTENT, user_message))
    app.add_handler(MessageHandler(
        filters.Sticker.ALL, user_sticker))

# ─── Flask ─────────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "OK", 200

# ─── ساخت اپ ───────────────────────────────────────────────
application = ApplicationBuilder().token(TOKEN).build()
register_handlers(application)

# ─── event loop ─────────────────────────────────────────────
loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_loop, daemon=True).start()
asyncio.run_coroutine_threadsafe(application.initialize(), loop).result()
asyncio.run_coroutine_threadsafe(application.start(), loop).result()
asyncio.run_coroutine_threadsafe(restore_db(), loop).result(timeout=10)

# ─── webhook endpoint ────────────────────────────────────────
@flask_app.route("/webhook", methods=["POST"])
def webhook_handler():
    received_secret = flask_request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not WEBHOOK_SECRET or not hmac.compare_digest(received_secret, WEBHOOK_SECRET):
        return "Forbidden", 403
    if flask_request.is_json:
        data   = flask_request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        asyncio.run_coroutine_threadsafe(
            application.process_update(update), loop
        ).result(timeout=30)
        return "", 200
    return "Forbidden", 403

# ─── اجرا ──────────────────────────────────────────────────
if __name__ == "__main__":
    if WEBHOOK_URL:
        if not WEBHOOK_SECRET:
            raise RuntimeError("WEBHOOK_SECRET is required when WEBHOOK_URL is set")
        logger.info("حالت Webhook فعاله")
        asyncio.run_coroutine_threadsafe(
            application.bot.set_webhook(
                f"{WEBHOOK_URL}/webhook", secret_token=WEBHOOK_SECRET
            ), loop
        ).result()
        flask_app.run(host="0.0.0.0", port=PORT)
    else:
        logger.info("حالت Polling فعاله")
        asyncio.run_coroutine_threadsafe(application.stop(), loop).result()
        loop.call_soon_threadsafe(loop.stop)
        poll_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(poll_loop)
        poll_app = ApplicationBuilder().token(TOKEN).build()
        register_handlers(poll_app)
        poll_app.run_polling(drop_pending_updates=False)
