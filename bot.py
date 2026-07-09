import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ============ KONFIGURATSIYA ============
TOKEN = "8948673778:AAGbL1gDl1tFtW6VO2ACoVJQCUxOvgw7kFE"
GROUP_ID = -1003521238585  # Guruh ID si
ADMIN_IDS = [8948673778]  # Adminlar ID si (o'zingizniki)

# ============ LOGING ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ============ MA'LUMOTLAR ============
user_data_store = {}  # Foydalanuvchi ma'lumotlarini saqlash (Callbacklar uchun)

# ============ Holatlar (States) ============
CHOOSING_FROM, CHOOSING_TO, CUSTOM_TO, ENTERING_INFO, SENDING_LOCATION = range(5)

# ============ KLAVIATURALAR ============
def get_main_menu():
    """Asosiy menyu"""
    keyboard = [
        [KeyboardButton("🚖 Andijondan 🚖")],
        [KeyboardButton("🚖 Marhamatdan 🚖")],
        [KeyboardButton("📞 Biz bilan bog'lanish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_where_to_go():
    """Qayerga borish menyusi"""
    keyboard = [
        [KeyboardButton("🚉 Vokzal"), KeyboardButton("🏥 Kasalxona")],
        [KeyboardButton("🏢 Markaziy Bozor"), KeyboardButton("🏫 Universitet")],
        [KeyboardButton("✈️ Aeroport"), KeyboardButton("📝 Boshqa manzil")],
        [KeyboardButton("⬅️ Asosiy menyuga qaytish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_confirmation_keyboard(user_id):
    """Tasdiqlash tugmalari"""
    keyboard = [
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_{user_id}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_{user_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_buttons(user_id):
    """Admin uchun tugmalar"""
    keyboard = [
        [InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{user_id}")],
        [InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{user_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ KOMANDALAR ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"🚕 *Andijon Marhamat Taksi* 🚕\n\n"
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        f"Men sizning shaxsiy taksi botingizman.\n"
        f"Quyidagi menyudan kerakli joyni tanlang:",
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )
    return CHOOSING_FROM

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Biz bilan bog'lanish:*\n\n"
        "📱 Telefon: +998 90 123 45 67\n"
        "📧 Email: andijonmarhamat@gmail.com\n"
        "📍 Manzil: Andijon shahar, Navoiy ko'chasi 12\n\n"
        "🕐 Ish vaqti: 24/7",
        parse_mode='Markdown'
    )
    return CHOOSING_FROM

async def choose_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qayerdan ketishni tanlash"""
    text = update.message.text
    context.user_data['from_location'] = text.replace("🚖 ", "").replace(" 🚖", "")
    
    await update.message.reply_text(
        f"📍 *{context.user_data['from_location']}* tanlandi!\n\n"
        "Qayerga borasiz? Manzilni tanlang:",
        reply_markup=get_where_to_go(),
        parse_mode='Markdown'
    )
    return CHOOSING_TO

async def choose_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qayerga borishni tanlash"""
    text = update.message.text
    
    if text == "⬅️ Asosiy menyuga qaytish":
        await update.message.reply_text("Asosiy menyu:", reply_markup=get_main_menu())
        return CHOOSING_FROM
        
    if text == "📝 Boshqa manzil":
        await update.message.reply_text(
            "✍️ Iltimos, manzilni to'liq yozib yuboring:\n"
            "(Masalan: Navoiy ko'chasi, 12-uy)",
            reply_markup=ReplyKeyboardMarkup([["⬅️ Orqaga"]], resize_keyboard=True)
        )
        return CUSTOM_TO
    
    context.user_data['destination'] = text.replace("🚉 ", "").replace("🏥 ", "").replace("🏢 ", "").replace("🏫 ", "").replace("✈️ ", "")
    
    await update.message.reply_text(
        f"📍 Manzil: *{context.user_data['destination']}* qabul qilindi!\n\n"
        "Endi ismingiz va telefon raqamingizni yuboring:\n"
        "(Masalan: Alisher 90 123 45 67)",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Orqaga"]], resize_keyboard=True),
        parse_mode='Markdown'
    )
    return ENTERING_INFO

async def custom_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boshqa manzilni kiritish"""
    text = update.message.text
    if text == "⬅️ Orqaga":
        await update.message.reply_text("Qayerga borasiz?", reply_markup=get_where_to_go())
        return CHOOSING_TO
        
    context.user_data['destination'] = text
    
    await update.message.reply_text(
        f"📍 Manzil: *{text}* qabul qilindi!\n\n"
        "Endi ismingiz va telefon raqamingizni yuboring:\n"
        "(Masalan: Alisher 90 123 45 67)",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Orqaga"]], resize_keyboard=True),
        parse_mode='Markdown'
    )
    return ENTERING_INFO

async def enter_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ism va telefonni qabul qilish"""
    text = update.message.text
    if text == "⬅️ Orqaga":
        await update.message.reply_text("Qayerga borasiz?", reply_markup=get_where_to_go())
        return CHOOSING_TO
        
    parts = text.split()
    if len(parts) >= 2:
        name = " ".join(parts[:-1])
        phone = parts[-1]
        phone = re.sub(r'[^0-9+]', '', phone)
    else:
        await update.message.reply_text(
            "❌ Iltimos, ismingiz va telefon raqamingizni to'g'ri yozing:\n"
            "Masalan: *Alisher +998901234567*",
            parse_mode='Markdown'
        )
        return ENTERING_INFO
    
    context.user_data['name'] = name
    context.user_data['phone'] = phone
    
    location_button = KeyboardButton("📍 Lokatsiya yuborish", request_location=True)
    keyboard = [[location_button], ["⬅️ Orqaga"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ Ma'lumotlar qabul qilindi!\n\n"
        f"👤 Ism: {name}\n"
        f"📱 Telefon: {phone}\n\n"
        f"📍 Iltimos, lokatsiyangizni yuboring (yoki pastdagi tugmani bosing):",
        reply_markup=reply_markup
    )
    return SENDING_LOCATION

async def send_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lokatsiyani qabul qilish va tasdiqlash so'rash"""
    if update.message.text == "⬅️ Orqaga":
        await update.message.reply_text(
            "Endi ismingiz va telefon raqamingizni yuboring:\n"
            "(Masalan: Alisher 90 123 45 67)",
            reply_markup=ReplyKeyboardMarkup([["⬅️ Orqaga"]], resize_keyboard=True)
        )
        return ENTERING_INFO

    if not update.message.location:
        await update.message.reply_text("Iltimos, lokatsiyangizni yuboring.")
        return SENDING_LOCATION
        
    location = update.message.location
    context.user_data['latitude'] = location.latitude
    context.user_data['longitude'] = location.longitude
    
    user_id = update.effective_user.id
    user_data_store[user_id] = context.user_data.copy()
    
    confirm_text = (
        f"📋 *Buyurtma ma'lumotlari:*\n\n"
        f"🚖 Qayerdan: {context.user_data.get('from_location')}\n"
        f"📍 Qayerga: {context.user_data.get('destination')}\n"
        f"👤 Ism: {context.user_data.get('name')}\n"
        f"📱 Telefon: {context.user_data.get('phone')}\n\n"
        f"✅ Buyurtmani tasdiqlaysizmi?"
    )
    
    await update.message.reply_text(
        confirm_text,
        reply_markup=get_confirmation_keyboard(user_id),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text("Javobingizni kutyapman...", reply_markup=get_main_menu())
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konversatsiyani bekor qilish"""
    await update.message.reply_text("Bekor qilindi. Bosh menyu:", reply_markup=get_main_menu())
    return ConversationHandler.END

# ============ CALLBACK FUNKSIYALAR ============
async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    data = user_data_store.get(user_id)
    
    if not data:
        await query.edit_message_text("❌ Xatolik! Ma'lumotlar topilmadi. Qaytadan /start bosing.")
        return
        
    order_text = (
        f"🚕 *YANGI BUYURTMA!* 🚕\n\n"
        f"👤 *Mijoz:* {data.get('name')}\n"
        f"📱 *Telefon:* {data.get('phone')}\n"
        f"🚖 *Qayerdan:* {data.get('from_location')}\n"
        f"📍 *Qayerga:* {data.get('destination')}\n"
        f"🆔 *ID:* {user_id}\n"
        f"🔗 *Profil:* [Foydalanuvchi profili](tg://user?id={user_id})\n\n"
        f"⬇️ *Buyurtmani qabul qilish yoki rad etish:*"
    )
    
    try:
        # Guruhga yuborish
        msg = await context.bot.send_message(
            chat_id=GROUP_ID,
            text=order_text,
            reply_markup=get_admin_buttons(user_id),
            parse_mode='Markdown'
        )
        
        # Lokatsiyani guruhga yuborish
        await context.bot.send_location(
            chat_id=GROUP_ID,
            latitude=data['latitude'],
            longitude=data['longitude'],
            reply_to_message_id=msg.message_id
        )
        
        await query.edit_message_text(
            f"✅ *Buyurtmangiz qabul qilindi!* ✅\n\n"
            f"Tez orada haydovchi siz bilan bog'lanadi.\n"
            f"⏳ Kuting, 5-10 daqiqa ichida yetib boramiz!\n\n"
            f"🚕 *Andijon Marhamat Taksi*\n"
            f"📞 Aloqa: +998 90 123 45 67",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending order: {e}")
        await query.edit_message_text("❌ Xatolik yuz berdi! Guruhga qo'shilmagan bo'lishim yoki admin huquqim yo'q bo'lishi mumkin.")

async def handle_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    if user_id in user_data_store:
        del user_data_store[user_id]
        
    await query.edit_message_text("❌ *Buyurtma bekor qilindi!*", parse_mode='Markdown')

async def handle_accept_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    admin = update.effective_user
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ *Buyurtmangiz qabul qilindi!* ✅\n\n"
                 f"🚖 Haydovchi: {admin.first_name}\n"
                 f"📞 Aloqa: Tez orada bog'lanadi\n\n"
                 f"⏳ Kuting, 5-10 daqiqa ichida yetib boramiz!\n"
                 f"🚕 *Andijon Marhamat Taksi*",
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            f"{query.message.text}\n\n"
            f"✅ *Qabul qilindi!*\n"
            f"👤 Haydovchi: {admin.first_name}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error accepting order: {e}")
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Xatolik: Mijoz botni bloklagan bo'lishi mumkin.")

async def handle_reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    admin = update.effective_user
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ *Kechirasiz, bo'sh haydovchilar yo'qligi sababli buyurtmangiz rad etildi!* ❌\n\n"
                 f"Iltimos, birozdan so'ng qayta urinib ko'ring.\n\n"
                 f"🚕 *Andijon Marhamat Taksi*",
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            f"{query.message.text}\n\n"
            f"❌ *Rad etildi!*\n"
            f"👤 Rad etgan: {admin.first_name}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error rejecting order: {e}")
        await query.edit_message_reply_markup(reply_markup=None)

# ============ ASOSIY FUNKSIYA ============
def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^(🚖 Andijondan 🚖|🚖 Marhamatdan 🚖)$'), choose_from)
        ],
        states={
            CHOOSING_FROM: [
                MessageHandler(filters.Regex('^(🚖 Andijondan 🚖|🚖 Marhamatdan 🚖)$'), choose_from),
                MessageHandler(filters.Regex("^📞 Biz bilan bog'lanish$"), handle_contact)
            ],
            CHOOSING_TO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_to)
            ],
            CUSTOM_TO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_to)
            ],
            ENTERING_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_info)
            ],
            SENDING_LOCATION: [
                MessageHandler(filters.LOCATION | (filters.TEXT & ~filters.COMMAND), send_location)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conv), CommandHandler('start', start)]
    )
    
    app.add_handler(conv_handler)
    
    app.add_handler(CallbackQueryHandler(handle_confirm, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(handle_cancel_order, pattern="^cancel_"))
    app.add_handler(CallbackQueryHandler(handle_accept_order, pattern="^accept_"))
    app.add_handler(CallbackQueryHandler(handle_reject_order, pattern="^reject_"))
    
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
