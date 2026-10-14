# -*- coding: utf-8 -*-
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
import json
import logging
import signal
import threading
import re
import sys
import atexit
import requests

# --- Flask Keep Alive ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'am Marco File Host"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask Keep-Alive server started.")
# --- End Flask Keep Alive ---

# --- Configuration ---
TOKEN = os.environ.get('BOT_TOKEN', '8974349846:AAGDqEr1NfjjfqngJEvJgJnbSI9DEe-phPQ')
OWNER_ID = 6048094235
ADMIN_ID = 7687242263  # New Admin ID as requested
YOUR_USERNAME = '@Rexws348'
UPDATE_CHANNEL = 'https://t.me/anikeshxhosting'

# Default Force Join Channel (Admin can change)
DEFAULT_FORCE_JOIN = 'https://t.me/anikeshxhosting'

# Default Limits
DEFAULT_FREE_USER_LIMIT = 3
DEFAULT_SUBSCRIBED_USER_LIMIT = 15
DEFAULT_ADMIN_LIMIT = 999
DEFAULT_OWNER_LIMIT = float('inf')

# Folder setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

# File upload limits (can be changed by admin)
FREE_USER_LIMIT = 3
SUBSCRIBED_USER_LIMIT = 15
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

# Create necessary directories
os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# --- Data structures ---
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False

# Force Join Data
force_join_channels = []  # List of channel links/usernames
force_join_enabled = False

# Per-user bot limits {user_id: limit}
user_bot_limits = {}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---
def init_db():
    """Initialize the database with required tables"""
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT,
                      PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS force_join
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_link TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_bot_limits
                     (user_id INTEGER PRIMARY KEY, limit_value INTEGER)''')
        
        # Ensure owner and initial admin are in admins table
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        
        # Add default force join channel if none exists
        c.execute('SELECT COUNT(*) FROM force_join')
        if c.fetchone()[0] == 0:
            c.execute('INSERT INTO force_join (channel_link) VALUES (?)', (DEFAULT_FORCE_JOIN,))
        
        # Add default settings
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('force_join_enabled', '1'))
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('free_user_limit', str(DEFAULT_FREE_USER_LIMIT)))
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('subscribed_user_limit', str(DEFAULT_SUBSCRIBED_USER_LIMIT)))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}", exc_info=True)

def load_data():
    """Load data from database into memory"""
    global force_join_channels, force_join_enabled, FREE_USER_LIMIT, SUBSCRIBED_USER_LIMIT, user_bot_limits
    logger.info("Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()

        # Load subscriptions
        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except ValueError:
                logger.warning(f"⚠️ Invalid expiry date format for user {user_id}: {expiry}")

        # Load user files
        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))

        # Load active users
        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())

        # Load admins
        c.execute('SELECT user_id FROM admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())

        # Load force join channels
        c.execute('SELECT channel_link FROM force_join')
        force_join_channels = [row[0] for row in c.fetchall()]

        # Load settings
        c.execute('SELECT key, value FROM settings')
        for key, value in c.fetchall():
            if key == 'force_join_enabled':
                force_join_enabled = value == '1'
            elif key == 'free_user_limit':
                FREE_USER_LIMIT = int(value)
            elif key == 'subscribed_user_limit':
                SUBSCRIBED_USER_LIMIT = int(value)

        # Load per-user bot limits
        c.execute('SELECT user_id, limit_value FROM user_bot_limits')
        for user_id, limit_value in c.fetchall():
            user_bot_limits[user_id] = limit_value

        conn.close()
        logger.info(f"Data loaded: {len(active_users)} users, {len(force_join_channels)} force join channels.")
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}", exc_info=True)

init_db()
load_data()

# --- Helper Functions ---
def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    """Get the file upload limit for a user"""
    if user_id == OWNER_ID:
        return OWNER_LIMIT
    if user_id in admin_ids:
        return user_bot_limits.get(user_id, ADMIN_LIMIT)
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return user_bot_limits.get(user_id, SUBSCRIBED_USER_LIMIT)
    return user_bot_limits.get(user_id, FREE_USER_LIMIT)

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                    try:
                        script_info['log_file'].close()
                    except:
                        pass
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
            return is_running
        except psutil.NoSuchProcess:
            if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                try:
                    script_info['log_file'].close()
                except:
                    pass
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            return False
        except Exception as e:
            logger.error(f"Error checking process status for {script_key}: {e}")
            return False
    return False

def kill_process_tree(process_info):
    pid = None
    script_key = process_info.get('script_key', 'N/A')
    try:
        if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
            try:
                process_info['log_file'].close()
            except:
                pass

        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            pid = process.pid
            if pid:
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except:
                            try:
                                child.kill()
                            except:
                                pass
                    gone, alive = psutil.wait_procs(children, timeout=1)
                    for p in alive:
                        try:
                            p.kill()
                        except:
                            pass
                    try:
                        parent.terminate()
                        try:
                            parent.wait(timeout=1)
                        except psutil.TimeoutExpired:
                            parent.kill()
                    except psutil.NoSuchProcess:
                        pass
                except psutil.NoSuchProcess:
                    pass
    except Exception as e:
        logger.error(f"❌ Error killing process tree: {e}")

# --- Force Join Functions ---
def check_force_join(user_id):
    """Check if user has joined all force join channels"""
    if not force_join_enabled or user_id in admin_ids or user_id == OWNER_ID:
        return True
    
    if not force_join_channels:
        return True
    
    for channel in force_join_channels:
        try:
            # Extract channel username from various formats
            channel_username = extract_channel_username(channel)
            if not channel_username:
                continue
            
            # Check membership
            try:
                member = bot.get_chat_member(f"@{channel_username}", user_id)
                if member.status in ['left', 'kicked']:
                    return False
            except telebot.apihelper.ApiTelegramException as e:
                if "user not found" in str(e).lower() or "participant not found" in str(e).lower():
                    return False
                # If bot is not admin in channel, skip this check
                logger.warning(f"Cannot check membership for @{channel_username}: {e}")
                continue
        except Exception as e:
            logger.error(f"Error checking force join for {channel}: {e}")
            continue
    return True

def extract_channel_username(channel_input):
    """Extract channel username from various input formats"""
    channel_input = channel_input.strip()
    
    # Handle t.me links
    patterns = [
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)',
        r'@([a-zA-Z0-9_]+)',
        r'^([a-zA-Z0-9_]+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, channel_input)
        if match:
            username = match.group(1)
            # Remove joinchat or + prefix if present
            if username.startswith('+') or username.startswith('joinchat'):
                return None  # Private invite links can't be checked
            return username
    return None

def get_force_join_markup():
    """Create inline keyboard for force join"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, channel in enumerate(force_join_channels):
        # Format channel link
        if channel.startswith('http'):
            link = channel
        elif channel.startswith('@'):
            link = f"https://t.me/{channel[1:]}"
        else:
            link = f"https://t.me/{channel}"
        
        markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i+1}", url=link))
    
    markup.add(types.InlineKeyboardButton("✅ I've Joined - Verify", callback_data="verify_join"))
    return markup

def send_force_join_message(chat_id, user_name):
    """Send force join message"""
    channels_text = "\n".join([f"• {ch}" for ch in force_join_channels])
    msg = (f"⚠️ **Force Join Required**\n\n"
           f"Hello {user_name},\n\n"
           f"To use this bot, you must join our channel(s):\n\n"
           f"{channels_text}\n\n"
           f"After joining, click the verify button below.")
    bot.send_message(chat_id, msg, reply_markup=get_force_join_markup(), parse_mode='Markdown')

# --- Automatic Package Installation ---
TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'bs4': 'beautifulsoup4',
    'requests': 'requests',
    'pillow': 'Pillow',
    'PIL': 'Pillow',
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
    'asyncio': None,
    'json': None,
    'datetime': None,
    'os': None,
    'sys': None,
    're': None,
    'time': None,
    'math': None,
    'random': None,
    'logging': None,
    'threading': None,
    'subprocess': None,
    'zipfile': None,
    'tempfile': None,
    'shutil': None,
    'sqlite3': None,
    'atexit': None
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None:
        return False
    try:
        bot.reply_to(message, f"🐍 Installing `{package_name}`...", parse_mode='Markdown')
        command = [sys.executable, '-m', 'pip', 'install', package_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"✅ Package `{package_name}` installed.", parse_mode='Markdown')
            return True
        else:
            error_msg = f"❌ Failed to install `{package_name}`."
            bot.reply_to(message, error_msg)
            return False
    except Exception as e:
        bot.reply_to(message, f"❌ Error installing: {str(e)}")
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"🟠 Installing Node package `{module_name}`...", parse_mode='Markdown')
        command = ['npm', 'install', module_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"✅ Node package `{module_name}` installed.", parse_mode='Markdown')
            return True
        else:
            bot.reply_to(message, f"❌ Failed to install `{module_name}`.")
            return False
    except FileNotFoundError:
        bot.reply_to(message, "❌ 'npm' not found.")
        return False
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")
        return False

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Failed to run '{file_name}' after {max_attempts} attempts.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run Python script: {script_path}")

    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Script '{file_name}' not found!")
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_command = [sys.executable, script_path]
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                if check_proc.returncode != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            bot.reply_to(message_obj_for_reply, f"🔄 Retrying '{file_name}'...")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            return
                    else:
                        bot.reply_to(message_obj_for_reply, f"❌ Error in '{file_name}':\n```\n{stderr[:500]}\n```", parse_mode='Markdown')
                        return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, f"❌ Python interpreter not found.")
                return
            except Exception as e:
                logger.error(f"Error in pre-check: {e}")
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()

        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"❌ Failed to open log file: {e}")
            return
        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
                stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore'
            )
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id,
                'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"✅ Python script '{file_name}' started! (PID: {process.pid})")
        except FileNotFoundError:
            bot.reply_to(message_obj_for_reply, f"❌ Python interpreter not found.")
            if log_file and not log_file.closed:
                log_file.close()
            if script_key in bot_scripts:
                del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()
            bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
            if process and process.poll() is None:
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts:
                del bot_scripts[script_key]
    except Exception as e:
        logger.error(f"❌ Error running script: {e}", exc_info=True)
        bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Failed to run '{file_name}' after {max_attempts} attempts.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run JS script: {script_path}")

    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Script '{file_name}' not found!")
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_command = ['node', script_path]
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                if check_proc.returncode != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                            if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                bot.reply_to(message_obj_for_reply, f"🔄 Retrying '{file_name}'...")
                                time.sleep(2)
                                threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                return
                            else:
                                return
                    bot.reply_to(message_obj_for_reply, f"❌ Error in '{file_name}':\n```\n{stderr[:500]}\n```", parse_mode='Markdown')
                    return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, "❌ 'node' not found.")
                return
            except Exception as e:
                logger.error(f"Error in pre-check: {e}")
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill()
                    check_proc.communicate()

        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"❌ Failed to open log file: {e}")
            return
        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                ['node', script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
                stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore'
            )
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id,
                'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'js', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"✅ JS script '{file_name}' started! (PID: {process.pid})")
        except FileNotFoundError:
            bot.reply_to(message_obj_for_reply, "❌ 'node' not found.")
            if log_file and not log_file.closed:
                log_file.close()
            if script_key in bot_scripts:
                del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed:
                log_file.close()
            bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
            if process and process.poll() is None:
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts:
                del bot_scripts[script_key]
    except Exception as e:
        logger.error(f"❌ Error running JS script: {e}", exc_info=True)
        bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

# --- Database Operations ---
DB_LOCK = threading.Lock()

def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)',
                      (user_id, file_name, file_type))
            conn.commit()
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
        finally:
            conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]:
                    del user_files[user_id]
        except Exception as e:
            logger.error(f"❌ Error removing file: {e}")
        finally:
            conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error adding active user: {e}")
        finally:
            conn.close()

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            expiry_str = expiry.isoformat()
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry_str))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
        except Exception as e:
            logger.error(f"❌ Error saving subscription: {e}")
        finally:
            conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
        except Exception as e:
            logger.error(f"❌ Error removing subscription: {e}")
        finally:
            conn.close()

def add_admin_db(admin_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (admin_id,))
            conn.commit()
            admin_ids.add(admin_id)
        except Exception as e:
            logger.error(f"❌ Error adding admin: {e}")
        finally:
            conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID:
        return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
            conn.commit()
            admin_ids.discard(admin_id)
            return True
        except Exception as e:
            logger.error(f"❌ Error removing admin: {e}")
            return False
        finally:
            conn.close()

def save_setting(key, value):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error saving setting: {e}")
        finally:
            conn.close()

def add_force_join_channel(channel_link):
    global force_join_channels
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO force_join (channel_link) VALUES (?)', (channel_link,))
            conn.commit()
            force_join_channels.append(channel_link)
            return True
        except Exception as e:
            logger.error(f"❌ Error adding force join: {e}")
            return False
        finally:
            conn.close()

def remove_force_join_channel(channel_link):
    global force_join_channels
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM force_join WHERE channel_link = ?', (channel_link,))
            conn.commit()
            if channel_link in force_join_channels:
                force_join_channels.remove(channel_link)
            return True
        except Exception as e:
            logger.error(f"❌ Error removing force join: {e}")
            return False
        finally:
            conn.close()

def clear_force_join_channels():
    global force_join_channels
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM force_join')
            conn.commit()
            force_join_channels = []
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing force join: {e}")
            return False
        finally:
            conn.close()

def set_user_bot_limit(user_id, limit):
    global user_bot_limits
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_bot_limits (user_id, limit_value) VALUES (?, ?)', (user_id, limit))
            conn.commit()
            user_bot_limits[user_id] = limit
            return True
        except Exception as e:
            logger.error(f"❌ Error setting user limit: {e}")
            return False
        finally:
            conn.close()

def remove_user_bot_limit(user_id):
    global user_bot_limits
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_bot_limits WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_bot_limits:
                del user_bot_limits[user_id]
            return True
        except Exception as e:
            logger.error(f"❌ Error removing user limit: {e}")
            return False
        finally:
            conn.close()

# --- Menu Creation ---
def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton('📢 Updates Channel', url=UPDATE_CHANNEL),
        types.InlineKeyboardButton('📤 Upload File', callback_data='upload'),
        types.InlineKeyboardButton('📂 Check Files', callback_data='check_files'),
        types.InlineKeyboardButton('⚡ Bot Speed', callback_data='speed'),
        types.InlineKeyboardButton('📞 Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    ]

    if user_id in admin_ids:
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3], types.InlineKeyboardButton('📊 Statistics', callback_data='stats'))
        markup.add(types.InlineKeyboardButton('💳 Subscriptions', callback_data='subscription'),
                   types.InlineKeyboardButton('📢 Broadcast', callback_data='broadcast'))
        markup.add(types.InlineKeyboardButton('🔒 Lock Bot' if not bot_locked else '🔓 Unlock Bot',
                                              callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
                   types.InlineKeyboardButton('🟢 Run All Scripts', callback_data='run_all_scripts'))
        markup.add(types.InlineKeyboardButton('📣 Force Join Settings', callback_data='force_join_settings'))
        markup.add(types.InlineKeyboardButton('🔔 Add Notification', callback_data='add_notification'))
        markup.add(types.InlineKeyboardButton('⚙️ User Bot Limits', callback_data='user_bot_limits'))
        markup.add(types.InlineKeyboardButton('👑 Admin Panel', callback_data='admin_panel'))
        markup.add(buttons[4])
    else:
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3])
        markup.add(types.InlineKeyboardButton('📊 Statistics', callback_data='stats'))
        markup.add(buttons[4])
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id in admin_ids:
        layout = [
            ["📢 Updates Channel"],
            ["📤 Upload File", "📂 Check Files"],
            ["⚡ Bot Speed", "📊 Statistics"],
            ["💳 Subscriptions", "📢 Broadcast"],
            ["🔒 Lock Bot", "🟢 Running All Code"],
            ["📣 Force Join", "🔔 Notification"],
            ["⚙️ User Limits", "👑 Admin Panel"],
            ["📞 Contact Owner"]
        ]
    else:
        layout = [
            ["📢 Updates Channel"],
            ["📤 Upload File", "📂 Check Files"],
            ["⚡ Bot Speed", "📊 Statistics"],
            ["📞 Contact Owner"]
        ]
    for row in layout:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Stop", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Start", callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("📜 View Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Admin', callback_data='add_admin'),
        types.InlineKeyboardButton('➖ Remove Admin', callback_data='remove_admin')
    )
    markup.row(types.InlineKeyboardButton('📋 List Admins', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription'),
        types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription')
    )
    markup.row(types.InlineKeyboardButton('🔍 Check Subscription', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_force_join_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    status = "✅ Enabled" if force_join_enabled else "❌ Disabled"
    markup.add(types.InlineKeyboardButton(f'🔄 Toggle Force Join ({status})', callback_data='toggle_force_join'))
    markup.add(types.InlineKeyboardButton('➕ Add Channel', callback_data='add_force_channel'))
    markup.add(types.InlineKeyboardButton('➖ Remove Channel', callback_data='remove_force_channel'))
    markup.add(types.InlineKeyboardButton('📋 List Channels', callback_data='list_force_channels'))
    markup.add(types.InlineKeyboardButton('🗑️ Clear All Channels', callback_data='clear_force_channels'))
    markup.add(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

# --- File Handling ---
def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        zip_path = os.path.join(temp_dir, file_name_zip)
        with open(zip_path, 'wb') as new_file:
            new_file.write(downloaded_file_content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not member_path.startswith(os.path.abspath(temp_dir)):
                    raise zipfile.BadZipFile(f"Unsafe path: {member.filename}")
            zip_ref.extractall(temp_dir)

        extracted_items = os.listdir(temp_dir)
        py_files = [f for f in extracted_items if f.endswith('.py')]
        js_files = [f for f in extracted_items if f.endswith('.js')]
        req_file = 'requirements.txt' if 'requirements.txt' in extracted_items else None
        pkg_json = 'package.json' if 'package.json' in extracted_items else None

        if req_file:
            req_path = os.path.join(temp_dir, req_file)
            bot.reply_to(message, f"🔄 Installing Python deps...")
            try:
                command = [sys.executable, '-m', 'pip', 'install', '-r', req_path]
                result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                bot.reply_to(message, f"✅ Python deps installed.")
            except Exception as e:
                bot.reply_to(message, f"❌ Failed to install deps.")
                return

        if pkg_json:
            bot.reply_to(message, f"🔄 Installing Node deps...")
            try:
                command = ['npm', 'install']
                result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=temp_dir, encoding='utf-8', errors='ignore')
                bot.reply_to(message, f"✅ Node deps installed.")
            except Exception as e:
                bot.reply_to(message, f"❌ Failed to install Node deps.")
                return

        main_script_name = None
        file_type = None
        preferred_py = ['main.py', 'bot.py', 'app.py']
        preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
        
        for p in preferred_py:
            if p in py_files:
                main_script_name = p
                file_type = 'py'
                break
        if not main_script_name:
            for p in preferred_js:
                if p in js_files:
                    main_script_name = p
                    file_type = 'js'
                    break
        if not main_script_name:
            if py_files:
                main_script_name = py_files[0]
                file_type = 'py'
            elif js_files:
                main_script_name = js_files[0]
                file_type = 'js'
        
        if not main_script_name:
            bot.reply_to(message, "❌ No .py or .js script found!")
            return

        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            elif os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(src_path, dest_path)

        save_user_file(user_id, main_script_name, file_type)
        main_script_path = os.path.join(user_folder, main_script_name)
        bot.reply_to(message, f"✅ Files extracted. Starting `{main_script_name}`...", parse_mode='Markdown')

        if file_type == 'py':
            threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()

    except zipfile.BadZipFile as e:
        bot.reply_to(message, f"❌ Invalid ZIP: {e}")
    except Exception as e:
        logger.error(f"❌ Error processing zip: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

# --- Logic Functions ---
def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username

    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot locked by admin. Try later.")
        return

    # Check Force Join
    if not check_force_join(user_id):
        send_force_join_message(chat_id, user_name)
        return

    user_bio = "Could not fetch bio"
    photo_file_id = None
    try:
        user_bio = bot.get_chat(user_id).bio or "No bio"
    except:
        pass
    try:
        user_profile_photos = bot.get_user_profile_photos(user_id, limit=1)
        if user_profile_photos.photos:
            photo_file_id = user_profile_photos.photos[0][-1].file_id
    except:
        pass

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            owner_notification = (f"🎉 New user!\n👤 Name: {user_name}\n✳️ User: @{user_username or 'N/A'}\n"
                                  f"🆔 ID: `{user_id}`\n📝 Bio: {user_bio}")
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"⚠️ Failed to notify owner: {e}")

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Owner"
    elif user_id in admin_ids:
        user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ Subscription expires in: {days_left} days"
        else:
            user_status = "🆓 Free User (Expired Sub)"
            remove_subscription_db(user_id)
    else:
        user_status = "🆓 Free User"

    welcome_msg_text = (f"〽️ Welcome, {user_name}!\n\n🆔 Your User ID: `{user_id}`\n"
                        f"✳️ Username: `@{user_username or 'Not set'}`\n"
                        f"🔰 Your Status: {user_status}{expiry_info}\n"
                        f"📁 Files Uploaded: {current_files} / {limit_str}\n\n"
                        f"🤖 Host & run Python (`.py`) or JS (`.js`) scripts.\n"
                        f"   Upload single scripts or `.zip` archives.\n\n"
                        f"👇 Use buttons or type commands.")
    main_reply_markup = create_reply_keyboard_main_menu(user_id)
    try:
        bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending welcome: {e}")

def _logic_updates_channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📢 Updates Channel', url=UPDATE_CHANNEL))
    bot.reply_to(message, "Visit our Updates Channel:", reply_markup=markup)

def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin.")
        return

    if not check_force_join(user_id):
        send_force_join_message(message.chat.id, message.from_user.first_name)
        return

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ File limit ({current_files}/{limit_str}) reached.")
        return
    bot.reply_to(message, "📤 Send your Python (`.py`), JS (`.js`), or ZIP (`.zip`) file.")

def _logic_check_files(message):
    user_id = message.from_user.id
    if not check_force_join(user_id):
        send_force_join_message(message.chat.id, message.from_user.first_name)
        return
    
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.reply_to(message, "📂 Your files:\n\n(No files uploaded yet)")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Running" if is_running else "🔴 Stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    bot.reply_to(message, "📂 Your files:\nClick to manage.", reply_markup=markup, parse_mode='Markdown')

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, "🏃 Testing speed...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID:
            user_level = "👑 Owner"
        elif user_id in admin_ids:
            user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = "⭐ Premium"
        else:
            user_level = "🆓 Free User"
        speed_msg = (f"⚡ Bot Speed & Status:\n\n⏱️ API Response Time: {response_time} ms\n"
                     f"🚦 Bot Status: {status}\n"
                     f"👤 Your Level: {user_level}")
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id)
    except Exception as e:
        logger.error(f"Error: {e}")

def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📞 Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    bot.reply_to(message, "Click to contact Owner:", reply_markup=markup)

def _logic_statistics(message):
    user_id = message.from_user.id
    total_users = len(active_users)
    total_files_records = sum(len(files) for files in user_files.values())
    running_bots_count = 0
    user_running_bots = 0

    for script_key_iter, script_info_iter in list(bot_scripts.items()):
        try:
            s_owner_id, _ = script_key_iter.split('_', 1)
            if is_bot_running(int(s_owner_id), script_info_iter['file_name']):
                running_bots_count += 1
                if int(s_owner_id) == user_id:
                    user_running_bots += 1
        except:
            pass

    stats_msg_base = (f"📊 Bot Statistics:\n\n"
                      f"👥 Total Users: {total_users}\n"
                      f"📂 Total File Records: {total_files_records}\n"
                      f"🟢 Total Active Bots: {running_bots_count}\n")

    if user_id in admin_ids:
        stats_msg_admin = (f"🔒 Bot Status: {'🔴 Locked' if bot_locked else '🟢 Unlocked'}\n"
                           f"📣 Force Join: {'✅ ON' if force_join_enabled else '❌ OFF'}\n"
                           f"🤖 Your Running Bots: {user_running_bots}")
        stats_msg = stats_msg_base + stats_msg_admin
    else:
        stats_msg = stats_msg_base + f"🤖 Your Running Bots: {user_running_bots}"

    bot.reply_to(message, stats_msg)

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    global bot_locked
    bot_locked = not bot_locked
    status = "locked" if bot_locked else "unlocked"
    bot.reply_to(message, f"🔒 Bot has been {status}.")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    bot.reply_to(message, "👑 Admin Panel", reply_markup=create_admin_panel())

def _logic_force_join_menu(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    status = "✅ Enabled" if force_join_enabled else "❌ Disabled"
    channels_text = "\n".join([f"• {ch}" for ch in force_join_channels]) if force_join_channels else "(No channels)"
    bot.reply_to(message, f"📣 Force Join Settings\n\nStatus: {status}\nChannels:\n{channels_text}",
                 reply_markup=create_force_join_menu())

def _logic_add_notification(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message, "🔔 Send notification message to all users.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_notification_message)

def _logic_user_bot_limits(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton('➕ Set User Limit', callback_data='set_user_limit'))
    markup.add(types.InlineKeyboardButton('➖ Remove User Limit', callback_data='remove_user_limit'))
    markup.add(types.InlineKeyboardButton('📋 List User Limits', callback_data='list_user_limits'))
    markup.add(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    bot.reply_to(message, "⚙️ User Bot Limits Management", reply_markup=markup)

def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, telebot.types.Message):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.chat.id
        reply_func = lambda text, **kwargs: bot.reply_to(message_or_call, text, **kwargs)
        admin_message_obj = message_or_call
    elif isinstance(message_or_call, telebot.types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kwargs: bot.send_message(admin_chat_id, text, **kwargs)
        admin_message_obj = message_or_call.message
    else:
        return

    if admin_user_id not in admin_ids:
        reply_func("⚠️ Admin permissions required.")
        return

    reply_func("⏳ Starting all user scripts...")
    started_count = 0
    skipped_files = 0

    for target_user_id, files_for_user in dict(user_files).items():
        if not files_for_user:
            continue
        user_folder = get_user_folder(target_user_id)
        for file_name, file_type in files_for_user:
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    try:
                        if file_type == 'py':
                            threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj)).start()
                            started_count += 1
                        elif file_type == 'js':
                            threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj)).start()
                            started_count += 1
                        time.sleep(0.5)
                    except:
                        skipped_files += 1
                else:
                    skipped_files += 1

    reply_func(f"✅ Started {started_count} scripts. Skipped: {skipped_files}")

# --- Button Text to Logic Mapping ---
BUTTON_TEXT_TO_LOGIC = {
    "📢 Updates Channel": _logic_updates_channel,
    "📤 Upload File": _logic_upload_file,
    "📂 Check Files": _logic_check_files,
    "⚡ Bot Speed": _logic_bot_speed,
    "📞 Contact Owner": _logic_contact_owner,
    "📊 Statistics": _logic_statistics,
    "💳 Subscriptions": lambda m: bot.reply_to(m, "💳 Subscription Management", reply_markup=create_subscription_menu()) if m.from_user.id in admin_ids else bot.reply_to(m, "⚠️ Admin only."),
    "📢 Broadcast": _logic_broadcast_init,
    "🔒 Lock Bot": _logic_toggle_lock_bot,
    "🟢 Running All Code": _logic_run_all_scripts,
    "👑 Admin Panel": _logic_admin_panel,
    "📣 Force Join": _logic_force_join_menu,
    "🔔 Notification": _logic_add_notification,
    "⚙️ User Limits": _logic_user_bot_limits,
}

# --- Command Handlers ---
@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message):
    _logic_send_welcome(message)

@bot.message_handler(commands=['status', 'statistics'])
def command_show_status(message):
    _logic_statistics(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    start_ping_time = time.time()
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! Latency: {latency} ms", message.chat.id, msg.message_id)

@bot.message_handler(func=lambda message: message.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    logic_func = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if logic_func:
        logic_func(message)

# --- Document Handler ---
@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked.")
        return

    if not check_force_join(user_id):
        send_force_join_message(chat_id, message.from_user.first_name)
        return

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ File limit ({current_files}/{limit_str}) reached.")
        return

    file_name = doc.file_name
    if not file_name:
        bot.reply_to(message, "⚠️ No file name.")
        return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "⚠️ Only .py, .js, .zip allowed.")
        return
    max_file_size = 20 * 1024 * 1024
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"⚠️ File too large (Max: 20 MB).")
        return

    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"⬆️ File '{file_name}' from {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except:
            pass

        download_wait_msg = bot.reply_to(message, f"⏳ Downloading `{file_name}`...")
        file_info_tg_doc = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg_doc.file_path)
        bot.edit_message_text(f"✅ Downloaded. Processing...", chat_id, download_wait_msg.message_id)
        user_folder = get_user_folder(user_id)

        if file_ext == '.zip':
            handle_zip_file(downloaded_file_content, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(downloaded_file_content)
            if file_ext == '.js':
                handle_js_file(file_path, user_id, user_folder, file_name, message)
            elif file_ext == '.py':
                handle_py_file(file_path, user_id, user_folder, file_name, message)
    except telebot.apihelper.ApiTelegramException as e:
        if "file is too big" in str(e).lower():
            bot.reply_to(message, f"❌ File too large to download.")
        else:
            bot.reply_to(message, f"❌ API Error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

# --- Callback Query Handlers ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats', 'verify_join']:
        bot.answer_callback_query(call.id, "⚠️ Bot locked.", show_alert=True)
        return

    try:
        if data == 'upload':
            upload_callback(call)
        elif data == 'check_files':
            check_files_callback(call)
        elif data.startswith('file_'):
            file_control_callback(call)
        elif data.startswith('start_'):
            start_bot_callback(call)
        elif data.startswith('stop_'):
            stop_bot_callback(call)
        elif data.startswith('restart_'):
            restart_bot_callback(call)
        elif data.startswith('delete_'):
            delete_bot_callback(call)
        elif data.startswith('logs_'):
            logs_bot_callback(call)
        elif data == 'speed':
            speed_callback(call)
        elif data == 'back_to_main':
            back_to_main_callback(call)
        elif data == 'verify_join':
            verify_join_callback(call)
        # Admin callbacks
        elif data == 'subscription':
            admin_required_callback(call, subscription_management_callback)
        elif data == 'stats':
            stats_callback(call)
        elif data == 'lock_bot':
            admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot':
            admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts':
            admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast':
            admin_required_callback(call, broadcast_init_callback)
        elif data == 'admin_panel':
            admin_required_callback(call, admin_panel_callback)
        elif data == 'add_admin':
            owner_required_callback(call, add_admin_init_callback)
        elif data == 'remove_admin':
            owner_required_callback(call, remove_admin_init_callback)
        elif data == 'list_admins':
            admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription':
            admin_required_callback(call, add_subscription_init_callback)
        elif data == 'remove_subscription':
            admin_required_callback(call, remove_subscription_init_callback)
        elif data == 'check_subscription':
            admin_required_callback(call, check_subscription_init_callback)
        # Force Join callbacks
        elif data == 'force_join_settings':
            admin_required_callback(call, force_join_settings_callback)
        elif data == 'toggle_force_join':
            admin_required_callback(call, toggle_force_join_callback)
        elif data == 'add_force_channel':
            admin_required_callback(call, add_force_channel_init_callback)
        elif data == 'remove_force_channel':
            admin_required_callback(call, remove_force_channel_init_callback)
        elif data == 'list_force_channels':
            admin_required_callback(call, list_force_channels_callback)
        elif data == 'clear_force_channels':
            admin_required_callback(call, clear_force_channels_callback)
        # Notification callbacks
        elif data == 'add_notification':
            admin_required_callback(call, add_notification_callback)
        # User Bot Limits callbacks
        elif data == 'user_bot_limits':
            admin_required_callback(call, user_bot_limits_callback)
        elif data == 'set_user_limit':
            admin_required_callback(call, set_user_limit_init_callback)
        elif data == 'remove_user_limit':
            admin_required_callback(call, remove_user_limit_init_callback)
        elif data == 'list_user_limits':
            admin_required_callback(call, list_user_limits_callback)
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
    except Exception as e:
        logger.error(f"Error handling callback '{data}': {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "Error processing request.", show_alert=True)
        except:
            pass

def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin permissions required.", show_alert=True)
        return
    func_to_run(call)

def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Owner permissions required.", show_alert=True)
        return
    func_to_run(call)

def upload_callback(call):
    user_id = call.from_user.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.answer_callback_query(call.id, f"⚠️ File limit ({current_files}/{limit_str}) reached.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📤 Send your Python (`.py`), JS (`.js`), or ZIP (`.zip`) file.")

def check_files_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id, "⚠️ No files uploaded.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
            bot.edit_message_text("📂 Your files:\n\n(No files uploaded)", chat_id, call.message.message_id, reply_markup=markup)
        except:
            pass
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢 Running" if is_running else "🔴 Stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    try:
        bot.edit_message_text("📂 Your files:\nClick to manage.", chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        pass

def file_control_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        is_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_running else '🔴 Stopped'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), '?')
        bot.edit_message_text(
            f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: {status_text}",
            call.message.chat.id, call.message.message_id,
            reply_markup=create_control_buttons(script_owner_id, file_name, is_running),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error: {e}")

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ File missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            return

        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Already running.", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"⏳ Starting...")

        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()

        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_now_running else '🟡 Starting...'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: {status_text}",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except:
            pass
    except Exception as e:
        logger.error(f"Error: {e}")

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        file_type = file_info[1]
        script_key = f"{script_owner_id}_{file_name}"

        if not is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Already stopped.", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"⏳ Stopping...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]

        bot.edit_message_text(
            f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: 🔴 Stopped",
            call.message.chat.id, call.message.message_id,
            reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error: {e}")

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        script_key = f"{script_owner_id}_{file_name}"

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ File missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            return

        bot.answer_callback_query(call.id, f"⏳ Restarting...")
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]
            time.sleep(1)

        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()

        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_now_running else '🟡 Starting...'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type})\nStatus: {status_text}",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except:
            pass
    except Exception as e:
        logger.error(f"Error: {e}")

def delete_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"🗑️ Deleting...")
        script_key = f"{script_owner_id}_{file_name}"

        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info:
                kill_process_tree(process_info)
            if script_key in bot_scripts:
                del bot_scripts[script_key]

        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")

        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(log_path):
            os.remove(log_path)

        remove_user_file_db(script_owner_id, file_name)
        bot.edit_message_text(
            f"🗑️ `{file_name}` deleted!",
            call.message.chat.id, call.message.message_id, reply_markup=None, parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error: {e}")

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True)
            return

        user_folder = get_user_folder(script_owner_id)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, f"⚠️ No logs.", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()

            if len(log_content) > 4000:
                log_content = log_content[-4000:]

            if not log_content.strip():
                log_content = "(Log empty)"

            bot.send_message(call.message.chat.id, f"📜 Logs for `{file_name}`:\n```\n{log_content}\n```", parse_mode='Markdown')
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error reading log.")
    except Exception as e:
        logger.error(f"Error: {e}")

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    start_cb_ping_time = time.time()
    try:
        bot.edit_message_text("🏃 Testing speed...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_cb_ping_time) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID:
            user_level = "👑 Owner"
        elif user_id in admin_ids:
            user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = "⭐ Premium"
        else:
            user_level = "🆓 Free User"
        speed_msg = (f"⚡ Bot Speed & Status:\n\n⏱️ Response Time: {response_time} ms\n"
                     f"🚦 Status: {status}\n"
                     f"👤 Your Level: {user_level}")
        bot.answer_callback_query(call.id)
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
        logger.error(f"Error: {e}")

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if not check_force_join(user_id):
        send_force_join_message(chat_id, call.from_user.first_name)
        return
    
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""
    if user_id == OWNER_ID:
        user_status = "👑 Owner"
    elif user_id in admin_ids:
        user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ Expires in: {days_left} days"
        else:
            user_status = "🆓 Free User"
    else:
        user_status = "🆓 Free User"
    
    main_menu_text = (f"〽️ Welcome back, {call.from_user.first_name}!\n\n🆔 ID: `{user_id}`\n"
                      f"🔰 Status: {user_status}{expiry_info}\n📁 Files: {current_files} / {limit_str}\n\n"
                      f"👇 Use buttons or type commands.")
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(main_menu_text, chat_id, call.message.message_id,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except:
        pass

def verify_join_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if check_force_join(user_id):
        bot.answer_callback_query(call.id, "✅ Verified! You can now use the bot.", show_alert=True)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        _logic_send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels yet!", show_alert=True)

# --- Admin Callbacks ---
def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text("💳 Subscription Management\nSelect action:",
                          call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu())

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)

def lock_bot_callback(call):
    global bot_locked
    bot_locked = True
    bot.answer_callback_query(call.id, "🔒 Bot locked.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except:
        pass

def unlock_bot_callback(call):
    global bot_locked
    bot_locked = False
    bot.answer_callback_query(call.id, "🔓 Bot unlocked.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except:
        pass

def run_all_scripts_callback(call):
    _logic_run_all_scripts(call)

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Broadcast cancelled.")
        return

    broadcast_content = message.text
    if not broadcast_content:
        bot.reply_to(message, "⚠️ Cannot broadcast empty message.")
        return

    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast"))

    bot.reply_to(message, f"⚠️ Confirm Broadcast to **{target_count}** users:\n\n```\n{broadcast_content[:500]}\n```",
                 reply_markup=markup, parse_mode='Markdown')

def execute_broadcast(broadcast_text, admin_chat_id):
    sent_count = 0
    failed_count = 0
    blocked_count = 0
    users_to_broadcast = list(active_users)
    total_users = len(users_to_broadcast)

    for i, user_id_bc in enumerate(users_to_broadcast):
        try:
            bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
            sent_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(s in err_desc for s in ["bot was blocked", "user is deactivated", "chat not found"]):
                blocked_count += 1
            else:
                failed_count += 1
        except:
            failed_count += 1

        if (i + 1) % 25 == 0:
            time.sleep(1.5)

    result_msg = (f"📢 Broadcast Complete!\n\n✅ Sent: {sent_count}\n❌ Failed: {failed_count}\n"
                  f"🚫 Blocked: {blocked_count}\n👥 Total: {total_users}")
    try:
        bot.send_message(admin_chat_id, result_msg)
    except:
        pass

def handle_confirm_broadcast(call):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True)
        return
    try:
        original_message = call.message.reply_to_message
        if not original_message:
            raise ValueError("Could not retrieve original message.")
        broadcast_text = original_message.text
        if not broadcast_text:
            raise ValueError("No text to broadcast.")

        bot.answer_callback_query(call.id, "🚀 Starting broadcast...")
        bot.edit_message_text(f"📢 Broadcasting to {len(active_users)} users...",
                              call.message.chat.id, call.message.message_id, reply_markup=None)
        threading.Thread(target=execute_broadcast, args=(broadcast_text, call.message.chat.id)).start()
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {e}", call.message.chat.id, call.message.message_id)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Broadcast cancelled.")
    bot.delete_message(call.message.chat.id, call.message.message_id)

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text("👑 Admin Panel", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID to promote to Admin.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "⚠️ Owner only.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0:
            raise ValueError("ID must be positive")
        if new_admin_id == OWNER_ID:
            bot.reply_to(message, "⚠️ Already Owner.")
            return
        if new_admin_id in admin_ids:
            bot.reply_to(message, f"⚠️ Already Admin.")
            return
        add_admin_db(new_admin_id)
        bot.reply_to(message, f"✅ User `{new_admin_id}` promoted to Admin.")
        try:
            bot.send_message(new_admin_id, "🎉 You are now an Admin!")
        except:
            pass
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID.")
    except Exception as e:
        logger.error(f"Error: {e}")

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID of Admin to remove.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "⚠️ Owner only.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    try:
        admin_id_remove = int(message.text.strip())
        if admin_id_remove <= 0:
            raise ValueError("ID must be positive")
        if admin_id_remove == OWNER_ID:
            bot.reply_to(message, "⚠️ Cannot remove Owner.")
            return
        if admin_id_remove not in admin_ids:
            bot.reply_to(message, f"⚠️ Not an Admin.")
            return
        if remove_admin_db(admin_id_remove):
            bot.reply_to(message, f"✅ Admin `{admin_id_remove}` removed.")
            try:
                bot.send_message(admin_id_remove, "ℹ️ You are no longer an Admin.")
            except:
                pass
        else:
            bot.reply_to(message, f"❌ Failed to remove.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID.")
    except Exception as e:
        logger.error(f"Error: {e}")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(f"- `{aid}` {'(Owner)' if aid == OWNER_ID else ''}" for aid in sorted(list(admin_ids)))
        if not admin_list_str:
            admin_list_str = "(No Admins configured!)"
        bot.edit_message_text(f"👑 Current Admins:\n\n{admin_list_str}", call.message.chat.id,
                              call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error: {e}")

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID & days (e.g., `12345678 30`).\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Format: ID days")
        sub_user_id = int(parts[0].strip())
        days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0:
            raise ValueError("Must be positive")

        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date_new_sub = datetime.now()
        if current_expiry and current_expiry > start_date_new_sub:
            start_date_new_sub = current_expiry
        new_expiry = start_date_new_sub + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)

        bot.reply_to(message, f"✅ Sub for `{sub_user_id}` by {days} days.\nExpiry: {new_expiry:%Y-%m-%d}")
        try:
            bot.send_message(sub_user_id, f"🎉 Sub activated! Expires: {new_expiry:%Y-%m-%d}.")
        except:
            pass
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid: {e}")
    except Exception as e:
        logger.error(f"Error: {e}")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID to remove sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    try:
        sub_user_id_remove = int(message.text.strip())
        if sub_user_id_remove <= 0:
            raise ValueError("Must be positive")
        if sub_user_id_remove not in user_subscriptions:
            bot.reply_to(message, f"⚠️ No active sub.")
            return
        remove_subscription_db(sub_user_id_remove)
        bot.reply_to(message, f"✅ Sub removed.")
        try:
            bot.send_message(sub_user_id_remove, "ℹ️ Your subscription removed.")
        except:
            pass
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID.")
    except Exception as e:
        logger.error(f"Error: {e}")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter User ID to check.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    try:
        sub_user_id_check = int(message.text.strip())
        if sub_user_id_check <= 0:
            raise ValueError("Must be positive")
        if sub_user_id_check in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id_check].get('expiry')
            if expiry_dt:
                if expiry_dt > datetime.now():
                    days_left = (expiry_dt - datetime.now()).days
                    bot.reply_to(message, f"✅ Active sub.\nExpires: {expiry_dt:%Y-%m-%d} ({days_left} days left).")
                else:
                    bot.reply_to(message, f"⚠️ Expired.")
                    remove_subscription_db(sub_user_id_check)
            else:
                bot.reply_to(message, f"⚠️ Expiry missing.")
        else:
            bot.reply_to(message, f"ℹ️ No active sub.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID.")
    except Exception as e:
        logger.error(f"Error: {e}")

# --- Force Join Callbacks ---
def force_join_settings_callback(call):
    bot.answer_callback_query(call.id)
    status = "✅ Enabled" if force_join_enabled else "❌ Disabled"
    channels_text = "\n".join([f"• {ch}" for ch in force_join_channels]) if force_join_channels else "(No channels)"
    bot.edit_message_text(f"📣 Force Join Settings\n\nStatus: {status}\nChannels:\n{channels_text}",
                          call.message.chat.id, call.message.message_id, reply_markup=create_force_join_menu())

def toggle_force_join_callback(call):
    global force_join_enabled
    force_join_enabled = not force_join_enabled
    save_setting('force_join_enabled', '1' if force_join_enabled else '0')
    status = "✅ Enabled" if force_join_enabled else "❌ Disabled"
    bot.answer_callback_query(call.id, f"Force Join: {status}")
    force_join_settings_callback(call)

def add_force_channel_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, 
        "📣 Send channel link/username.\n\n"
        "Supported formats:\n"
        "• https://t.me/channelname\n"
        "• @channelname\n"
        "• channelname\n\n"
        "/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_force_channel)

def process_add_force_channel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    
    channel_input = message.text.strip()
    if add_force_join_channel(channel_input):
        bot.reply_to(message, f"✅ Channel added: `{channel_input}`")
    else:
        bot.reply_to(message, f"❌ Failed to add channel.")

def remove_force_channel_init_callback(call):
    bot.answer_callback_query(call.id)
    if not force_join_channels:
        bot.send_message(call.message.chat.id, "⚠️ No channels to remove.")
        return
    channels_text = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(force_join_channels)])
    msg = bot.send_message(call.message.chat.id, 
        f"📣 Current Channels:\n{channels_text}\n\n"
        "Send channel link to remove.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_force_channel)

def process_remove_force_channel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    
    channel_input = message.text.strip()
    if channel_input in force_join_channels:
        if remove_force_join_channel(channel_input):
            bot.reply_to(message, f"✅ Channel removed: `{channel_input}`")
        else:
            bot.reply_to(message, f"❌ Failed to remove.")
    else:
        bot.reply_to(message, f"⚠️ Channel not found.")

def list_force_channels_callback(call):
    bot.answer_callback_query(call.id)
    if not force_join_channels:
        channels_text = "(No channels configured)"
    else:
        channels_text = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(force_join_channels)])
    bot.edit_message_text(f"📣 Force Join Channels:\n\n{channels_text}",
                          call.message.chat.id, call.message.message_id, reply_markup=create_force_join_menu())

def clear_force_channels_callback(call):
    if clear_force_join_channels():
        bot.answer_callback_query(call.id, "✅ All channels cleared.")
    else:
        bot.answer_callback_query(call.id, "❌ Failed to clear.")
    force_join_settings_callback(call)

# --- Notification Callbacks ---
def add_notification_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, 
        "🔔 Send notification message to all users.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_notification_message)

def process_notification_message(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    
    notification_text = message.text
    if not notification_text:
        bot.reply_to(message, "⚠️ Empty message.")
        return
    
    # Send notification to all users
    sent = 0
    failed = 0
    for user_id in active_users:
        try:
            bot.send_message(user_id, f"🔔 **Notification from Admin**\n\n{notification_text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.reply_to(message, f"✅ Notification sent!\n\n✅ Sent: {sent}\n❌ Failed: {failed}")

# --- User Bot Limits Callbacks ---
def user_bot_limits_callback(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton('➕ Set User Limit', callback_data='set_user_limit'))
    markup.add(types.InlineKeyboardButton('➖ Remove User Limit', callback_data='remove_user_limit'))
    markup.add(types.InlineKeyboardButton('📋 List User Limits', callback_data='list_user_limits'))
    markup.add(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    bot.edit_message_text("⚙️ User Bot Limits Management", call.message.chat.id, 
                          call.message.message_id, reply_markup=markup)

def set_user_limit_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, 
        "⚙️ Enter User ID and limit.\n"
        "Format: `USER_ID LIMIT`\n"
        "Example: `12345678 10`\n"
        "Use `0` for unlimited.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_set_user_limit)

def process_set_user_limit(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Format: USER_ID LIMIT")
        target_user_id = int(parts[0])
        limit = int(parts[1])
        
        if target_user_id <= 0:
            raise ValueError("Invalid User ID")
        
        # 0 means unlimited
        if limit == 0:
            limit_value = 999999  # Effectively unlimited
        else:
            limit_value = limit
        
        if set_user_bot_limit(target_user_id, limit_value):
            if limit == 0:
                bot.reply_to(message, f"✅ User `{target_user_id}` limit set to **Unlimited**.")
            else:
                bot.reply_to(message, f"✅ User `{target_user_id}` limit set to **{limit}** bots.")
            try:
                bot.send_message(target_user_id, f"ℹ️ Your bot hosting limit has been set to {limit if limit > 0 else 'Unlimited'}.")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Failed to set limit.")
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid: {e}")
    except Exception as e:
        logger.error(f"Error: {e}")

def remove_user_limit_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, 
        "⚙️ Enter User ID to remove custom limit.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_user_limit)

def process_remove_user_limit(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized.")
        return
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled.")
        return
    
    try:
        target_user_id = int(message.text.strip())
        if target_user_id <= 0:
            raise ValueError("Invalid ID")
        
        if remove_user_bot_limit(target_user_id):
            bot.reply_to(message, f"✅ Custom limit removed for `{target_user_id}`.")
        else:
            bot.reply_to(message, f"⚠️ No custom limit found for `{target_user_id}`.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID.")
    except Exception as e:
        logger.error(f"Error: {e}")

def list_user_limits_callback(call):
    bot.answer_callback_query(call.id)
    if not user_bot_limits:
        limits_text = "(No custom limits set)"
    else:
        limits_text = "\n".join([f"• User `{uid}`: {limit if limit < 999999 else 'Unlimited'}" 
                                  for uid, limit in user_bot_limits.items()])
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🔙 Back', callback_data='user_bot_limits'))
    bot.edit_message_text(f"⚙️ User Bot Limits:\n\n{limits_text}",
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- Cleanup Function ---
def cleanup():
    logger.warning("Shutdown. Cleaning up processes...")
    script_keys_to_stop = list(bot_scripts.keys())
    if not script_keys_to_stop:
        logger.info("No scripts running.")
        return
    logger.info(f"Stopping {len(script_keys_to_stop)} scripts...")
    for key in script_keys_to_stop:
        if key in bot_scripts:
            kill_process_tree(bot_scripts[key])
    logger.warning("Cleanup finished.")

atexit.register(cleanup)

# --- Main Execution ---
if __name__ == '__main__':
    logger.info("="*40 + "\n🤖 Bot Starting Up...\n" + f"🐍 Python: {sys.version.split()[0]}\n" +
                f"🔧 Base Dir: {BASE_DIR}\n📁 Upload Dir: {UPLOAD_BOTS_DIR}\n" +
                f"📊 Data Dir: {IROTECH_DIR}\n🔑 Owner ID: {OWNER_ID}\n" +
                f"🛡️ Admin IDs: {admin_ids}\n" + "="*40)
    keep_alive()
    logger.info("🚀 Starting polling...")
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            logger.warning("Polling ReadTimeout. Restarting in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"Polling ConnectionError: {ce}. Retrying in 15s...")
            time.sleep(15)
        except Exception as e:
            logger.critical(f"💥 Unrecoverable polling error: {e}", exc_info=True)
            logger.info("Restarting polling in 30s...")
            time.sleep(30)
        finally:
            logger.warning("Polling attempt finished.")
            time.sleep(1)