
import json
import os
import re
from datetime import datetime, date, time, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, CallbackQueryHandler, filters

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9170467133:AAEtyfAuc8PUxsXcKt1oXhryy-IiggRfz8Y")
ADMIN_CHAT_IDS = [int(x) for x in os.environ.get("ADMIN_CHAT_IDS", "8845795700").split(",") if x.strip().isdigit()]
DATA_FILE = Path("royxat.json")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
GOOGLE_CREDS_FILE = os.environ.get("GOOGLE_CREDS_FILE", "credentials.json")

# ====================== FILIALLAR - TO'LIQ YANGILANGAN ======================
FILIALLAR = {
    "Chilonzor": {
        "manzil": "Chilonzor filialimiz\nNovza metro bekati, Sport tovar chorraxasida, 4-etaj",
        "tel": "+998(71)278-07-97, +998(91)405-09-15, +998(93)777-09-23",
        "lat": 41.295842, "lon": 69.216420  # Inspiring Education asosiy
    },
    "Sergeli": {
        "manzil": "Sergeli filialimiz\nSergeli tumani, 3-bekat oldida, Asal med klinikasi tepasida, Avto maktab Saxiy bazar majmualari",
        "tel": "+998(90)065-21-15, +998(93)554-37-74, +998(50)800-97-00",
        "lat": 41.2273, "lon": 69.2090
    },
    "Yunusobod": {
        "manzil": "Yunusobod filialimiz\nYunusobod tumani, Turkiston metrosi",
        "tel": "+998(95)855-81-81, +998(50)450-06-29",
        "lat": 41.3626, "lon": 69.2860
    },
    "Beruniy": {
        "manzil": "Beruniy filialimiz\nBeruniy metrosidan 5 daqiqa\nMo'ljal: Huvaydo to'yxonasi qarshisida, Bellisimo pitsa yonidagi eshikdan 3-etaj",
        "tel": "+998(94)978-07-97, +998(99)106-81-98, +998(90)515-19-86",
        "lat": 41.3143, "lon": 69.2280
    },
    "Yangidarxon": {
        "manzil": "Yangidarxon filialimiz (Sergeli 2)\nYangihayot tumani, Yangidarxon mahallasi",
        "tel": "+998(77)449-97-27, +998(33)539-09-99",
        "lat": 41.1890, "lon": 69.2020
    },
    "Yashnobod": {
        "manzil": "Yashnobod filialimiz\nMaxtumquli ko'chasi 85, Yashnobod tumani\nMo'ljal: Makro supermarketi qarshisida",
        "tel": "+998(55)055-07-97, +998(33)539-09-99, +998(94)474-34-74",
        "lat": 41.3000, "lon": 69.3500
    },
    "TTZ": {
        "manzil": "TTZ filialimiz\nMirzo Ulug'bek tumani\nMo'ljal: Diadora chorrahasidan keyin, Lokomotiv bekati yonida",
        "tel": "+998(93)554-37-74, +998(94)939-64-12",
        "lat": 41.3005, "lon": 69.3300
    },
    "Samarqand": {
        "manzil": "Samarqand filiali Future Leaders' Academy\nSamarqand Shahar, Bo'stonsaroy ko'chasi 29\nMo'ljal: Respublika kasalxonasi, Dagbitskiy yangi ko'prik",
        "tel": "+998(91)556-78-22, +998(91)545-88-22",
        "lat": 39.6540, "lon": 66.9630
    },
    "Termiz": {
        "manzil": "Termiz filialimiz\nTermiz shahri, Soat chorraha",
        "tel": "+998(91)905-62-60, +998(93)220-33-43",
        "lat": 37.2240, "lon": 67.2780
    },
    "Navoiy": {
        "manzil": "Navoiy filialimiz\nTalabalar ko'chasi 50/1\nMo'ljal: Azamat Fayz to'yxonasi qarshisida, Ped institut, 14 mikrorayon",
        "tel": "990949990, 977978242",
        "lat": 40.1030, "lon": 65.3740
    },
    "Olmos": {
        "manzil": "Olmos filialimiz (Yashnobod tumani)\nOlmos metrodan 10 daqiqa\nManzil: 58a Harbiylar shaharchasi 8\nMo'ljal: Aziz Shifo med qarshisida",
        "tel": "+99894-474-34-74",
        "lat": 41.3500, "lon": 69.3400
    },
    "International School": {
        "manzil": "Inspiring International School xususiy maktabi\nChilonzor tumani, 1-Katta Chilonzor MFY 6-uy\nMo'ljal: Toshkent shahar Prokuraturasi to'g'risida",
        "tel": "+998(77)256-11-77, +998(77)338-11-77",
        "lat": 41.2850, "lon": 69.2030
    },
}

CHOOSE_BRANCH, ENTER_NAME, ENTER_PHONE, ENTER_DATE = range(4)

def add_to_google_sheet(entry):
    if not GOOGLE_SHEET_ID or not Path(GOOGLE_CREDS_FILE).exists():
        return False
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        sheet.append_row([entry['sana'], entry['ism'], entry['telefon'], entry['filial'], datetime.now().strftime("%d.%m.%Y %H:%M"), str(entry['chat_id']), entry.get('username',''), "Yo'q"])
        return True
    except Exception as e:
        print(f"Sheet xato: {e}")
        return False

def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except:
            return []
    return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"🏢 {f}", callback_data=f)] for f in FILIALLAR]
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\nInspiring Education probniy dars botiga xush kelibsiz.\n\nQaysi filialga kelasiz? 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_BRANCH

async def choose_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["filial"] = query.data
    await query.edit_message_text(f"✅ Filial: {query.data}\n\nIsm-sharifingizni kiriting:")
    return ENTER_NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ism"] = update.message.text.strip()
    contact_kb = ReplyKeyboardMarkup([[KeyboardButton("📱 Raqamni yuborish", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Telefon raqamingizni yuboring:", reply_markup=contact_kb)
    return ENTER_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    context.user_data["telefon"] = phone
    await update.message.reply_text("Qaysi kuni kelasiz? Masalan: 15.11", reply_markup=ReplyKeyboardRemove())
    return ENTER_DATE

async def enter_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    m = re.match(r"^(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{4}))?$", text)
    if not m:
        await update.message.reply_text("❌ 15.11 deb yozing")
        return ENTER_DATE
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3) or datetime.now().year)
    try:
        chosen_date = date(year, month, day)
    except:
        await update.message.reply_text("Bunday sana yo'q")
        return ENTER_DATE
    if chosen_date < date.today():
        await update.message.reply_text("O'tgan sana")
        return ENTER_DATE

    chat_id = update.effective_chat.id
    username = update.effective_user.username or ""
    filial_name = context.user_data["filial"]
    filial_data = FILIALLAR[filial_name]

    data = load_data()
    entry = {"chat_id": chat_id, "username": username, "ism": context.user_data["ism"], "telefon": context.user_data["telefon"], "filial": filial_name, "sana": chosen_date.isoformat(), "eslatildi": False, "created_at": datetime.now().isoformat()}
    data.append(entry)
    save_data(data)
    add_to_google_sheet(entry)

    await update.message.reply_text(
        f"✅ Muvaffaqiyatli yozildingiz!\n\n"
        f"👤 Ism: {entry['ism']}\n"
        f"🏢 Filial: {filial_name}\n"
        f"📅 Sana: {chosen_date.strftime('%d.%m.%Y')}\n\n"
        f"📍 {filial_data['manzil']}\n"
        f"☎️ {filial_data['tel']}\n\n"
        f"🔔 Ertaga kechqurun 19:00 da eslatma yuboramiz."
    )
    
    # Lokatsiyani yuborish
    try:
        await context.bot.send_location(chat_id=chat_id, latitude=filial_data["lat"], longitude=filial_data["lon"])
        await update.message.reply_text(f"📍 {filial_name} filialining lokatsiyasi 👆\nBosib yo'nalishni oling.")
    except Exception as e:
        print(f"Lokatsiya xato: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. /start bosing.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def royxat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_IDS and update.effective_chat.id not in ADMIN_CHAT_IDS:
        return
    data = [d for d in load_data() if date.fromisoformat(d["sana"]) >= date.today()]
    if not data:
        await update.message.reply_text("Hozircha yo'q")
        return
    lines = [f"{d['sana']} — {d['ism']} ({d['telefon']}) — {d['filial']}" for d in data]
    await update.message.reply_text("\n".join(lines))

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    changed = False
    for e in data:
        if e["sana"] == tomorrow and not e["eslatildi"]:
            try:
                fd = FILIALLAR.get(e["filial"], {})
                await context.bot.send_message(
                    e["chat_id"],
                    f"🔔 *Ertaga probniy dars!*\n\n"
                    f"Hurmatli {e['ism']}, siz ertaga \"Inspiring Education\" "
                    f"{e['filial']} filialiga probniy darsga yozilgansiz.\n\n"
                    f"📅 Sana: {date.fromisoformat(e['sana']).strftime('%d.%m.%Y')}\n"
                    f"📍 {fd.get('manzil','')}\n"
                    f"☎️ {fd.get('tel','')}\n\n"
                    f"Iltimos, o'z vaqtida keling! Sizni kutib qolamiz 😊",
                    parse_mode="Markdown"
                )
                if fd.get("lat"):
                    await context.bot.send_location(chat_id=e["chat_id"], latitude=fd["lat"], longitude=fd["lon"])
                e["eslatildi"] = True
                changed = True
            except Exception as ex:
                print(f"Eslatma xato: {ex}")
    if changed:
        save_data(data)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_BRANCH: [CallbackQueryHandler(choose_branch)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, enter_phone)],
            ENTER_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_date)],
        },
        fallbacks=[CommandHandler("bekor", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("royxat", royxat))
    try:
        import pytz
        tz = pytz.timezone("Asia/Tashkent")
        app.job_queue.run_daily(send_reminders, time=time(hour=19, minute=0, tzinfo=tz))
    except:
        app.job_queue.run_daily(send_reminders, time=time(hour=19, minute=0))
    print("Bot ishga tushdi - 12 filial, lokatsiya bilan")
    app.run_polling()

if __name__ == "__main__":
    main()
