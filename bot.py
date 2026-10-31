
import os
import re
from datetime import datetime, date, time, timedelta
from pathlib import Path
from flask import Flask, request

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_IDS = [int(x) for x in os.environ.get("ADMIN_CHAT_IDS", "8845795700").split(",") if x.strip().isdigit()]
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1eN0Mis_VzZvT5d17uFbIKVcFjfnZ0w-Z6PsaGtU4wdY")
GOOGLE_CREDS_FILE = os.environ.get("GOOGLE_CREDS_FILE", "credentials.json")
SHEET_NAME = os.environ.get("SHEET_NAME", "Varaq1")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://inspiring-call-centre.onrender.com")

print(f"BOT_TOKEN mavjud: {bool(BOT_TOKEN)} len={len(BOT_TOKEN) if BOT_TOKEN else 0}")
print(f"RENDER_URL: {RENDER_URL}")

# Flask
app = Flask(__name__)

# Telegram bot setup - webhook mode
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

FILIALLAR = {
    "CHILONZOR": {"nomi": "Chilonzor", "manzil": "Novza metro", "lat": 41.295842, "lon": 69.21642},
    "YASHNOBOD": {"nomi": "Yashnobod", "manzil": "Maxtumquli 85", "lat": 41.3000, "lon": 69.3500},
    "MIRZO ULUG'BEK": {"nomi": "Mirzo Ulug'bek", "manzil": "Mirzo Ulug'bek", "lat": 41.3005, "lon": 69.33},
    "SERGELI": {"nomi": "Sergeli", "manzil": "Sergeli", "lat": 41.2273, "lon": 69.209},
    "BERUNIY": {"nomi": "Beruniy", "manzil": "Beruniy metro", "lat": 41.3143, "lon": 69.228},
}

FILIAL, ISM, TELEFON, SANA = range(4)

def parse_izoh_date(izoh_text):
    if not izoh_text:
        return None
    patterns = [
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})",
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
        r"(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, str(izoh_text))
        if m:
            try:
                if len(m.groups()) == 5:
                    d, mo, y, h, mi = map(int, m.groups())
                    return datetime(y, mo, d, h, mi)
                elif len(m.groups()) == 3:
                    d, mo, y = map(int, m.groups())
                    return datetime(y, mo, d, 10, 0)
                elif len(m.groups()) == 4:
                    d, mo, h, mi = map(int, m.groups())
                    return datetime(datetime.now().year, mo, d, h, mi)
            except:
                continue
    return None

def read_sheet():
    if not GOOGLE_SHEET_ID or not Path(GOOGLE_CREDS_FILE).exists():
        return []
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sheet.worksheet(SHEET_NAME)
        except:
            ws = sheet.sheet1
        return ws.get_all_records()
    except Exception as e:
        print(f"Sheet xato: {e}")
        return []

async def check_and_send_reminders(context: ContextTypes.DEFAULT_TYPE):
    rows = read_sheet()
    if not rows:
        return
    tomorrow = date.today() + timedelta(days=1)
    ertaga = []
    for row in rows:
        ism = row.get("ISM FAMILIYASI") or ""
        tel = row.get("TEL NOMERI") or ""
        filial = row.get("FILIALI") or ""
        maqsad = row.get("MAQSADI") or ""
        izoh = row.get("IZOH") or row.get("izoh") or ""
        if not izoh:
            for k, v in row.items():
                if re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", str(v)):
                    izoh = v
                    break
        if not izoh or "KELADI" not in str(maqsad).upper():
            continue
        dt = parse_izoh_date(izoh)
        if dt and dt.date() == tomorrow:
            ertaga.append({"ism": ism, "tel": tel, "filial": filial, "vaqt": dt})
    if not ertaga:
        return
    msg = f"🔔 *Ertaga keladiganlar - {tomorrow.strftime('%d.%m.%Y')}*\nJami: {len(ertaga)} ta\n\n"
    for i, m in enumerate(ertaga, 1):
        msg += f"{i}. 👤 {m['ism']}\n   📞 {m['tel']}\n   🏢 {m['filial']}\n   🕐 {m['vaqt'].strftime('%d.%m %H:%M')}\n\n"
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(f"✅ Filial: {v['nomi']}")] for k, v in FILIALLAR.items()]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Assalomu alaykum! Filialni tanlang:", reply_markup=markup)
    return FILIAL

async def filial_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    for key, val in FILIALLAR.items():
        if val["nomi"].lower() in text.lower() or key.lower() in text.lower():
            context.user_data["filial"] = val["nomi"]
            context.user_data["filial_info"] = val
            await update.message.reply_text(f"✅ Filial: {val['nomi']}\nIsm-sharifingiz:")
            return ISM
    await update.message.reply_text("Filialni tanlang:")
    return FILIAL

async def ism_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ism"] = update.message.text
    await update.message.reply_text("Telefon raqamingizni yuboring:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📞 Telefonni yuborish", request_contact=True)]], resize_keyboard=True))
    return TELEFON

async def telefon_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tel = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data["tel"] = tel
    await update.message.reply_text("Qachon kelasiz? Masalan: 02.11 14:00")
    return SANA

async def sana_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dt = parse_izoh_date(update.message.text)
    if not dt:
        try:
            dt = parse_izoh_date(update.message.text + f".{datetime.now().year} 10:00")
        except:
            dt = datetime.now() + timedelta(days=1)
    ism = context.user_data.get("ism", "")
    tel = context.user_data.get("tel", "")
    filial = context.user_data.get("filial", "")
    filial_info = context.user_data.get("filial_info", {})
    try:
        if GOOGLE_SHEET_ID and Path(GOOGLE_CREDS_FILE).exists():
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(GOOGLE_SHEET_ID)
            try:
                ws = sheet.worksheet(SHEET_NAME)
            except:
                ws = sheet.sheet1
            ws.append_row([ism, tel, filial, "KELADI", "", "", "", "", dt.strftime("%d.%m.%Y %H:%M"), "BOT ORQALI"])
    except Exception as e:
        print(f"Sheet yozish xato: {e}")
    await update.message.reply_text(f"✅ Yozildingiz!\n👤 {ism}\n🏢 {filial}\n📅 {dt.strftime('%d.%m %H:%M')}", parse_mode="Markdown")
    return ConversationHandler.END

async def tekshir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_IDS and update.effective_chat.id not in ADMIN_CHAT_IDS:
        await update.message.reply_text("Faqat admin uchun")
        return
    await update.message.reply_text("⏳ Izoh tekshirilmoqda...")
    await check_and_send_reminders(context)
    await update.message.reply_text("✅ Tugadi!")

async def ertaga_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_send_reminders(context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi")
    return ConversationHandler.END

# Build application
application = Application.builder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        FILIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, filial_handler)],
        ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ism_handler)],
        TELEFON: [MessageHandler(filters.TEXT | filters.CONTACT, telefon_handler)],
        SANA: [MessageHandler(filters.TEXT & ~filters.COMMAND, sana_handler)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
application.add_handler(conv)
application.add_handler(CommandHandler("tekshir", tekshir))
application.add_handler(CommandHandler("ertaga", ertaga_cmd))

try:
    import pytz
    tz = pytz.timezone("Asia/Tashkent")
    application.job_queue.run_daily(check_and_send_reminders, time=time(hour=19, minute=0, tzinfo=tz))
    application.job_queue.run_repeating(check_and_send_reminders, interval=3600, first=30)
except:
    application.job_queue.run_daily(check_and_send_reminders, time=time(hour=19, minute=0))
    application.job_queue.run_repeating(check_and_send_reminders, interval=3600, first=30)

@app.route('/', methods=['GET'])
def index():
    return "Bot is running - webhook mode", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put_nowait(update)
    except Exception as e:
        print(f"Webhook xato: {e}")
    return "OK", 200

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={RENDER_URL}/webhook"
        r = requests.get(url)
        return f"Webhook set: {r.text}", 200
    except Exception as e:
        return f"Xato: {e}", 500

if __name__ == '__main__':
    import asyncio
    # Webhook ni o'rnatish uchun bir marta chaqirish
    try:
        import requests
        webhook_url = f"{RENDER_URL}/webhook"
        set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
        print(f"Webhook o'rnatilmoqda: {webhook_url}")
        r = requests.get(set_url)
        print(f"Webhook natija: {r.text}")
    except Exception as e:
        print(f"Webhook o'rnatish xato: {e}")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
