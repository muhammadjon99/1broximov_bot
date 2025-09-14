import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Loglarni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Admin ID (boshlang'ichda bo'sh)
ADMIN_ID = 6829390664

# Bazani yaratish
def init_db():
    conn = sqlite3.connect('kino.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS kinolar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            link TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Start buyrug'i — asosiy menyuni chiqaradi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🔍 Kino Qidirish", callback_data="search")],
        [InlineKeyboardButton("🎬 Barcha Kinolar", callback_data="list_all")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Salom! Men kino botman.\n\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=reply_markup
    )

# Tugma bosilganda ishlaydigan funksiya
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Tugmani bosgan foydalanuvchiga "loading" ko'rsatmaydi
    
    user_id = update.effective_user.id
    
    if query.data == "search":
        await query.edit_message_text(
            "🔎 Qidirmoqchi bo'lgan kino nomini yozing:\n\n"
            "Misol: Inception, Avengers, O'tkir Hikoyalar"
        )
        context.user_data['awaiting_search'] = True
        
    elif query.data == "list_all":
        await list_all_kinos(query, context)
        
    elif query.data == "admin_panel":
        if user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("➕ Kino Qo'shish", callback_data="add_kino")],
                [InlineKeyboardButton("📋 Barcha Kinolar", callback_data="list_all")],
                [InlineKeyboardButton("🗑 Bazani Tozalash", callback_data="clear_db")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚙️ *Admin Panel*\n\n"
                "Quyidagi amallardan foydalaning:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Siz admin emassiz!")
            
    elif query.data == "add_kino":
        await query.edit_message_text(
            "📥 Yangi kino qo'shish uchun quyidagi formatda yozing:\n\n"
            "`Kino nomi | link`\n\n"
            "Misol:\n`Inception | https://example.com/inception.mp4`"
        )
        context.user_data['awaiting_add'] = True
        
    elif query.data == "clear_db":
        if user_id == ADMIN_ID:
            conn = sqlite3.connect('kino.db')
            c = conn.cursor()
            c.execute("DELETE FROM kinolar")
            conn.commit()
            conn.close()
            await query.edit_message_text("✅ Baza muvaffaqiyatli tozalandi!")
        else:
            await query.edit_message_text("❌ Siz admin emassiz!")
            
    elif query.data == "start":
        await start(update, context)

# Foydalanuvchi matn yozganda (qidiruv yoki kino qo'shish)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Kino qidirish
    if context.user_data.get('awaiting_search'):
        context.user_data['awaiting_search'] = False
        await search_kino(update, context, text)
        return
        
    # Kino qo'shish (faqat admin)
    if context.user_data.get('awaiting_add'):
        context.user_data['awaiting_add'] = False
        if "|" not in text:
            await update.message.reply_text("❌ Noto'g'ri format! Iltimos, `Kino nomi | link` shaklida kiriting.")
            return
        parts = text.split("|", 1)
        kino_nom = parts[0].strip()
        kino_link = parts[1].strip()
        
        if not kino_nom or not kino_link:
            await update.message.reply_text("❌ Nom yoki link bo'sh bo'lmasligi kerak!")
            return
            
        try:
            conn = sqlite3.connect('kino.db')
            c = conn.cursor()
            c.execute("INSERT INTO kinolar (nom, link) VALUES (?, ?)", (kino_nom, kino_link))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ Kino qo'shildi:\n🎬 {kino_nom}\n🔗 {kino_link}")
        except sqlite3.IntegrityError:
            await update.message.reply_text("❌ Bu kino allaqachon mavjud!")
        return

# Kino qidiruv funksiyasi
async def search_kino(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text):
    if not query_text:
        await update.message.reply_text("🔎 So'rov bo'sh!")
        return
        
    conn = sqlite3.connect('kino.db')
    c = conn.cursor()
    c.execute("SELECT nom, link FROM kinolar WHERE nom LIKE ?", ('%' + query_text + '%',))
    results = c.fetchall()
    conn.close()
    
    if results:
        response = "🔍 *Qidiruv natijalari:*\n\n"
        for nom, link in results:
            response += f"🎬 *{nom}*\n🔗 {link}\n\n"
        await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Kino topilmadi.")

# Barcha kinolarni ko'rsatish
async def list_all_kinos(query, context):
    conn = sqlite3.connect('kino.db')
    c = conn.cursor()
    c.execute("SELECT nom, link FROM kinolar ORDER BY nom")
    results = c.fetchall()
    conn.close()
    
    if results:
        response = "🎬 *Barcha kinolar:*\n\n"
        for nom, link in results:
            response += f"🎬 *{nom}*\n🔗 {link}\n\n"
        await query.edit_message_text(response, parse_mode='Markdown')
    else:
        await query.edit_message_text("📦 Hozircha hech qanday kino yo'q.")

# Adminni o'rnatish
async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    if ADMIN_ID is None:
        ADMIN_ID = user_id
        await update.message.reply_text(
            "✅ Siz botning birinchi foydalanuvchisi bo'ldingiz! Siz endi admin siz.\n"
            "Endi boshqalar /setadmin buyrug'ini ishlatmasin!"
        )
        logger.info(f"Admin ID o'rnatildi: {ADMIN_ID}")
    else:
        await update.message.reply_text(f"Admin allaqachon o'rnatilgan: {ADMIN_ID}")

# Xatoliklar uchun handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Asosiy funksiya
def main():
    init_db()  # Bazani yaratish
    TOKEN = ""  # 👈 O'ZINGIZNING BOT TOKENINGIZNI KIRITING!
    
    application = Application.builder().token(TOKEN).build()

    # Buyruqlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setadmin", set_admin))

    # Tugmalar
    application.add_handler(CallbackQueryHandler(button_handler))

    # Matn qabul qilish
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Xatoliklar
    application.add_error_handler(error_handler)

    print("🚀 Mukammal Kino Bot ishga tushdi...")
    application.run_polling()

if __name__ == '__main__':
    main()













