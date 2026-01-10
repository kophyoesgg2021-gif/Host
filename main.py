import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import logging
import threading
import re
import sys
import atexit
import requests
import random
import string
import json

# --- Flask Keep Alive ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "⚡ DEV-PAI Core - Cloud Execution Platform"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🟣 Flask Keep-Alive server started.")
# --- End Flask Keep Alive ---

# --- Configuration ---
TOKEN = '8340915072:AAGDJ4a4x06-K9eRcAvEjz_UsyJ1fgaMefM'
OWNER_ID = 7259590181
ADMIN_ID = 7259590181
YOUR_USERNAME = '@leostrike223'

# Force Join Settings
FORCE_CHANNEL = '@leolotterydev'
FORCE_GROUP = '@devpaitrxsignal' 

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
PAI_DIR = os.path.join(BASE_DIR, 'pai_data')
DATABASE_PATH = os.path.join(PAI_DIR, 'pai_host.db')

# File upload limits
FREE_USER_LIMIT = 1
PREMIUM_USER_LIMIT = 999
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(PAI_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
force_join_enabled = True  
broadcast_messages = {} 

# Supported files
SUPPORTED_EXTENSIONS = {
    '.py': '🐍 Python', '.java': '☕ Java', '.html': '🌐 HTML', '.htm': '🌐 HTML',
    '.js': '📜 JavaScript', '.css': '🎨 CSS', '.txt': '📄 Text', '.json': '📋 JSON',
    '.xml': '📊 XML', '.php': '🐘 PHP', '.c': '🔧 C', '.cpp': '⚙️ C++', '.cs': '💠 C#',
    '.rb': '💎 Ruby', '.go': '🚀 Go', '.rs': '🦀 Rust', '.md': '📝 Markdown',
    '.yaml': '⚙️ YAML', '.yml': '⚙️ YAML', '.sql': '🗄️ SQL', '.sh': '🐚 Shell',
    '.bat': '🪟 Batch', '.ps1': '💻 PowerShell', '.r': '📊 R', '.swift': '🐦 Swift',
    '.kt': '🤖 Kotlin', '.scala': '⚡ Scala', '.pl': '🐪 Perl', '.lua': '🌙 Lua',
    '.ts': '📘 TypeScript', '.jsx': '⚛️ React JSX', '.tsx': '⚛️ React TSX',
    '.vue': '🟢 Vue', '.svelte': '✨ Svelte', '.dart': '🎯 Dart', '.scss': '💅 SCSS',
    '.less': '🎨 Less', '.styl': '💄 Stylus', '.coffee': '☕ CoffeeScript'
}

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db():
    """initialize the database with required tables"""
    logger.info(f"🛢️ Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''create table if not exists users
                     (user_id integer primary key, 
                      username text, 
                      first_name text, 
                      last_name text, 
                      join_date timestamp default current_timestamp,
                      verified integer default 0,
                      key_used text,
                      key_used_date timestamp)''')
        
        c.execute('''create table if not exists subscriptions
                     (user_id integer primary key, expiry text, 
                      file_limit integer default 999,
                      redeemed_date timestamp default current_timestamp)''')
        
        c.execute('''create table if not exists user_files
                     (file_id integer primary key autoincrement,
                      user_id integer,
                      username text,
                      chat_id integer,
                      file_name text, 
                      file_type text, 
                      file_path text,
                      original_filename text,
                      file_size integer,
                      upload_date timestamp default current_timestamp,
                      is_active integer default 1,
                      FOREIGN KEY (user_id) REFERENCES users(user_id))''')
        
        c.execute('''create table if not exists active_users
                     (user_id integer primary key)''')
        
        c.execute('''create table if not exists admins
                     (user_id integer primary key)''')
        
        c.execute('''create table if not exists subscription_keys
                     (key_value text primary key,
                      created_by integer,
                      created_date timestamp default current_timestamp,
                      days_valid integer,
                      max_uses integer default 1,
                      used_count integer default 0,
                      file_limit integer default 999,
                      is_active integer default 1,
                      used_by_user integer,
                      used_date timestamp)''')
        
        c.execute('''create table if not exists key_usage
                     (key_value text, user_id integer, used_date timestamp default current_timestamp,
                      primary key (key_value, user_id))''')
        
        c.execute('''create table if not exists bot_settings
                     (setting_key text primary key, setting_value text)''')
        
        c.execute('insert or ignore into bot_settings (setting_key, setting_value) values (?, ?)', 
                 ('free_user_limit', str(FREE_USER_LIMIT)))
        c.execute('insert or ignore into bot_settings (setting_key, setting_value) values (?, ?)', 
                 ('force_join_enabled', '1'))
        
        c.execute('insert or ignore into admins (user_id) values (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('insert or ignore into admins (user_id) values (?)', (ADMIN_ID,))
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}", exc_info=True)

def load_data():
    """load data from database into memory"""
    logger.info("📥 Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()

        c.execute('select user_id, expiry, file_limit from subscriptions')
        for user_id, expiry, file_limit in c.fetchall():
            try:
                user_subscriptions[user_id] = {
                    'expiry': datetime.fromisoformat(expiry),
                    'file_limit': file_limit if file_limit else 999
                }
            except ValueError:
                logger.warning(f"⚠️ Invalid expiry date format for user {user_id}: {expiry}. Skipping.")

        c.execute('select user_id, file_name, file_type, file_path from user_files')
        for user_id, file_name, file_type, file_path in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type, file_path))

        c.execute('select user_id from active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())

        c.execute('select user_id from admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())

        c.execute('select setting_key, setting_value from bot_settings')
        for key, value in c.fetchall():
            if key == 'free_user_limit':
                global FREE_USER_LIMIT
                FREE_USER_LIMIT = int(value) if value.isdigit() else 1
            elif key == 'force_join_enabled':
                global force_join_enabled
                force_join_enabled = value == '1'

        conn.close()
        logger.info(f"📊 Data loaded: {len(active_users)} users, {len(user_subscriptions)} subscriptions, {len(admin_ids)} admins.")
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}", exc_info=True)

init_db()
load_data()

def to_small_caps(text):
    """convert text to small caps style"""
    small_caps_map = {
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ',
        'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ',
        'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x',
        'Y': 'ʏ', 'Z': 'ᴢ',
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ',
        'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ',
        'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
        'y': 'ʏ', 'z': 'ᴢ'
    }
    return ''.join(small_caps_map.get(char, char) for char in text)

def check_force_join(user_id):
    """check if user is member of required channel and group"""
    if user_id in admin_ids:
        return True
    
    if not force_join_enabled:
        return True
    
    try:
        channel_member = bot.get_chat_member(FORCE_CHANNEL, user_id)
        if channel_member.status not in ['member', 'administrator', 'creator']:
            return False
        
        group_member = bot.get_chat_member(FORCE_GROUP, user_id)
        if group_member.status not in ['member', 'administrator', 'creator']:
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Error checking membership for user {user_id}: {e}")
        return False

def create_force_join_message():
    """create force join message with modern UI"""
    return f"""
🔐 *ᴍᴇᴍʙᴇʀsʜɪᴘ ʀᴇǫᴜɪʀᴇᴅ* 🔐

✨ **ᴊᴏɪɴ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ᴛᴏ ᴜɴʟᴏᴄᴋ ғᴜʟʟ ᴀᴄᴄᴇss:**

 📣 **ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ:** {FORCE_CHANNEL}
 👥 **ᴄᴏᴍᴍᴜɴɪᴛʏ ɢʀᴏᴜᴘ:** {FORCE_GROUP}

📋 **ǫᴜɪᴄᴋ ɢᴜɪᴅᴇ:**

1️⃣ ᴛᴀᴘ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴊᴏɪɴ
2️⃣ ᴡᴀɪᴛ 5 sᴇᴄᴏɴᴅs
3️⃣ ᴛᴀᴘ "✅ ᴠᴇʀɪғʏ ᴍᴇᴍʙᴇʀsʜɪᴘ"
4️⃣ ᴀᴄᴄᴇss ɢʀᴀɴᴛᴇᴅ

🎁 **ᴘᴇʀᴋs:** ᴇxᴄʟᴜsɪᴠᴇ sᴄʀɪᴘᴛs & ᴘʀɪᴏʀɪᴛʏ sᴜᴘᴘᴏʀᴛ
    """

def create_force_join_keyboard():
    """create force join keyboard with modern buttons"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📣 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{FORCE_CHANNEL[1:]}"),
        types.InlineKeyboardButton("👥 ᴊᴏɪɴ ɢʀᴏᴜᴘ", url=f"https://t.me/{FORCE_GROUP[1:]}")
    )
    
    markup.add(types.InlineKeyboardButton("✅ ᴠᴇʀɪғʏ ᴍᴇᴍʙᴇʀsʜɪᴘ", callback_data='check_membership'))
    
    return markup

def mark_user_verified(user_id, verified=True):
    """mark user as verified in database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('update users set verified = ? where user_id = ?', 
                 (1 if verified else 0, user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error marking user verified: {e}")
    finally:
        conn.close()

def is_user_verified(user_id):
    """check if user is verified in database"""
    if user_id in admin_ids:
        return True
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('select verified from users where user_id = ?', (user_id,))
        result = c.fetchone()
        return result and result[0] == 1
    except Exception as e:
        logger.error(f"❌ Error checking user verification: {e}")
        return False
    finally:
        conn.close()

def get_user_folder(user_id):
    """get or create user's folder for storing files"""
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    """get the file upload limit for a user"""
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    
    if is_premium_user(user_id):
        subscription_info = user_subscriptions.get(user_id, {})
        return subscription_info.get('file_limit', PREMIUM_USER_LIMIT)
    
    return FREE_USER_LIMIT  

def get_user_file_count(user_id):
    """get the number of files uploaded by a user"""
    return len(user_files.get(user_id, []))

def is_premium_user(user_id):
    """check if user has active subscription"""
    if user_id in user_subscriptions:
        expiry = user_subscriptions[user_id]['expiry']
        return expiry > datetime.now()
    return False

def get_user_status(user_id):
    """get user status with modern emojis"""
    if user_id == OWNER_ID: return "👑 ꜰᴏᴜɴᴅᴇʀ"
    if user_id in admin_ids: return "🛡️ ᴀᴅᴍɪɴ"
    if is_premium_user(user_id): return "✨ ᴘʀᴏ"
    return "🎯 ʙᴀsɪᴄ"

def get_premium_users_details():
    """get detailed information about premium users"""
    premium_users = []
    for user_id in active_users:
        if is_premium_user(user_id):
            try:
                chat = bot.get_chat(user_id)
                user_files_list = user_files.get(user_id, [])
                running_files = sum(1 for file_name, _, _ in user_files_list if is_bot_running(user_id, file_name))
                subscription_info = user_subscriptions.get(user_id, {})
                file_limit = subscription_info.get('file_limit', PREMIUM_USER_LIMIT)
                
                premium_users.append({
                    'user_id': user_id,
                    'first_name': chat.first_name,
                    'username': chat.username,
                    'file_count': len(user_files_list),
                    'file_limit': file_limit,
                    'running_files': running_files,
                    'expiry': subscription_info['expiry']
                })
            except Exception as e:
                logger.error(f"❌ Error getting user details for {user_id}: {e}")
    
    return premium_users

def generate_subscription_key(days, max_uses=1, file_limit=999, created_by=None):
    """generate subscription key with 1-key 1-user enforcement"""
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    key = f"PAI-{part1}-{part2}"
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''insert into subscription_keys 
                 (key_value, days_valid, max_uses, file_limit, created_by) 
                 values (?, ?, ?, ?, ?)''',
              (key, days, max_uses, file_limit, created_by))
    conn.commit()
    conn.close()
    
    return key

def redeem_subscription_key(key_value, user_id):
    """redeem subscription key - one key per user"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    
    try:
        # check if key exists and is active
        c.execute('''select days_valid, max_uses, used_count, file_limit, is_active, used_by_user
                     from subscription_keys where key_value = ?''', (key_value,))
        key_data = c.fetchone()
        
        if not key_data:
            return False, "❌ ɪɴᴠᴀʟɪᴅ ᴋᴇʏ"
        
        days_valid, max_uses, used_count, file_limit, is_active, used_by_user = key_data
        
        # check if key is active
        if is_active != 1:
            return False, "❌ ᴋᴇʏ ɪɴᴀᴄᴛɪᴠᴇ"
        
        # check if key usage limit reached
        if used_count >= max_uses:
            return False, f"❌ ᴋᴇʏ ᴀʟʀᴇᴀᴅʏ ᴜsᴇᴅ ({used_count}/{max_uses} ᴜsᴇs)"
        
        # check if user already used this key
        if used_by_user and used_by_user == user_id:
            return False, "❌ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴜsᴇᴅ ᴛʜɪs ᴋᴇʏ"
        
        # check if user already has an active key
        c.execute('''select key_used from users where user_id = ? and 
                     key_used is not null''', (user_id,))
        user_key = c.fetchone()
        
        if user_key:
            return False, "❌ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ᴋᴇʏ"
        
        current_expiry = user_subscriptions.get(user_id, {}).get('expiry', datetime.now())
        if current_expiry < datetime.now():
            current_expiry = datetime.now()
        
        new_expiry = current_expiry + timedelta(days=days_valid)
        
        save_subscription(user_id, new_expiry, file_limit)
        
        current_time = datetime.now().isoformat()
        c.execute('''update subscription_keys 
                     set used_count = used_count + 1,
                         used_by_user = ?,
                         used_date = ?
                     where key_value = ?''',
                  (user_id, current_time, key_value))
        
        c.execute('''update users 
                     set key_used = ?,
                         key_used_date = ?
                     where user_id = ?''',
                  (key_value, current_time, user_id))
        
        conn.commit()

        try:
            user_info = bot.get_chat(user_id)
            user_mention = f"[{user_info.first_name}](tg://user?id={user_id})" if user_info.first_name else f"User {user_id}"
    
            admin_msg = f"""
🔔 **ɴᴇᴡ 1ᴋᴇʏ-1ᴜsᴇʀ ᴀᴄᴛɪᴠᴀᴛɪᴏɴ** 🔔

👤 **ᴜsᴇʀ:**
├─ ɪᴅ: `{user_id}`
├─ ɴᴀᴍᴇ: {user_mention}
├─ ᴜsᴇʀɴᴀᴍᴇ: @{user_info.username if user_info.username else 'N/A'}
└─ ᴛɪᴍᴇ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔑 **ᴋᴇʏ ᴅᴇᴛᴀɪʟs:**
├─ ᴋᴇʏ: `{key_value}`
├─ ᴅᴜʀᴀᴛɪᴏɴ: {days_valid} ᴅᴀʏs
├─ ғɪʟᴇs: {file_limit} ғɪʟᴇs
├─ ᴜsᴇs: {used_count + 1}/{max_uses}
└─ ᴇxᴘɪʀᴇs: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}

📝 **ɴᴏᴛᴇ:** 1ᴋᴇʏ = 1ᴜsᴇʀ
            """
            bot.send_message(OWNER_ID, admin_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ Failed to notify admin: {e}")    
        
        return True, f"""
✨ **1ᴋᴇʏ-1ᴜsᴇʀ ᴀᴄᴛɪᴠᴀᴛɪᴏɴ sᴜᴄᴄᴇssғᴜʟ!** ✨

🔑 **ᴋᴇʏ:** `{key_value}`
👤 **ᴀssɪɢɴᴇᴅ ᴛᴏ:** You
📅 **ᴅᴜʀᴀᴛɪᴏɴ:** {days_valid} ᴅᴀʏs
🗃 **ғɪʟᴇ ʟɪᴍɪᴛ:** {file_limit} ғɪʟᴇs
⏰ **sᴛᴀʀᴛ:** {datetime.now().strftime('%Y-%m-%d')}
⏳ **ᴇɴᴅ:** {new_expiry.strftime('%Y-%m-%d')}

📝 **ʀᴇᴍᴇᴍʙᴇʀ:**
• ᴛʜɪs ᴋᴇʏ ɪs ɴᴏᴡ ʟɪɴᴋᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ
• ɪᴛ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜsᴇᴅ ʙʏ ᴀɴʏᴏɴᴇ ᴇʟsᴇ
• ʏᴏᴜ ᴄᴀɴɴᴏᴛ ᴜsᴇ ᴀɴᴏᴛʜᴇʀ ᴋᴇʏ
        """
    
    except Exception as e:
        return False, f"❌ ᴇʀʀᴏʀ: {str(e)}"
    finally:
        conn.close()

def get_all_subscription_keys():
    """get all subscription keys with details"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('select key_value, days_valid, max_uses, used_count, file_limit, created_date from subscription_keys order by created_date desc')
    keys = c.fetchall()
    conn.close()
    return keys

def delete_subscription_key(key_value):
    """delete subscription key and remove premium status from users"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    
    c.execute('select user_id from key_usage where key_value = ?', (key_value,))
    users_affected = c.fetchall()
    
    for (user_id,) in users_affected:
        if user_id in user_subscriptions:
            del user_subscriptions[user_id]
        c.execute('delete from subscriptions where user_id = ?', (user_id,))
        
        try:
            bot.send_message(user_id, "⚠️ **ʏᴏᴜʀ ᴘʀᴏ ᴀᴄᴄᴇss ʜᴀs ʙᴇᴇɴ ʀᴇᴠᴏᴋᴇᴅ**\n\nᴛʜᴇ ᴋᴇʏ ᴜsᴇᴅ ʜᴀs ʙᴇᴇɴ ᴅᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ.")
        except Exception as e:
            logger.error(f"❌ Failed to notify user {user_id}: {e}")
    
    c.execute('delete from subscription_keys where key_value = ?', (key_value,))
    c.execute('delete from key_usage where key_value = ?', (key_value,))
    conn.commit()
    conn.close()

def update_file_limit(new_limit):
    """update free user file limit"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('insert or replace into bot_settings (setting_key, setting_value) values (?, ?)', 
              ('free_user_limit', str(new_limit)))
    conn.commit()
    conn.close()
    
    global FREE_USER_LIMIT
    FREE_USER_LIMIT = new_limit

def update_force_join_status(enabled):
    """update force join status"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('insert or replace into bot_settings (setting_key, setting_value) values (?, ?)', 
              ('force_join_enabled', '1' if enabled else '0'))
    conn.commit()
    conn.close()
    
    global force_join_enabled
    force_join_enabled = enabled

def get_bot_statistics():
    """get comprehensive bot statistics"""
    total_users = len(active_users)
    total_files = sum(len(files) for files in user_files.values())
    
    active_files = 0
    for script_key in bot_scripts:
        if is_bot_running(int(script_key.split('_')[0]), bot_scripts[script_key]['file_name']):
            active_files += 1
    
    # count premium users
    premium_users = sum(1 for user_id in active_users if is_premium_user(user_id))
    
    return {
        'total_users': total_users,
        'total_files': total_files,
        'active_files': active_files,
        'premium_users': premium_users
    }

def get_all_users_details():
    """get details of all bot users"""
    users_list = []
    for user_id in active_users:
        try:
            chat = bot.get_chat(user_id)
            users_list.append({
                'user_id': user_id,
                'first_name': chat.first_name,
                'username': chat.username,
                'is_premium': is_premium_user(user_id)
            })
        except:
            users_list.append({
                'user_id': user_id,
                'first_name': 'Unknown',
                'username': 'Unknown',
                'is_premium': is_premium_user(user_id)
            })
    return users_list

def get_all_admins():
    """get all admin IDs from database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('select user_id from admins')
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

def add_admin_to_db(admin_id):
    """add admin to database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('insert or ignore into admins (user_id) values (?)', (admin_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error adding admin: {e}")
        return False
    finally:
        conn.close()

def remove_admin_from_db(admin_id):
    """remove admin from database"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('delete from admins where user_id = ?', (admin_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error removing admin: {e}")
        return False
    finally:
        conn.close()

def is_bot_running(script_owner_id, file_name):
    """check if a bot script is currently running"""
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
    return False

def kill_process_tree(process_info):
    """kill a process and all its children"""
    try:
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            pid = process.pid
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            try:
                parent.kill()
                parent.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass
            
            if process_info.get('log_file'):
                try:
                    process_info['log_file'].close()
                except:
                    pass
                
    except Exception as e:
        logger.error(f"❌ Error killing process: {e}")

TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'python_telegram_bot': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'requests': 'requests',
    'bs4': 'beautifulsoup4',
    'pillow': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'flask': 'Flask',
    'django': 'Django',
    'sqlalchemy': 'SQLAlchemy',
    'psutil': 'psutil',
    'asyncio': None, 'json': None, 'datetime': None, 'os': None, 'sys': None, 're': None,
    'time': None, 'math': None, 'random': None, 'logging': None, 'threading': None,
    'subprocess': None, 'zipfile': None, 'tempfile': None, 'shutil': None, 'sqlite3': None
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name) 
    if package_name is None: 
        logger.info(f"📦 Module '{module_name}' is core. Skipping pip install.")
        return False 
    try:
        bot.reply_to(message, f"🔧 ɪɴsᴛᴀʟʟɪɴɢ `{package_name}`...", parse_mode='Markdown')
        command = [sys.executable, '-m', 'pip', 'install', package_name, '--timeout', '60', '--retries', '3']
        logger.info(f"🔨 Running install: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore', timeout=120)
        if result.returncode == 0:
            logger.info(f"✅ Installed {package_name}. Output:\n{result.stdout}")
            bot.reply_to(message, f"✅ ɪɴsᴛᴀʟʟᴇᴅ `{package_name}`", parse_mode='Markdown')
            return True
        else:
            error_msg = f"❌ ғᴀɪʟᴇᴅ `{package_name}`\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (ᴛʀᴜɴᴄᴀᴛᴇᴅ)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False
    except subprocess.TimeoutExpired:
        error_msg = f"❌ ᴛɪᴍᴇᴏᴜᴛ `{package_name}`"
        logger.error(error_msg)
        bot.reply_to(message, error_msg)
        return False
    except Exception as e:
        error_msg = f"❌ ᴇʀʀᴏʀ: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message, error_msg)
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"📦 ɪɴsᴛᴀʟʟɪɴɢ `{module_name}`...", parse_mode='Markdown')
        command = ['npm', 'install', module_name, '--timeout=60000']
        logger.info(f"🔨 Running npm install: {' '.join(command)} in {user_folder}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore', timeout=120)
        if result.returncode == 0:
            logger.info(f"✅ Installed {module_name}. Output:\n{result.stdout}")
            bot.reply_to(message, f"✅ ɪɴsᴛᴀʟʟᴇᴅ `{module_name}`", parse_mode='Markdown')
            return True
        else:
            error_msg = f"❌ ғᴀɪʟᴇᴅ `{module_name}`\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (ᴛʀᴜɴᴄᴀᴛᴇᴅ)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False
    except FileNotFoundError:
         error_msg = "❌ ɴᴏᴅᴇ.ᴊs ɴᴏᴛ ғᴏᴜɴᴅ"
         logger.error(error_msg)
         bot.reply_to(message, error_msg)
         return False
    except subprocess.TimeoutExpired:
        error_msg = f"❌ ᴛɪᴍᴇᴏᴜᴛ `{module_name}`"
        logger.error(error_msg)
        bot.reply_to(message, error_msg)
        return False
    except Exception as e:
        error_msg = f"❌ ᴇʀʀᴏʀ: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message, error_msg)
        return False

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    """run python script with automatic dependency installation"""
    max_attempts = 2 
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ ғᴀɪʟᴇᴅ `{file_name}`")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run python script: {script_path}")

    try:
        if not os.path.exists(script_path):
             bot.reply_to(message_obj_for_reply, f"❌ ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ")
             return

        if attempt == 1:
            check_command = [sys.executable, script_path]
            logger.info(f"🔍 Running python pre-check: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=10)
                return_code = check_proc.returncode
                logger.info(f"🔍 Python pre-check. rc: {return_code}. stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        logger.info(f"📦 Detected missing python module: {module_name}")
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            logger.info(f"✅ Install ok for {module_name}. Retrying run_script...")
                            bot.reply_to(message_obj_for_reply, f"⚡ ʀᴇsᴛᴀʀᴛɪɴɢ `{file_name}`...")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            bot.reply_to(message_obj_for_reply, f"❌ ᴄᴀɴɴᴏᴛ ʀᴜɴ `{file_name}`")
                            return
            except subprocess.TimeoutExpired:
                logger.info("⏱️ Python pre-check timed out, imports likely ok.")
                if check_proc and check_proc.poll() is None: 
                    check_proc.kill()
                    check_proc.communicate()
            except Exception as e:
                 logger.error(f"❌ Error in python pre-check: {e}")
                 return

        logger.info(f"🚀 Starting python process for {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: 
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
             logger.error(f"❌ Failed to open log file: {e}")
             bot.reply_to(message_obj_for_reply, f"❌ ʟᴏɴɢ ғɪʟᴇ ᴇʀʀᴏʀ")
             return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [sys.executable, script_path], 
                cwd=user_folder, 
                stdout=log_file, 
                stderr=log_file,
                stdin=subprocess.PIPE, 
                startupinfo=startupinfo, 
                creationflags=creationflags,
                encoding='utf-8', 
                errors='ignore',
                bufsize=1
            )
            logger.info(f"✅ Started python process {process.pid} for {script_key}")
            bot_scripts[script_key] = {
                'process': process, 
                'log_file': log_file, 
                'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id,
                'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 
                'user_folder': user_folder, 
                'type': 'py', 
                'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"✅ `{file_name}` ʀᴜɴɴɪɴɢ (ᴘɪᴅ: {process.pid})")
        except Exception as e:
            if log_file and not log_file.closed: 
                log_file.close()
            error_msg = f"❌ ᴇʀʀᴏʀ `{file_name}`: {str(e)}"
            logger.error(error_msg, exc_info=True)
            bot.reply_to(message_obj_for_reply, error_msg)
            if script_key in bot_scripts: 
                del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"❌ ᴇʀʀᴏʀ `{file_name}`: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message_obj_for_reply, error_msg)

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    """run js script with automatic dependency installation"""
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ ғᴀɪʟᴇᴅ `{file_name}`")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run js script: {script_path}")

    try:
        if not os.path.exists(script_path):
             bot.reply_to(message_obj_for_reply, f"❌ ғɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ")
             return

        if attempt == 1:
            check_command = ['node', script_path]
            logger.info(f"🔍 Running js pre-check: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=10)
                return_code = check_proc.returncode
                logger.info(f"🔍 JS pre-check. rc: {return_code}. stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                             logger.info(f"📦 Detected missing node module: {module_name}")
                             if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                 logger.info(f"✅ npm install ok for {module_name}. Retrying run_js_script...")
                                 bot.reply_to(message_obj_for_reply, f"⚡ ʀᴇsᴛᴀʀᴛɪɴɢ `{file_name}`...")
                                 time.sleep(2)
                                 threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                 return
            except subprocess.TimeoutExpired:
                logger.info("⏱️ JS pre-check timed out, imports likely ok.")
                if check_proc and check_proc.poll() is None: 
                    check_proc.kill()
                    check_proc.communicate()
            except Exception as e:
                 logger.error(f"❌ Error in js pre-check: {e}")
                 return

        logger.info(f"🚀 Starting js process for {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: 
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"❌ Failed to open log file: {e}")
            bot.reply_to(message_obj_for_reply, f"❌ ʟᴏɴɢ ғɪʟᴇ ᴇʀʀᴏʀ")
            return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                ['node', script_path], 
                cwd=user_folder, 
                stdout=log_file, 
                stderr=log_file,
                stdin=subprocess.PIPE, 
                startupinfo=startupinfo, 
                creationflags=creationflags,
                encoding='utf-8', 
                errors='ignore',
                bufsize=1
            )
            logger.info(f"✅ Started js process {process.pid} for {script_key}")
            bot_scripts[script_key] = {
                'process': process, 
                'log_file': log_file, 
                'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id,
                'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 
                'user_folder': user_folder, 
                'type': 'js', 
                'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"✅ `{file_name}` ʀᴜɴɴɪɴɢ (ᴘɪᴅ: {process.pid})")
        except Exception as e:
            if log_file and not log_file.closed: 
                log_file.close()
            error_msg = f"❌ ᴇʀʀᴏʀ `{file_name}`: {str(e)}"
            logger.error(error_msg, exc_info=True)
            bot.reply_to(message_obj_for_reply, error_msg)
            if script_key in bot_scripts: 
                del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"❌ ᴇʀʀᴏʀ `{file_name}`: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message_obj_for_reply, error_msg)

# --- Database  ---
DB_LOCK = threading.Lock()

def save_user(user_id, username, first_name, last_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('insert or replace into users (user_id, username, first_name, last_name) values (?, ?, ?, ?)',
                      (user_id, username, first_name, last_name))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error saving user: {e}")
        finally:
            conn.close()

def save_user_file(user_id, file_name, file_type='unknown', file_path=''):
    """Save user file with chat ID and username"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            # Get user info
            c.execute('select username, first_name from users where user_id = ?', (user_id,))
            user_info = c.fetchone()
            username = user_info[0] if user_info else None
            first_name = user_info[1] if user_info else "Unknown"
            
            # Get file size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            c.execute('''insert into user_files 
                        (user_id, username, chat_id, file_name, file_type, file_path, 
                         original_filename, file_size)
                        values (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (user_id, username, user_id, file_name, file_type, file_path, 
                      file_name, file_size))
            
            conn.commit()
            
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id] = [(fn, ft, fp) for fn, ft, fp in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type, file_path))
            
            logger.info(f"✅ File saved for user {user_id} (@{username}): {file_name}")
            
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
        finally:
            conn.close()

def remove_user_file_db(user_id, file_name):
    """Remove user file from database and file system"""
    file_path = None
    
    if user_id in user_files:
        for fn, ft, fp in user_files[user_id]:
            if fn == file_name:
                file_path = fp
                break
    
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            if not file_path:
                c.execute('select file_path from user_files where user_id = ? and file_name = ?', (user_id, file_name))
                result = c.fetchone()
                if result:
                    file_path = result[0]
            
            c.execute('delete from user_files where user_id = ? and file_name = ?', (user_id, file_name))
            conn.commit()
            
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]: 
                    del user_files[user_id]
            
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"✅ Deleted physical file: {file_path}")
                except Exception as e:
                    logger.error(f"❌ Error deleting physical file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error removing file from database: {e}")
        finally:
            conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('insert or ignore into active_users (user_id) values (?)', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error adding active user: {e}")
        finally:
            conn.close()

def save_subscription(user_id, expiry, file_limit=999):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            expiry_str = expiry.isoformat()
            c.execute('insert or replace into subscriptions (user_id, expiry, file_limit) values (?, ?, ?)', 
                     (user_id, expiry_str, file_limit))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry, 'file_limit': file_limit}
        except Exception as e:
            logger.error(f"❌ Error saving subscription: {e}")
        finally:
            conn.close()

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def get_user_files_with_details(user_id):
    """Get all files for a user with complete details"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''select file_id, file_name, file_type, file_path, 
                     original_filename, file_size, upload_date, is_active
                     from user_files 
                     where user_id = ? 
                     order by upload_date desc''', (user_id,))
        files = c.fetchall()
        
        file_details = []
        for file in files:
            file_id, file_name, file_type, file_path, original_filename, file_size, upload_date, is_active = file
            
            size_str = format_file_size(file_size)
            
            is_running = is_bot_running(user_id, file_name)
            
            file_details.append({
                'file_id': file_id,
                'file_name': file_name,
                'file_type': file_type,
                'file_path': file_path,
                'original_filename': original_filename,
                'file_size': size_str,
                'upload_date': upload_date,
                'is_active': bool(is_active),
                'is_running': is_running
            })
        
        return file_details
    except Exception as e:
        logger.error(f"❌ Error getting user files: {e}")
        return []
    finally:
        conn.close()

def get_all_user_files_for_owner():
    """Get all files from all users - Owner only access"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''select u.user_id, u.username, u.first_name, 
                     f.file_name, f.file_type, f.file_size, f.upload_date, f.is_active,
                     f.file_path
                     from user_files f
                     join users u on f.user_id = u.user_id
                     order by f.upload_date desc''')
        files = c.fetchall()
        
        files_by_user = {}
        for file in files:
            user_id, username, first_name, file_name, file_type, file_size, upload_date, is_active, file_path = file
            
            if user_id not in files_by_user:
                files_by_user[user_id] = {
                    'username': username,
                    'first_name': first_name,
                    'files': []
                }
            
            files_by_user[user_id]['files'].append({
                'file_name': file_name,
                'file_type': file_type,
                'file_size': format_file_size(file_size),
                'upload_date': upload_date,
                'is_active': bool(is_active),
                'file_path': file_path
            })
        
        return files_by_user
    except Exception as e:
        logger.error(f"❌ Error getting all files: {e}")
        return {}
    finally:
        conn.close()

def get_user_by_key(key_value):
    """Get user who used a specific key"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''select u.user_id, u.username, u.first_name, u.key_used_date,
                     k.days_valid, k.file_limit, k.used_date
                     from users u
                     join subscription_keys k on u.key_used = k.key_value
                     where u.key_used = ?''', (key_value,))
        user = c.fetchone()
        
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'key_used_date': user[3],
                'days_valid': user[4],
                'file_limit': user[5],
                'key_activation_date': user[6]
            }
        return None
    except Exception as e:
        logger.error(f"❌ Error getting user by key: {e}")
        return None
    finally:
        conn.close()

def get_owner_files_summary():
    """Get summary of all files for owner dashboard"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('select count(*) from user_files')
        total_files = c.fetchone()[0]
        
        c.execute('select sum(file_size) from user_files')
        total_size = c.fetchone()[0] or 0
        
        c.execute('select file_type, count(*) from user_files group by file_type order by count(*) desc')
        files_by_type = c.fetchall()
        
        c.execute('''select u.user_id, u.username, u.first_name, count(f.file_id) as file_count
                     from users u
                     left join user_files f on u.user_id = f.user_id
                     group by u.user_id
                     order by file_count desc
                     limit 10''')
        top_users = c.fetchall()
        
        return {
            'total_files': total_files,
            'total_size': format_file_size(total_size),
            'files_by_type': files_by_type,
            'top_users': top_users
        }
    except Exception as e:
        logger.error(f"❌ Error getting owner summary: {e}")
        return None
    finally:
        conn.close()

# --- Menu Creation ---
def create_main_menu_keyboard(user_id):
    """create modern main menu keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        '📤 ᴜᴘʟᴏᴀᴅ',
        '📁 ᴍʏ ғɪʟᴇs', 
        '🔑 ᴋᴇʏ',
        '✨ ᴜᴘɢʀᴀᴅᴇ',
        '👤 ᴘʀᴏғɪʟᴇ',
        '📊 sᴛᴀᴛs'
    ]
    
    if user_id in admin_ids:
        buttons.append('⚙️ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ')
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.row(buttons[i])
    
    return markup

def create_start_hosting_keyboard():
    """create start hosting button"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🚀 ᴅᴇᴘʟᴏʏ', callback_data='start_hosting'))
    return markup

def create_manage_files_keyboard(user_id):
    """create modern files management keyboard"""
    user_files_list = user_files.get(user_id, [])
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not user_files_list:
        markup.add(types.InlineKeyboardButton("📭 ɴᴏ ғɪʟᴇs", callback_data='no_files'))
    else:
        for file_name, file_type, file_path in user_files_list:
            is_running = is_bot_running(user_id, file_name)
            status_emoji = "🟢" if is_running else "🔴"
            button_text = f"{status_emoji} {file_name}"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f'file_{user_id}_{file_name}'))
    
    markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data='back_to_main'))
    return markup

def create_file_management_buttons(user_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("⏸️ ᴘᴀᴜsᴇ", callback_data=f'stop_{user_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ", callback_data=f'restart_{user_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("▶️ ᴘʟᴀʏ", callback_data=f'start_{user_id}_{file_name}'),
        )
    markup.row(
        types.InlineKeyboardButton("🗑️ ᴅᴇʟᴇᴛᴇ", callback_data=f'delete_{user_id}_{file_name}'),
        types.InlineKeyboardButton("📋 ʟᴏɢs", callback_data=f'logs_{user_id}_{file_name}')
    )
    markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data='manage_files'))
    return markup

def create_admin_panel_keyboard(user_id=None):
    """create modern admin panel with owner-only options"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Base buttons for all admins
    buttons = [
        '📊 ᴜsᴇʀs sᴛᴀᴛs',
        '👥 ᴜsᴇʀs',
        '✨ ᴘʀᴏ ᴜsᴇʀs',
        '🔑 ɢᴇɴᴇʀᴀᴛᴇ', 
        '🔍 ᴋᴇʏ-ᴜsᴇʀ',
        '🗑️ ʀᴇᴠᴏᴋᴇ',
        '🔢 ᴋᴇʏs',
        '⬅️ ʙᴀᴄᴋ'
    ]
    
    # Owner-only buttons
    if user_id == OWNER_ID:
        owner_buttons = [
            '➕ ᴀᴅᴅ ᴀᴅᴍɪɴ',
            '➖ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ',
            '📢 ʙʀᴏᴀᴅᴄᴀsᴛ',
            '📈 ʟɪᴍɪᴛs',
            '⚙️ sᴇᴛᴛɪɴɢs',
            '📁 ᴀʟʟ ғɪʟᴇs'  # Owner-only feature
        ]
        buttons = owner_buttons + buttons
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.row(buttons[i])
    
    return markup

# --- Command Handlers ---
@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message):
    user_id = message.from_user.id
    
    if message.chat.type in ['group', 'supergroup']:
        return

    if bot_locked and user_id not in admin_ids:
        bot.send_message(message.chat.id, 
                        f"""
🔒 *ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ*
⚠️ ᴛᴇᴍᴘᴏʀᴀʀɪʟʏ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ
ʀᴇᴛʀʏ sᴏᴏɴ
👑 **ᴄᴏɴᴛᴀᴄᴛ:** @leostrike223
                        """,
                        parse_mode='Markdown')
        return

    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode='Markdown')
        return
    
    add_active_user(user_id)
    save_user(user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    
    # Get user's file limit
    user_file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    # Format limit display
    if user_file_limit == float('inf'):
        limit_display = '∞'
    else:
        limit_display = user_file_limit
    
    welcome_text = f"""
⚡ **DEV-PAI CORE** ⚡

✨ ᴡᴇʟᴄᴏᴍᴇ, *{message.from_user.first_name}*!

🚀 **ᴄʟᴏᴜᴅ ᴇxᴇᴄᴜᴛɪᴏɴ ᴘʟᴀᴛғᴏʀᴍ**
├─📦 30+ ʟᴀɴɢᴜᴀɢᴇs
├─⚡ ᴀᴜᴛᴏ ᴅᴇᴘᴇɴᴅᴇɴᴄɪᴇs
└─🔧 ʀᴇᴀʟ-ᴛɪᴍᴇ ᴍᴏɴɪᴛᴏʀɪɴɢ


📊 **ʏᴏᴜʀ sᴛᴀᴛᴜs:** {get_user_status(user_id)}
📈 **ғɪʟᴇs:** {current_files}/{limit_display}

💳 **ᴜᴘɢʀᴀᴅᴇ ᴘʟᴀɴs:**
├─ 7ᴅ: 6000s Ks / $1.5 (5 ғɪʟᴇs)
├─ 30ᴅ: 25000 Ks / $6.5 (15 ғɪʟᴇs)  
├─ 90ᴅ: 70000 Ks / $15 (∞ ғɪʟᴇs)
├─ 1ʏ: 200000 Ks / $50 (∞ ғɪʟᴇs)
└─ ʟɪғᴇᴛɪᴍᴇ: 500000 Ks / $110 (∞ ғɪʟᴇs)

ᴛᴀᴘ ʙᴜᴛᴛᴏɴs ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ!
    """
    
    markup = create_main_menu_keyboard(user_id)
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

# --- Text Message Handlers ---
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id

    if message.chat.type in ['group', 'supergroup']:
        return  

    if bot_locked and user_id not in admin_ids:
        bot.send_message(message.chat.id, 
                        f"""
🔧 *ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ*
⚠️ ᴛᴇᴍᴘᴏʀᴀʀɪʟʏ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ
ʀᴇᴛʀʏ sᴏᴏɴ
👑 **ᴄᴏɴᴛᴀᴄᴛ:** @leostrike223
                        """,
                        parse_mode='Markdown')
        return
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode='Markdown')
        return
    
    text = message.text

    # Owner-only handlers
    if text == '📁 ᴀʟʟ ғɪʟᴇs' and user_id == OWNER_ID:
        handle_admin_files_text(message)
    elif text == '🔍 ᴋᴇʏ-ᴜsᴇʀ' and user_id in admin_ids:
        handle_key_user_info_text(message)
    elif text == '📊 ᴜsᴇʀs sᴛᴀᴛs' and user_id in admin_ids:
        handle_bot_statistics_text(message)
    elif text == '👥 ᴜsᴇʀs' and user_id in admin_ids:
        handle_all_users_text(message)
    elif text == '✨ ᴘʀᴏ ᴜsᴇʀs' and user_id in admin_ids:
        handle_premium_users_text(message)
    elif text == '📢 ʙʀᴏᴀᴅᴄᴀsᴛ' and user_id in admin_ids:
        handle_broadcast_text(message)
    elif text == '🔑 ɢᴇɴᴇʀᴀᴛᴇ' and user_id in admin_ids:
        handle_generate_key_text(message)
    elif text == '🗑️ ʀᴇᴠᴏᴋᴇ' and user_id in admin_ids:
        handle_delete_key_text(message)
    elif text == '🔢 ᴋᴇʏs' and user_id in admin_ids:
        handle_total_keys_text(message)
    elif text == '📈 ʟɪᴍɪᴛs' and user_id in admin_ids:
        handle_file_limit_text(message)
    elif text == '⚙️ sᴇᴛᴛɪɴɢs' and user_id in admin_ids:
        handle_bot_settings_text(message)
    elif text == '➕ ᴀᴅᴅ ᴀᴅᴍɪɴ' and user_id == OWNER_ID:
        handle_add_admin_text(message)
    elif text == '➖ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ' and user_id == OWNER_ID:
        handle_remove_admin_text(message)
    elif text == '⬅️ ʙᴀᴄᴋ':
        handle_back_to_main_text(message)
    elif text == '📤 ᴜᴘʟᴏᴀᴅ':
        handle_upload_file_text(message)
    elif text == '📁 ᴍʏ ғɪʟᴇs':
        handle_manage_files_text(message)
    elif text == '🔑 ᴋᴇʏ':
        handle_redeem_key_text(message)
    elif text == '✨ ᴜᴘɢʀᴀᴅᴇ':
        handle_buy_subscription_text(message)
    elif text == '👤 ᴘʀᴏғɪʟᴇ':
        handle_my_info_text(message)
    elif text == '📊 sᴛᴀᴛs':
        handle_status_text(message)
    elif text == '⚙️ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ' and user_id in admin_ids:
        handle_admin_panel_text(message)
    else:
        bot.send_message(message.chat.id, "❌ ɪɴᴠᴀʟɪᴅ ᴄᴏᴍᴍᴀɴᴅ")

def handle_add_admin_text(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ")
        return
    
    msg = bot.send_message(message.chat.id, "🆔 ᴇɴᴛᴇʀ ᴀᴅᴍɪɴ ɪᴅ:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    try:
        admin_id = int(message.text.strip())
        
        if admin_id == OWNER_ID:
            bot.send_message(message.chat.id, "❌ ᴄᴀɴ'ᴛ ᴀᴅᴅ ᴏᴡɴᴇʀ")
            return
        
        if add_admin_to_db(admin_id):
            admin_ids.add(admin_id)
            
            try:
                # Get user info
                user_info = bot.get_chat(admin_id)
                username = f"@{user_info.username}" if user_info.username else "N/A"
                name = user_info.first_name
                
                bot.send_message(message.chat.id, 
                                f"""
✅ **ᴀᴅᴍɪɴ ᴀᴅᴅᴇᴅ**

👤 {name}
🆔 {admin_id}
👥 {username}
                """, 
                                parse_mode='Markdown')
                
                bot.send_message(admin_id, 
                                f"""
🛡️ **ʏᴏᴜ'ᴠᴇ ʙᴇᴇɴ ᴘʀᴏᴍᴏᴛᴇᴅ ᴛᴏ ᴀᴅᴍɪɴ**

👑 ʙʏ: {message.from_user.first_name}
🔑 ᴀᴄᴄᴇss: ғᴜʟʟ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ

ᴜsᴇ /sᴛᴀʀᴛ ᴛᴏ sᴇᴇ ʏᴏᴜʀ ɴᴇᴡ ᴍᴇɴᴜ
                """, 
                                parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"✅ ᴀᴅᴍɪɴ ᴀᴅᴅᴇᴅ (ɪᴅ: {admin_id})")
                logger.error(f"❌ Failed to get user info: {e}")
        else:
            bot.send_message(message.chat.id, "❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴀᴅᴅ ᴀᴅᴍɪɴ")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ ɪɴᴠᴀʟɪᴅ ɪᴅ")

def handle_remove_admin_text(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ")
        return
    
    # Get current admins
    admins = get_all_admins()
    if not admins:
        bot.send_message(message.chat.id, "📭 ɴᴏ ᴀᴅᴍɪɴs")
        return
    
    admin_list = "🛡️ **ᴄᴜʀʀᴇɴᴛ ᴀᴅᴍɪɴs:**\n\n"
    for admin_id in admins:
        if admin_id != OWNER_ID:
            try:
                user_info = bot.get_chat(admin_id)
                username = f"@{user_info.username}" if user_info.username else "N/A"
                admin_list += f"👤 {user_info.first_name} - `{admin_id}` {username}\n"
            except:
                admin_list += f"👤 Unknown - `{admin_id}`\n"
    
    admin_list += "\n🆔 ᴇɴᴛᴇʀ ᴀᴅᴍɪɴ ɪᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ:"
    msg = bot.send_message(message.chat.id, admin_list, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    try:
        admin_id = int(message.text.strip())
        
        if admin_id == OWNER_ID:
            bot.send_message(message.chat.id, "❌ ᴄᴀɴ'ᴛ ʀᴇᴍᴏᴠᴇ ᴏᴡɴᴇʀ")
            return
        
        if admin_id not in admin_ids:
            bot.send_message(message.chat.id, "❌ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")
            return
        
        if remove_admin_from_db(admin_id):
            admin_ids.discard(admin_id)
            
            try:
                # Get user info
                user_info = bot.get_chat(admin_id)
                username = f"@{user_info.username}" if user_info.username else "N/A"
                name = user_info.first_name
                
                bot.send_message(message.chat.id, 
                                f"""
❌ **ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴇᴅ**

👤 {name}
🆔 {admin_id}
👥 {username}
                """, 
                                parse_mode='Markdown')
                
                # Notify removed admin
                bot.send_message(admin_id, 
                                f"""
⚠️ **ʏᴏᴜ'ᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴀᴅᴍɪɴ**

👑 ʙʏ: {message.from_user.first_name}
🔑 ᴀᴄᴄᴇss: ʀᴇᴠᴏᴋᴇᴅ
                """, 
                                parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴇᴅ (ɪᴅ: {admin_id})")
                logger.error(f"❌ Failed to get user info: {e}")
        else:
            bot.send_message(message.chat.id, "❌ ғᴀɪʟᴇᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ ɪɴᴠᴀʟɪᴅ ɪᴅ")

def handle_bot_settings_text(message):
    """Handle bot settings panel for admins"""
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    # Create settings keyboard
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Force Join toggle (Owner only)
    if message.from_user.id == OWNER_ID:
        force_status = "🟢 ᴇɴᴀʙʟᴇᴅ" if force_join_enabled else "🔴 ᴅɪsᴀʙʟᴇᴅ"
        markup.add(types.InlineKeyboardButton(f"🔐 ғᴏʀᴄᴇ ᴊᴏɪɴ: {force_status}", callback_data='toggle_force_join'))
    
    # Bot lock/unlock (Owner only)
    if message.from_user.id == OWNER_ID:
        lock_status = "🔓 ᴜɴʟᴏᴄᴋᴇᴅ" if not bot_locked else "🔒 ʟᴏᴄᴋᴇᴅ"
        markup.add(types.InlineKeyboardButton(f"🔒 ʙᴏᴛ sᴛᴀᴛᴜs: {lock_status}", callback_data='toggle_bot_lock'))
    
    # File limit settings (all admins)
    markup.add(types.InlineKeyboardButton(f"🗃 ғɪʟᴇ ʟɪᴍɪᴛ: {FREE_USER_LIMIT}", callback_data='change_file_limit'))
    
    # Broadcast settings (all admins)
    markup.add(types.InlineKeyboardButton("📢 ʙʀᴏᴀᴅᴄᴀsᴛ", callback_data='broadcast_settings'))
    
    # System info (all admins)
    markup.add(types.InlineKeyboardButton("ℹ️ sʏsᴛᴇᴍ ɪɴғᴏ", callback_data='system_info'))
    
    # Back button
    markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data='back_to_admin'))
    
    # Create settings message
    settings_text = f"""
⚙️ **ᴮᵒᵗ ˢᵉᵗᵗⁱⁿᵍˢ** ⚙️

👤 **ᴀᴅᴍɪɴ:** {message.from_user.first_name}
🆔 **ɪᴅ:** `{message.from_user.id}`

---
🔐 **ғᴏʀᴄᴇ ᴊᴏɪɴ:** {'ᴇɴᴀʙʟᴇᴅ' if force_join_enabled else 'ᴅɪsᴀʙʟᴇᴅ'}
🔒 **ʙᴏᴛ sᴛᴀᴛᴜs:** {'ᴜɴʟᴏᴄᴋᴇᴅ' if not bot_locked else 'ʟᴏᴄᴋᴇᴅ'}
🗃 **ғɪʟᴇ ʟɪᴍɪᴛ:** {FREE_USER_LIMIT}
---

📝 **ɴᴏᴛᴇ:**
• 👑 = ᴏᴡɴᴇʀ ᴏɴʟʏ
• 🛡️ = ᴀʟʟ ᴀᴅᴍɪɴs
    """
    
    bot.send_message(message.chat.id, settings_text, reply_markup=markup, parse_mode='Markdown')

# Callback handler for Force Join toggle
@bot.callback_query_handler(func=lambda call: call.data == 'toggle_force_join')
def callback_toggle_force_join(call):
    """Handle Force Join toggle callback"""
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    
    try:
        new_status = not force_join_enabled
        update_force_join_status(new_status)
        
        if new_status:
            response_text = "✅ **Force Join has been ENABLED**\n\nUsers must join both channel and group to use the bot."
            bot.answer_callback_query(call.id, "✅ Force Join Enabled", show_alert=False)
        else:
            response_text = "❌ **Force Join has been DISABLED**\n\nUsers can use the bot without joining."
            bot.answer_callback_query(call.id, "❌ Force Join Disabled", show_alert=False)
        
        force_status = "🟢 ᴇɴᴀʙʟᴇᴅ" if new_status else "🔴 ᴅɪsᴀʙʟᴇᴅ"
        lock_status = "🔓 ᴜɴʟᴏᴄᴋᴇᴅ" if not bot_locked else "🔒 ʟᴏᴄᴋᴇᴅ"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f"🔐 ғᴏʀᴄᴇ ᴊᴏɪɴ: {force_status}", callback_data='toggle_force_join'))
        markup.add(types.InlineKeyboardButton(f"🔒 ʙᴏᴛ sᴛᴀᴛᴜs: {lock_status}", callback_data='toggle_bot_lock'))
        markup.add(types.InlineKeyboardButton(f"📊 ғɪʟᴇ ʟɪᴍɪᴛ: {FREE_USER_LIMIT}", callback_data='change_file_limit'))
        markup.add(types.InlineKeyboardButton("📢 ʙʀᴏᴀᴅᴄᴀsᴛ", callback_data='broadcast_settings'))
        markup.add(types.InlineKeyboardButton("ℹ️ sʏsᴛᴇᴍ ɪɴғᴏ", callback_data='system_info'))
        markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data='back_to_admin'))
        
        settings_text = f"""
⚙️ **ᴮᵒᵗ ˢᵉᵗᵗⁱⁿᵍˢ** ⚙️

👤 **ᴀᴅᴍɪɴ:** {call.from_user.first_name}
🆔 **ɪᴅ:** `{call.from_user.id}`

---
🔐 **ғᴏʀᴄᴇ ᴊᴏɪɴ:** {'ᴇɴᴀʙʟᴇᴅ' if new_status else 'ᴅɪsᴀʙʟᴇᴅ'}
🔧 **ʙᴏᴛ sᴛᴀᴛᴜs:** {'ᴜɴʟᴏᴄᴋᴇᴅ' if not bot_locked else 'ʟᴏᴄᴋᴇᴅ'}
🗃 **ғɪʟᴇ ʟɪᴍɪᴛ:** {FREE_USER_LIMIT}
---

📝 **ɴᴏᴛᴇ:**
• 👑 = ᴏᴡɴᴇʀ ᴏɴʟʏ
• 🛡️ = ᴀʟʟ ᴀᴅᴍɪɴs
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=settings_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # Send confirmation message
        bot.send_message(call.message.chat.id, response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error toggling force join: {e}")
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)

# Callback handler for(Owner only)
@bot.callback_query_handler(func=lambda call: call.data == 'toggle_bot_lock')
def callback_toggle_bot_lock(call):
    """Handle Bot Lock toggle callback"""
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    
    try:
        global bot_locked
        bot_locked = not bot_locked
        
        if bot_locked:
            response_text = "🔒 **Bot has been LOCKED**\n\nOnly admins can use the bot now."
            bot.answer_callback_query(call.id, "🔒 Bot Locked", show_alert=False)
        else:
            response_text = "🔓 **Bot has been UNLOCKED**\n\nAll users can use the bot now."
            bot.answer_callback_query(call.id, "🔓 Bot Unlocked", show_alert=False)
        
        force_status = "🟢 ᴇɴᴀʙʟᴇᴅ" if force_join_enabled else "🔴 ᴅɪsᴀʙʟᴇᴅ"
        lock_status = "🔓 ᴜɴʟᴏᴄᴋᴇᴅ" if not bot_locked else "🔒 ʟᴏᴄᴋᴇᴅ"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f"🔐 ғᴏʀᴄᴇ ᴊᴏɪɴ: {force_status}", callback_data='toggle_force_join'))
        markup.add(types.InlineKeyboardButton(f"🔒 ʙᴏᴛ sᴛᴀᴛᴜs: {lock_status}", callback_data='toggle_bot_lock'))
        markup.add(types.InlineKeyboardButton(f"📊 ғɪʟᴇ ʟɪᴍɪᴛ: {FREE_USER_LIMIT}", callback_data='change_file_limit'))
        markup.add(types.InlineKeyboardButton("📢 ʙʀᴏᴀᴅᴄᴀsᴛ", callback_data='broadcast_settings'))
        markup.add(types.InlineKeyboardButton("ℹ️ sʏsᴛᴇᴍ ɪɴғᴏ", callback_data='system_info'))
        markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data='back_to_admin'))
        
        settings_text = f"""
⚙️ **ᴮᵒᵗ ˢᵉᵗᵗⁱⁿᵍˢ** ⚙️

👤 **ᴀᴅᴍɪɴ:** {call.from_user.first_name}
🆔 **ɪᴅ:** `{call.from_user.id}`

---
🔐 **ғᴏʀᴄᴇ ᴊᴏɪɴ:** {'ᴇɴᴀʙʟᴇᴅ' if force_join_enabled else 'ᴅɪsᴀʙʟᴇᴅ'}
🔧 **ʙᴏᴛ sᴛᴀᴛᴜs:** {'ᴜɴʟᴏᴄᴋᴇᴅ' if not bot_locked else 'ʟᴏᴄᴋᴇᴅ'}
🗃 **ғɪʟᴇ ʟɪᴍɪᴛ:** {FREE_USER_LIMIT}
---

📝 **ɴᴏᴛᴇ:**
• 👑 = ᴏᴡɴᴇʀ ᴏɴʟʏ
• 🛡️ = ᴀʟʟ ᴀᴅᴍɪɴs
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=settings_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # Send confirmation message
        bot.send_message(call.message.chat.id, response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error toggling bot lock: {e}")
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'change_file_limit')
def callback_change_file_limit(call):
    """Handle file limit change callback"""
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ", show_alert=True)
        return
    
    msg = bot.send_message(call.message.chat.id, "📊 Enter new file limit for free users:")
    bot.register_next_step_handler(msg, process_file_limit_change)

def process_file_limit_change(message):
    """Process file limit change"""
    try:
        new_limit = int(message.text.strip())
        if new_limit < 0:
            bot.send_message(message.chat.id, "❌ Limit must be positive")
            return
        
        update_file_limit(new_limit)
        bot.send_message(message.chat.id, f"✅ File limit updated to {new_limit}")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid number")

@bot.callback_query_handler(func=lambda call: call.data == 'broadcast_settings')
def callback_broadcast_settings(call):
    """Handle broadcast settings callback"""
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ", show_alert=True)
        return
    
    msg = bot.send_message(call.message.chat.id, "📢 Enter message to broadcast:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    """Process broadcast message"""
    try:
        broadcast_text = message.text
        success_count = 0
        fail_count = 0
        
        for user_id in active_users:
            try:
                bot.send_message(user_id, broadcast_text)
                success_count += 1
                time.sleep(0.1)  
            except:
                fail_count += 1
        
        bot.send_message(
            message.chat.id,
            f"📢 **Broadcast Complete**\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'system_info')
def callback_system_info(call):
    """Handle system info callback"""
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ", show_alert=True)
        return
    
    try:
        stats = get_bot_statistics()
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        info_text = f"""
ℹ️ **System Information**

📊 **Bot Statistics:**
• Total Users: {stats['total_users']}
• Total Files: {stats['total_files']}
• Active Files: {stats['active_files']}
• Premium Users: {stats['premium_users']}

💻 **System Resources:**
• CPU Usage: {cpu_percent}%
• Memory: {memory.percent}% ({memory.used/1024/1024/1024:.1f}GB/{memory.total/1024/1024/1024:.1f}GB)
• Disk: {disk.percent}% ({disk.used/1024/1024/1024:.1f}GB/{disk.total/1024/1024/1024:.1f}GB)

⚙️ **Bot Settings:**
• Force Join: {'Enabled' if force_join_enabled else 'Disabled'}
• Bot Lock: {'Locked' if bot_locked else 'Unlocked'}
• Free User Limit: {FREE_USER_LIMIT}
        """
        
        bot.send_message(call.message.chat.id, info_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_admin')
def callback_back_to_admin(call):
    """Handle back to admin panel callback"""
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ", show_alert=True)
        return
    
    handle_admin_panel_text(call.message)

def handle_admin_panel_text(message):
    """Handle admin panel text command with owner distinction"""
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    markup = create_admin_panel_keyboard(message.from_user.id)
    
    if message.from_user.id == OWNER_ID:
        role_text = "👑 Owner"
        features = "• 📁 View all user files\n• 👑 Full system access"
    else:
        role_text = "🛡️ Admin"
        features = "• 👥 User management\n• 🔑 Key management"
    
    admin_text = f"""
🛡️ **ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ** 🛡️

👤 **ᴜsᴇʀ:** {message.from_user.first_name}
🆔 **ɪᴅ:** `{message.from_user.id}`
📋 **ʀᴏʟᴇ:** {role_text}

📊 **sᴛᴀᴛɪsᴛɪᴄs:**
• ᴛᴏᴛᴀʟ ᴜsᴇʀs: {len(active_users)}
• ᴛᴏᴛᴀʟ ғɪʟᴇs: {sum(len(files) for files in user_files.values())}
• ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs: {sum(1 for user_id in active_users if is_premium_user(user_id))}

⚙️ **ʏᴏᴜʀ ғᴇᴀᴛᴜʀᴇs:**
{features}
    """
    
    bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode='Markdown')

def handle_admin_files_text(message):
    """Handle admin view of all user files - Owner only"""
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.send_message(message.chat.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ")
        return
    
    files_data = get_all_user_files_for_owner()
    
    if not files_data:
        bot.send_message(message.chat.id, "📭 ɴᴏ ғɪʟᴇs ғᴏᴜɴᴅ")
        return
    
    files_text = "👑 **ᴏᴡɴᴇʀ ᴠɪᴇᴡ - ᴀʟʟ ᴜsᴇʀ ғɪʟᴇs:**\n\n"
    
    for user_id, user_data in list(files_data.items())[:20]:  # Limit to 20 users
        username = f"@{user_data['username']}" if user_data['username'] else "No Username"
        files_text += f"👤 **{user_data['first_name']}** ({username}) - `{user_id}`\n"
        
        for file in user_data['files'][:5]: 
            status = "🟢" if file['is_active'] else "🔴"
            files_text += f"  {status} `{file['file_name']}` ({file['file_size']}) - {file['upload_date'][:10]}\n"
            
            files_text += f"  📍 `{file['file_path'][-50:]}`\n"
        
        files_text += "\n"
    
    if len(files_data) > 20:
        files_text += f"\n... {len(files_data) - 20} ᴍᴏʀᴇ ᴜsᴇʀs"
    
    total_users = len(files_data)
    total_files = sum(len(user_data['files']) for user_data in files_data.values())
    
    files_text += f"\n📊 **sᴜᴍᴍᴀʀʏ:** {total_files} ғɪʟᴇs ғʀᴏᴍ {total_users} ᴜsᴇʀs"
    
    bot.send_message(message.chat.id, files_text, parse_mode='Markdown')

def handle_all_files_text(message):
    """Handle viewing all user files - Owner only"""
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.send_message(message.chat.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ")
        return
    
    handle_admin_files_text(message)

def handle_upload_file_text(message):
    user_id = message.from_user.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    if current_files >= file_limit and not is_premium_user(user_id):
        bot.send_message(message.chat.id, f"❌ ʟɪᴍɪᴛ {FREE_USER_LIMIT} ғɪʟᴇ\n✨ ᴜᴘɢʀᴀᴅᴇ ғᴏʀ ᴍᴏʀᴇ")
        return
    
    supported_files = ", ".join([ext for ext in SUPPORTED_EXTENSIONS.keys()])
    bot.send_message(message.chat.id, 
                    f"""
📤 **ᴜᴘʟᴏᴀᴅ ғɪʟᴇ**

sᴜᴘᴘᴏʀᴛᴇᴅ: `{supported_files}`

ᴜᴘʟᴏᴀᴅ ʏᴏᴜʀ ғɪʟᴇ ɴᴏᴡ
ᴀᴜᴛᴏ-ᴅᴇᴘʟᴏʏ ᴀᴠᴀɪʟᴀʙʟᴇ
                    """,
                    parse_mode='Markdown')

def handle_manage_files_text(message):
    user_id = message.from_user.id
    user_files_list = user_files.get(user_id, [])
    
    if not user_files_list:
        bot.send_message(message.chat.id, "📭 ɴᴏ ғɪʟᴇs")
        return
    
    files_text = f"📁 **ғɪʟᴇs:**\n\n"
    
    for file_name, file_type, file_path in user_files_list:
        is_running = is_bot_running(user_id, file_name)
        status = "🟢 ᴀᴄᴛɪᴠᴇ" if is_running else "🔴 ᴘᴀᴜsᴇᴅ"
        files_text += f"• `{file_name}` - {status}\n"
    
    files_text += "\nᴛᴀᴘ ғɪʟᴇ ᴛᴏ ᴍᴀɴᴀɢᴇ"
    
    markup = create_manage_files_keyboard(user_id)
    bot.send_message(message.chat.id, files_text, reply_markup=markup, parse_mode='Markdown')

def handle_redeem_key_text(message):
    msg = bot.send_message(message.chat.id, "🔑 ᴇɴᴛᴇʀ ᴋᴇʏ (PAI-XXXX-XXXX):")
    bot.register_next_step_handler(msg, process_redeem_key)

def handle_buy_subscription_text(message):
    plans_text = f"""
💎 **ᴜᴘɢʀᴀᴅᴇ ᴘʟᴀɴs**

├─🟢 **7 ᴅᴀʏs** 
│ 6000 Ks / 1.5 USDT
│ 5 ғɪʟᴇs • ᴘʀɪᴏʀɪᴛʏ

├─🔵 **30 ᴅᴀʏs**
│ 25000 Ks / 6.5 USDT  
│ 15 ғɪʟᴇs • ᴇᴀʀʟʏ ᴀᴄᴄᴇss

├─🟣 **90 ᴅᴀʏs**
│ 70000 Ks / 15 USDT
│ ∞ ғɪʟᴇs • ᴠɪᴘ sᴜᴘᴘᴏʀᴛ

├─🟡 **1 ʏᴇᴀʀ**
│ 200000 Ks / 50 USDT
│ ғᴜʟʟ ᴀᴄᴄᴇss • ᴀᴅᴍɪɴ

├─⚡️ **ʟɪғᴇᴛɪᴍᴇ**
│ 500000 Ks / 110 USDT
│ ғᴜʟʟ ᴀᴄᴄᴇss • ᴀᴅᴍɪɴ
│ 24/7 Developer Support



💳 **ᴘᴀʏᴍᴇɴᴛs:** Binance, Bybit, KPAY, WAVE
📲 **ᴄᴏɴᴛᴀᴄᴛ:** @leostrike223
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 ᴄᴏɴᴛᴀᴄᴛ", url="https://t.me/leostrike223"))
    markup.add(types.InlineKeyboardButton("🔑 ʀᴇᴅᴇᴇᴍ", callback_data='redeem_key'))
    
    bot.send_message(message.chat.id, plans_text, reply_markup=markup, parse_mode='Markdown')

def handle_bot_statistics_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    stats = get_bot_statistics()
    stats_text = f"""
📊 **sʏsᴛᴇᴍ sᴛᴀᴛs**

👥 ᴜsᴇʀs: `{stats['total_users']}`
✨ ᴘʀᴏ: `{stats['premium_users']}`
📁 ғɪʟᴇs: `{stats['total_files']}`
🟢 ᴀᴄᴛɪᴠᴇ: `{stats['active_files']}`

⚡ sᴛᴀᴛᴜs: 🟢 ᴏɴʟɪɴᴇ
🔒 ᴍᴏᴅᴇ: {'🔒 ʟᴏᴄᴋᴇᴅ' if bot_locked else '🔓 ᴏᴘᴇɴ'}
📈 ʙᴀsɪᴄ ʟɪᴍɪᴛ: {FREE_USER_LIMIT}
🔰 ᴄᴏᴍᴍᴜɴɪᴛʏ: {'✅ ᴏɴ' if force_join_enabled else '❌ ᴏғғ'}
    """
    
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

def handle_premium_users_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    premium_users = get_premium_users_details()
    if not premium_users:
        bot.send_message(message.chat.id, "📭 ɴᴏ ᴘʀᴏ ᴜsᴇʀs")
        return
    
    premium_text = f"✨ **ᴘʀᴏ ᴜsᴇʀs:**\n\n"
    
    for user in premium_users:
        days_left = (user['expiry'] - datetime.now()).days
        premium_text += f"""
👤 {user['first_name']} (@{user['username']})
📁 {user['file_count']}/{user['file_limit']} ғɪʟᴇs (🟢 {user['running_files']})
⏳ {days_left}ᴅ ʟᴇғᴛ
───────────────────────
        """
    
    bot.send_message(message.chat.id, premium_text, parse_mode='Markdown')

def handle_broadcast_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    msg = bot.send_message(message.chat.id, "📢 ᴇɴᴛᴇʀ ᴍᴇssᴀɢᴇ:")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    broadcast_messages[message.message_id] = message.text
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ sᴇɴᴅ", callback_data=f'confirm_broadcast_{message.message_id}'),
        types.InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data='cancel_broadcast')
    )
    
    bot.send_message(message.chat.id, 
                    f"📢 **ᴘʀᴇᴠɪᴇᴡ:**\n\n{message.text}\n\nsᴇɴᴅ ᴛᴏ ᴀʟʟ ᴜsᴇʀs?",
                    reply_markup=markup, parse_mode='Markdown')

def handle_generate_key_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    msg = bot.send_message(message.chat.id, "📅 ᴅᴀʏs:")
    bot.register_next_step_handler(msg, process_generate_key_days)

def process_generate_key_days(message):
    try:
        days = int(message.text.strip())
        if days <= 0:
            bot.send_message(message.chat.id, "❌ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ")
            return
        
        bot.send_message(message.chat.id, f"✅ {days} ᴅᴀʏs\n\nᴍᴀx ᴜsᴇs:")
        bot.register_next_step_handler(message, process_generate_key_uses, days)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ ɴᴜᴍʙᴇʀ ʀᴇǫᴜɪʀᴇᴅ")

def process_generate_key_uses(message, days):
    try:
        max_uses = int(message.text.strip())
        if max_uses <= 0:
            bot.send_message(message.chat.id, "❌ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ")
            return
        
        bot.send_message(message.chat.id, f"🗃 ғɪʟᴇ ʟɪᴍɪᴛ (1-999):")
        bot.register_next_step_handler(message, process_generate_key_file_limit, days, max_uses)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ ɴᴜᴍʙᴇʀ ʀᴇǫᴜɪʀᴇᴅ")

def process_generate_key_file_limit(message, days, max_uses):
    try:
        file_limit = int(message.text.strip())
        if file_limit < 1 or file_limit > 999:
            bot.send_message(message.chat.id, "❌ 1-999")
            return
        
        key = generate_subscription_key(days, max_uses, file_limit, created_by=message.from_user.id)
        bot.send_message(message.chat.id, 
                        f"""
✅ **ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ**

🔑 `{key}`
📅 {days} ᴅᴀʏs
🗃 {file_limit} ғɪʟᴇs
🔢 {max_uses} ᴜsᴇs
                        """,
                        parse_mode='Markdown')
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ ɴᴜᴍʙᴇʀ ʀᴇǫᴜɪʀᴇᴅ")

def handle_delete_key_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    keys = get_all_subscription_keys()
    if not keys:
        bot.send_message(message.chat.id, "📭 ɴᴏ ᴋᴇʏs")
        return
    
    keys_text = f"🗑️ **ᴀᴄᴛɪᴠᴇ ᴋᴇʏs:**\n\n"
    for key in keys:
        keys_text += f"• `{key[0]}` - {key[1]}ᴅ, {key[3]}/{key[2]}, {key[4]} ғɪʟᴇs\n"
    
    keys_text += "\nᴇɴᴛᴇʀ ᴋᴇʏ ᴛᴏ ʀᴇᴠᴏᴋᴇ:"
    bot.send_message(message.chat.id, keys_text, parse_mode='Markdown')
    
    msg = bot.send_message(message.chat.id, "🔑 ᴋᴇʏ:")
    bot.register_next_step_handler(msg, process_delete_key)

def process_delete_key(message):
    key_value = message.text.strip().upper()

    keys = get_all_subscription_keys()
    key_exists = any(key[0] == key_value for key in keys)
    
    if not key_exists:
        bot.send_message(message.chat.id, f"❌ `{key_value}` ɴᴏᴛ ғᴏᴜɴᴅ", parse_mode='Markdown')
        return
    
    delete_subscription_key(key_value)
    bot.send_message(message.chat.id, f"✅ `{key_value}` ʀᴇᴠᴏᴋᴇᴅ", parse_mode='Markdown')

def handle_total_keys_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    keys = get_all_subscription_keys()
    if not keys:
        bot.send_message(message.chat.id, "📭 ɴᴏ ᴋᴇʏs")
        return
    
    keys_text = f"🔢 **ᴀʟʟ ᴋᴇʏs:**\n\n"
    for key in keys:
        keys_text += f"• `{key[0]}`\n  📅 {key[1]}ᴅ, 📊 {key[4]} ғɪʟᴇs, 🔢 {key[3]}/{key[2]}\n  🕐 {key[5][:16]}\n\n"
    
    bot.send_message(message.chat.id, keys_text, parse_mode='Markdown')

def handle_file_limit_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    current_limit = FREE_USER_LIMIT
    msg = bot.send_message(message.chat.id, f"📈 ᴄᴜʀʀᴇɴᴛ ʟɪᴍɪᴛ: {current_limit}\n\nɴᴇᴡ ʟɪᴍɪᴛ (1-100):")
    bot.register_next_step_handler(msg, process_file_limit)

def process_file_limit(message):
    try:
        new_limit = int(message.text.strip())
        if 1 <= new_limit <= 100:
            update_file_limit(new_limit)
            bot.send_message(message.chat.id, f"✅ ʟɪᴍɪᴛ: {new_limit}")
        else:
            bot.send_message(message.chat.id, "❌ 1-100")
    except ValueError:
        bot.send_message(message.chat.id, "❌ ɴᴜᴍʙᴇʀ")

def handle_key_user_info_text(message):
    """Handle key-user relationship info"""
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    msg = bot.send_message(message.chat.id, "🔑 ᴇɴᴛᴇʀ ᴋᴇʏ ᴛᴏ ᴄʜᴇᴄᴋ:")
    bot.register_next_step_handler(msg, process_key_user_info)

def process_key_user_info(message):
    """Process key to get user info"""
    key_value = message.text.strip().upper()
    
    user_info = get_user_by_key(key_value)
    
    if not user_info:
        bot.reply_to(message, f"❌ ɴᴏ ᴜsᴇʀ ғᴏᴜɴᴅ ғᴏʀ ᴋᴇʏ `{key_value}`", parse_mode='Markdown')
        return
    
    user_text = f"""
🔑 **ᴋᴇʏ:** `{key_value}`

👤 **ᴜsᴇʀ ɪɴғᴏ:**
├─ ɪᴅ: `{user_info['user_id']}`
├─ ɴᴀᴍᴇ: {user_info['first_name']}
├─ ᴜsᴇʀɴᴀᴍᴇ: @{user_info['username'] if user_info['username'] else 'N/A'}
├─ ᴅᴜʀᴀᴛɪᴏɴ: {user_info['days_valid']} ᴅᴀʏs
├─ ғɪʟᴇ ʟɪᴍɪᴛ: {user_info['file_limit']}
├─ ᴋᴇʏ ᴀᴄᴛɪᴠᴀᴛᴇᴅ: {user_info['key_activation_date'][:19]}
└─ ᴜsᴇʀ ᴅᴀᴛᴀ sᴀᴠᴇᴅ: {user_info['key_used_date'][:19]}

📝 **ɴᴏᴛᴇ:** 1ᴋᴇʏ = 1ᴜsᴇʀ
    """
    
    # Get user's files
    user_files_list = get_user_files_with_details(user_info['user_id'])
    
    if user_files_list:
        user_text += f"\n📁 **ғɪʟᴇs ({len(user_files_list)}):**\n"
        for file in user_files_list[:10]:  # Limit to 10 files
            status = "🟢" if file['is_running'] else "🔴"
            user_text += f"├─ {status} `{file['file_name']}` ({file['file_size']})\n"
        
        if len(user_files_list) > 10:
            user_text += f"└─ ... {len(user_files_list) - 10} ᴍᴏʀᴇ ғɪʟᴇs\n"
    else:
        user_text += "\n📭 **ɴᴏ ғɪʟᴇs**"
    
    bot.reply_to(message, user_text, parse_mode='Markdown')

def handle_all_users_text(message):
    if message.from_user.id not in admin_ids:
        bot.send_message(message.chat.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ")
        return
    
    users = get_all_users_details()
    if not users:
        bot.send_message(message.chat.id, "📭 ɴᴏ ᴜsᴇʀs")
        return
    
    users_text = f"👥 **ᴜsᴇʀs:**\n\n"
    for user in users[:50]:
        status = "✨" if user['is_premium'] else "🎯"
        username = f"@{user['username']}" if user['username'] else "-"
        users_text += f"• {status} {user['first_name']} ({username})\n"
    
    if len(users) > 50:
        users_text += f"\n... {len(users) - 50} ᴍᴏʀᴇ"
    
    bot.send_message(message.chat.id, users_text, parse_mode='Markdown')

def handle_back_to_main_text(message):
    user_id = message.from_user.id
    markup = create_main_menu_keyboard(user_id)
    bot.send_message(message.chat.id, "⬅️ ʙᴀᴄᴋ", reply_markup=markup)

def handle_my_info_text(message):
    user_id = message.from_user.id
    user_status = get_user_status(user_id)
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    subscription_info = ""
    if is_premium_user(user_id):
        subscription_data = user_subscriptions.get(user_id, {})
        expiry = subscription_data.get('expiry', datetime.now())
        file_limit = subscription_data.get('file_limit', 999)
        days_left = (expiry - datetime.now()).days
        subscription_info = f"📅 ᴇxᴘɪʀᴇs: {expiry.strftime('%Y-%m-%d')}\n📊 ʟɪᴍɪᴛ: {file_limit} ғɪʟᴇs\n⏳ ᴅᴀʏs ʟᴇғᴛ: {days_left}"
    else:
        subscription_info = "⏳ ʙᴀsɪᴄ ᴘʟᴀɴ"
    
    limit_str = str(file_limit) if file_limit != float('inf') else "∞"
    
    my_info_text = f"""
👤 **ᴘʀᴏғɪʟᴇ**

🤖 ɪᴅ: `{user_id}`
👤 ɴᴀᴍᴇ: {message.from_user.first_name}
📱 ᴜsᴇʀɴᴀᴍᴇ: @{message.from_user.username if message.from_user.username else '-'}
📊 sᴛᴀᴛᴜs: {user_status}

💎 ᴛɪᴇʀ:
{subscription_info}
📂 ᴜsᴇᴅ: {current_files}/{limit_str}

📁 ғɪʟᴇs:
├─ 🗃 ᴛᴏᴛᴀʟ: {current_files}
├─ 🟢 ᴀᴄᴛɪᴠᴇ: {sum(1 for fn, _, _ in user_files.get(user_id, []) if is_bot_running(user_id, fn))}
└─ 🔴 ᴘᴀᴜsᴇᴅ: {sum(1 for fn, _, _ in user_files.get(user_id, []) if not is_bot_running(user_id, fn))}
    """
    
    markup = types.InlineKeyboardMarkup()
    if not is_premium_user(user_id):
        markup.add(types.InlineKeyboardButton("✨ ᴜᴘɢʀᴀᴅᴇ", callback_data='buy_subscription'))
    markup.add(types.InlineKeyboardButton("📁 ғɪʟᴇs", callback_data='manage_files'))
    markup.add(types.InlineKeyboardButton("🔑 ᴋᴇʏ", callback_data='redeem_key'))
    
    bot.send_message(message.chat.id, my_info_text, reply_markup=markup, parse_mode='Markdown')

def handle_status_text(message):
    user_id = message.from_user.id
    user_status = get_user_status(user_id)
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    status_text = f"""
📊 **Current Status**

👤ᴜsᴇʀ: {message.from_user.first_name}
📊sᴛᴀᴛᴜs: {user_status}
📁ғɪʟᴇs: {current_files}/{file_limit if file_limit != float('inf') else '∞'}
🟢ʀᴜɴɴɪɴɢ: {sum(1 for fn, _, _ in user_files.get(user_id, []) if is_bot_running(user_id, fn))}
🔴sᴛᴏᴘᴘᴇᴅ: {sum(1 for fn, _, _ in user_files.get(user_id, []) if not is_bot_running(user_id, fn))}

💎ᴘʀᴇᴍɪᴜᴍ: {'ᴀᴄᴛɪᴠᴇ' if is_premium_user(user_id) else 'ʙᴀsɪᴄ'}
🔒ʙᴏᴛ sᴛᴀᴛᴜs: {'ʟᴏᴄᴋᴇᴅ' if bot_locked else 'ᴏᴘᴇɴ'}
🔰ғᴏʀᴄᴇ ᴊᴏɪɴ: {'ᴏɴ' if force_join_enabled else 'ᴏғғ'}
    """
    
    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')

# --- File Upload Handler ---
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id

    if message.chat.type in ['group', 'supergroup']:
        return  

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, 
                    f"""
🔒 *ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ*
⚠️ ᴛᴇᴍᴘᴏʀᴀʀɪʟʏ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ
ʀᴇᴛʀʏ sᴏᴏɴ
👑 **ᴄᴏɴᴛᴀᴄᴛ:** @leostrike223
                    """,
                    parse_mode='Markdown')
        return
    
    # Check force join for non-admin users
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode='Markdown')
        return
    
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    
    if current_files >= file_limit:
        if is_premium_user(user_id):
            subscription_info = user_subscriptions.get(user_id, {})
            premium_limit = subscription_info.get('file_limit', PREMIUM_USER_LIMIT)
            bot.reply_to(message, f"❌ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ᴍᴏʀᴇ ᴛʜᴀɴ {premium_limit} ғɪʟᴇs\n✨ ᴘʀᴇᴍɪᴜᴍ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ")
        else:
            bot.reply_to(message, f"❌ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ᴍᴏʀᴇ ᴛʜᴀɴ {FREE_USER_LIMIT} ғɪʟᴇs\n✨ ᴜᴘɢʀᴀᴅᴇ ғᴏʀ ᴍᴏʀᴇ")
        return
    
    doc = message.document
    file_name = doc.file_name
    file_ext = os.path.splitext(file_name)[1].lower()
    
    if file_ext not in SUPPORTED_EXTENSIONS:
        supported_list = ", ".join([f"`{ext}`" for ext in sorted(SUPPORTED_EXTENSIONS.keys())])
        bot.reply_to(message, f"❌ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ\nsᴜᴘᴘᴏʀᴛᴇᴅ: {supported_list}", parse_mode='Markdown')
        return
    
    try:
        file_info = bot.get_file(doc.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        user_folder = get_user_folder(user_id)
        file_path = os.path.join(user_folder, file_name)
        
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        file_type = SUPPORTED_EXTENSIONS.get(file_ext, 'ᴜɴᴋɴᴏᴡɴ')
        save_user_file(user_id, file_name, file_type, file_path)
        
        try:
            bot.forward_message(OWNER_ID, message.chat.id, message.message_id)
            user_mention = f"[{message.from_user.first_name}](tg://user?id={user_id})" if message.from_user.first_name else f"User {user_id}"
            bot.send_message(OWNER_ID, 
                           f"""
📤 ɴᴇᴡ ғɪʟᴇ
👤User: {user_mention}
🤖ID: `{user_id}`
📄File Name: `{file_name}`
📦File Type:{file_type}
                           """,
                           parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ Failed to notify owner: {e}")
        
        # send success message
        success_text = f"""
STATUS: `{file_name}` ᴜᴘʟᴏᴀᴅᴇᴅ
FILE TYPE: {file_type}

📊 **ʏᴏᴜʀ ᴜsᴀɢᴇ:** {current_files + 1}/{file_limit if file_limit != float('inf') else '∞'}

ᴛᴀᴘ ᴅᴇᴘʟᴏʏ ᴛᴏ ʀᴜɴ
        """
        
        markup = create_start_hosting_keyboard()
        bot.reply_to(message, success_text, reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error uploading file: {e}")
        bot.reply_to(message, f"❌ ᴇʀʀᴏʀ: {str(e)}")

# --- Callback Query Handlers ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id

    if call.message.chat.type in ['group', 'supergroup']:
        bot.answer_callback_query(call.id, "❌ This bot only works in private chats", show_alert=True)
        return

    if bot_locked and user_id not in admin_ids:
        bot.answer_callback_query(call.id, 
                                 f"🔒 ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ", 
                                 show_alert=True)
        return
    
    data = call.data
    
    try:
        if data == 'check_membership':
            handle_check_membership(call)
        elif data == 'start_hosting':
            handle_start_hosting_callback(call)
        elif data == 'manage_files':
            handle_manage_files_callback(call)
        elif data.startswith('file_'):
            handle_file_click(call)
        elif data == 'redeem_key':
            msg = bot.send_message(call.message.chat.id, "🔑 ᴇɴᴛᴇʀ ᴋᴇʏ:")
            bot.register_next_step_handler(msg, process_redeem_key)
        elif data == 'buy_subscription':
            handle_buy_subscription_text(call.message)
        elif data == 'admin_panel':
            handle_admin_panel_text(call.message)
        elif data == 'bot_statistics':
            handle_bot_statistics_text(call.message)
        elif data == 'all_users':
            handle_all_users_text(call.message)
        elif data == 'premium_users':
            handle_premium_users_text(call.message)
        elif data == 'broadcast':
            handle_broadcast_text(call.message)
        elif data == 'generate_key':
            handle_generate_key_text(call.message)
        elif data == 'delete_key':
            handle_delete_key_text(call.message)
        elif data == 'total_keys':
            handle_total_keys_text(call.message)
        elif data == 'bot_settings':
            handle_bot_settings_text(call.message)
        elif data == 'back_to_main':
            handle_back_to_main_callback(call)
        elif data.startswith('start_'):
            handle_start_file(call)
        elif data.startswith('stop_'):
            handle_stop_file(call)
        elif data.startswith('restart_'):
            handle_restart_file(call)
        elif data.startswith('delete_'):
            handle_delete_file(call)
        elif data.startswith('logs_'):
            handle_logs_file(call)
        elif data.startswith('confirm_broadcast_'):
            handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast':
            handle_cancel_broadcast(call)
        elif data == 'lock_bot':
            handle_lock_bot(call)
        elif data == 'unlock_bot':
            handle_unlock_bot(call)
        elif data == 'enable_force_join':
            handle_enable_force_join(call)
        elif data == 'disable_force_join':
            handle_disable_force_join(call)
        elif data == 'no_files':
            bot.answer_callback_query(call.id, "📭 ɴᴏ ғɪʟᴇs", show_alert=True)
        # Owner-only callbacks
        elif data == 'owner_view_all_files':
            callback_owner_view_all_files(call)
        elif data == 'owner_cleanup_files':
            callback_owner_cleanup_files(call)
        elif data == 'owner_export_data':
            callback_owner_export_data(call)
        elif data == 'owner_generate_report':
            callback_owner_generate_report(call)
            
    except Exception as e:
        logger.error(f"❌ Error in callback handler: {e}")
        bot.answer_callback_query(call.id, "❌ ᴇʀʀᴏʀ", show_alert=True)

def handle_check_membership(call):
    user_id = call.from_user.id
    
    if user_id in admin_ids:
        bot.answer_callback_query(call.id, "✅ ᴀᴅᴍɪɴ ᴀᴄᴄᴇss", show_alert=True)
        return
    
    if check_force_join(user_id):
        bot.answer_callback_query(call.id, "✅ ᴠᴇʀɪғɪᴇᴅ", show_alert=True)
        
        add_active_user(user_id)
        save_user(user_id, call.from_user.username, call.from_user.first_name, call.from_user.last_name)
        
        welcome_text = f"""
⚡ **DEV-PAI CORE** ⚡

✨ ᴡᴇʟᴄᴏᴍᴇ, *{call.from_user.first_name}*!

✅ **ᴍᴇᴍʙᴇʀsʜɪᴘ ᴠᴇʀɪғɪᴇᴅ**

📊 **ʏᴏᴜʀ sᴛᴀᴛᴜs:** {get_user_status(user_id)}
🗃 **ғɪʟᴇs:** {get_user_file_count(user_id)}/{get_user_file_limit(user_id) if get_user_file_limit(user_id) != float('inf') else '∞'}

ᴛᴀᴘ ʙᴜᴛᴛᴏɴs ᴛᴏ sᴛᴀʀᴛ
        """
        
        markup = create_main_menu_keyboard(user_id)

        try:
            bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            logger.error(f"❌ Error sending welcome message: {e}")
            try:
                bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, 
                                     reply_markup=markup, parse_mode='Markdown')
            except Exception as e2:
                logger.error(f"❌ Error editing message: {e2}")
                bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ ᴊᴏɪɴ ʙᴏᴛʜ", show_alert=True)

def handle_manage_files_callback(call):
    user_id = call.from_user.id
    
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                             reply_markup=force_markup, parse_mode='Markdown')
        return
    
    user_files_list = user_files.get(user_id, [])
    
    if not user_files_list:
        bot.answer_callback_query(call.id, "📭 ɴᴏ ғɪʟᴇs", show_alert=True)
        return
    
    files_text = f"📁 **ғɪʟᴇs:**\n\n"
    
    for file_name, file_type, file_path in user_files_list:
        is_running = is_bot_running(user_id, file_name)
        status = "🟢 ᴀᴄᴛɪᴠᴇ" if is_running else "🔴 ᴘᴀᴜsᴇᴅ"
        files_text += f"• `{file_name}` - {status}\n"
    
    files_text += "\nᴛᴀᴘ ғɪʟᴇ ᴛᴏ ᴍᴀɴᴀɢᴇ"
    
    markup = create_manage_files_keyboard(user_id)
    bot.edit_message_text(files_text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')

def handle_file_click(call):
    try:
        _, user_id_str, file_name = call.data.split('_', 2)
        user_id = int(user_id_str)
        
        if call.from_user.id != user_id and call.from_user.id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ ᴅᴇɴɪᴇᴅ", show_alert=True)
            return
        
        if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
            force_message = create_force_join_message()
            force_markup = create_force_join_keyboard()
            bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                                 reply_markup=force_markup, parse_mode='Markdown')
            return
        
        file_details = None
        for fn, ft, fp in user_files.get(user_id, []):
            if fn == file_name:
                file_details = (fn, ft, fp)
                break
        
        if not file_details:
            bot.answer_callback_query(call.id, "❌ ɴᴏᴛ ғᴏᴜɴᴅ", show_alert=True)
            return
        
        file_name, file_type, file_path = file_details
        is_running = is_bot_running(user_id, file_name)
        
        file_text = f"""
FILE NAME:**{file_name}**

FILE TYPE:{file_type}
STATUS:{'🟢 ᴀᴄᴛɪᴠᴇ' if is_running else '🔴 ᴘᴀᴜsᴇᴅ'}
        """
        
        markup = create_file_management_buttons(user_id, file_name, is_running)
        bot.edit_message_text(file_text, call.message.chat.id, call.message.message_id,
                             reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def handle_start_hosting_callback(call):
    user_id = call.from_user.id
    
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                             reply_markup=force_markup, parse_mode='Markdown')
        return
    
    user_files_list = user_files.get(user_id, [])
    
    if not user_files_list:
        bot.answer_callback_query(call.id, "❌ ɴᴏ ғɪʟᴇs", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, "🚀 sᴛᴀʀᴛɪɴɢ...")
    
    started_count = 0
    for file_name, file_type, file_path in user_files_list:
        if not is_bot_running(user_id, file_name):
            user_folder = get_user_folder(user_id)
            
            if os.path.exists(file_path):
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext == '.py':
                    threading.Thread(target=run_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
                    started_count += 1
                elif file_ext == '.js':
                    threading.Thread(target=run_js_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
                    started_count += 1
                time.sleep(1)
    
    if started_count > 0:
        bot.send_message(call.message.chat.id, f"✅ ᴅᴇᴘʟᴏʏᴇᴅ {started_count} ғɪʟᴇs")
    else:
        bot.send_message(call.message.chat.id, "ℹ️ ᴀʟʟ ᴀᴄᴛɪᴠᴇ")

def handle_back_to_main_callback(call):
    user_id = call.from_user.id
    
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                             reply_markup=force_markup, parse_mode='Markdown')
        return
    
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "∞"
    user_status = get_user_status(user_id)
    
    main_menu_text = f"""
⚡ **DEV-PAI CORE** ⚡

👋 *{call.from_user.first_name}*

🤖 `{user_id}`
📊 {user_status}
📁 {current_files} / {limit_str}
    """
    
    markup = create_main_menu_keyboard(user_id)
    bot.edit_message_text(main_menu_text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')

def handle_start_file(call):
    try:
        _, user_id_str, file_name = call.data.split('_', 2)
        user_id = int(user_id_str)
        
        if call.from_user.id != user_id and call.from_user.id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ ᴅᴇɴɪᴇᴅ", show_alert=True)
            return
        
        if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
            force_message = create_force_join_message()
            force_markup = create_force_join_keyboard()
            bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                                 reply_markup=force_markup, parse_mode='Markdown')
            return
        
        file_path = None
        for fn, ft, fp in user_files.get(user_id, []):
            if fn == file_name:
                file_path = fp
                break
        
        if not file_path or not os.path.exists(file_path):
            bot.answer_callback_query(call.id, "❌ ɴᴏᴛ ғᴏᴜɴᴅ", show_alert=True)
            return
        
        user_folder = get_user_folder(user_id)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if file_ext == '.py':
            threading.Thread(target=run_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
            bot.answer_callback_query(call.id, f"🚀 sᴛᴀʀᴛɪɴɢ...")
        elif file_ext == '.js':
            threading.Thread(target=run_js_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
            bot.answer_callback_query(call.id, f"🚀 sᴛᴀʀᴛɪɴɢ...")
        else:
            bot.answer_callback_query(call.id, f"✅ ᴅᴇᴘʟᴏʏᴇᴅ")
        
        # refresh
        time.sleep(1)
        handle_file_click(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def handle_stop_file(call):
    try:
        _, user_id_str, file_name = call.data.split('_', 2)
        user_id = int(user_id_str)
        script_key = f"{user_id}_{file_name}"
        
        if call.from_user.id != user_id and call.from_user.id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ ᴅᴇɴɪᴇᴅ", show_alert=True)
            return
        
        if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
            force_message = create_force_join_message()
            force_markup = create_force_join_keyboard()
            bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                                 reply_markup=force_markup, parse_mode='Markdown')
            return
        
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            bot.answer_callback_query(call.id, f"⏸️ ᴘᴀᴜsᴇᴅ")
        else:
            bot.answer_callback_query(call.id, f"ℹ️ ɴᴏᴛ ʀᴜɴɴɪɴɢ")
        
        # refresh
        time.sleep(1)
        handle_file_click(call)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def handle_restart_file(call):
    try:
        _, user_id_str, file_name = call.data.split('_', 2)
        user_id = int(user_id_str)
        
        if call.from_user.id != user_id and call.from_user.id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ ᴅᴇɴɪᴇᴅ", show_alert=True)
            return
        
        if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
            force_message = create_force_join_message()
            force_markup = create_force_join_keyboard()
            bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                                 reply_markup=force_markup, parse_mode='Markdown')
            return
        
        script_key = f"{user_id}_{file_name}"
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            time.sleep(1)
        
        file_path = None
        for fn, ft, fp in user_files.get(user_id, []):
            if fn == file_name:
                file_path = fp
                break
        
        if file_path and os.path.exists(file_path):
            user_folder = get_user_folder(user_id)
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext == '.py':
                threading.Thread(target=run_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
            elif file_ext == '.js':
                threading.Thread(target=run_js_script, args=(file_path, user_id, user_folder, file_name, call.message)).start()
            bot.answer_callback_query(call.id, f"🔄 ʀᴇsᴛᴀʀᴛɪɴɢ")
        else:
            bot.answer_callback_query(call.id, "❌ ɴᴏᴛ ғᴏᴜɴᴅ", show_alert=True)
        
        time.sleep(1)
        handle_file_click(call)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def handle_delete_file(call):
    try:
        _, user_id_str, file_name = call.data.split('_', 2)
        user_id = int(user_id_str)
        
        if call.from_user.id != user_id and call.from_user.id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ ᴅᴇɴɪᴇᴅ", show_alert=True)
            return
        
        if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
            force_message = create_force_join_message()
            force_markup = create_force_join_keyboard()
            bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                                 reply_markup=force_markup, parse_mode='Markdown')
            return
        
        # First, find the file path
        file_path = None
        file_type = None
        for fn, ft, fp in user_files.get(user_id, []):
            if fn == file_name:
                file_path = fp
                file_type = ft
                break
        
        if not file_path:
            bot.answer_callback_query(call.id, "❌ ɴᴏᴛ ғᴏᴜɴᴅ", show_alert=True)
            return
        
        # Stop the script if it's running
        script_key = f"{user_id}_{file_name}"
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
        
        # Remove from database
        remove_user_file_db(user_id, file_name)
        
        # Delete the physical file from upload_bots folder
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"✅ Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"❌ Error deleting file {file_path}: {e}")
        
        # Delete log file if it exists
        user_folder = get_user_folder(user_id)
        log_file = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
                logger.info(f"✅ Deleted log file: {log_file}")
            except Exception as e:
                logger.error(f"❌ Error deleting log file {log_file}: {e}")
        
        # Clean up user_files in-memory cache
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
            if not user_files[user_id]:  # If empty, remove the user entry
                del user_files[user_id]
        
        bot.answer_callback_query(call.id, f"🗑️ ᴅᴇʟᴇᴛᴇᴅ")
        
        # Go back to manage files view
        handle_manage_files_callback(call)
        
    except Exception as e:
        logger.error(f"❌ Error in handle_delete_file: {e}")
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def handle_logs_file(call):
    try:
        _, user_id_str, file_name = call.data.split('_', 2)
        user_id = int(user_id_str)
        
        if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
            force_message = create_force_join_message()
            force_markup = create_force_join_keyboard()
            bot.edit_message_text(force_message, call.message.chat.id, call.message.message_id, 
                                 reply_markup=force_markup, parse_mode='Markdown')
            return
        
        user_folder = get_user_folder(user_id)
        log_file = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                logs = f.read()
            
            if len(logs) > 4000:
                logs = logs[:4000] + "\n\n... (ᴛʀᴜɴᴄᴀᴛᴇᴅ)"
            
            log_text = f"📋 **{file_name}:**\n\n```\n{logs}\n```"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data=f'file_{user_id}_{file_name}'))
            
            bot.edit_message_text(log_text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=markup, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "📭 ɴᴏ ʟᴏɢs", show_alert=True)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def can_use_subscription_key(key_value):
    """Check if a subscription key can still be used"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    c = conn.cursor()
    
    try:
        c.execute('select max_uses, used_count from subscription_keys where key_value = ?', (key_value,))
        key_data = c.fetchone()
        
        if not key_data:
            return False
        
        max_uses, used_count = key_data
        
        if used_count >= max_uses:
            return False
        
        return True
    finally:
        conn.close()        

def handle_lock_bot(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    
    global bot_locked
    bot_locked = True
    bot.answer_callback_query(call.id, "🔒 ʟᴏᴄᴋᴇᴅ")
    bot.edit_message_text("🔒 **ʟᴏᴄᴋᴇᴅ**", 
                         call.message.chat.id, call.message.message_id, parse_mode='Markdown')

def handle_unlock_bot(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    
    global bot_locked
    bot_locked = False
    bot.answer_callback_query(call.id, "🔓 ᴜɴʟᴏᴄᴋᴇᴅ")
    bot.edit_message_text("🔓 **ᴜɴʟᴏᴄᴋᴇᴅ**", 
                         call.message.chat.id, call.message.message_id, parse_mode='Markdown')

def handle_enable_force_join(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    
    update_force_join_status(True)
    bot.answer_callback_query(call.id, "✅ ᴇɴᴀʙʟᴇᴅ")
    handle_bot_settings_text(call.message)

def handle_disable_force_join(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    
    update_force_join_status(False)
    bot.answer_callback_query(call.id, "❌ ᴅɪsᴀʙʟᴇᴅ")
    handle_bot_settings_text(call.message)

def handle_confirm_broadcast(call):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ ᴀᴅᴍɪɴ ᴏɴʟʏ", show_alert=True)
        return
    
    try:
        message_id = int(call.data.split('_')[2])
        
        if message_id in broadcast_messages:
            broadcast_text = broadcast_messages[message_id]
        else:
            bot.answer_callback_query(call.id, "❌ ᴍᴇssᴀɢᴇ ɴᴏᴛ ғᴏᴜɴᴅ", show_alert=True)
            return
        
        sent_count = 0
        failed_count = 0
        
        for user_id in active_users:
            try:
                bot.send_message(user_id, broadcast_text)
                sent_count += 1
                time.sleep(0.1)
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Failed to send to {user_id}: {e}")
        
        bot.answer_callback_query(call.id, f"✅ sᴇɴᴛ: {sent_count}, ғᴀɪʟᴇᴅ: {failed_count}")
        bot.edit_message_text(f"📢 ᴄᴏᴍᴘʟᴇᴛᴇ\n✅ {sent_count}\n❌ {failed_count}", 
                             call.message.chat.id, call.message.message_id)
        
        # Clean up stored message
        if message_id in broadcast_messages:
            del broadcast_messages[message_id]
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {str(e)}", show_alert=True)

def handle_cancel_broadcast(call):
    try:
        message_id = int(call.data.split('_')[2]) if '_' in call.data else None
        
        # Clean up stored message if exists
        if message_id and message_id in broadcast_messages:
            del broadcast_messages[message_id]
            
        bot.answer_callback_query(call.id, "❌ ᴄᴀɴᴄᴇʟʟᴇᴅ")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logger.error(f"❌ Error in cancel broadcast: {e}")

def process_redeem_key(message):
    user_id = message.from_user.id
    
    # Check force join
    if force_join_enabled and user_id not in admin_ids and not check_force_join(user_id):
        force_message = create_force_join_message()
        force_markup = create_force_join_keyboard()
        bot.send_message(message.chat.id, force_message, reply_markup=force_markup, parse_mode='Markdown')
        return
    
    key_value = message.text.strip().upper()
    
    # key format:
    if not key_value.startswith('PAI-') or len(key_value) != 13:
        bot.reply_to(message, "❌ ғᴏʀᴍᴀᴛ: `PAI-XXXX-XXXX`\nᴇx: `PAI-A1B2-C3D4`", parse_mode='Markdown')
        return
    
    success, result_msg = redeem_subscription_key(key_value, user_id)
    bot.reply_to(message, result_msg, parse_mode='Markdown')

# Owner-only callback handlers
@bot.callback_query_handler(func=lambda call: call.data == 'owner_view_all_files')
def callback_owner_view_all_files(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    handle_admin_files_text(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'owner_cleanup_files')
def callback_owner_cleanup_files(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    bot.answer_callback_query(call.id, "🔄 ᴄʟᴇᴀɴᴜᴘ ᴄᴏᴍᴘʟᴇᴛᴇ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'owner_export_data')
def callback_owner_export_data(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    bot.answer_callback_query(call.id, "📥 ᴇxᴘᴏʀᴛ sᴛᴀʀᴛᴇᴅ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'owner_generate_report')
def callback_owner_generate_report(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ", show_alert=True)
        return
    bot.answer_callback_query(call.id, "📊 ʀᴇᴘᴏʀᴛ ɢᴇɴᴇʀᴀᴛᴇᴅ", show_alert=True)

def cleanup():
    logger.warning("🛑 sʜᴜᴛᴛɪɴɢ ᴅᴏᴡɴ...")
    for script_key in list(bot_scripts.keys()):
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])

atexit.register(cleanup)

# Start the bot
if __name__ == '__main__':
    keep_alive()
    logger.info("🚀 Bot starting...")
    bot.polling(none_stop=True)
