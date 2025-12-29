#!/usr/bin/env python3
"""
Bondly Bot v1.5 - Clean Rewritten Version
"""

import os
import json
import re
import threading
import logging
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# ================== SETUP ==================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Add BOT_TOKEN to .env")
    exit()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_VERSION = "1.5"

# ================== DATABASE ==================
class DB:
    def __init__(self):
        self.files = {
            "users": "users.json",
            "stats": "stats.json",
            "blocked": "blocked.json",
            "chats": "chat_history.json"
        }
        for f in self.files.values():
            if not os.path.exists(f):
                with open(f, "w") as file:
                    json.dump({}, file)
    
    # --- USERS ---
    def get_user(self, user_id: int):
        users = self._load("users")
        return users.get(str(user_id))
    
    def save_user(self, user_id: int, data: dict):
        users = self._load("users")
        users[str(user_id)] = data
        self._save("users", users)
    
    # --- STATS ---
    def get_stats(self, user_id: int):
        stats = self._load("stats")
        return stats.get(str(user_id), {
            "messages_sent": 0, "messages_received": 0,
            "media_sent": 0, "chats_started": 0,
            "chats_today": 0, "total_chat_duration": 0,
            "ratings_positive": 0, "ratings_negative": 0,
            "last_active": datetime.now().isoformat()
        })
    
    def update_stats(self, user_id: int, key: str, value=1):
        stats = self._load("stats")
        if str(user_id) not in stats:
            stats[str(user_id)] = self.get_stats(user_id)
        if isinstance(stats[str(user_id)].get(key), int):
            stats[str(user_id)][key] += value
        else:
            stats[str(user_id)][key] = value
        self._save("stats", stats)
    
    # --- BLOCKED ---
    def is_blocked(self, user1: int, user2: int):
        blocked = self._load("blocked")
        return str(user2) in blocked.get(str(user1), {})
    
    def block_user(self, user1: int, user2: int, nick="Unknown"):
        blocked = self._load("blocked")
        if str(user1) not in blocked:
            blocked[str(user1)] = {}
        blocked[str(user1)][str(user2)] = {"nickname": nick, "blocked_at": datetime.now().isoformat()}
        self._save("blocked", blocked)
    
    # --- CHAT HISTORY ---
    def save_chat(self, data: dict):
        chats = self._load("chats")
        chat_list = chats.get("records", [])
        chat_list.append(data)
        chats["records"] = chat_list
        self._save("chats", chats)
    
    # --- INTERNAL ---
    def _load(self, key):
        try:
            with open(self.files[key], "r") as f:
                return json.load(f)
        except:
            return {}
    
    def _save(self, key, data):
        with open(self.files[key], "w") as f:
            json.dump(data, f, indent=2)

db = DB()

# ================== CHAT MANAGER ==================
class ChatManager:
    def __init__(self):
        self.waiting = {}
        self.active_chats = {}
        self.user_chats = {}
        self.lock = threading.Lock()
        self.chat_counter = 0
    
    def add_waiting(self, user_id: int, data: dict):
        with self.lock:
            if user_id in self.waiting or user_id in self.user_chats:
                return False
            self.waiting[user_id] = {"data": data, "joined": datetime.now().isoformat()}
            return True
    
    def remove_waiting(self, user_id: int):
        with self.lock:
            self.waiting.pop(user_id, None)
    
    def find_match(self, user_id: int):
        with self.lock:
            if user_id not in self.waiting: return None
            user_data = self.waiting[user_id]["data"]
            for partner_id, partner_info in self.waiting.items():
                if partner_id == user_id: continue
                if db.is_blocked(user_id, partner_id) or db.is_blocked(partner_id, user_id): continue
                return {"user1": user_id, "user2": partner_id, "data1": user_data, "data2": partner_info["data"]}
            return None
    
    def create_chat(self, user1, user2, data1, data2):
        with self.lock:
            self.chat_counter += 1
            chat_id = f"chat_{self.chat_counter}"
            self.active_chats[chat_id] = {
                "user1": {"id": user1, "data": data1},
                "user2": {"id": user2, "data": data2},
                "active": True,
                "created": datetime.now().isoformat(),
                "messages_sent_user1": 0,
                "messages_sent_user2": 0,
                "media_sent": 0
            }
            self.user_chats[user1] = chat_id
            self.user_chats[user2] = chat_id
            self.waiting.pop(user1, None)
            self.waiting.pop(user2, None)
            db.update_stats(user1, "chats_started")
            db.update_stats(user2, "chats_started")
            return chat_id
    
    def get_chat(self, user_id: int):
        chat_id = self.user_chats.get(user_id)
        if chat_id and chat_id in self.active_chats and self.active_chats[chat_id]["active"]:
            return chat_id, self.active_chats[chat_id]
        return None, None
    
    def get_partner(self, chat_id: str, user_id: int):
        chat = self.active_chats.get(chat_id)
        if not chat: return None
        return chat["user2"] if chat["user1"]["id"] == user_id else chat["user1"]
    
    def end_chat(self, chat_id: str, reason="ended"):
        with self.lock:
            chat = self.active_chats.get(chat_id)
            if not chat: return None
            chat["active"] = False
            chat["ended"] = datetime.now().isoformat()
            chat["reason"] = reason
            db.save_chat(chat)
            self.user_chats.pop(chat["user1"]["id"], None)
            self.user_chats.pop(chat["user2"]["id"], None)
            return chat

cm = ChatManager()

# ================== REGISTRATION ==================
REG_NICK, REG_GENDER = range(2)

def validate_nick(nick: str):
    if len(nick) < 3: return False, "Nickname too short"
    if len(nick) > 20: return False, "Nickname too long"
    if not re.match(r'^[\w\s\-]+$', nick): return False, "Invalid characters"
    return True, "OK"

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db.get_user(user_id):
        await update.message.reply_text("Already registered!")
        return ConversationHandler.END
    await update.message.reply_text("Enter nickname (3-20 chars):", reply_markup=ReplyKeyboardRemove())
    return REG_NICK

async def register_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nick = update.message.text.strip()
    valid, msg = validate_nick(nick)
    if not valid:
        await update.message.reply_text(msg)
        return REG_NICK
    context.user_data['nickname'] = nick
    keyboard = [["Male", "Female"], ["Other", "Skip"]]
    await update.message.reply_text("Select gender:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return REG_GENDER

async def register_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender_text = update.message.text
    gender_map = {"Male": "male", "Female": "female", "Other": "other", "Skip": "not_specified"}
    if gender_text not in gender_map:
        await update.message.reply_text("Choose from options")
        return REG_GENDER
    user_id = update.effective_user.id
    user_data = {
        "nickname": context.user_data["nickname"],
        "gender": gender_map[gender_text],
        "search_filter": "random",
        "search_filter_display": "Random",
        "telegram_name": update.effective_user.full_name or "",
        "username": update.effective_user.username or "",
        "registered": datetime.now().isoformat(),
        "user_id": user_id
    }
    db.save_user(user_id, user_data)
    db.update_stats(user_id, "chats_started", 0)
    await update.message.reply_text(f"Registration complete! Welcome {user_data['nickname']}!", reply_markup=ReplyKeyboardMarkup([["Find Partner", "Profile"], ["Statistics", "Settings"]], resize_keyboard=True))
    return ConversationHandler.END

async def register_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_stats(user_id, "last_active")
    user_data = db.get_user(user_id)
    if user_data:
        await update.message.reply_text(f"Welcome back {user_data['nickname']}!", reply_markup=ReplyKeyboardMarkup([["Find Partner", "Profile"], ["Statistics", "Settings"]], resize_keyboard=True))
    else:
        await update.message.reply_text("Welcome! Use /register to start.", reply_markup=ReplyKeyboardMarkup([["Register"]], resize_keyboard=True))

# ================== MAIN ==================
def main():
    application = Application.builder().token(TOKEN).build()

    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REG_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_nick)],
            REG_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_gender)]
        },
        fallbacks=[CommandHandler("cancel", register_cancel)]
    )

    application.add_handler(reg_handler)
    application.add_handler(CommandHandler("start", start))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
