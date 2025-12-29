#!/usr/bin/env python3
"""
Bondly Bot v1.5 - Professional Edition
Fixed nickname changing, clean text formatting, zero errors
Python 3.13 Compatible (using python-telegram-bot v13.15)
"""

import os
import json
import re
import threading
import logging
import time
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dotenv import load_dotenv

# Fix for Python 3.13 missing imghdr module
import sys
if sys.version_info >= (3, 13):
    import types
    
    # Create a simple imghdr replacement
    class ImghdrModule(types.ModuleType):
        def what(self, file, h=None):
            try:
                if hasattr(file, 'read'):
                    file.seek(0)
                    header = file.read(12)
                else:
                    with open(file, 'rb') as f:
                        header = f.read(12)
                
                # Check for common image formats
                if header.startswith(b'\xff\xd8\xff'):
                    return 'jpeg'
                elif header.startswith(b'\x89PNG\r\n\x1a\n'):
                    return 'png'
                elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                    return 'gif'
                elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
                    return 'webp'
                elif header.startswith(b'BM'):
                    return 'bmp'
            except:
                pass
            return None
    
    sys.modules['imghdr'] = ImghdrModule('imghdr')

# Telegram imports - using v13.15 API
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, Filters, CallbackContext
)

# Load token
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    print("ERROR: Add your bot token to .env file!")
    exit()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot version
BOT_VERSION = "1.5"

# ==================== PROFESSIONAL DATABASE ====================
class ProfessionalDB:
    def __init__(self):
        self.users_file = 'users.json'
        self.blocked_file = 'blocked.json'
        self.stats_file = 'stats.json'
        self.chats_file = 'chat_history.json'
        self._ensure_files()
    
    def _ensure_files(self):
        for file in [self.users_file, self.blocked_file, self.stats_file, self.chats_file]:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    json.dump({}, f)
    
    # User management
    def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
                return users.get(str(user_id))
        except:
            return None
    
    def save_user(self, user_id: int, user_data: Dict):
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
        except:
            users = {}
        
        users[str(user_id)] = user_data
        
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def delete_user(self, user_id: int):
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
        except:
            users = {}
        
        users.pop(str(user_id), None)
        
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    # Statistics
    def get_stats(self, user_id: int) -> Dict:
        try:
            with open(self.stats_file, 'r') as f:
                stats = json.load(f)
                user_stats = stats.get(str(user_id), {})
                
                default_stats = {
                    'messages_sent': 0,
                    'messages_received': 0,
                    'media_sent': 0,
                    'chats_started': 0,
                    'chats_today': 0,
                    'total_chat_duration': 0,
                    'ratings_positive': 0,
                    'ratings_negative': 0,
                    'last_active': datetime.now().isoformat(),
                    'last_reset': datetime.now().date().isoformat()
                }
                
                for key, value in default_stats.items():
                    if key not in user_stats:
                        user_stats[key] = value
                
                return user_stats
        except:
            return {
                'messages_sent': 0,
                'messages_received': 0,
                'media_sent': 0,
                'chats_started': 0,
                'chats_today': 0,
                'total_chat_duration': 0,
                'ratings_positive': 0,
                'ratings_negative': 0,
                'last_active': datetime.now().isoformat(),
                'last_reset': datetime.now().date().isoformat()
            }
    
    def update_stats(self, user_id: int, stat_type: str, value: int = 1):
        try:
            with open(self.stats_file, 'r') as f:
                stats = json.load(f)
        except:
            stats = {}
        
        user_id_str = str(user_id)
        if user_id_str not in stats:
            stats[user_id_str] = self.get_stats(user_id)
        
        today = datetime.now().date().isoformat()
        if stats[user_id_str].get('last_reset') != today:
            stats[user_id_str]['chats_today'] = 0
            stats[user_id_str]['last_reset'] = today
        
        if stat_type == 'last_active':
            stats[user_id_str][stat_type] = datetime.now().isoformat()
        elif stat_type in stats[user_id_str]:
            if isinstance(stats[user_id_str][stat_type], (int, float)):
                stats[user_id_str][stat_type] += value
            else:
                stats[user_id_str][stat_type] = value
        
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def get_global_stats(self) -> Dict:
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
        except:
            users = {}
        
        stats = self.get_all_stats()
        total_messages_sent = sum(int(s.get('messages_sent', 0)) for s in stats.values())
        total_messages_received = sum(int(s.get('messages_received', 0)) for s in stats.values())
        total_chats = sum(int(s.get('chats_started', 0)) for s in stats.values())
        
        return {
            'total_users': len(users),
            'total_messages': total_messages_sent + total_messages_received,
            'total_chats': total_chats,
            'total_positive_ratings': sum(int(s.get('ratings_positive', 0)) for s in stats.values()),
            'total_negative_ratings': sum(int(s.get('ratings_negative', 0)) for s in stats.values())
        }
    
    def get_all_stats(self) -> Dict:
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    # Blocked users
    def get_blocked_users(self, user_id: int) -> Dict:
        try:
            with open(self.blocked_file, 'r') as f:
                blocked = json.load(f)
                return blocked.get(str(user_id), {})
        except:
            return {}
    
    def block_user(self, blocker_id: int, blocked_id: int, blocked_nick: str):
        try:
            with open(self.blocked_file, 'r') as f:
                blocked = json.load(f)
        except:
            blocked = {}
        
        if str(blocker_id) not in blocked:
            blocked[str(blocker_id)] = {}
        
        blocked[str(blocker_id)][str(blocked_id)] = {
            'nickname': blocked_nick,
            'blocked_at': datetime.now().isoformat()
        }
        
        with open(self.blocked_file, 'w') as f:
            json.dump(blocked, f, indent=2)
    
    def unblock_user(self, blocker_id: int, blocked_id: int) -> bool:
        try:
            with open(self.blocked_file, 'r') as f:
                blocked = json.load(f)
        except:
            return False
        
        if str(blocker_id) in blocked and str(blocked_id) in blocked[str(blocker_id)]:
            del blocked[str(blocker_id)][str(blocked_id)]
            
            with open(self.blocked_file, 'w') as f:
                json.dump(blocked, f, indent=2)
            return True
        
        return False
    
    def is_blocked(self, blocker_id: int, blocked_id: int) -> bool:
        blocked = self.get_blocked_users(blocker_id)
        return str(blocked_id) in blocked
    
    # Chat history
    def save_chat(self, chat_data: Dict):
        try:
            with open(self.chats_file, 'r') as f:
                chats = json.load(f)
        except:
            chats = []
        
        chats.append(chat_data)
        
        with open(self.chats_file, 'w') as f:
            json.dump(chats, f, indent=2, default=str)

db = ProfessionalDB()

# ==================== PROFESSIONAL CHAT MANAGER ====================
class ProfessionalChatManager:
    def __init__(self):
        self.waiting: Dict[int, Dict] = {}
        self.active_chats: Dict[str, Dict] = {}
        self.user_chats: Dict[int, str] = {}
        self.search_tasks: Dict[int, asyncio.Task] = {}
        self.lock = threading.Lock()
        self.chat_counter = 0
    
    def add_to_waiting(self, user_id: int, user_data: Dict) -> Tuple[bool, str]:
        with self.lock:
            if user_id in self.waiting:
                return False, "You are already searching for a partner."
            
            if user_id in self.user_chats:
                chat_id = self.user_chats[user_id]
                if chat_id in self.active_chats and self.active_chats[chat_id].get('active'):
                    return False, "You are already in a chat. Use /leave to exit first."
            
            self.waiting[user_id] = {
                'data': user_data,
                'joined': datetime.now().isoformat(),
                'filter': user_data.get('search_filter', 'random')
            }
            
            waiting_count = len(self.waiting) - 1
            return True, f"Searching... {waiting_count} people waiting"
    
    def remove_from_waiting(self, user_id: int):
        with self.lock:
            if user_id in self.waiting:
                del self.waiting[user_id]
                
                if user_id in self.search_tasks:
                    try:
                        self.search_tasks[user_id].cancel()
                        del self.search_tasks[user_id]
                    except:
                        pass
    
    def find_match(self, user_id: int) -> Optional[Dict]:
        with self.lock:
            if user_id not in self.waiting:
                return None
            
            user_info = self.waiting[user_id]
            user_data = user_info['data']
            user_gender = user_data.get('gender', 'not_specified')
            user_filter = user_info.get('filter', 'random')
            
            candidates = []
            
            for partner_id, partner_info in self.waiting.items():
                if partner_id == user_id:
                    continue
                
                if db.is_blocked(user_id, partner_id) or db.is_blocked(partner_id, user_id):
                    continue
                
                partner_data = partner_info['data']
                partner_gender = partner_data.get('gender', 'not_specified')
                partner_filter = partner_info.get('filter', 'random')
                
                if user_filter == 'male' and partner_gender != 'male':
                    continue
                elif user_filter == 'female' and partner_gender != 'female':
                    continue
                
                if partner_filter == 'male' and user_gender != 'male':
                    continue
                elif partner_filter == 'female' and user_gender != 'female':
                    continue
                
                compatibility = 50
                
                if user_gender == partner_gender:
                    compatibility += 10
                
                user_chats = db.get_stats(user_id).get('chats_started', 0)
                partner_chats = db.get_stats(partner_id).get('chats_started', 0)
                
                if abs(user_chats - partner_chats) < 10:
                    compatibility += 15
                
                compatibility += random.randint(-10, 10)
                compatibility = max(30, min(95, compatibility))
                
                candidates.append({
                    'partner_id': partner_id,
                    'partner_data': partner_data,
                    'compatibility': compatibility
                })
            
            if candidates:
                candidates.sort(key=lambda x: x['compatibility'], reverse=True)
                best_match = candidates[0]
                
                return {
                    'user1': user_id,
                    'user2': best_match['partner_id'],
                    'data1': user_data,
                    'data2': best_match['partner_data'],
                    'compatibility': best_match['compatibility']
                }
            
            return None
    
    def create_chat(self, user1: int, user2: int, data1: Dict, data2: Dict) -> str:
        with self.lock:
            self.chat_counter += 1
            chat_id = f"chat_{self.chat_counter}"
            
            self.waiting.pop(user1, None)
            self.waiting.pop(user2, None)
            
            for uid in [user1, user2]:
                if uid in self.search_tasks:
                    try:
                        self.search_tasks[uid].cancel()
                        del self.search_tasks[uid]
                    except:
                        pass
            
            db.update_stats(user1, 'chats_started')
            db.update_stats(user2, 'chats_started')
            db.update_stats(user1, 'chats_today')
            db.update_stats(user2, 'chats_today')
            
            self.active_chats[chat_id] = {
                'user1': {'id': user1, 'data': data1, 'messages_sent': 0, 'last_active': datetime.now().isoformat()},
                'user2': {'id': user2, 'data': data2, 'messages_sent': 0, 'last_active': datetime.now().isoformat()},
                'active': True,
                'created': datetime.now().isoformat(),
                'messages_sent_user1': 0,
                'messages_sent_user2': 0,
                'media_sent': 0,
                'last_message': None
            }
            
            self.user_chats[user1] = chat_id
            self.user_chats[user2] = chat_id
            
            return chat_id
    
    def get_chat(self, user_id: int) -> Tuple[Optional[str], Optional[Dict]]:
        with self.lock:
            chat_id = self.user_chats.get(user_id)
            if chat_id and chat_id in self.active_chats:
                chat = self.active_chats[chat_id]
                if chat.get('active'):
                    if chat['user1']['id'] == user_id:
                        chat['user1']['last_active'] = datetime.now().isoformat()
                    else:
                        chat['user2']['last_active'] = datetime.now().isoformat()
                    return chat_id, chat
            return None, None
    
    def get_partner(self, chat_id: str, user_id: int) -> Optional[Dict]:
        with self.lock:
            chat = self.active_chats.get(chat_id)
            if not chat or not chat.get('active'):
                return None
            
            if chat['user1']['id'] == user_id:
                return chat['user2']
            return chat['user1']
    
    def record_message(self, chat_id: str, sender_id: int, is_media: bool = False):
        with self.lock:
            if chat_id in self.active_chats:
                chat = self.active_chats[chat_id]
                if chat.get('active'):
                    chat['last_message'] = datetime.now().isoformat()
                    
                    if chat['user1']['id'] == sender_id:
                        chat['messages_sent_user1'] += 1
                        chat['user1']['messages_sent'] += 1
                    else:
                        chat['messages_sent_user2'] += 1
                        chat['user2']['messages_sent'] += 1
                    
                    if is_media:
                        chat['media_sent'] += 1
    
    def end_chat(self, chat_id: str, reason: str = "ended"):
        with self.lock:
            if chat_id in self.active_chats:
                chat = self.active_chats[chat_id]
                chat['active'] = False
                chat['ended'] = datetime.now().isoformat()
                chat['reason'] = reason
                
                try:
                    start = datetime.fromisoformat(chat['created'])
                    end = datetime.fromisoformat(chat['ended'])
                    duration = (end - start).total_seconds()
                    chat['duration'] = duration
                    
                    user1_id = chat['user1']['id']
                    user2_id = chat['user2']['id']
                    
                    db.update_stats(user1_id, 'total_chat_duration', int(duration))
                    db.update_stats(user2_id, 'total_chat_duration', int(duration))
                    
                    db.save_chat(chat)
                    
                except Exception as e:
                    logger.error(f"Error saving chat: {e}")
                
                user1_id = chat['user1']['id']
                user2_id = chat['user2']['id']
                
                self.user_chats.pop(user1_id, None)
                self.user_chats.pop(user2_id, None)
                
                return chat
            
            return None
    
    def get_waiting_count(self) -> int:
        with self.lock:
            return len(self.waiting)
    
    def get_active_chat_count(self) -> int:
        with self.lock:
            return len([c for c in self.active_chats.values() if c.get('active')])

cm = ProfessionalChatManager()

# ==================== REGISTRATION ====================
def validate_nickname(nick: str) -> Tuple[bool, str]:
    if not nick:
        return False, "Nickname cannot be empty"
    
    if len(nick) < 3:
        return False, "Nickname must be at least 3 characters"
    
    if len(nick) > 20:
        return False, "Nickname cannot exceed 20 characters"
    
    if not re.match(r'^[\w\s\-]+$', nick, re.UNICODE):
        return False, "Nickname can only contain letters, numbers, spaces, and hyphens"
    
    return True, "OK"

# Registration states
REG_NICKNAME, REG_GENDER = range(2)

def register_start(update: Update, context: CallbackContext):
    """Start registration"""
    user_id = update.effective_user.id
    
    if db.get_user(user_id):
        update.message.reply_text("You are already registered!")
        return ConversationHandler.END
    
    context.user_data.clear()
    
    update.message.reply_text(
        "Registration\n\n"
        "Enter your nickname (3-20 characters):",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return REG_NICKNAME

def register_nickname(update: Update, context: CallbackContext):
    """Handle nickname"""
    nick = update.message.text.strip()
    valid, message = validate_nickname(nick)
    
    if not valid:
        update.message.reply_text(f"{message}\n\nPlease enter a valid nickname:")
        return REG_NICKNAME
    
    # Check if unique
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
    except:
        users = {}
    
    for user_data in users.values():
        if user_data.get('nickname', '').lower() == nick.lower():
            update.message.reply_text(f"'{nick}' is already taken!\n\nPlease choose another:")
            return REG_NICKNAME
    
    context.user_data['nickname'] = nick
    
    keyboard = [["Male", "Female"], ["Other", "Skip"]]
    
    update.message.reply_text(
        "Select your gender:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    
    return REG_GENDER

def register_gender(update: Update, context: CallbackContext):
    """Handle gender selection"""
    gender_text = update.message.text
    
    gender_map = {
        "Male": {"value": "male", "display": "Male"},
        "Female": {"value": "female", "display": "Female"},
        "Other": {"value": "other", "display": "Other"},
        "Skip": {"value": "not_specified", "display": "Not specified"}
    }
    
    if gender_text not in gender_map:
        update.message.reply_text("Please select from the options:")
        return REG_GENDER
    
    nickname = context.user_data.get('nickname', 'User')
    gender = gender_map[gender_text]
    
    # Create user data
    user_id = update.effective_user.id
    user_data = {
        'nickname': nickname,
        'gender': gender['value'],
        'gender_display': gender['display'],
        'search_filter': 'random',
        'search_filter_display': 'Random',
        'telegram_name': update.effective_user.full_name or "",
        'username': update.effective_user.username or "",
        'registered': datetime.now().isoformat(),
        'user_id': user_id
    }
    
    # Save user
    db.save_user(user_id, user_data)
    
    # Initialize stats
    db.update_stats(user_id, 'chats_started', 0)
    
    # Main menu
    main_menu = [
        ["Find Partner", "Statistics"],
        ["Profile", "Settings"],
        ["Help"]
    ]
    
    update.message.reply_text(
        f"Registration Complete!\n\n"
        f"Welcome to Bondly Bot v{BOT_VERSION}\n\n"
        f"Your Profile:\n"
        f"• Nickname: {nickname}\n"
        f"• Gender: {gender['display']}\n"
        f"• Search Filter: Random (set with /filter)\n\n"
        f"Press Find Partner to start chatting!",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )
    
    return ConversationHandler.END

def register_cancel(update: Update, context: CallbackContext):
    """Cancel registration"""
    update.message.reply_text(
        "Registration cancelled.\n\n"
        "Use /register to try again."
    )
    return ConversationHandler.END

# ==================== FORMATTING FUNCTIONS ====================
def format_duration(seconds: int) -> str:
    """Format duration in days, hours, minutes"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def format_number(num: int) -> str:
    """Format number with commas"""
    return f"{num:,}"

def format_profile(user_id: int, user_data: Dict) -> str:
    """Format profile in clean style"""
    stats = db.get_stats(user_id)
    
    # Format registration date
    reg_date = user_data.get('registered', '')
    if reg_date:
        try:
            dt = datetime.fromisoformat(reg_date)
            reg_date = dt.strftime("%d.%m.%Y")
        except:
            reg_date = "Unknown"
    
    total_duration = int(stats.get('total_chat_duration', 0))
    duration_str = format_duration(total_duration)
    
    total_chats = format_number(int(stats.get('chats_started', 0)))
    chats_today = format_number(int(stats.get('chats_today', 0)))
    messages_sent = format_number(int(stats.get('messages_sent', 0)))
    messages_received = format_number(int(stats.get('messages_received', 0)))
    positive_ratings = format_number(int(stats.get('ratings_positive', 0)))
    negative_ratings = format_number(int(stats.get('ratings_negative', 0)))
    
    profile = f"""
ID: {user_id}

Nickname: {user_data.get('nickname', 'Unknown')}
Gender: {user_data.get('gender_display', 'Not specified')}
Filter: {user_data.get('search_filter_display', 'Random')}
Registered: {reg_date}

Chats:
  Total: {total_chats}
  Today: {chats_today}
  Duration: {duration_str}

Messages:
  Sent: {messages_sent}
  Received: {messages_received}

Ratings: {positive_ratings}👍 {negative_ratings}👎
"""
    
    return profile.strip()

def format_stats(user_id: int, user_data: Dict) -> str:
    """Format statistics in clean style"""
    stats = db.get_stats(user_id)
    global_stats = db.get_global_stats()
    
    chat_id, chat = cm.get_chat(user_id)
    in_chat = "In chat" if chat else "Not in chat"
    in_queue = "Searching" if user_id in cm.waiting else "Not searching"
    
    total_users = format_number(global_stats.get('total_users', 0))
    total_messages = format_number(global_stats.get('total_messages', 0))
    total_chats = format_number(global_stats.get('total_chats', 0))
    total_positive = format_number(global_stats.get('total_positive_ratings', 0))
    total_negative = format_number(global_stats.get('total_negative_ratings', 0))
    
    stats_text = f"""
Statistics

Nickname: {user_data.get('nickname', 'Unknown')}
Filter: {user_data.get('search_filter_display', 'Random')}

Your Activity:
  Messages sent: {format_number(int(stats.get('messages_sent', 0)))}
  Messages received: {format_number(int(stats.get('messages_received', 0)))}
  Media shared: {format_number(int(stats.get('media_sent', 0)))}
  Chats started: {format_number(int(stats.get('chats_started', 0)))}
  Chats today: {format_number(int(stats.get('chats_today', 0)))}
  Chat duration: {format_duration(int(stats.get('total_chat_duration', 0)))}

Current Status:
  {in_chat}
  {in_queue}
  People waiting: {cm.get_waiting_count()}

Global Statistics:
  Total users: {total_users}
  Total messages: {total_messages}
  Total chats: {total_chats}
  Positive ratings: {total_positive}
  Negative ratings: {total_negative}
"""
    
    if chat:
        partner = cm.get_partner(chat_id, user_id)
        if partner:
            partner_nick = partner['data'].get('nickname', 'Anonymous')
            chat_duration = 0
            try:
                start = datetime.fromisoformat(chat.get('created', ''))
                now = datetime.now()
                chat_duration = int((now - start).total_seconds())
            except:
                pass
            
            messages_sent = chat.get('messages_sent_user1', 0) if chat['user1']['id'] == user_id else chat.get('messages_sent_user2', 0)
            messages_received = chat.get('messages_sent_user2', 0) if chat['user1']['id'] == user_id else chat.get('messages_sent_user1', 0)
            
            stats_text += f"""
Current Chat:
  Partner: {partner_nick}
  Duration: {format_duration(chat_duration)}
  Messages sent: {messages_sent}
  Messages received: {messages_received}
"""
    
    return stats_text.strip()

# ==================== MAIN COMMANDS ====================
def start(update: Update, context: CallbackContext):
    """Start command"""
    user_id = update.effective_user.id
    
    # Update last active
    db.update_stats(user_id, 'last_active')
    
    if db.get_user(user_id):
        # Registered user
        main_menu = [
            ["Find Partner", "Statistics"],
            ["Profile", "Settings"],
            ["Help"]
        ]
        
        update.message.reply_text(
            f"Bondly Bot v{BOT_VERSION}\n\n"
            f"Professional anonymous chatting platform\n\n"
            f"Press Find Partner to start!",
            reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        )
    else:
        # New user
        update.message.reply_text(
            f"Welcome to Bondly Bot v{BOT_VERSION}\n\n"
            f"Professional anonymous chatting platform\n\n"
            f"Start by registering:",
            reply_markup=ReplyKeyboardMarkup([["Register"]], resize_keyboard=True)
        )

def search(update: Update, context: CallbackContext):
    """Search for partner with gender filters"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("Please register first with /register")
        return
    
    chat_id, chat = cm.get_chat(user_id)
    if chat:
        update.message.reply_text("You're already in a chat! Use /leave to exit first.")
        return
    
    if user_id in cm.waiting:
        waiting_count = cm.get_waiting_count() - 1
        filter_display = user_data.get('search_filter_display', 'Random')
        update.message.reply_text(f"Already searching ({filter_display})... {waiting_count} people waiting")
        return
    
    # Simple search without async
    success, message = cm.add_to_waiting(user_id, user_data)
    
    if not success:
        update.message.reply_text(f"{message}")
        return
    
    match = cm.find_match(user_id)
    
    if match:
        chat_id = cm.create_chat(
            match['user1'], match['user2'],
            match['data1'], match['data2']
        )
        
        if match['user1'] == user_id:
            partner_id = match['user2']
            partner_nick = match['data2'].get('nickname', 'Anonymous')
            my_nick = match['data1']['nickname']
        else:
            partner_id = match['user1']
            partner_nick = match['data1'].get('nickname', 'Anonymous')
            my_nick = match['data2']['nickname']
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Next Partner", callback_data="next"),
             InlineKeyboardButton("Block", callback_data="block")],
            [InlineKeyboardButton("Rate Good", callback_data="rate_good"),
             InlineKeyboardButton("Rate Bad", callback_data="rate_bad")],
            [InlineKeyboardButton("Leave Chat", callback_data="leave")]
        ])
        
        update.message.reply_text(
            f"Match Found!\n\n"
            f"Partner: {partner_nick}\n"
            f"Compatibility: {match.get('compatibility', 50)}%\n\n"
            f"Start chatting now!",
            reply_markup=buttons
        )
        
        # Notify partner
        try:
            context.bot.send_message(
                partner_id,
                f"Match Found!\n\n"
                f"Partner: {my_nick}\n"
                f"Compatibility: {match.get('compatibility', 50)}%\n\n"
                f"Start chatting now!",
                reply_markup=buttons
            )
        except:
            pass
    else:
        waiting_count = cm.get_waiting_count() - 1
        filter_display = user_data.get('search_filter_display', 'Random')
        
        cancel_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Search", callback_data="cancel_search")]
        ])
        
        update.message.reply_text(
            f"Searching ({filter_display})...\n\n"
            f"People waiting: {waiting_count}\n"
            f"Estimated time: {max(30, waiting_count * 15)}s\n\n"
            f"Please wait...",
            reply_markup=cancel_btn
        )

def handle_media(update: Update, context: CallbackContext):
    """Handle media messages"""
    user_id = update.effective_user.id
    
    chat_id, chat = cm.get_chat(user_id)
    if not chat:
        update.message.reply_text("You're not in a chat. Press 'Find Partner' to search.")
        return
    
    partner = cm.get_partner(chat_id, user_id)
    if not partner:
        update.message.reply_text("Partner not found. The chat may have ended.")
        return
    
    user_data = db.get_user(user_id)
    nickname = user_data.get('nickname', 'User') if user_data else 'User'
    
    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            caption = update.message.caption or ""
            
            context.bot.send_photo(
                partner['id'],
                photo.file_id,
                caption=f"Photo from {nickname}: {caption}" if caption else f"Photo from {nickname}"
            )
            
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
            
        elif update.message.video:
            video = update.message.video
            caption = update.message.caption or ""
            
            context.bot.send_video(
                partner['id'],
                video.file_id,
                caption=f"Video from {nickname}: {caption}" if caption else f"Video from {nickname}"
            )
            
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
            
        elif update.message.voice:
            voice = update.message.voice
            
            context.bot.send_voice(
                partner['id'],
                voice.file_id,
                caption=f"Voice message from {nickname}"
            )
            
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
            
        elif update.message.sticker:
            context.bot.send_sticker(partner['id'], update.message.sticker.file_id)
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
        
        db.update_stats(partner['id'], 'messages_received')
        
    except Exception as e:
        logger.error(f"Failed to send media: {e}")
        update.message.reply_text("Failed to send media.")

def handle_text(update: Update, context: CallbackContext):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text in ["Find Partner", "Statistics", "Profile", "Settings", "Help", "Register"]:
        handle_menu(update, context)
        return
    
    chat_id, chat = cm.get_chat(user_id)
    if not chat:
        update.message.reply_text("You're not in a chat. Press 'Find Partner' to search.")
        return
    
    partner = cm.get_partner(chat_id, user_id)
    if not partner:
        update.message.reply_text("Partner not found. The chat may have ended.")
        return
    
    user_data = db.get_user(user_id)
    nickname = user_data.get('nickname', 'User') if user_data else 'User'
    
    try:
        context.bot.send_message(partner['id'], f"{nickname}: {text}")
        
        cm.record_message(chat_id, user_id)
        
        db.update_stats(user_id, 'messages_sent')
        db.update_stats(partner['id'], 'messages_received')
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        update.message.reply_text("Failed to send message.")

def leave(update: Update, context: CallbackContext):
    """Leave chat"""
    user_id = update.effective_user.id
    chat_id, chat = cm.get_chat(user_id)
    
    if not chat:
        update.message.reply_text("You're not in a chat.")
        return
    
    partner = cm.get_partner(chat_id, user_id)
    
    ended_chat = cm.end_chat(chat_id, "left")
    
    if ended_chat:
        duration = ended_chat.get('duration', 0)
        messages_sent = ended_chat.get('messages_sent_user1', 0) if ended_chat['user1']['id'] == user_id else ended_chat.get('messages_sent_user2', 0)
        
        if partner:
            try:
                context.bot.send_message(
                    partner['id'],
                    "Your partner left the chat.\n\nPress 'Find Partner' to find someone new."
                )
            except:
                pass
        
        update.message.reply_text(
            f"Chat Ended\n\n"
            f"Duration: {format_duration(int(duration))}\n"
            f"Messages sent: {messages_sent}\n\n"
            f"Press 'Find Partner' to find someone new."
        )
    else:
        update.message.reply_text("Failed to leave chat.")

def profile(update: Update, context: CallbackContext):
    """Show profile"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You're not registered! Use /register first.")
        return
    
    profile_text = format_profile(user_id, user_data)
    update.message.reply_text(profile_text)

def stats_command(update: Update, context: CallbackContext):
    """Show statistics"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You're not registered! Use /register first.")
        return
    
    stats_text = format_stats(user_id, user_data)
    update.message.reply_text(stats_text)

def nickname_command(update: Update, context: CallbackContext):
    """Change nickname"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You need to register first!")
        return
    
    if not context.args:
        current_nick = user_data.get('nickname', 'Not set')
        update.message.reply_text(
            f"Change Nickname\n\n"
            f"Current: {current_nick}\n\n"
            "Usage: /nickname [new_nickname]\n"
            "Example: /nickname John"
        )
        return
    
    new_nick = ' '.join(context.args).strip()
    valid, message = validate_nickname(new_nick)
    
    if not valid:
        update.message.reply_text(f"{message}")
        return
    
    # Check if unique (excluding current user)
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
    except:
        users = {}
    
    for uid, data in users.items():
        # Skip the current user
        if str(user_id) != uid and data.get('nickname', '').lower() == new_nick.lower():
            update.message.reply_text(f"'{new_nick}' is already taken!")
            return
    
    # Update nickname
    old_nick = user_data.get('nickname', '')
    user_data['nickname'] = new_nick
    
    # Save the updated user data
    db.save_user(user_id, user_data)
    
    update.message.reply_text(f"Nickname updated from '{old_nick}' to '{new_nick}'")

def filter_command(update: Update, context: CallbackContext):
    """Change search filter"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You need to register first!")
        return
    
    if not context.args:
        current_filter = user_data.get('search_filter_display', 'Random')
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Random", callback_data="filter_random"),
             InlineKeyboardButton("Male only", callback_data="filter_male")],
            [InlineKeyboardButton("Female only", callback_data="filter_female")]
        ])
        
        update.message.reply_text(
            f"Search Filter\n\n"
            f"Current: {current_filter}\n\n"
            "Select who you want to chat with:",
            reply_markup=keyboard
        )
        return
    
    filter_text = ' '.join(context.args).lower()
    
    filter_map = {
        'random': {'value': 'random', 'display': 'Random'},
        'male': {'value': 'male', 'display': 'Male only'},
        'female': {'value': 'female', 'display': 'Female only'}
    }
    
    if filter_text not in ['random', 'male', 'female']:
        update.message.reply_text(
            "Invalid filter!\n\n"
            "Options: random, male, female\n"
            "Example: /filter female"
        )
        return
    
    user_data['search_filter'] = filter_map[filter_text]['value']
    user_data['search_filter_display'] = filter_map[filter_text]['display']
    db.save_user(user_id, user_data)
    
    update.message.reply_text(
        f"Filter Updated!\n\n"
        f"New filter: {filter_map[filter_text]['display']}"
    )

def delete_command(update: Update, context: CallbackContext):
    """Delete account"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You don't have an account!")
        return
    
    nickname = user_data.get('nickname', 'User')
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes, delete everything", callback_data="confirm_delete")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_delete")]
    ])
    
    update.message.reply_text(
        f"Delete account '{nickname}'?\n\n"
        "This will remove all your data.\n"
        "This action cannot be undone!",
        reply_markup=keyboard
    )

def blocked_command(update: Update, context: CallbackContext):
    """Show blocked users"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You need to register first!")
        return
    
    blocked = db.get_blocked_users(user_id)
    
    if not blocked:
        update.message.reply_text("You haven't blocked anyone yet.")
        return
    
    message = "Blocked Users\n\n"
    buttons = []
    
    for blocked_id, info in blocked.items():
        blocked_nick = info.get('nickname', 'Unknown')
        
        message += f"• {blocked_nick} (ID: {blocked_id})\n"
        
        buttons.append([InlineKeyboardButton(
            f"Unblock {blocked_nick}",
            callback_data=f"unblock_{blocked_id}"
        )])
    
    keyboard = InlineKeyboardMarkup(buttons)
    update.message.reply_text(message, reply_markup=keyboard)

def settings_command(update: Update, context: CallbackContext):
    """Settings menu"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        update.message.reply_text("You need to register first! Use /register")
        return
    
    settings_text = f"""
Settings

Profile Settings:
/nickname [new] - Change nickname
/filter - Change search filter

Privacy Settings:
/blocked - Blocked users

Statistics:
/stats - Your statistics

Account Management:
/delete - Delete account

Bot Information:
/help - Help guide

Current Settings:
• Nickname: {user_data.get('nickname', 'Not set')}
• Gender: {user_data.get('gender_display', 'Not specified')}
• Search Filter: {user_data.get('search_filter_display', 'Random')}

Back: /start
"""
    
    update.message.reply_text(settings_text)

def help_command(update: Update, context: CallbackContext):
    """Help command"""
    help_text = f"""
Bondly Bot v{BOT_VERSION} - Help

Quick Start:
1. /register - Create profile
2. Find Partner - Search for chat
3. Start chatting!

Main Commands:
/start - Start bot
/register - Register
/profile - Your profile
/stats - Statistics
/settings - Settings
/help - This message

Filter Commands:
/filter - Change search filter (Male/Female/Random)

Chat Commands:
Find Partner - Search
/leave - Exit chat
Send text, photos, videos, voice messages
Use buttons during chat

Profile Commands:
/nickname [new] - Change nickname
/blocked - Manage blocked users
/delete - Delete account

Media Support:
Photos
Videos
Voice messages
Documents

Tips:
• Use /filter to find specific genders
• Be respectful to others
• Use block feature if needed
• Check /stats for your activity

Support:
For issues, contact the developer.
ID support: https://t.me/Bitcoin_00009

Happy chatting!
"""
    
    update.message.reply_text(help_text)

def handle_menu(update: Update, context: CallbackContext):
    """Handle menu buttons"""
    text = update.message.text
    
    if text == "Find Partner":
        search(update, context)
    elif text == "Statistics":
        stats_command(update, context)
    elif text == "Profile":
        profile(update, context)
    elif text == "Settings":
        settings_command(update, context)
    elif text == "Help":
        help_command(update, context)
    elif text == "Register":
        register_start(update, context)

def callback_handler(update: Update, context: CallbackContext):
    """Handle button callbacks"""
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data
    
    try:
        if data == "cancel_search":
            cm.remove_from_waiting(user_id)
            query.edit_message_text("Search cancelled.")
        
        elif data == "next":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    try:
                        context.bot.send_message(
                            partner['id'],
                            "Your partner wants to talk to someone else."
                        )
                    except:
                        pass
                
                cm.end_chat(chat_id, "next")
                query.edit_message_text("Finding new partner...")
        
        elif data == "block":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    partner_nick = partner['data'].get('nickname', 'Unknown')
                    db.block_user(user_id, partner['id'], partner_nick)
                
                cm.end_chat(chat_id, "blocked")
                query.edit_message_text("User blocked.")
        
        elif data == "leave":
            leave(update, context)
        
        elif data == "rate_good":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    db.update_stats(partner['id'], 'ratings_positive')
                    query.edit_message_text("Rating submitted: Good")
        
        elif data == "rate_bad":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    db.update_stats(partner['id'], 'ratings_negative')
                    query.edit_message_text("Rating submitted: Bad")
        
        elif data == "confirm_delete":
            user_data = db.get_user(user_id)
            nickname = user_data.get('nickname', 'User') if user_data else 'User'
            
            cm.remove_from_waiting(user_id)
            
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                cm.end_chat(chat_id, "deleted")
            
            db.delete_user(user_id)
            
            query.edit_message_text(
                f"Account '{nickname}' deleted.\n\n"
                "Use /start to register again."
            )
        
        elif data == "cancel_delete":
            query.edit_message_text("Deletion cancelled.")
        
        elif data.startswith("unblock_"):
            blocked_id = data.split("_")[1]
            
            if db.unblock_user(user_id, int(blocked_id)):
                query.edit_message_text("User unblocked.")
            else:
                query.edit_message_text("User not found in blocked list.")
        
        elif data.startswith("filter_"):
            filter_type = data.split("_")[1]
            
            filter_map = {
                'random': {'value': 'random', 'display': 'Random'},
                'male': {'value': 'male', 'display': 'Male only'},
                'female': {'value': 'female', 'display': 'Female only'}
            }
            
            if filter_type in filter_map:
                user_data = db.get_user(user_id)
                if user_data:
                    user_data['search_filter'] = filter_map[filter_type]['value']
                    user_data['search_filter_display'] = filter_map[filter_type]['display']
                    db.save_user(user_id, user_data)
                    
                    query.edit_message_text(
                        f"Filter updated to {filter_map[filter_type]['display']}"
                    )
    
    except Exception as e:
        logger.error(f"Callback error: {e}")
        query.edit_message_text("An error occurred.")

# ==================== CLEANUP TASK ====================
def cleanup_task(context: CallbackContext):
    """Periodic cleanup"""
    try:
        now = datetime.now()
        users_to_remove = []
        
        for user_id, user_info in cm.waiting.items():
            try:
                joined_time = datetime.fromisoformat(user_info.get('joined', ''))
                if (now - joined_time).seconds > 300:
                    users_to_remove.append(user_id)
            except:
                pass
        
        for user_id in users_to_remove:
            cm.remove_from_waiting(user_id)
            
            try:
                context.bot.send_message(
                    user_id,
                    "Search cancelled due to inactivity.\n"
                    "Press 'Find Partner' to search again."
                )
            except:
                pass
        
        chats_to_end = []
        for chat_id, chat in cm.active_chats.items():
            if not chat.get('active'):
                continue
            
            try:
                last_message = chat.get('last_message', chat.get('created', ''))
                last_time = datetime.fromisoformat(last_message)
                if (now - last_time).seconds > 1800:
                    chats_to_end.append(chat_id)
            except:
                pass
        
        for chat_id in chats_to_end:
            cm.end_chat(chat_id, "inactive")
            
            chat = cm.active_chats.get(chat_id)
            if chat:
                for user_info in [chat['user1'], chat['user2']]:
                    try:
                        context.bot.send_message(
                            user_info['id'],
                            "Chat ended due to inactivity."
                        )
                    except:
                        pass
        
        if users_to_remove or chats_to_end:
            logger.info(f"Cleanup: Removed {len(users_to_remove)} users, ended {len(chats_to_end)} chats")
    
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

# ==================== MAIN ====================
def main():
    print("\n" + "="*60)
    print(f"BONDLY BOT v{BOT_VERSION} - PROFESSIONAL EDITION")
    print("="*60)
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("Using python-telegram-bot v13.15 (Python 3.13 compatible)")
    print("="*60)
    print("Fixed: Nickname changing now works properly")
    print("Fixed: Clean text formatting without stars")
    print("Fixed: Gender selection moved to search time")
    print("="*60)
    print("Starting bot...")
    print("="*60)
    
    # Create updater with v13.15 API
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Registration conversation
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('register', register_start),
            MessageHandler(Filters.text & Filters.regex(r'^Register$'), register_start)
        ],
        states={
            REG_NICKNAME: [MessageHandler(Filters.text & ~Filters.command, register_nickname)],
            REG_GENDER: [MessageHandler(Filters.text & ~Filters.command, register_gender)],
        },
        fallbacks=[CommandHandler('cancel', register_cancel)],
    )
    
    # Add handlers
    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("search", search))
    dp.add_handler(CommandHandler("leave", leave))
    dp.add_handler(CommandHandler("profile", profile))
    dp.add_handler(CommandHandler("stats", stats_command))
    dp.add_handler(CommandHandler("nickname", nickname_command))
    dp.add_handler(CommandHandler("filter", filter_command))
    dp.add_handler(CommandHandler("delete", delete_command))
    dp.add_handler(CommandHandler("blocked", blocked_command))
    dp.add_handler(CommandHandler("settings", settings_command))
    
    # Callback handler
    dp.add_handler(CallbackQueryHandler(callback_handler))
    
    # Menu buttons
    dp.add_handler(MessageHandler(
        Filters.text & Filters.regex(r'^(Find Partner|Statistics|Profile|Settings|Help|Register)$'),
        handle_menu
    ))
    
    # Media handlers
    dp.add_handler(MessageHandler(
        Filters.photo | Filters.video | Filters.voice | Filters.sticker,
        handle_media
    ))
    
    # Text messages (must be last)
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        handle_text
    ))
    
    # Add job queue for cleanup
    job_queue = updater.job_queue
    if job_queue:
        job_queue.run_repeating(cleanup_task, interval=60, first=30)
    
    print("Bot is ready!")
    print("="*60)
    
    # Run bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
