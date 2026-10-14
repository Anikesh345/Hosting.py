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
import logging
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
    return "Bot Hosting Service is Running"

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
TOKEN = '8871876463:AAGh--FmgZojjv5TC_0SKxMGR5pHdXETa28'
OWNER_ID = 7687242263
YOUR_USERNAME = '@Rexws348'
UPDATE_CHANNEL = '@anikeshxhosting'

# Force Join Default
DEFAULT_FORCE_JOIN_USERNAME = '@anikeshxhosting'

# Folder setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

# File upload limits
FREE_USER_LIMIT = 3
SUBSCRIBED_USER_LIMIT = 15
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

# Bot hosting limits
FREE_BOT_LIMIT = 1
SUBSCRIBED_BOT_LIMIT = 5
DEFAULT_ADMIN_BOT_LIMIT = 5
OWNER_BOT_LIMIT = float('inf')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

# --- Data structures ---
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = set()
admin_bot_limits = {}
bot_locked = False
force_join_enabled = True
force_join_usernames = [DEFAULT_FORCE_JOIN_USERNAME]
user_languages = {}  # {user_id: 'en'/'hi'/'bn'/'zh'}

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== LANGUAGE SYSTEM ====================
LANGUAGES = {
    'en': {
        'name': '🇬🇧 English',
        'welcome': "〽️ Welcome, {name}!",
        'your_id': "🆔 Your User ID",
        'username': "✳️ Username",
        'status': "🔰 Your Status",
        'files': "📁 Files Uploaded",
        'bots': "🤖 Running Bots",
        'owner': "👑 Owner",
        'admin': "🛡️ Admin",
        'premium': "⭐ Premium",
        'free_user': "🆓 Free User",
        'expired_sub': "🆓 Free User (Expired)",
        'expires_in': "⏳ Subscription expires in: {days} days",
        'send_file': "📤 Send your Python (`.py`), JS (`.js`), or ZIP (`.zip`) file.",
        'no_files': "📂 Your files:\n\n(No files uploaded yet)",
        'your_files': "📂 Your files:\nClick to manage.",
        'bot_locked': "⚠️ Bot locked by admin. Try later.",
        'force_join_required': "🔒 **Force Join Required**\n\nTo use this bot, you must join our channel(s) first!\n\nAfter joining, click '✅ I've Joined - Verify'",
        'join_channel': "📢 Join Channel",
        'verify_join': "✅ I've Joined - Verify",
        'verified': "✅ Verified! You can now use the bot.",
        'not_joined': "❌ You haven't joined all channels yet!",
        'file_limit_reached': "⚠️ File limit ({current}/{limit}) reached. Delete files first.",
        'bot_limit_reached': "⚠️ Bot limit ({current}/{limit}) reached. Stop some bots first.",
        'upload_success': "✅ Files extracted. Starting main script: `{name}`...",
        'script_started': "✅ {type} script '{name}' started! (PID: {pid})",
        'script_stopped': "🔴 Script stopped.",
        'delete_confirm': "🗑️ `{name}` deleted!",
        'download_started': "⏳ Downloading `{name}`...",
        'download_done': "✅ Downloaded. Processing...",
        'unsupported_file': "⚠️ Only `.py`, `.js`, `.zip` allowed.",
        'file_too_large': "⚠️ File too large (Max: 20 MB).",
        'speed_test': "⚡ Bot Speed & Status:",
        'response_time': "⏱️ API Response Time",
        'bot_status': "🚦 Bot Status",
        'your_level': "👤 Your Level",
        'unlocked': "🔓 Unlocked",
        'locked': "🔒 Locked",
        'stats': "📊 Bot Statistics:",
        'total_users': "👥 Total Users",
        'total_files': "📂 Total File Records",
        'active_bots': "🟢 Total Active Bots",
        'your_running_bots': "🤖 Your Running Bots",
        'updates_channel': "📢 Updates Channel",
        'upload_file': "📤 Upload File",
        'check_files': "📂 Check Files",
        'bot_speed': "⚡ Bot Speed",
        'statistics': "📊 Statistics",
        'contact_owner': "📞 Contact Owner",
        'subscriptions': "💳 Subscriptions",
        'broadcast': "📢 Broadcast",
        'lock_bot': "🔒 Lock Bot",
        'unlock_bot': "🔓 Unlock Bot",
        'run_all': "🟢 Running All Code",
        'admin_panel': "👑 Admin Panel",
        'force_join_settings': "⚙️ Force Join Settings",
        'send_notification': "🔔 Send Notification",
        'change_language': "🌐 Change Language",
        'back_to_main': "🔙 Back to Main",
        'back_to_files': "🔙 Back to Files",
        'start': "🟢 Start",
        'stop': "🔴 Stop",
        'restart': "🔄 Restart",
        'delete': "🗑️ Delete",
        'logs': "📜 Logs",
        'view_logs': "📜 View Logs",
        'contact_owner_btn': "📞 Contact Owner",
        'select_language': "🌐 **Select Your Language**\n\nChoose your preferred language:",
        'language_changed': "✅ Language changed to English!",
        'notification_sent': "🔔 Notification sent to all users!",
        'add_channel_prompt': "📢 Send channel username (e.g., `@channelname` or `channelname`)\n\n/cancel to abort.",
        'channel_added': "✅ Channel added: {username}",
        'channel_removed': "✅ Channel removed.",
        'invalid_channel': "⚠️ Invalid channel username. Please send again or /cancel.",
        'invalid_format': "⚠️ Invalid format.",
        'file_forwarded_admin': "📁 New file from user",
    },
    'hi': {
        'name': '🇮🇳 हिन्दी',
        'welcome': "〽️ स्वागत है, {name}!",
        'your_id': "🆔 आपकी यूज़र आईडी",
        'username': "✳️ यूज़रनेम",
        'status': "🔰 आपकी स्थिति",
        'files': "📁 अपलोड की गई फाइलें",
        'bots': "🤖 चल रहे बॉट्स",
        'owner': "👑 मालिक",
        'admin': "🛡️ एडमिन",
        'premium': "⭐ प्रीमियम",
        'free_user': "🆓 फ्री यूज़र",
        'expired_sub': "🆓 फ्री यूज़र (एक्सपायर्ड)",
        'expires_in': "⏳ सब्सक्रिप्शन {days} दिन में खत्म होगा",
        'send_file': "📤 अपनी Python (`.py`), JS (`.js`), या ZIP (`.zip`) फाइल भेजें।",
        'no_files': "📂 आपकी फाइलें:\n\n(अभी तक कोई फाइल अपलोड नहीं)",
        'your_files': "📂 आपकी फाइलें:\nप्रबंधित करने के लिए क्लिक करें।",
        'bot_locked': "⚠️ बॉट एडमिन द्वारा लॉक है। बाद में प्रयास करें।",
        'force_join_required': "🔒 **चैनल जॉइन करना जरूरी है**\n\nबॉट का उपयोग करने के लिए पहले हमारा चैनल जॉइन करें!\n\nजॉइन करने के बाद '✅ I've Joined - Verify' पर क्लिक करें",
        'join_channel': "📢 चैनल जॉइन करें",
        'verify_join': "✅ मैंने जॉइन कर लिया - वेरिफाई",
        'verified': "✅ वेरिफाइड! अब आप बॉट का उपयोग कर सकते हैं।",
        'not_joined': "❌ आपने अभी तक सभी चैनल जॉइन नहीं किए!",
        'file_limit_reached': "⚠️ फाइल लिमिट ({current}/{limit}) पूरी हो गई। पहले फाइलें डिलीट करें।",
        'bot_limit_reached': "⚠️ बॉट लिमिट ({current}/{limit}) पूरी हो गई। पहले कुछ बॉट्स बंद करें।",
        'upload_success': "✅ फाइलें एक्सट्रैक्ट हो गईं। मुख्य स्क्रिप्ट शुरू हो रही है: `{name}`...",
        'script_started': "✅ {type} स्क्रिप्ट '{name}' शुरू हो गई! (PID: {pid})",
        'script_stopped': "🔴 स्क्रिप्ट बंद हो गई।",
        'delete_confirm': "🗑️ `{name}` डिलीट हो गई!",
        'download_started': "⏳ `{name}` डाउनलोड हो रही है...",
        'download_done': "✅ डाउनलोड हो गई। प्रोसेस हो रही है...",
        'unsupported_file': "⚠️ केवल `.py`, `.js`, `.zip` allowed है।",
        'file_too_large': "⚠️ फाइल बहुत बड़ी है (Max: 20 MB)।",
        'speed_test': "⚡ बॉट स्पीड और स्टेटस:",
        'response_time': "⏱️ API रिस्पॉन्स टाइम",
        'bot_status': "🚦 बॉट स्टेटस",
        'your_level': "👤 आपका लेवल",
        'unlocked': "🔓 अनलॉक",
        'locked': "🔒 लॉक",
        'stats': "📊 बॉट स्टैटिस्टिक्स:",
        'total_users': "👥 कुल यूज़र्स",
        'total_files': "📂 कुल फाइल रिकॉर्ड्स",
        'active_bots': "🟢 कुल एक्टिव बॉट्स",
        'your_running_bots': "🤖 आपके चल रहे बॉट्स",
        'updates_channel': "📢 अपडेट्स चैनल",
        'upload_file': "📤 फाइल अपलोड करें",
        'check_files': "📂 फाइलें चेक करें",
        'bot_speed': "⚡ बॉट स्पीड",
        'statistics': "📊 स्टैटिस्टिक्स",
        'contact_owner': "📞 मालिक से संपर्क करें",
        'subscriptions': "💳 सब्सक्रिप्शन",
        'broadcast': "📢 ब्रॉडकास्ट",
        'lock_bot': "🔒 बॉट लॉक करें",
        'unlock_bot': "🔓 बॉट अनलॉक करें",
        'run_all': "🟢 सभी कोड चलाएं",
        'admin_panel': "👑 एडमिन पैनल",
        'force_join_settings': "⚙️ फोर्स जॉइन सेटिंग्स",
        'send_notification': "🔔 नोटिफिकेशन भेजें",
        'change_language': "🌐 भाषा बदलें",
        'back_to_main': "🔙 मुख्य मेनू",
        'back_to_files': "🔙 फाइलों पर वापस",
        'start': "🟢 शुरू करें",
        'stop': "🔴 बंद करें",
        'restart': "🔄 रीस्टार्ट",
        'delete': "🗑️ डिलीट",
        'logs': "📜 लॉग्स",
        'view_logs': "📜 लॉग्स देखें",
        'contact_owner_btn': "📞 मालिक से संपर्क",
        'select_language': "🌐 **अपनी भाषा चुनें**\n\nअपनी पसंदीदा भाषा चुनें:",
        'language_changed': "✅ भाषा हिन्दी में बदल गई!",
        'notification_sent': "🔔 सभी यूज़र्स को नोटिफिकेशन भेज दिया गया!",
        'add_channel_prompt': "📢 चैनल यूज़रनेम भेजें (जैसे `@channelname` या `channelname`)\n\n/cancel रद्द करने के लिए।",
        'channel_added': "✅ चैनल जोड़ा गया: {username}",
        'channel_removed': "✅ चैनल हटा दिया गया।",
        'invalid_channel': "⚠️ गलत चैनल यूज़रनेम। दोबारा भेजें या /cancel।",
        'invalid_format': "⚠️ गलत फॉर्मेट।",
        'file_forwarded_admin': "📁 यूज़र से नई फाइल",
    },
    'bn': {
        'name': '🇧🇩 বাংলা',
        'welcome': "〽️ স্বাগতম, {name}!",
        'your_id': "🆔 আপনার ইউজার আইডি",
        'username': "✳️ ইউজারনেম",
        'status': "🔰 আপনার স্ট্যাটাস",
        'files': "📁 আপলোড করা ফাইল",
        'bots': "🤖 চলমান বট",
        'owner': "👑 মালিক",
        'admin': "🛡️ অ্যাডমিন",
        'premium': "⭐ প্রিমিয়াম",
        'free_user': "🆓 ফ্রি ইউজার",
        'expired_sub': "🆓 ফ্রি ইউজার (মেয়াদ শেষ)",
        'expires_in': "⏳ সাবস্ক্রিপশন {days} দিনে শেষ হবে",
        'send_file': "📤 আপনার Python (`.py`), JS (`.js`), বা ZIP (`.zip`) ফাইল পাঠান।",
        'no_files': "📂 আপনার ফাইল:\n\n(এখনো কোনো ফাইল আপলোড হয়নি)",
        'your_files': "📂 আপনার ফাইল:\nম্যানেজ করতে ক্লিক করুন।",
        'bot_locked': "⚠️ বট অ্যাডমিন দ্বারা লক করা হয়েছে। পরে চেষ্টা করুন।",
        'force_join_required': "🔒 **চ্যানেল জয়েন করা বাধ্যতামূলক**\n\nবট ব্যবহার করতে প্রথমে আমাদের চ্যানেল জয়েন করুন!\n\nজয়েন করার পর '✅ I've Joined - Verify' ক্লিক করুন",
        'join_channel': "📢 চ্যানেল জয়েন করুন",
        'verify_join': "✅ আমি জয়েন করেছি - ভেরিফাই",
        'verified': "✅ ভেরিফাইড! এখন আপনি বট ব্যবহার করতে পারেন।",
        'not_joined': "❌ আপনি এখনো সব চ্যানেল জয়েন করেননি!",
        'file_limit_reached': "⚠️ ফাইল লিমিট ({current}/{limit}) পূর্ণ। আগে ফাইল ডিলিট করুন।",
        'bot_limit_reached': "⚠️ বট লিমিট ({current}/{limit}) পূর্ণ। আগে কিছু বট বন্ধ করুন।",
        'upload_success': "✅ ফাইল এক্সট্রাক্ট হয়েছে। মূল স্ক্রিপ্ট চালু হচ্ছে: `{name}`...",
        'script_started': "✅ {type} স্ক্রিপ্ট '{name}' চালু হয়েছে! (PID: {pid})",
        'script_stopped': "🔴 স্ক্রিপ্ট বন্ধ হয়েছে।",
        'delete_confirm': "🗑️ `{name}` ডিলিট হয়েছে!",
        'download_started': "⏳ `{name}` ডাউনলোড হচ্ছে...",
        'download_done': "✅ ডাউনলোড হয়েছে। প্রসেস হচ্ছে...",
        'unsupported_file': "⚠️ শুধুমাত্র `.py`, `.js`, `.zip` অনুমোদিত।",
        'file_too_large': "⚠️ ফাইল অনেক বড় (Max: 20 MB)।",
        'speed_test': "⚡ বট স্পিড ও স্ট্যাটাস:",
        'response_time': "⏱️ API রেসপন্স টাইম",
        'bot_status': "🚦 বট স্ট্যাটাস",
        'your_level': "👤 আপনার লেভেল",
        'unlocked': "🔓 আনলকড",
        'locked': "🔒 লকড",
        'stats': "📊 বট স্ট্যাটিসটিক্স:",
        'total_users': "👥 মোট ইউজার",
        'total_files': "📂 মোট ফাইল রেকর্ড",
        'active_bots': "🟢 মোট এক্টিভ বট",
        'your_running_bots': "🤖 আপনার চলমান বট",
        'updates_channel': "📢 আপডেট চ্যানেল",
        'upload_file': "📤 ফাইল আপলোড",
        'check_files': "📂 ফাইল চেক",
        'bot_speed': "⚡ বট স্পিড",
        'statistics': "📊 স্ট্যাটিসটিক্স",
        'contact_owner': "📞 মালিকের সাথে যোগাযোগ",
        'subscriptions': "💳 সাবস্ক্রিপশন",
        'broadcast': "📢 ব্রডকাস্ট",
        'lock_bot': "🔒 বট লক",
        'unlock_bot': "🔓 বট আনলক",
        'run_all': "🟢 সব কোড চালান",
        'admin_panel': "👑 অ্যাডমিন প্যানেল",
        'force_join_settings': "⚙️ ফোর্স জয়েন সেটিংস",
        'send_notification': "🔔 নোটিফিকেশন পাঠান",
        'change_language': "🌐 ভাষা পরিবর্তন",
        'back_to_main': "🔙 মেইন মেনু",
        'back_to_files': "🔙 ফাইলে ফিরে যান",
        'start': "🟢 চালু",
        'stop': "🔴 বন্ধ",
        'restart': "🔄 রিস্টার্ট",
        'delete': "🗑️ ডিলিট",
        'logs': "📜 লগস",
        'view_logs': "📜 লগস দেখুন",
        'contact_owner_btn': "📞 মালিকের সাথে যোগাযোগ",
        'select_language': "🌐 **আপনার ভাষা নির্বাচন করুন**\n\nআপনার পছন্দের ভাষা বেছে নিন:",
        'language_changed': "✅ ভাষা বাংলায় পরিবর্তন হয়েছে!",
        'notification_sent': "🔔 সব ইউজারকে নোটিফিকেশন পাঠানো হয়েছে!",
        'add_channel_prompt': "📢 চ্যানেল ইউজারনেম পাঠান (যেমন `@channelname` বা `channelname`)\n\n/cancel বাতিল করতে।",
        'channel_added': "✅ চ্যানেল যোগ করা হয়েছে: {username}",
        'channel_removed': "✅ চ্যানেল সরানো হয়েছে।",
        'invalid_channel': "⚠️ ভুল চ্যানেল ইউজারনেম। আবার পাঠান বা /cancel।",
        'invalid_format': "⚠️ ভুল ফরম্যাট।",
        'file_forwarded_admin': "📁 ইউজার থেকে নতুন ফাইল",
    },
    'zh': {
        'name': '🇨🇳 中文',
        'welcome': "〽️ 欢迎, {name}!",
        'your_id': "🆔 您的用户ID",
        'username': "✳️ 用户名",
        'status': "🔰 您的状态",
        'files': "📁 已上传文件",
        'bots': "🤖 运行中的机器人",
        'owner': "👑 所有者",
        'admin': "🛡️ 管理员",
        'premium': "⭐ 高级会员",
        'free_user': "🆓 免费用户",
        'expired_sub': "🆓 免费用户（已过期）",
        'expires_in': "⏳ 订阅将在 {days} 天后过期",
        'send_file': "📤 发送您的 Python (`.py`)、JS (`.js`) 或 ZIP (`.zip`) 文件。",
        'no_files': "📂 您的文件:\n\n(还没有上传文件)",
        'your_files': "📂 您的文件:\n点击管理。",
        'bot_locked': "⚠️ 机器人已被管理员锁定。请稍后再试。",
        'force_join_required': "🔒 **需要强制加入**\n\n要使用此机器人，您必须先加入我们的频道！\n\n加入后，点击 '✅ I've Joined - Verify'",
        'join_channel': "📢 加入频道",
        'verify_join': "✅ 我已加入 - 验证",
        'verified': "✅ 验证成功！您现在可以使用机器人了。",
        'not_joined': "❌ 您还没有加入所有频道！",
        'file_limit_reached': "⚠️ 文件限制 ({current}/{limit}) 已达到。请先删除文件。",
        'bot_limit_reached': "⚠️ 机器人限制 ({current}/{limit}) 已达到。请先停止一些机器人。",
        'upload_success': "✅ 文件已解压。正在启动主脚本: `{name}`...",
        'script_started': "✅ {type} 脚本 '{name}' 已启动! (PID: {pid})",
        'script_stopped': "🔴 脚本已停止。",
        'delete_confirm': "🗑️ `{name}` 已删除!",
        'download_started': "⏳ 正在下载 `{name}`...",
        'download_done': "✅ 已下载。正在处理...",
        'unsupported_file': "⚠️ 仅允许 `.py`、`.js`、`.zip` 文件。",
        'file_too_large': "⚠️ 文件太大 (最大: 20 MB)。",
        'speed_test': "⚡ 机器人速度与状态:",
        'response_time': "⏱️ API 响应时间",
        'bot_status': "🚦 机器人状态",
        'your_level': "👤 您的等级",
        'unlocked': "🔓 已解锁",
        'locked': "🔒 已锁定",
        'stats': "📊 机器人统计:",
        'total_users': "👥 总用户数",
        'total_files': "📂 总文件记录",
        'active_bots': "🟢 总活跃机器人",
        'your_running_bots': "🤖 您运行中的机器人",
        'updates_channel': "📢 更新频道",
        'upload_file': "📤 上传文件",
        'check_files': "📂 检查文件",
        'bot_speed': "⚡ 机器人速度",
        'statistics': "📊 统计",
        'contact_owner': "📞 联系所有者",
        'subscriptions': "💳 订阅",
        'broadcast': "📢 广播",
        'lock_bot': "🔒 锁定机器人",
        'unlock_bot': "🔓 解锁机器人",
        'run_all': "🟢 运行所有代码",
        'admin_panel': "👑 管理面板",
        'force_join_settings': "⚙️ 强制加入设置",
        'send_notification': "🔔 发送通知",
        'change_language': "🌐 更改语言",
        'back_to_main': "🔙 返回主菜单",
        'back_to_files': "🔙 返回文件",
        'start': "🟢 启动",
        'stop': "🔴 停止",
        'restart': "🔄 重启",
        'delete': "🗑️ 删除",
        'logs': "📜 日志",
        'view_logs': "📜 查看日志",
        'contact_owner_btn': "📞 联系所有者",
        'select_language': "🌐 **选择您的语言**\n\n选择您喜欢的语言:",
        'language_changed': "✅ 语言已更改为中文!",
        'notification_sent': "🔔 通知已发送给所有用户!",
        'add_channel_prompt': "📢 发送频道用户名 (例如 `@channelname` 或 `channelname`)\n\n/cancel 取消。",
        'channel_added': "✅ 频道已添加: {username}",
        'channel_removed': "✅ 频道已移除。",
        'invalid_channel': "⚠️ 无效的频道用户名。请重新发送或 /cancel。",
        'invalid_format': "⚠️ 格式无效。",
        'file_forwarded_admin': "📁 来自用户的新文件",
    }
}

def get_lang(user_id):
    """Get user's language, default to English"""
    return user_languages.get(user_id, 'en')

def t(user_id, key, **kwargs):
    """Translate function"""
    lang = get_lang(user_id)
    text = LANGUAGES.get(lang, LANGUAGES['en']).get(key, LANGUAGES['en'].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text

# ==================== DATABASE ====================
def init_db():
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
                     (user_id INTEGER PRIMARY KEY, bot_limit INTEGER DEFAULT 5)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS force_join_channels
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_username TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_languages
                     (user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'en')''')
        
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('force_join_enabled', '1'))
        
        c.execute('SELECT COUNT(*) FROM force_join_channels')
        if c.fetchone()[0] == 0:
            c.execute('INSERT INTO force_join_channels (channel_username) VALUES (?)', (DEFAULT_FORCE_JOIN_USERNAME,))
        
        c.execute('INSERT OR IGNORE INTO admins (user_id, bot_limit) VALUES (?, ?)', (OWNER_ID, 999999))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"DB init error: {e}", exc_info=True)

def load_data():
    global force_join_enabled, force_join_usernames
    logger.info("Loading data...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()

        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except: pass

        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files: user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))

        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())

        c.execute('SELECT user_id, bot_limit FROM admins')
        for admin_id, bot_limit in c.fetchall():
            admin_ids.add(admin_id)
            admin_bot_limits[admin_id] = bot_limit if bot_limit else DEFAULT_ADMIN_BOT_LIMIT

        c.execute('SELECT key, value FROM settings')
        for key, value in c.fetchall():
            if key == 'force_join_enabled':
                force_join_enabled = value == '1'

        c.execute('SELECT channel_username FROM force_join_channels')
        force_join_usernames = [row[0] for row in c.fetchall()]

        c.execute('SELECT user_id, language FROM user_languages')
        for user_id, lang in c.fetchall():
            user_languages[user_id] = lang

        conn.close()
        logger.info(f"Loaded: {len(active_users)} users, {len(admin_ids)} admins")
    except Exception as e:
        logger.error(f"Load error: {e}", exc_info=True)

init_db()
load_data()

# ==================== HELPERS ====================
def get_user_folder(user_id):
    folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_file_limit(user_id):
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_bot_limit(user_id):
    if user_id == OWNER_ID: return OWNER_BOT_LIMIT
    if user_id in admin_ids:
        return admin_bot_limits.get(user_id, DEFAULT_ADMIN_BOT_LIMIT)
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_BOT_LIMIT
    return FREE_BOT_LIMIT

def get_user_running_bots(user_id):
    count = 0
    for script_key in bot_scripts.keys():
        if script_key.startswith(f"{user_id}_"):
            count += 1
    return count

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_user_joined_force_channels(user_id):
    if not force_join_enabled:
        return True
    if user_id == OWNER_ID or user_id in admin_ids:
        return True
    if not force_join_usernames:
        return True
    
    for channel_username in force_join_usernames:
        if not channel_username:
            continue
        try:
            username = channel_username.replace('@', '')
            member = bot.get_chat_member(f"@{username}", user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            logger.warning(f"Membership check failed for {channel_username}: {e}")
            # Don't block if check fails
            continue
    return True

def get_force_join_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, username in enumerate(force_join_usernames):
        clean_username = username.replace('@', '')
        link = f"https://t.me/{clean_username}"
        btn_text = t(user_id, 'join_channel')
        if len(force_join_usernames) > 1:
            btn_text = f"{t(user_id, 'join_channel')} {i+1}"
        markup.add(types.InlineKeyboardButton(btn_text, url=link))
    markup.add(types.InlineKeyboardButton(t(user_id, 'verify_join'), callback_data='verify_join'))
    return markup

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                    try: script_info['log_file'].close()
                    except: pass
                if script_key in bot_scripts: del bot_scripts[script_key]
            return is_running
        except psutil.NoSuchProcess:
            if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                try: script_info['log_file'].close()
                except: pass
            if script_key in bot_scripts: del bot_scripts[script_key]
            return False
        except Exception as e:
            logger.error(f"Status check error: {e}", exc_info=True)
            return False
    return False

def kill_process_tree(process_info):
    pid = None
    script_key = process_info.get('script_key', 'N/A')
    try:
        if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
            try: process_info['log_file'].close()
            except: pass

        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            pid = process.pid
            if pid:
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try: child.terminate()
                        except: 
                            try: child.kill()
                            except: pass
                    gone, alive = psutil.wait_procs(children, timeout=1)
                    for p in alive:
                        try: p.kill()
                        except: pass
                    try:
                        parent.terminate()
                        try: parent.wait(timeout=1)
                        except psutil.TimeoutExpired: parent.kill()
                    except psutil.NoSuchProcess: pass
                    except: 
                        try: parent.kill()
                        except: pass
                except psutil.NoSuchProcess: pass
    except Exception as e:
        logger.error(f"Kill error: {e}", exc_info=True)

# ==================== MODULES ====================
TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram', 'pyrogram': 'pyrogram', 'telethon': 'telethon',
    'tgcrypto': 'tgcrypto', 'bs4': 'beautifulsoup4', 'requests': 'requests',
    'pillow': 'Pillow', 'cv2': 'opencv-python', 'yaml': 'PyYAML',
    'dotenv': 'python-dotenv', 'dateutil': 'python-dateutil',
    'pandas': 'pandas', 'numpy': 'numpy', 'flask': 'Flask',
    'django': 'Django', 'sqlalchemy': 'SQLAlchemy', 'psutil': 'psutil',
    'asyncio': None, 'json': None, 'datetime': None, 'os': None, 'sys': None,
    're': None, 'time': None, 'math': None, 'random': None, 'logging': None,
    'threading': None, 'subprocess': None, 'zipfile': None, 'tempfile': None,
    'shutil': None, 'sqlite3': None, 'atexit': None
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None: return False
    try:
        bot.reply_to(message, f"🐍 Installing `{package_name}`...", parse_mode='Markdown')
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package_name],
                                capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"✅ Installed `{package_name}`.", parse_mode='Markdown')
            return True
        bot.reply_to(message, f"❌ Failed to install `{package_name}`.")
        return False
    except Exception as e:
        logger.error(f"Install error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error installing `{package_name}`.")
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"🟠 Installing `{module_name}`...", parse_mode='Markdown')
        result = subprocess.run(['npm', 'install', module_name], capture_output=True, text=True,
                                check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"✅ Installed `{module_name}`.", parse_mode='Markdown')
            return True
        bot.reply_to(message, f"❌ Failed to install `{module_name}`.")
        return False
    except FileNotFoundError:
        bot.reply_to(message, "❌ 'npm' not found.")
        return False
    except Exception as e:
        logger.error(f"npm error: {e}", exc_info=True)
        return False

def notify_admin_file_upload(user_id, file_name, file_type):
    """Notify admin when user uploads a file"""
    try:
        user_name = "Unknown"
        try:
            chat = bot.get_chat(user_id)
            user_name = chat.first_name or "Unknown"
        except: pass
        
        msg = (f"📁 **New File Uploaded**\n\n"
               f"👤 User: {user_name}\n"
               f"🆔 User ID: `{user_id}`\n"
               f"📄 File: `{file_name}`\n"
               f"🔧 Type: {file_type.upper()}\n"
               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        bot.send_message(OWNER_ID, msg, parse_mode='Markdown')
        for admin_id in admin_ids:
            if admin_id != OWNER_ID:
                try: bot.send_message(admin_id, msg, parse_mode='Markdown')
                except: pass
    except Exception as e:
        logger.error(f"Notify admin error: {e}")

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Failed to run '{file_name}' after {max_attempts} attempts.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Running Python: {script_path} (Key: {script_key})")

    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Script '{file_name}' not found!")
            if script_owner_id in user_files:
                user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_proc = None
            try:
                check_proc = subprocess.Popen([sys.executable, script_path], cwd=user_folder,
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                              text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                if check_proc.returncode != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        return
                    else:
                        bot.reply_to(message_obj_for_reply, f"❌ Error in '{file_name}':\n```\n{stderr[:500]}\n```", parse_mode='Markdown')
                        return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, "❌ Python not found.")
                return
            except Exception as e:
                logger.error(f"Pre-check error: {e}", exc_info=True)
                return
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill(); check_proc.communicate()

        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"❌ Log file error.")
            return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen([sys.executable, script_path], cwd=user_folder,
                                       stdout=log_file, stderr=log_file, stdin=subprocess.PIPE,
                                       startupinfo=startupinfo, creationflags=creationflags,
                                       encoding='utf-8', errors='ignore')
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
            }
            lang = get_lang(script_owner_id)
            bot.reply_to(message_obj_for_reply, t(script_owner_id, 'script_started', type='Python', name=file_name, pid=process.pid))
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
            if process and process.poll() is None:
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        logger.error(f"Run error: {e}", exc_info=True)
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"❌ Failed after {max_attempts} attempts.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Running JS: {script_path} (Key: {script_key})")

    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Not found!")
            if script_owner_id in user_files:
                user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
            remove_user_file_db(script_owner_id, file_name)
            return

        if attempt == 1:
            check_proc = None
            try:
                check_proc = subprocess.Popen(['node', script_path], cwd=user_folder,
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                              text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                if check_proc.returncode != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                            if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                time.sleep(2)
                                threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                return
                            return
                    bot.reply_to(message_obj_for_reply, f"❌ Error:\n```\n{stderr[:500]}\n```", parse_mode='Markdown')
                    return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, "❌ 'node' not found.")
                return
            finally:
                if check_proc and check_proc.poll() is None:
                    check_proc.kill(); check_proc.communicate()

        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"❌ Log error.")
            return
        try:
            process = subprocess.Popen(['node', script_path], cwd=user_folder,
                                       stdout=log_file, stderr=log_file, stdin=subprocess.PIPE,
                                       encoding='utf-8', errors='ignore')
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'js', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, t(script_owner_id, 'script_started', type='JS', name=file_name, pid=process.pid))
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
            if process and process.poll() is None:
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        logger.error(f"JS error: {e}", exc_info=True)
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key])
            del bot_scripts[script_key]

# ==================== DB OPS ====================
DB_LOCK = threading.Lock()

def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)',
                      (user_id, file_name, file_type))
            conn.commit()
            if user_id not in user_files: user_files[user_id] = []
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
        except Exception as e: logger.error(f"Save file error: {e}", exc_info=True)
        finally: conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]: del user_files[user_id]
        except Exception as e: logger.error(f"Remove file error: {e}", exc_info=True)
        finally: conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
        except Exception as e: logger.error(f"Add user error: {e}", exc_info=True)
        finally: conn.close()

def save_user_language(user_id, language):
    user_languages[user_id] = language
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_languages (user_id, language) VALUES (?, ?)', (user_id, language))
            conn.commit()
        except Exception as e: logger.error(f"Save lang error: {e}", exc_info=True)
        finally: conn.close()

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry.isoformat()))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
        except Exception as e: logger.error(f"Save sub error: {e}", exc_info=True)
        finally: conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_subscriptions: del user_subscriptions[user_id]
        except Exception as e: logger.error(f"Remove sub error: {e}", exc_info=True)
        finally: conn.close()

def add_admin_db(admin_id, bot_limit=DEFAULT_ADMIN_BOT_LIMIT):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO admins (user_id, bot_limit) VALUES (?, ?)', (admin_id, bot_limit))
            conn.commit()
            admin_ids.add(admin_id)
            admin_bot_limits[admin_id] = bot_limit
        except Exception as e: logger.error(f"Add admin error: {e}", exc_info=True)
        finally: conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID: return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
            conn.commit()
            removed = c.rowcount > 0
            if removed:
                admin_ids.discard(admin_id)
                if admin_id in admin_bot_limits: del admin_bot_limits[admin_id]
            return removed
        except Exception as e: logger.error(f"Remove admin error: {e}", exc_info=True); return False
        finally: conn.close()

def save_setting(key, value):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
            conn.commit()
        except Exception as e: logger.error(f"Save setting error: {e}", exc_info=True)
        finally: conn.close()

def add_force_join_channel(username):
    """Add force join channel - accepts username only"""
    if not username.startswith('@'):
        username = '@' + username
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO force_join_channels (channel_username) VALUES (?)', (username,))
            conn.commit()
            force_join_usernames.append(username)
            return True
        except Exception as e: logger.error(f"Add channel error: {e}", exc_info=True); return False
        finally: conn.close()

def remove_force_join_channel(index):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('SELECT id FROM force_join_channels LIMIT 1 OFFSET ?', (index,))
            row = c.fetchone()
            if row:
                c.execute('DELETE FROM force_join_channels WHERE id = ?', (row[0],))
                conn.commit()
                if index < len(force_join_usernames):
                    force_join_usernames.pop(index)
                return True
        except Exception as e: logger.error(f"Remove channel error: {e}", exc_info=True)
        finally: conn.close()
    return False

# ==================== MENUS ====================
def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(t(user_id, 'updates_channel'), url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'))
    markup.add(types.InlineKeyboardButton(t(user_id, 'upload_file'), callback_data='upload'),
               types.InlineKeyboardButton(t(user_id, 'check_files'), callback_data='check_files'))
    markup.add(types.InlineKeyboardButton(t(user_id, 'bot_speed'), callback_data='speed'),
               types.InlineKeyboardButton(t(user_id, 'statistics'), callback_data='stats'))
    markup.add(types.InlineKeyboardButton(t(user_id, 'change_language'), callback_data='change_language'))
    
    if user_id in admin_ids:
        markup.add(types.InlineKeyboardButton(t(user_id, 'subscriptions'), callback_data='subscription'),
                   types.InlineKeyboardButton(t(user_id, 'broadcast'), callback_data='broadcast'))
        lock_text = t(user_id, 'lock_bot') if not bot_locked else t(user_id, 'unlock_bot')
        lock_cb = 'lock_bot' if not bot_locked else 'unlock_bot'
        markup.add(types.InlineKeyboardButton(lock_text, callback_data=lock_cb),
                   types.InlineKeyboardButton(t(user_id, 'run_all'), callback_data='run_all_scripts'))
        markup.add(types.InlineKeyboardButton(t(user_id, 'send_notification'), callback_data='send_notification'),
                   types.InlineKeyboardButton(t(user_id, 'force_join_settings'), callback_data='force_join_settings'))
        markup.add(types.InlineKeyboardButton(t(user_id, 'admin_panel'), callback_data='admin_panel'))
    
    markup.add(types.InlineKeyboardButton(t(user_id, 'contact_owner_btn'), url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id in admin_ids:
        layout = [
            [t(user_id, 'updates_channel')],
            [t(user_id, 'upload_file'), t(user_id, 'check_files')],
            [t(user_id, 'bot_speed'), t(user_id, 'statistics')],
            [t(user_id, 'change_language')],
            [t(user_id, 'subscriptions'), t(user_id, 'broadcast')],
            [t(user_id, 'lock_bot'), t(user_id, 'run_all')],
            [t(user_id, 'send_notification'), t(user_id, 'force_join_settings')],
            [t(user_id, 'admin_panel'), t(user_id, 'contact_owner')]
        ]
    else:
        layout = [
            [t(user_id, 'updates_channel')],
            [t(user_id, 'upload_file'), t(user_id, 'check_files')],
            [t(user_id, 'bot_speed'), t(user_id, 'statistics')],
            [t(user_id, 'change_language')],
            [t(user_id, 'contact_owner')]
        ]
    for row in layout:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup

def create_control_buttons(user_id, script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton(t(user_id, 'stop'), callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton(t(user_id, 'restart'), callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton(t(user_id, 'delete'), callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton(t(user_id, 'logs'), callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton(t(user_id, 'start'), callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton(t(user_id, 'delete'), callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton(t(user_id, 'view_logs'), callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    markup.add(types.InlineKeyboardButton(t(user_id, 'back_to_files'), callback_data='check_files'))
    return markup

def create_admin_panel(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Admin', callback_data='add_admin'),
        types.InlineKeyboardButton('➖ Remove Admin', callback_data='remove_admin')
    )
    markup.row(types.InlineKeyboardButton('📋 List Admins', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('⚙️ Set Admin Bot Limit', callback_data='set_admin_limit'))
    markup.row(types.InlineKeyboardButton(t(user_id, 'back_to_main'), callback_data='back_to_main'))
    return markup

def create_subscription_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription'),
        types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription')
    )
    markup.row(types.InlineKeyboardButton('🔍 Check Subscription', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton(t(user_id, 'back_to_main'), callback_data='back_to_main'))
    return markup

def create_force_join_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Channel', callback_data='add_force_channel'),
        types.InlineKeyboardButton('➖ Remove Channel', callback_data='remove_force_channel')
    )
    markup.row(types.InlineKeyboardButton('📋 List Channels', callback_data='list_force_channels'))
    status = "🟢 ON" if force_join_enabled else "🔴 OFF"
    markup.row(types.InlineKeyboardButton(f'Force Join: {status}', callback_data='toggle_force_join'))
    markup.row(types.InlineKeyboardButton(t(user_id, 'back_to_main'), callback_data='back_to_main'))
    return markup

def create_language_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('🇬🇧 English', callback_data='lang_en'),
        types.InlineKeyboardButton('🇮🇳 हिन्दी', callback_data='lang_hi')
    )
    markup.add(
        types.InlineKeyboardButton('🇧🇩 বাংলা', callback_data='lang_bn'),
        types.InlineKeyboardButton('🇨🇳 中文', callback_data='lang_zh')
    )
    return markup

# ==================== FILE HANDLING ====================
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
            bot.reply_to(message, "🔄 Installing Python deps...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path],
                               capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                bot.reply_to(message, "✅ Python deps installed.")
            except Exception as e:
                bot.reply_to(message, "❌ Failed to install deps.")
                return

        if pkg_json:
            bot.reply_to(message, "🔄 Installing Node deps...")
            try:
                subprocess.run(['npm', 'install'], capture_output=True, text=True, check=True,
                               cwd=temp_dir, encoding='utf-8', errors='ignore')
                bot.reply_to(message, "✅ Node deps installed.")
            except Exception as e:
                bot.reply_to(message, "❌ Failed to install Node deps.")
                return

        main_script_name = None
        file_type = None
        preferred_py = ['main.py', 'bot.py', 'app.py']
        preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
        for p in preferred_py:
            if p in py_files: main_script_name = p; file_type = 'py'; break
        if not main_script_name:
            for p in preferred_js:
                if p in js_files: main_script_name = p; file_type = 'js'; break
        if not main_script_name:
            if py_files: main_script_name = py_files[0]; file_type = 'py'
            elif js_files: main_script_name = js_files[0]; file_type = 'js'
        if not main_script_name:
            bot.reply_to(message, "❌ No `.py` or `.js` script found!")
            return

        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path): shutil.rmtree(dest_path)
            elif os.path.exists(dest_path): os.remove(dest_path)
            shutil.move(src_path, dest_path)

        save_user_file(user_id, main_script_name, file_type)
        main_script_path = os.path.join(user_folder, main_script_name)
        
        # Notify admins
        notify_admin_file_upload(user_id, main_script_name, file_type)
        
        bot.reply_to(message, t(user_id, 'upload_success', name=main_script_name), parse_mode='Markdown')

        if file_type == 'py':
            threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()

    except zipfile.BadZipFile as e:
        bot.reply_to(message, f"❌ Invalid ZIP: {e}")
    except Exception as e:
        logger.error(f"Zip error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except: pass

def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        notify_admin_file_upload(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"JS error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        notify_admin_file_upload(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"Py error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ==================== LOGIC ====================
def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username

    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, t(user_id, 'bot_locked'))
        return

    # First-time: ask language
    if user_id not in user_languages and user_id not in admin_ids:
        bot.send_message(chat_id, LANGUAGES['en']['select_language'], reply_markup=create_language_menu(), parse_mode='Markdown')
        return

    if not is_user_joined_force_channels(user_id):
        bot.send_message(chat_id, t(user_id, 'force_join_required'), reply_markup=get_force_join_markup(user_id), parse_mode='Markdown')
        return

    photo_file_id = None
    try:
        photos = bot.get_user_profile_photos(user_id, limit=1)
        if photos.photos: photo_file_id = photos.photos[0][-1].file_id
    except: pass

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            user_bio = "N/A"
            try: user_bio = bot.get_chat(user_id).bio or "No bio"
            except: pass
            owner_msg = (f"🎉 New user!\n👤 {user_name}\n✳️ @{user_username or 'N/A'}\n"
                         f"🆔 `{user_id}`\n📝 Bio: {user_bio}")
            bot.send_message(OWNER_ID, owner_msg, parse_mode='Markdown')
            if photo_file_id: bot.send_photo(OWNER_ID, photo_file_id, caption=f"New user {user_id}")
        except Exception as e: logger.error(f"Notify owner: {e}")

    file_limit = get_user_file_limit(user_id)
    bot_limit = get_user_bot_limit(user_id)
    current_files = get_user_file_count(user_id)
    current_bots = get_user_running_bots(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "∞"
    bot_limit_str = str(bot_limit) if bot_limit != float('inf') else "∞"
    expiry_info = ""
    if user_id == OWNER_ID: user_status = t(user_id, 'owner')
    elif user_id in admin_ids: user_status = t(user_id, 'admin')
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = t(user_id, 'premium'); days_left = (expiry_date - datetime.now()).days
            expiry_info = "\n" + t(user_id, 'expires_in', days=days_left)
        else:
            user_status = t(user_id, 'expired_sub')
            remove_subscription_db(user_id)
    else: user_status = t(user_id, 'free_user')

    welcome_text = (f"{t(user_id, 'welcome', name=user_name)}\n\n"
                    f"{t(user_id, 'your_id')}: `{user_id}`\n"
                    f"{t(user_id, 'username')}: `@{user_username or 'N/A'}`\n"
                    f"{t(user_id, 'status')}: {user_status}{expiry_info}\n"
                    f"{t(user_id, 'files')}: {current_files} / {limit_str}\n"
                    f"{t(user_id, 'bots')}: {current_bots} / {bot_limit_str}\n\n"
                    f"👇 Use buttons or type commands.")
    
    try:
        if photo_file_id: bot.send_photo(chat_id, photo_file_id)
        bot.send_message(chat_id, welcome_text, reply_markup=create_reply_keyboard_main_menu(user_id), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Welcome error: {e}", exc_info=True)
        try: bot.send_message(chat_id, welcome_text, reply_markup=create_reply_keyboard_main_menu(user_id), parse_mode='Markdown')
        except: pass

def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, t(user_id, 'bot_locked')); return
    if not is_user_joined_force_channels(user_id):
        bot.reply_to(message, t(user_id, 'force_join_required'), reply_markup=get_force_join_markup(user_id)); return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "∞"
        bot.reply_to(message, t(user_id, 'file_limit_reached', current=current_files, limit=limit_str))
        return
    bot.reply_to(message, t(user_id, 'send_file'), parse_mode='Markdown')

def _logic_check_files(message):
    user_id = message.from_user.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.reply_to(message, t(user_id, 'no_files'))
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢" if is_running else "🔴"
        btn_text = f"{status_icon} {file_name} ({file_type})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    bot.reply_to(message, t(user_id, 'your_files'), reply_markup=markup)

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, "🏃...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = t(user_id, 'unlocked') if not bot_locked else t(user_id, 'locked')
        if user_id == OWNER_ID: user_level = t(user_id, 'owner')
        elif user_id in admin_ids: user_level = t(user_id, 'admin')
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = t(user_id, 'premium')
        else: user_level = t(user_id, 'free_user')
        speed_msg = (f"{t(user_id, 'speed_test')}\n\n"
                     f"{t(user_id, 'response_time')}: {response_time} ms\n"
                     f"{t(user_id, 'bot_status')}: {status}\n"
                     f"{t(user_id, 'your_level')}: {user_level}")
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id)
    except Exception as e:
        logger.error(f"Speed error: {e}", exc_info=True)
        bot.edit_message_text("❌ Error.", chat_id, wait_msg.message_id)

def _logic_contact_owner(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(t(user_id, 'contact_owner_btn'), url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    bot.reply_to(message, "👇", reply_markup=markup)

def _logic_updates_channel(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(t(user_id, 'updates_channel'), url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'))
    bot.reply_to(message, "👇", reply_markup=markup)

def _logic_change_language(message):
    user_id = message.from_user.id
    bot.reply_to(message, t(user_id, 'select_language'), reply_markup=create_language_menu(), parse_mode='Markdown')

def _logic_statistics(message):
    user_id = message.from_user.id
    total_users = len(active_users)
    total_files_records = sum(len(files) for files in user_files.values())
    running_bots_count = 0
    user_running_bots = 0
    for script_key_iter in list(bot_scripts.keys()):
        s_owner_id_str, _ = script_key_iter.split('_', 1)
        s_owner_id = int(s_owner_id_str)
        if is_bot_running(s_owner_id, bot_scripts[script_key_iter]['file_name']):
            running_bots_count += 1
            if s_owner_id == user_id: user_running_bots += 1
    stats_msg = (f"{t(user_id, 'stats')}\n\n"
                 f"{t(user_id, 'total_users')}: {total_users}\n"
                 f"{t(user_id, 'total_files')}: {total_files_records}\n"
                 f"{t(user_id, 'active_bots')}: {running_bots_count}\n"
                 f"{t(user_id, 'your_running_bots')}: {user_running_bots}")
    if user_id in admin_ids:
        stats_msg += f"\n\n🔒 Bot: {'Locked' if bot_locked else 'Unlocked'}\n📢 Force Join: {'ON' if force_join_enabled else 'OFF'}"
    bot.reply_to(message, stats_msg)

def _logic_subscriptions_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only."); return
    bot.reply_to(message, "💳 Subscription Management", reply_markup=create_subscription_menu(message.from_user.id))

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only."); return
    msg = bot.reply_to(message, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only."); return
    global bot_locked
    bot_locked = not bot_locked
    bot.reply_to(message, f"🔒 Bot {'locked' if bot_locked else 'unlocked'}.")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only."); return
    bot.reply_to(message, "👑 Admin Panel", reply_markup=create_admin_panel(message.from_user.id))

def _logic_force_join_settings(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only."); return
    status = "🟢 ON" if force_join_enabled else "🔴 OFF"
    channels_list = "\n".join([f"{i+1}. {u}" for i, u in enumerate(force_join_usernames)])
    bot.reply_to(message, f"⚙️ Force Join Settings\n\nStatus: {status}\nChannels:\n{channels_list or 'None'}",
                 reply_markup=create_force_join_menu(message.from_user.id))

def _logic_send_notification(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin only."); return
    msg = bot.reply_to(message, "🔔 Send notification to all users.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_send_notification)

def process_send_notification(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled."); return
    if not message.text:
        bot.reply_to(message, "⚠️ Send text.")
        return
    notification_text = message.text
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Send", callback_data=f'confirm_notification_{message.message_id}'),
        types.InlineKeyboardButton("❌ Cancel", callback_data='cancel_notification')
    )
    bot.reply_to(message, f"🔔 Confirm notification:\n\n```\n{notification_text[:500]}\n```\nTo {len(active_users)} users?",
                 reply_markup=markup, parse_mode='Markdown')

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
    else: return

    if admin_user_id not in admin_ids:
        reply_func("⚠️ Admin only."); return

    reply_func("⏳ Starting all user scripts...")
    started_count = 0
    for target_user_id, files_for_user in dict(user_files).items():
        if not files_for_user: continue
        user_folder = get_user_folder(target_user_id)
        for file_name, file_type in files_for_user:
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    if file_type == 'py':
                        threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj)).start()
                        started_count += 1
                    elif file_type == 'js':
                        threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj)).start()
                        started_count += 1
                    time.sleep(0.5)
    reply_func(f"✅ Started {started_count} scripts.")

# ==================== BUTTON MAP ====================
def get_button_map(user_id):
    return {
        t(user_id, 'updates_channel'): _logic_updates_channel,
        t(user_id, 'upload_file'): _logic_upload_file,
        t(user_id, 'check_files'): _logic_check_files,
        t(user_id, 'bot_speed'): _logic_bot_speed,
        t(user_id, 'statistics'): _logic_statistics,
        t(user_id, 'contact_owner'): _logic_contact_owner,
        t(user_id, 'change_language'): _logic_change_language,
        t(user_id, 'subscriptions'): _logic_subscriptions_panel,
        t(user_id, 'broadcast'): _logic_broadcast_init,
        t(user_id, 'lock_bot'): _logic_toggle_lock_bot,
        t(user_id, 'unlock_bot'): _logic_toggle_lock_bot,
        t(user_id, 'run_all'): _logic_run_all_scripts,
        t(user_id, 'admin_panel'): _logic_admin_panel,
        t(user_id, 'force_join_settings'): _logic_force_join_settings,
        t(user_id, 'send_notification'): _logic_send_notification,
    }

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message): _logic_send_welcome(message)

@bot.message_handler(commands=['lang', 'language', 'changelang'])
def command_language(message): _logic_change_language(message)

@bot.message_handler(commands=['status'])
def command_show_status(message): _logic_statistics(message)

@bot.message_handler(func=lambda message: message.text in get_button_map(message.from_user.id))
def handle_button_text(message):
    logic_func = get_button_map(message.from_user.id).get(message.text)
    if logic_func: logic_func(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    start_ping_time = time.time()
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! {latency} ms", message.chat.id, msg.message_id)

@bot.message_handler(commands=['uploadfile'])
def cmd_upload(message): _logic_upload_file(message)
@bot.message_handler(commands=['checkfiles'])
def cmd_check(message): _logic_check_files(message)
@bot.message_handler(commands=['botspeed'])
def cmd_speed(message): _logic_bot_speed(message)
@bot.message_handler(commands=['statistics'])
def cmd_stats(message): _logic_statistics(message)
@bot.message_handler(commands=['forcejoin'])
def cmd_fj(message): _logic_force_join_settings(message)
@bot.message_handler(commands=['notification'])
def cmd_notif(message): _logic_send_notification(message)
@bot.message_handler(commands=['adminpanel'])
def cmd_admin(message): _logic_admin_panel(message)

# ==================== DOCUMENT HANDLER ====================
@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, t(user_id, 'bot_locked')); return

    if not is_user_joined_force_channels(user_id):
        bot.reply_to(message, t(user_id, 'force_join_required'), reply_markup=get_force_join_markup(user_id)); return

    file_limit = get_user_file_limit(user_id)
    if get_user_file_count(user_id) >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "∞"
        bot.reply_to(message, t(user_id, 'file_limit_reached', current=get_user_file_count(user_id), limit=limit_str))
        return

    bot_limit = get_user_bot_limit(user_id)
    if get_user_running_bots(user_id) >= bot_limit:
        bot_limit_str = str(bot_limit) if bot_limit != float('inf') else "∞"
        bot.reply_to(message, t(user_id, 'bot_limit_reached', current=get_user_running_bots(user_id), limit=bot_limit_str))
        return

    file_name = doc.file_name
    if not file_name:
        bot.reply_to(message, "⚠️ No file name."); return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, t(user_id, 'unsupported_file')); return
    if doc.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, t(user_id, 'file_too_large')); return

    try:
        # Forward file to owner and admins
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            user_info = f"👤 {message.from_user.first_name} (`{user_id}`)"
            bot.send_message(OWNER_ID, f"📁 {t(user_id, 'file_forwarded_admin')}: {user_info}", parse_mode='Markdown')
            for adm_id in admin_ids:
                if adm_id != OWNER_ID:
                    try:
                        bot.forward_message(adm_id, chat_id, message.message_id)
                        bot.send_message(adm_id, f"📁 {t(user_id, 'file_forwarded_admin')}: {user_info}", parse_mode='Markdown')
                    except: pass
        except Exception as e: logger.error(f"Forward fail: {e}")

        wait_msg = bot.reply_to(message, t(user_id, 'download_started', name=file_name), parse_mode='Markdown')
        file_info_tg = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info_tg.file_path)
        bot.edit_message_text(t(user_id, 'download_done'), chat_id, wait_msg.message_id)
        user_folder = get_user_folder(user_id)

        if file_ext == '.zip':
            handle_zip_file(downloaded, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f: f.write(downloaded)
            if file_ext == '.js': handle_js_file(file_path, user_id, user_folder, file_name, message)
            elif file_ext == '.py': handle_py_file(file_path, user_id, user_folder, file_name, message)
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"API error: {e}", exc_info=True)
        if "file is too big" in str(e).lower():
            bot.reply_to(message, "❌ File too large for Telegram API.")
        else: bot.reply_to(message, f"❌ API Error: {str(e)}")
    except Exception as e:
        logger.error(f"File error: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ==================== CALLBACKS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    # Language callbacks (always allowed)
    if data.startswith('lang_'):
        lang_code = data.replace('lang_', '')
        if lang_code in LANGUAGES:
            save_user_language(user_id, lang_code)
            bot.answer_callback_query(call.id, t(user_id, 'language_changed'))
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            _logic_send_welcome(call.message)
        return

    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats', 'verify_join', 'change_language']:
        bot.answer_callback_query(call.id, t(user_id, 'bot_locked'), show_alert=True); return

    try:
        if data == 'upload': upload_callback(call)
        elif data == 'check_files': check_files_callback(call)
        elif data == 'verify_join': verify_join_callback(call)
        elif data == 'change_language':
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(t(user_id, 'select_language'), call.message.chat.id,
                                      call.message.message_id, reply_markup=create_language_menu(), parse_mode='Markdown')
            except: pass
        elif data.startswith('file_'): file_control_callback(call)
        elif data.startswith('start_'): start_bot_callback(call)
        elif data.startswith('stop_'): stop_bot_callback(call)
        elif data.startswith('restart_'): restart_bot_callback(call)
        elif data.startswith('delete_'): delete_bot_callback(call)
        elif data.startswith('logs_'): logs_bot_callback(call)
        elif data == 'speed': speed_callback(call)
        elif data == 'back_to_main': back_to_main_callback(call)
        elif data.startswith('confirm_broadcast_'): handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast': handle_cancel_broadcast(call)
        elif data.startswith('confirm_notification_'): handle_confirm_notification(call)
        elif data == 'cancel_notification': handle_cancel_notification(call)
        elif data == 'subscription': admin_required(call, subscription_management_callback)
        elif data == 'stats': stats_callback(call)
        elif data == 'lock_bot': admin_required(call, lock_bot_callback)
        elif data == 'unlock_bot': admin_required(call, unlock_bot_callback)
        elif data == 'run_all_scripts': admin_required(call, run_all_scripts_callback)
        elif data == 'broadcast': admin_required(call, broadcast_init_callback)
        elif data == 'admin_panel': admin_required(call, admin_panel_callback)
        elif data == 'force_join_settings': admin_required(call, force_join_settings_callback)
        elif data == 'send_notification': admin_required(call, send_notification_callback)
        elif data == 'add_admin': owner_required(call, add_admin_init_callback)
        elif data == 'remove_admin': owner_required(call, remove_admin_init_callback)
        elif data == 'list_admins': admin_required(call, list_admins_callback)
        elif data == 'set_admin_limit': owner_required(call, set_admin_limit_callback)
        elif data == 'add_subscription': admin_required(call, add_subscription_init_callback)
        elif data == 'remove_subscription': admin_required(call, remove_subscription_init_callback)
        elif data == 'check_subscription': admin_required(call, check_subscription_init_callback)
        elif data == 'add_force_channel': admin_required(call, add_force_channel_callback)
        elif data == 'remove_force_channel': admin_required(call, remove_force_channel_callback)
        elif data == 'list_force_channels': admin_required(call, list_force_channels_callback)
        elif data == 'toggle_force_join': admin_required(call, toggle_force_join_callback)
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
    except Exception as e:
        logger.error(f"Callback error '{data}': {e}", exc_info=True)
        try: bot.answer_callback_query(call.id, "Error.", show_alert=True)
        except: pass

def admin_required(call, func):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True); return
    func(call)

def owner_required(call, func):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Owner only.", show_alert=True); return
    func(call)

def verify_join_callback(call):
    user_id = call.from_user.id
    if is_user_joined_force_channels(user_id):
        bot.answer_callback_query(call.id, t(user_id, 'verified'), show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        _logic_send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, t(user_id, 'not_joined'), show_alert=True)

def upload_callback(call):
    user_id = call.from_user.id
    if not is_user_joined_force_channels(user_id):
        bot.answer_callback_query(call.id, "🔒 Join first!", show_alert=True); return
    file_limit = get_user_file_limit(user_id)
    if get_user_file_count(user_id) >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "∞"
        bot.answer_callback_query(call.id, t(user_id, 'file_limit_reached', current=get_user_file_count(user_id), limit=limit_str), show_alert=True); return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, t(user_id, 'send_file'), parse_mode='Markdown')

def check_files_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id, "⚠️ No files.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(t(user_id, 'back_to_main'), callback_data='back_to_main'))
            bot.edit_message_text(t(user_id, 'no_files'), chat_id, call.message.message_id, reply_markup=markup)
        except: pass
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢" if is_running else "🔴"
        btn_text = f"{status_icon} {file_name} ({file_type})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton(t(user_id, 'back_to_main'), callback_data='back_to_main'))
    try:
        bot.edit_message_text(t(user_id, 'your_files'), chat_id, call.message.message_id, reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e): logger.error(f"Error: {e}")

def file_control_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        user_id = call.from_user.id
        if not (user_id == script_owner_id or user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Only your own files.", show_alert=True)
            check_files_callback(call); return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True)
            check_files_callback(call); return
        bot.answer_callback_query(call.id)
        is_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_running else '🔴 Stopped'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), '?')
        try:
            bot.edit_message_text(
                f"⚙️ `{file_name}` ({file_type})\nStatus: {status_text}",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(user_id, script_owner_id, file_name, is_running),
                parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e): raise
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error.", show_alert=True)

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        if not (user_id == script_owner_id or user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Denied.", show_alert=True); return
        bot_limit = get_user_bot_limit(script_owner_id)
        if get_user_running_bots(script_owner_id) >= bot_limit:
            bot_limit_str = str(bot_limit) if bot_limit != float('inf') else "∞"
            bot.answer_callback_query(call.id, t(user_id, 'bot_limit_reached', current=get_user_running_bots(script_owner_id), limit=bot_limit_str), show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, "⚠️ Missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name); check_files_callback(call); return
        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, "⚠️ Running.", show_alert=True); return
        bot.answer_callback_query(call.id, "⏳ Starting...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        time.sleep(1.5)
        is_now = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_now else '🟡 Starting'
        try:
            bot.edit_message_text(
                f"⚙️ `{file_name}` ({file_type})\nStatus: {status_text}",
                chat_id, call.message.message_id,
                reply_markup=create_control_buttons(user_id, script_owner_id, file_name, is_now), parse_mode='Markdown')
        except: pass
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error.", show_alert=True)

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        if not (user_id == script_owner_id or user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Denied.", show_alert=True); return
        script_key = f"{script_owner_id}_{file_name}"
        if not is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, "⚠️ Already stopped.", show_alert=True); return
        bot.answer_callback_query(call.id, "⏳ Stopping...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
        file_type = next((f[1] for f in user_files.get(script_owner_id, []) if f[0] == file_name), '?')
        try:
            bot.edit_message_text(
                f"⚙️ `{file_name}` ({file_type})\nStatus: 🔴 Stopped",
                chat_id, call.message.message_id,
                reply_markup=create_control_buttons(user_id, script_owner_id, file_name, False), parse_mode='Markdown')
        except: pass
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        if not (user_id == script_owner_id or user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        script_key = f"{script_owner_id}_{file_name}"
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, "⚠️ Missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            if script_key in bot_scripts: del bot_scripts[script_key]
            check_files_callback(call); return
        bot.answer_callback_query(call.id, "⏳ Restarting...")
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(1.5)
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        time.sleep(1.5)
        is_now = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 Running' if is_now else '🟡 Starting'
        try:
            bot.edit_message_text(
                f"⚙️ `{file_name}` ({file_type})\nStatus: {status_text}",
                chat_id, call.message.message_id,
                reply_markup=create_control_buttons(user_id, script_owner_id, file_name, is_now), parse_mode='Markdown')
        except: pass
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

def delete_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        if not (user_id == script_owner_id or user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); check_files_callback(call); return
        bot.answer_callback_query(call.id, "🗑️ Deleting...")
        script_key = f"{script_owner_id}_{file_name}"
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(0.5)
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(log_path): os.remove(log_path)
        remove_user_file_db(script_owner_id, file_name)
        try:
            bot.edit_message_text(t(user_id, 'delete_confirm', name=file_name), chat_id, call.message.message_id, reply_markup=None, parse_mode='Markdown')
        except: pass
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        if not (user_id == script_owner_id or user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Denied.", show_alert=True); return
        user_folder = get_user_folder(script_owner_id)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, "⚠️ No logs.", show_alert=True); return
        bot.answer_callback_query(call.id)
        try:
            log_content = ""
            file_size = os.path.getsize(log_path)
            max_kb = 100; max_msg = 4096
            if file_size == 0: log_content = "(Log empty)"
            elif file_size > max_kb * 1024:
                with open(log_path, 'rb') as f: f.seek(-max_kb * 1024, os.SEEK_END); log_content = f.read().decode('utf-8', errors='ignore')
                log_content = f"(Last {max_kb} KB)\n...\n" + log_content
            else:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f: log_content = f.read()
            if len(log_content) > max_msg: log_content = log_content[-max_msg:]
            if not log_content.strip(): log_content = "(No content)"
            bot.send_message(chat_id, f"📜 `{file_name}`:\n```\n{log_content}\n```", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Log error: {e}", exc_info=True)
            bot.send_message(chat_id, f"❌ Error reading log.")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    start_cb = time.time()
    try:
        bot.edit_message_text("🏃...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_cb) * 1000, 2)
        status = t(user_id, 'unlocked') if not bot_locked else t(user_id, 'locked')
        if user_id == OWNER_ID: user_level = t(user_id, 'owner')
        elif user_id in admin_ids: user_level = t(user_id, 'admin')
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            user_level = t(user_id, 'premium')
        else: user_level = t(user_id, 'free_user')
        speed_msg = (f"{t(user_id, 'speed_test')}\n\n"
                     f"{t(user_id, 'response_time')}: {response_time} ms\n"
                     f"{t(user_id, 'bot_status')}: {status}\n"
                     f"{t(user_id, 'your_level')}: {user_level}")
        bot.answer_callback_query(call.id)
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error.", show_alert=True)

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    file_limit = get_user_file_limit(user_id)
    bot_limit = get_user_bot_limit(user_id)
    current_files = get_user_file_count(user_id)
    current_bots = get_user_running_bots(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "∞"
    bot_limit_str = str(bot_limit) if bot_limit != float('inf') else "∞"
    expiry_info = ""
    if user_id == OWNER_ID: user_status = t(user_id, 'owner')
    elif user_id in admin_ids: user_status = t(user_id, 'admin')
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = t(user_id, 'premium'); days_left = (expiry_date - datetime.now()).days
            expiry_info = "\n" + t(user_id, 'expires_in', days=days_left)
        else: user_status = t(user_id, 'expired_sub')
    else: user_status = t(user_id, 'free_user')
    text = (f"{t(user_id, 'welcome', name=call.from_user.first_name)}\n\n"
            f"{t(user_id, 'your_id')}: `{user_id}`\n"
            f"{t(user_id, 'status')}: {user_status}{expiry_info}\n"
            f"{t(user_id, 'files')}: {current_files} / {limit_str}\n"
            f"{t(user_id, 'bots')}: {current_bots} / {bot_limit_str}\n\n"
            f"👇 Use buttons or type commands.")
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, chat_id, call.message.message_id,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e): logger.error(f"Error: {e}")

def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("💳 Subscription Management", call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu(call.from_user.id))
    except: pass

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except: pass

def lock_bot_callback(call):
    global bot_locked; bot_locked = True
    bot.answer_callback_query(call.id, "🔒 Locked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except: pass

def unlock_bot_callback(call):
    global bot_locked; bot_locked = False
    bot.answer_callback_query(call.id, "🔓 Unlocked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except: pass

def run_all_scripts_callback(call):
    _logic_run_all_scripts(call)

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    if not message.text:
        bot.reply_to(message, "⚠️ Send text."); return
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ Send", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast"))
    bot.reply_to(message, f"⚠️ Confirm:\n\n```\n{message.text[:1000]}\n```\nTo {len(active_users)} users.",
                 reply_markup=markup, parse_mode='Markdown')

def handle_confirm_broadcast(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids: bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True); return
    try:
        original_message = call.message.reply_to_message
        if not original_message or not original_message.text: raise ValueError("No text.")
        bot.answer_callback_query(call.id, "🚀 Starting...")
        bot.edit_message_text(f"📢 Broadcasting to {len(active_users)} users...", chat_id, call.message.message_id, reply_markup=None)
        threading.Thread(target=execute_broadcast, args=(original_message.text, chat_id)).start()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        bot.edit_message_text(f"❌ Error: {e}", chat_id, call.message.message_id, reply_markup=None)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Cancelled.")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

def execute_broadcast(broadcast_text, admin_chat_id):
    sent = 0; failed = 0; blocked = 0
    start = time.time()
    users = list(active_users); total = len(users)
    for i, uid in enumerate(users):
        try:
            bot.send_message(uid, broadcast_text, parse_mode='Markdown')
            sent += 1
        except telebot.apihelper.ApiTelegramException as e:
            err = str(e).lower()
            if any(s in err for s in ["blocked", "deactivated", "not found", "kicked"]): blocked += 1
            elif "flood" in err or "too many" in err:
                match = re.search(r"retry after (\d+)", err)
                wait = int(match.group(1)) + 1 if match else 5
                time.sleep(wait)
                try: bot.send_message(uid, broadcast_text, parse_mode='Markdown'); sent += 1
                except: failed += 1
            else: failed += 1
        except: failed += 1
        if (i + 1) % 25 == 0 and i < total - 1: time.sleep(1.5)
        elif i % 5 == 0: time.sleep(0.2)
    duration = round(time.time() - start, 2)
    result = (f"📢 Broadcast Complete!\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n"
              f"🚫 Blocked: {blocked}\n👥 Targets: {total}\n⏱️ Duration: {duration}s")
    try: bot.send_message(admin_chat_id, result)
    except: pass

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👑 Admin Panel", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(call.from_user.id))
    except: pass

def force_join_settings_callback(call):
    bot.answer_callback_query(call.id)
    status = "🟢 ON" if force_join_enabled else "🔴 OFF"
    channels_list = "\n".join([f"{i+1}. {u}" for i, u in enumerate(force_join_usernames)])
    try:
        bot.edit_message_text(f"⚙️ Force Join Settings\n\nStatus: {status}\nChannels:\n{channels_list or 'None'}",
                              call.message.chat.id, call.message.message_id, reply_markup=create_force_join_menu(call.from_user.id))
    except: pass

def add_force_channel_callback(call):
    """Simplified: only accept username"""
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send channel username (e.g., `@channelname` or `channelname`)\n\n/cancel to abort.", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_add_force_channel)

def process_add_force_channel(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled."); return
    if not message.text:
        bot.reply_to(message, "⚠️ Send username.")
        msg = bot.send_message(message.chat.id, "📢 Send channel username (e.g., `@channelname`)\n/cancel to abort.", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_force_channel)
        return
    
    # Accept any format - extract username
    raw = message.text.strip()
    # Remove any URL prefix
    raw = raw.replace('https://t.me/', '').replace('http://t.me/', '').replace('t.me/', '').replace('telegram.me/', '')
    # Remove @ if present
    username = raw.replace('@', '').strip()
    # Remove any trailing slashes or spaces
    username = username.split('/')[0].split()[0] if username else ""
    
    if not username or len(username) < 3:
        bot.reply_to(message, "⚠️ Invalid username. Please send a valid channel username.")
        msg = bot.send_message(message.chat.id, "📢 Send channel username (e.g., `@channelname`)\n/cancel to abort.", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_force_channel)
        return
    
    username = '@' + username
    if add_force_join_channel(username):
        bot.reply_to(message, f"✅ Channel added: {username}")
    else:
        bot.reply_to(message, "❌ Failed to add channel.")

def remove_force_channel_callback(call):
    bot.answer_callback_query(call.id)
    if not force_join_usernames:
        bot.send_message(call.message.chat.id, "⚠️ No channels to remove."); return
    channels_list = "\n".join([f"{i+1}. {u}" for i, u in enumerate(force_join_usernames)])
    msg = bot.send_message(call.message.chat.id, f"📢 Send channel number to remove:\n\n{channels_list}\n\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_force_channel)

def process_remove_force_channel(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "Cancelled."); return
    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(force_join_usernames): raise ValueError("Invalid")
        if remove_force_join_channel(index):
            bot.reply_to(message, "✅ Channel removed.")
        else:
            bot.reply_to(message, "❌ Failed.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid number.")

def list_force_channels_callback(call):
    bot.answer_callback_query(call.id)
    if not force_join_usernames:
        bot.send_message(call.message.chat.id, "⚠️ No channels."); return
    channels_list = "\n".join([f"{i+1}. {u}" for i, u in enumerate(force_join_usernames)])
    bot.send_message(call.message.chat.id, f"📢 Force Join Channels:\n\n{channels_list}")

def toggle_force_join_callback(call):
    global force_join_enabled
    force_join_enabled = not force_join_enabled
    save_setting('force_join_enabled', '1' if force_join_enabled else '0')
    bot.answer_callback_query(call.id, f"Force Join: {'ON' if force_join_enabled else 'OFF'}")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_force_join_menu(call.from_user.id))
    except: pass

def send_notification_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔔 Send notification to all users.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_send_notification)

def handle_confirm_notification(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids: bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True); return
    try:
        original_message = call.message.reply_to_message
        if not original_message or not original_message.text: raise ValueError("No text.")
        bot.answer_callback_query(call.id, "🔔 Sending...")
        bot.edit_message_text(f"🔔 Sending to {len(active_users)} users...", chat_id, call.message.message_id, reply_markup=None)
        threading.Thread(target=execute_broadcast, args=(f"🔔 **Notification**\n\n{original_message.text}", chat_id)).start()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        bot.edit_message_text(f"❌ Error: {e}", chat_id, call.message.message_id, reply_markup=None)

def handle_cancel_notification(call):
    bot.answer_callback_query(call.id, "Cancelled.")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Send User ID (and optional bot limit).\nFormat: `user_id bot_limit` (e.g., `12345678 10`)\n/cancel to abort.", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.split()
        new_admin_id = int(parts[0].strip())
        bot_limit = int(parts[1].strip()) if len(parts) > 1 else DEFAULT_ADMIN_BOT_LIMIT
        if new_admin_id <= 0 or bot_limit <= 0: raise ValueError("Must be positive")
        if new_admin_id == OWNER_ID: bot.reply_to(message, "⚠️ Owner is already Owner."); return
        if new_admin_id in admin_ids: bot.reply_to(message, "⚠️ Already Admin."); return
        add_admin_db(new_admin_id, bot_limit)
        bot.reply_to(message, f"✅ User `{new_admin_id}` promoted with bot limit {bot_limit}.")
        try: bot.send_message(new_admin_id, f"🎉 You are now an Admin! Your bot limit: {bot_limit}")
        except: pass
    except (ValueError, IndexError):
        bot.reply_to(message, "⚠️ Invalid format. Send: `user_id bot_limit` or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Send format: `user_id bot_limit`\n/cancel to abort.", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_admin_id)

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Send User ID to remove.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        admin_id = int(message.text.strip())
        if admin_id <= 0: raise ValueError("Positive")
        if admin_id == OWNER_ID: bot.reply_to(message, "⚠️ Cannot remove Owner."); return
        if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not Admin."); return
        if remove_admin_db(admin_id):
            bot.reply_to(message, f"✅ Admin `{admin_id}` removed.")
            try: bot.send_message(admin_id, "ℹ️ You are no longer an Admin.")
            except: pass
        else: bot.reply_to(message, "❌ Failed.")
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid ID.")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        lines = []
        for aid in sorted(list(admin_ids)):
            if aid == OWNER_ID: lines.append(f"- `{aid}` (Owner)")
            else: lines.append(f"- `{aid}` (Limit: {admin_bot_limits.get(aid, DEFAULT_ADMIN_BOT_LIMIT)})")
        text = "👑 Current Admins:\n\n" + ("\n".join(lines) if lines else "(No Admins!)")
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_panel(call.from_user.id), parse_mode='Markdown')
    except Exception as e: logger.error(f"Error: {e}")

def set_admin_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "⚙️ Send Admin ID and new bot limit.\nFormat: `admin_id new_limit`\n/cancel to abort.", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_set_admin_limit)

def process_set_admin_limit(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError("Need ID and limit")
        admin_id = int(parts[0].strip())
        new_limit = int(parts[1].strip())
        if admin_id not in admin_ids: bot.reply_to(message, "⚠️ Not Admin."); return
        if admin_id == OWNER_ID: bot.reply_to(message, "⚠️ Owner has unlimited."); return
        if new_limit <= 0: raise ValueError("Positive")
        admin_bot_limits[admin_id] = new_limit
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('UPDATE admins SET bot_limit = ? WHERE user_id = ?', (new_limit, admin_id))
            conn.commit()
            conn.close()
        bot.reply_to(message, f"✅ Admin `{admin_id}` bot limit set to {new_limit}.")
    except (ValueError, IndexError):
        bot.reply_to(message, "⚠️ Invalid format.")

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Send User ID & days (e.g., `12345678 30`).\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError("Format")
        sub_user_id = int(parts[0].strip()); days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0: raise ValueError("Positive")
        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date = datetime.now()
        if current_expiry and current_expiry > start_date: start_date = current_expiry
        new_expiry = start_date + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)
        bot.reply_to(message, f"✅ Sub for `{sub_user_id}` {days} days.\nExpiry: {new_expiry:%Y-%m-%d}")
        try: bot.send_message(sub_user_id, f"🎉 Sub activated! Expires: {new_expiry:%Y-%m-%d}.")
        except: pass
    except ValueError:
        bot.reply_to(message, "⚠️ Invalid format.")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Send User ID to remove sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        sub_user_id = int(message.text.strip())
        if sub_user_id <= 0: raise ValueError("Positive")
        if sub_user_id not in user_subscriptions: bot.reply_to(message, "⚠️ No sub."); return
        remove_subscription_db(sub_user_id)
        bot.reply_to(message, f"✅ Sub removed.")
        try: bot.send_message(sub_user_id, "ℹ️ Sub removed.")
        except: pass
    except ValueError: bot.reply_to(message, "⚠️ Invalid ID.")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Send User ID to check.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        if uid <= 0: raise ValueError("Positive")
        if uid in user_subscriptions:
            exp = user_subscriptions[uid].get('expiry')
            if exp and exp > datetime.now():
                days = (exp - datetime.now()).days
                bot.reply_to(message, f"✅ `{uid}` active.\nExpires: {exp:%Y-%m-%d} ({days} days left).")
            else:
                bot.reply_to(message, f"⚠️ Expired.")
                remove_subscription_db(uid)
        else: bot.reply_to(message, f"ℹ️ No sub record.")
    except ValueError: bot.reply_to(message, "⚠️ Invalid ID.")

# ==================== CLEANUP ====================
def cleanup():
    logger.warning("Shutdown. Cleaning up...")
    for key in list(bot_scripts.keys()):
        if key in bot_scripts:
            kill_process_tree(bot_scripts[key])
    logger.warning("Cleanup finished.")
atexit.register(cleanup)

# ==================== MAIN ====================
if __name__ == '__main__':
    logger.info("="*40 + "\n🤖 Bot Starting Up...\n" + f"🐍 Python: {sys.version.split()[0]}\n" +
                f"🔧 Base Dir: {BASE_DIR}\n🔑 Owner ID: {OWNER_ID}\n🛡️ Admins: {admin_ids}\n" + "="*40)
    keep_alive()
    logger.info("🚀 Starting polling...")
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            logger.warning("ReadTimeout. Restarting in 5s..."); time.sleep(5)
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"ConnectionError: {ce}. Retrying in 15s..."); time.sleep(15)
        except Exception as e:
            logger.critical(f"💥 Polling error: {e}", exc_info=True)
            logger.info("Restarting in 30s..."); time.sleep(30)
        finally:
            time.sleep(1)