import logging
import re
import os
import json
import asyncio
from flask import Flask, request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ============ KONFIGURATSIYA ============
TOKEN = "8948673778:AAGbL1gDl1tFtW6VO2ACoVJQCUxOvgw7kFE"
GROUP_ID = -1003521238585
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ IN-MEMORY STATE ============
# Har bir foydalanuvchi uchun holat va ma'lumotlar
user_states = {}   # {user_id: "state_name"}
user_data_store = {}  # {user_id: {...}}

# Holatlar
STATE_MAIN = "main"
STATE_CHOOSING_TO = "choosing_to"
STATE_ENTERING_NAME = "entering_name"
STATE_ENTERING_PHONE = "entering_phone"
STATE_SENDING_LOCATION = "sending_location"

# ============ FLASK APP ============
flask_app = Flask(__name__)

# ============ TELEGRAM APP (global) ============
ptb_app = Application.builder().token(TOKEN).build()

# ============ KLAVIATURALAR ============
def get_main_menu():
    keyboard = [
        [KeyboardButton("🚖 Andijondan 🚖")],
        [KeyboardButton("🚖 Marhamatdan 🚖")],
        [KeyboardButton("📞 Biz bilan bog'lanish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_menu():
    return ReplyKeyboardMarkup([["⬅️ Asosiy menyu"]], resize_keyboard=True)

def get_location_menu():
    location_button = KeyboardButton("📍 Lokatsiya yuborish", request_location=True)
    return ReplyKeyboardMarkup([[location_button], ["⬅️ Asosiy menyu"]], resize_keyboard=True)

def get_confirmation_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_{user_id}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_{user_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_buttons(user_id):
    keyboard = [
        [InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{user_id}")],
        [InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{user_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ HANDLERS ============
async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    user_states[user_id] = STATE_MAIN
    user_data_store[user_id] = {}
    await update.message.reply_text(
        f"🚕 *Andijon Marhamat Taksi* 🚕\n\n"
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        f"Quyidagi menyudan kerakli joyni tanlang:",
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )

async def chatid(update: Update, context):
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: `{chat.id}`\nTuri: {chat.type}", parse_mode='Markdown')

async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text or ""
    state = user_states.get(user_id, STATE_MAIN)

    # Asosiy menyuga qaytish
    if text == "⬅️ Asosiy menyu":
        user_states[user_id] = STATE_MAIN
        user_data_store[user_id] = {}
        await update.message.reply_text("Asosiy menyu:", reply_markup=get_main_menu())
        return

    # ---- MAIN STATE ----
    if state == STATE_MAIN:
        if text in ["🚖 Andijondan 🚖", "🚖 Marhamatdan 🚖"]:
            from_loc = text.replace("🚖 ", "").replace(" 🚖", "")
            user_data_store[user_id] = {"from_location": from_loc}
            user_states[user_id] = STATE_CHOOSING_TO
            await update.message.reply_text(
                f"📍 *{from_loc}* tanlandi!\n\nQayerga borasiz? Manzilni yozib yuboring:",
                reply_markup=get_back_menu(),
                parse_mode='Markdown'
            )
        elif text == "📞 Biz bilan bog'lanish":
            await update.message.reply_text(
                "📞 *Biz bilan bog'lanish:*\n\n"
                "📱 Telefon: +998 90 123 45 67\n"
                "📧 Email: andijonmarhamat@gmail.com\n"
                "📍 Manzil: Andijon shahar, Navoiy ko'chasi 12\n\n"
                "🕐 Ish vaqti: 24/7",
                parse_mode='Markdown'
            )

    # ---- CHOOSING TO STATE ----
    elif state == STATE_CHOOSING_TO:
        user_data_store[user_id]['destination'] = text
        user_states[user_id] = STATE_ENTERING_NAME
        await update.message.reply_text(
            f"📍 Manzil: *{text}* qabul qilindi!\n\nIsmingizni yozing:",
            reply_markup=get_back_menu(),
            parse_mode='Markdown'
        )

    # ---- ENTERING NAME STATE ----
    elif state == STATE_ENTERING_NAME:
        user_data_store[user_id]['name'] = text
        user_states[user_id] = STATE_ENTERING_PHONE
        await update.message.reply_text(
            f"👤 Ism: *{text}* qabul qilindi!\n\nTelefon raqamingizni yuboring:\n(Masalan: +998901234567)",
            reply_markup=get_back_menu(),
            parse_mode='Markdown'
        )

    # ---- ENTERING PHONE STATE ----
    elif state == STATE_ENTERING_PHONE:
        phone = re.sub(r'[^0-9+]', '', text)
        if len(phone) < 5:
            await update.message.reply_text(
                "❌ Telefon raqami noto'g'ri! Qaytadan yozing:\nMasalan: *+998901234567*",
                parse_mode='Markdown'
            )
            return
        user_data_store[user_id]['phone'] = phone
        user_states[user_id] = STATE_SENDING_LOCATION
        await update.message.reply_text(
            f"📱 Telefon: *{phone}* qabul qilindi!\n\n📍 Iltimos, lokatsiyangizni yuboring:",
            reply_markup=get_location_menu(),
            parse_mode='Markdown'
        )

    # ---- SENDING LOCATION STATE ----
    elif state == STATE_SENDING_LOCATION:
        await update.message.reply_text("📍 Iltimos, lokatsiyangizni yuboring (pastdagi tugmani bosing).", reply_markup=get_location_menu())

async def handle_location(update: Update, context):
    user_id = update.effective_user.id
    state = user_states.get(user_id, STATE_MAIN)

    if state != STATE_SENDING_LOCATION:
        return

    location = update.message.location
    user_data_store[user_id]['latitude'] = location.latitude
    user_data_store[user_id]['longitude'] = location.longitude
    user_states[user_id] = STATE_MAIN

    data = user_data_store[user_id]
    confirm_text = (
        f"📋 *Buyurtma ma'lumotlari:*\n\n"
        f"🚖 Qayerdan: {data.get('from_location')}\n"
        f"📍 Qayerga: {data.get('destination')}\n"
        f"👤 Ism: {data.get('name')}\n"
        f"📱 Telefon: {data.get('phone')}\n\n"
        f"✅ Buyurtmani tasdiqlaysizmi?"
    )
    await update.message.reply_text(
        confirm_text,
        reply_markup=get_confirmation_keyboard(user_id),
        parse_mode='Markdown'
    )
    await update.message.reply_text("Javobingizni kutyapman...", reply_markup=get_main_menu())

async def handle_confirm(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    data = user_data_store.get(user_id)

    if not data or 'latitude' not in data:
        await query.edit_message_text("❌ Ma'lumotlar topilmadi. Qaytadan /start bosing.")
        return

    order_caption = (
        f"🚕 *YANGI BUYURTMA!* 🚕\n\n"
        f"👤 *Mijoz:* {data.get('name')}\n"
        f"📱 *Telefon:* [{data.get('phone')}](tel:{data.get('phone')})\n"
        f"🚖 *Qayerdan:* {data.get('from_location')}\n"
        f"📍 *Qayerga:* {data.get('destination')}\n"
        f"🔗 *Profil:* [Mijoz profili](tg://user?id={user_id})"
    )

    try:
        await context.bot.send_venue(
            chat_id=GROUP_ID,
            latitude=data['latitude'],
            longitude=data['longitude'],
            title=f"Mijoz: {data.get('name')} | {data.get('phone')}",
            address=f"{data.get('from_location')} → {data.get('destination')}",
        )
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=order_caption,
            parse_mode='Markdown',
            reply_markup=get_admin_buttons(user_id)
        )
        await query.edit_message_text(
            "✅ *Buyurtmangiz qabul qilindi!* ✅\n\n"
            "Tez orada haydovchi siz bilan bog'lanadi.\n"
            "⏳ Kuting, 5-10 daqiqa ichida yetib boramiz!\n\n"
            "🚕 *Andijon Marhamat Taksi*\n"
            "📞 Aloqa: +998 90 123 45 67",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text(f"❌ Xatolik: {e}")

async def handle_cancel_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    user_data_store.pop(user_id, None)
    user_states[user_id] = STATE_MAIN
    await query.edit_message_text("❌ *Buyurtma bekor qilindi!*", parse_mode='Markdown')

async def handle_accept_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    admin = update.effective_user
    driver_name = admin.first_name
    if admin.last_name:
        driver_name += f" {admin.last_name}"
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ *Buyurtmangiz qabul qilindi!* ✅\n\n"
                 f"🚖 *Haydovchi:* [{driver_name}](tg://user?id={admin.id})\n"
                 f"📞 Aloqa: Tez orada bog'lanadi\n\n"
                 f"⏳ Kuting, 5-10 daqiqa ichida yetib boramiz!\n"
                 f"🚕 *Andijon Marhamat Taksi*",
            parse_mode='Markdown'
        )
        await query.edit_message_text(
            f"{query.message.text}\n\n✅ *Qabul qilindi!*\n👤 Haydovchi: {driver_name}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error: {e}")

async def handle_reject_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    admin = update.effective_user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ *Kechirasiz, buyurtmangiz rad etildi!* ❌\n\n"
                 "Iltimos, qayta urinib ko'ring.\n\n"
                 "🚕 *Andijon Marhamat Taksi*",
            parse_mode='Markdown'
        )
        await query.edit_message_text(
            f"{query.message.text}\n\n❌ *Rad etildi!*\n👤 Rad etgan: {admin.first_name}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error: {e}")

# ============ HANDLERS QO'SHISH ============
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(CommandHandler("chatid", chatid))
ptb_app.add_handler(MessageHandler(filters.LOCATION, handle_location))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
ptb_app.add_handler(CallbackQueryHandler(handle_confirm, pattern="^confirm_"))
ptb_app.add_handler(CallbackQueryHandler(handle_cancel_order, pattern="^cancel_"))
ptb_app.add_handler(CallbackQueryHandler(handle_accept_order, pattern="^accept_"))
ptb_app.add_handler(CallbackQueryHandler(handle_reject_order, pattern="^reject_"))

# ============ FLASK ROUTES ============
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def process():
        async with ptb_app:
            update = Update.de_json(data, ptb_app.bot)
            await ptb_app.process_update(update)
    loop.run_until_complete(process())
    return Response("ok", status=200)

@flask_app.route("/", methods=["GET"])
def index():
    return "Andijon Marhamat Taksi Bot ishlayapti!", 200

@flask_app.route("/set_webhook", methods=["GET"])
def set_webhook():
    async def _set():
        async with ptb_app:
            url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
            await ptb_app.bot.set_webhook(url=url)
            return url
    loop = asyncio.new_event_loop()
    url = loop.run_until_complete(_set())
    return f"Webhook o'rnatildi: {url}", 200

# ============ LOCAL RUN ============
if __name__ == "__main__":
    if WEBHOOK_URL:
        flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    else:
        # Local polling
        import sys
        from telegram.ext import Application
        app2 = Application.builder().token(TOKEN).build()
        app2.add_handler(CommandHandler("start", start))
        app2.add_handler(CommandHandler("chatid", chatid))
        app2.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app2.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app2.add_handler(CallbackQueryHandler(handle_confirm, pattern="^confirm_"))
        app2.add_handler(CallbackQueryHandler(handle_cancel_order, pattern="^cancel_"))
        app2.add_handler(CallbackQueryHandler(handle_accept_order, pattern="^accept_"))
        app2.add_handler(CallbackQueryHandler(handle_reject_order, pattern="^reject_"))
        print("Bot polling rejimida ishga tushdi...")
        app2.run_polling(allowed_updates=Update.ALL_TYPES)
