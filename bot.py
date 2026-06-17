import logging
import asyncio
import secrets
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
import json
import os
import html

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration (Environment Variables থেকে ডেটা নেবে, যা সিকিউর)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8825366245:AAEX3Bf2A5wV-KYMhg83jVmOXekRCaWsO3Q")
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "6992010963"))
except ValueError:
    ADMIN_ID = 6992010963

BOT_USERNAME = os.getenv("BOT_USERNAME", "Bbbbbbbfurhr_bot")

# CHANNELS list (এখানে আপনার চ্যানেলের ইউজারনেম দিন, কমা দিয়ে আলাদা করুন)
CHANNELS = ["@knhjjjo", "@smmpanelotp"] 

# Files storage
FILES_DATA_FILE = "files_data.json"
LINKS_DATA_FILE = "links_data.json"

files_data = {}
links_data = {}

# Initialize data files
if os.path.exists(FILES_DATA_FILE):
    with open(FILES_DATA_FILE, 'r') as f:
        try: files_data = json.load(f)
        except json.JSONDecodeError: files_data = {}

if os.path.exists(LINKS_DATA_FILE):
    with open(LINKS_DATA_FILE, 'r') as f:
        try: links_data = json.load(f)
        except json.JSONDecodeError: links_data = {}

def generate_unique_id(): return secrets.token_urlsafe(8)
def generate_link_id(): return secrets.token_urlsafe(6)

def save_files_data():
    with open(FILES_DATA_FILE, 'w') as f: json.dump(files_data, f)

def save_links_data():
    with open(LINKS_DATA_FILE, 'w') as f: json.dump(links_data, f)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("📝 Host Text"), KeyboardButton("📁 Host File")],
        [KeyboardButton("🔗 Generate Link"), KeyboardButton("📊 Files List")],
        [KeyboardButton("📢 Broadcast"), KeyboardButton("📋 Content Manager")],
        [KeyboardButton("📈 Stats"), KeyboardButton("❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_keyboard():
    keyboard = [
        [KeyboardButton("/start")],
        [KeyboardButton("📁 My Files"), KeyboardButton("❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if args and len(args) > 0:
        await handle_file_link(update, context, args[0])
        return
    
    reply_markup = get_admin_keyboard() if user_id == ADMIN_ID else get_user_keyboard()
    is_subscribed = await check_subscription(user_id, context)
    welcome_text = f"👋 Welcome {update.effective_user.first_name}!\n\n"
    
    if is_subscribed:
        welcome_text += "✅ You have access to all channels.\nUse the menu below to access files."
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        welcome_text += "📋 Please join all channels to access files."
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        await ask_for_subscription(update, context)

async def handle_file_link(update: Update, context: ContextTypes.DEFAULT_TYPE, link_id: str):
    user_id = update.effective_user.id
    if link_id not in links_data or links_data[link_id]["file_id"] not in files_data:
        await update.message.reply_text("❌ Link Invalid or File Not Found!", reply_markup=get_user_keyboard())
        return
    
    file_id = links_data[link_id]["file_id"]
    is_subscribed = await check_subscription(user_id, context)
    
    if is_subscribed:
        await send_file_to_user(update, file_id)
        files_data[file_id]["downloads"] = files_data[file_id].get("downloads", 0) + 1
        
        user_files = files_data[file_id].setdefault("accessed_by", {})
        if str(user_id) not in user_files:
            user_files[str(user_id)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_files_data()
    else:
        await update.message.reply_text(
            f"📋 <b>File Access Required!</b>\n\n📁 File: {files_data[file_id].get('name', 'Unnamed')}\n\nYou need to join all channels first.",
            parse_mode=ParseMode.HTML
        )
        await ask_for_subscription_with_file(update, context, link_id)

async def ask_for_subscription_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE, link_id: str):
    keyboard = [[InlineKeyboardButton(f"📢 Channel {i} - {c.replace('@', '')}", url=f"https://t.me/{c.replace('@', '')}")] for i, c in enumerate(CHANNELS, 1)]
    keyboard.append([InlineKeyboardButton("✅ Verify & Get File", callback_data=f"verify_file_{link_id}")])
    await update.message.reply_text("📋 <b>Join all channels to get the file:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def ask_for_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"📢 Channel {i} - {c.replace('@', '')}", url=f"https://t.me/{c.replace('@', '')}")] for i, c in enumerate(CHANNELS, 1)]
    keyboard.append([InlineKeyboardButton("✅ Verify Subscription", callback_data="verify_subscription")])
    await update.message.reply_text("📋 <b>Join all channels to access files:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        for channel in CHANNELS:
            chat_member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status in ['left', 'kicked']: return False
        return True
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        return False

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "verify_subscription":
        if await check_subscription(user_id, context):
            await query.edit_message_text("✅ <b>Verified!</b> Use /start to continue.", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("❌ <b>You haven't joined all channels!</b>", parse_mode=ParseMode.HTML)
    
    elif query.data.startswith("verify_file_"):
        link_id = query.data.replace("verify_file_", "")
        if link_id not in links_data: return
        
        if await check_subscription(user_id, context):
            file_id = links_data[link_id]["file_id"]
            await query.edit_message_text("✅ <b>Access Granted!</b> Sending file...", parse_mode=ParseMode.HTML)
            await send_file_to_user(update, file_id, from_callback=True)
            
            files_data[file_id]["downloads"] = files_data[file_id].get("downloads", 0) + 1
            files_data[file_id].setdefault("accessed_by", {})[str(user_id)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_files_data()
        else:
            await query.edit_message_text("❌ <b>Join ALL channels first!</b>", parse_mode=ParseMode.HTML)

async def send_file_to_user(update, file_id: str, from_callback=False):
    file_data = files_data[file_id]
    target = update.callback_query.message if from_callback else update.message
    try:
        caption = f"📁 <b>{file_data.get('name', 'File')}</b>\n\n{html.escape(file_data.get('caption', ''))}"
        if file_data["file_type"] == "photo": await target.reply_photo(photo=file_data["file_id"], caption=caption, parse_mode=ParseMode.HTML)
        elif file_data["file_type"] == "video": await target.reply_video(video=file_data["file_id"], caption=caption, parse_mode=ParseMode.HTML)
        elif file_data["file_type"] == "document": await target.reply_document(document=file_data["file_id"], caption=caption, parse_mode=ParseMode.HTML)
        elif file_data["file_type"] == "text": await target.reply_text(f"📝 <b>{file_data.get('name')}</b>\n\n{caption}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Send error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id == ADMIN_ID:
        if text == "📝 Host Text":
            await update.message.reply_text("📝 Send text:\nFormat: First line = filename, Rest = content")
            context.user_data['awaiting_text'] = True
        elif text == "📁 Host File":
            await update.message.reply_text("📁 Send file with caption: <code>/host [filename] [caption]</code>", parse_mode=ParseMode.HTML)
        elif text == "🔗 Generate Link":
            if not files_data: return await update.message.reply_text("📭 No files hosted.")
            keyboard = [[InlineKeyboardButton(f"📁 {f['name'][:20]}", callback_data=f"genlink_{fid}")] for fid, f in list(files_data.items())[:10]]
            await update.message.reply_text("🔗 <b>Select file:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        elif text == "📊 Files List":
            if not files_data: return await update.message.reply_text("📭 Empty.")
            out = "".join([f"• <b>{f['name']}</b> ({f['file_type']}) | 📥 {f.get('downloads',0)}\n" for f in files_data.values()])
            await update.message.reply_text(out, parse_mode=ParseMode.HTML)
        elif text == "📈 Stats":
            total_dl = sum(f.get('downloads', 0) for f in files_data.values())
            await update.message.reply_text(f"📊 Files: {len(files_data)}\n🔗 Links: {len(links_data)}\n📥 Downloads: {total_dl}")
        elif text == "📋 Content Manager":
            keyboard = [[InlineKeyboardButton("🗑️ Clear Files", callback_data="cls_files"), InlineKeyboardButton("🗑️ Clear Links", callback_data="cls_links")]]
            await update.message.reply_text("📋 <b>Manager:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        elif context.user_data.get('awaiting_text'):
            lines = text.split('\n')
            fname = lines[0][:40] if lines[0].strip() else "Text_File"
            fid = generate_unique_id()
            files_data[fid] = {"name": fname, "caption": text, "file_type": "text", "file_id": None, "downloads": 0, "accessed_by": {}}
            save_files_data()
            context.user_data['awaiting_text'] = False
            lid = generate_link_id()
            links_data[lid] = {"file_id": fid}
            save_links_data()
            await update.message.reply_text(f"✅ Hosted!\n🔗 Link: https://t.me/{BOT_USERNAME}?start={lid}")
    else:
        if text == "📁 My Files":
            user_files = [f for f in files_data.values() if str(user_id) in f.get("accessed_by", {})]
            if not user_files: return await update.message.reply_text("📭 No history found.")
            await update.message.reply_text("📁 <b>Your Files:</b>\n" + "".join([f"• {f['name']}\n" for f in user_files]), parse_mode=ParseMode.HTML)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not update.message.caption: return
    msg = update.message
    if msg.caption.startswith('/host'):
        parts = msg.caption.split(' ', 2)
        fname = parts[1] if len(parts) > 1 else "File"
        cap = parts[2] if len(parts) > 2 else ""
        
        if msg.photo: fid, ftype = msg.photo[-1].file_id, "photo"
        elif msg.video: fid, ftype = msg.video.file_id, "video"
        elif msg.document: fid, ftype = msg.document.file_id, "document"
        else: return
        
        uid = generate_unique_id()
        files_data[uid] = {"name": fname, "caption": cap, "file_type": ftype, "file_id": fid, "downloads": 0, "accessed_by": {}}
        save_files_data()
        lid = generate_link_id()
        links_data[lid] = {"file_id": uid}
        save_links_data()
        await msg.reply_text(f"✅ Hosted!\n🔗 Link: https://t.me/{BOT_USERNAME}?start={lid}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("genlink_"):
        fid = query.data.replace("genlink_", "")
        if fid not in files_data: return
        lid = generate_link_id()
        links_data[lid] = {"file_id": fid}
        save_links_data()
        await query.edit_message_text(f"✅ Link:\n🔗 https://t.me/{BOT_USERNAME}?start={lid}")
    elif query.data == "cls_files":
        files_data.clear(); save_files_data(); await query.edit_message_text("Deleted Files.")
    elif query.data == "cls_links":
        links_data.clear(); save_links_data(); await query.edit_message_text("Deleted Links.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^(verify_subscription|verify_file_)"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_file))
    print("🤖 Bot started successfully...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()