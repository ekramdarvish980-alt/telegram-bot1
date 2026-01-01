#!/usr/bin/env python3
"""
Bondly Bot v1.8 - Ultimate Edition
Fixed: Username conversion, Leave partner button, Auto registration, Next partner functionality
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

# Telegram imports
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
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
BOT_VERSION = "1.8"

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

# ==================== IMPROVED USERNAME CONVERSION ====================
def clean_nickname(nickname: str) -> str:
    """Clean and format nickname properly"""
    if not nickname:
        return "User"
    
    # Remove @ symbol if present
    nickname = nickname.replace('@', '')
    
    # Remove special characters but keep letters, numbers, spaces, and underscores
    nickname = re.sub(r'[^\w\s]', '', nickname, flags=re.UNICODE)
    
    # Remove extra spaces
    nickname = ' '.join(nickname.split())
    
    # Capitalize first letter of each word
    nickname = nickname.title()
    
    return nickname[:20]  # Limit to 20 characters

def generate_nickname(user: Update.effective_user) -> str:
    """Generate nickname from Telegram profile - IMPROVED VERSION"""
    # Priority 1: Username (without @)
    if user.username:
        nickname = user.username.replace('@', '')
        return clean_nickname(nickname)
    
    # Priority 2: First name + last name
    if user.first_name:
        if user.last_name:
            nickname = f"{user.first_name} {user.last_name}"
        else:
            nickname = user.first_name
        return clean_nickname(nickname)
    
    # Priority 3: Just first name
    if user.first_name:
        return clean_nickname(user.first_name)
    
    # Priority 4: Generate random name
    adjectives = ["Cool", "Smart", "Happy", "Funny", "Brave", "Kind", "Wise", "Gentle"]
    nouns = ["Tiger", "Eagle", "Dolphin", "Phoenix", "Wolf", "Lion", "Dragon", "Bear"]
    
    random_num = random.randint(10, 99)
    nickname = f"{random.choice(adjectives)}{random.choice(nouns)}{random_num}"
    
    return nickname

def auto_register_user(user_id: int, user: Update.effective_user) -> Dict:
    """Automatically register a user with improved nickname system"""
    # Generate nickname from username/name
    nickname = generate_nickname(user)
    
    # Create user data with default values
    user_data = {
        'nickname': nickname,
        'gender': 'not_specified',
        'gender_display': 'Not specified',
        'search_filter': 'random',
        'search_filter_display': 'Random',
        'telegram_name': user.full_name or "",
        'username': user.username or "",
        'registered': datetime.now().isoformat(),
        'user_id': user_id,
        'auto_registered': True
    }
    
    # Save user
    db.save_user(user_id, user_data)
    
    # Initialize stats
    db.update_stats(user_id, 'chats_started', 0)
    
    return user_data

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
    
    auto_registered = user_data.get('auto_registered', False)
    
    profile = f"""
📋 Profile

🆔 ID: {user_id}
👤 Nickname: {user_data.get('nickname', 'Unknown')}
⚤ Gender: {user_data.get('gender_display', 'Not specified')} {'(Auto)' if auto_registered else ''}
🔍 Filter: {user_data.get('search_filter_display', 'Random')}
📅 Registered: {reg_date}

💬 Chats:
  • Total: {total_chats}
  • Today: {chats_today}
  • Duration: {duration_str}

✉️ Messages:
  • Sent: {messages_sent}
  • Received: {messages_received}

⭐ Ratings: {positive_ratings}👍 {negative_ratings}👎
"""
    
    return profile.strip()

def format_stats(user_id: int, user_data: Dict) -> str:
    """Format statistics in clean style"""
    stats = db.get_stats(user_id)
    global_stats = db.get_global_stats()
    
    chat_id, chat = cm.get_chat(user_id)
    in_chat = "✅ In chat" if chat else "❌ Not in chat"
    in_queue = "🔍 Searching" if user_id in cm.waiting else "⏸️ Not searching"
    
    total_users = format_number(global_stats.get('total_users', 0))
    total_messages = format_number(global_stats.get('total_messages', 0))
    total_chats = format_number(global_stats.get('total_chats', 0))
    total_positive = format_number(global_stats.get('total_positive_ratings', 0))
    total_negative = format_number(global_stats.get('total_negative_ratings', 0))
    
    stats_text = f"""
📊 Statistics

👤 Nickname: {user_data.get('nickname', 'Unknown')}
🔍 Filter: {user_data.get('search_filter_display', 'Random')}

📈 Your Activity:
  • Messages sent: {format_number(int(stats.get('messages_sent', 0)))}
  • Messages received: {format_number(int(stats.get('messages_received', 0)))}
  • Media shared: {format_number(int(stats.get('media_sent', 0)))}
  • Chats started: {format_number(int(stats.get('chats_started', 0)))}
  • Chats today: {format_number(int(stats.get('chats_today', 0)))}
  • Chat duration: {format_duration(int(stats.get('total_chat_duration', 0)))}

📱 Current Status:
  • {in_chat}
  • {in_queue}
  • People waiting: {cm.get_waiting_count()}

🌐 Global Statistics:
  • Total users: {total_users}
  • Total messages: {total_messages}
  • Total chats: {total_chats}
  • Positive ratings: {total_positive}
  • Negative ratings: {total_negative}
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
💬 Current Chat:
  • Partner: {partner_nick}
  • Duration: {format_duration(chat_duration)}
  • Messages sent: {messages_sent}
  • Messages received: {messages_received}
"""
    
    return stats_text.strip()

# ==================== FIXED LEAVE PARTNER FUNCTION ====================
async def leave_chat_from_callback(user_id: int, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Leave chat function for both callback and command - FIXED VERSION"""
    chat_id, chat = cm.get_chat(user_id)
    
    if not chat:
        if query:
            await query.answer("You're not in a chat.", show_alert=True)
        return False
    
    partner = cm.get_partner(chat_id, user_id)
    
    ended_chat = cm.end_chat(chat_id, "left")
    
    if ended_chat:
        duration = ended_chat.get('duration', 0)
        messages_sent = ended_chat.get('messages_sent_user1', 0) if ended_chat['user1']['id'] == user_id else ended_chat.get('messages_sent_user2', 0)
        
        if partner:
            try:
                await context.bot.send_message(
                    partner['id'],
                    "❌ Your partner left the chat.\n\n"
                    "Press 'Find Partner' to find someone new."
                )
            except:
                pass
        
        # Send response based on how function was called
        if query:
            await query.edit_message_text(
                f"""
✅ Chat Ended

⏱️ Duration: {format_duration(int(duration))}
✉️ Messages sent: {messages_sent}

Press 'Find Partner' to find someone new.
"""
            )
        else:
            return f"""
✅ Chat Ended

⏱️ Duration: {format_duration(int(duration))}
✉️ Messages sent: {messages_sent}

Press 'Find Partner' to find someone new.
"""
        return True
    else:
        if query:
            await query.answer("Failed to leave chat.", show_alert=True)
        return False

# ==================== SEARCH HELPER FUNCTIONS ====================
async def start_search_for_user(user_id: int, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Helper function to start search for a user"""
    user_data = db.get_user(user_id)
    if not user_data:
        if query:
            await query.answer("Please register first!", show_alert=True)
        return False
    
    # Check if already in chat
    chat_id, chat = cm.get_chat(user_id)
    if chat:
        if query:
            await query.answer("You're already in a chat!", show_alert=True)
        return False
    
    # Check if already searching
    if user_id in cm.waiting:
        waiting_count = cm.get_waiting_count() - 1
        filter_display = user_data.get('search_filter_display', 'Random')
        if query:
            await query.answer(f"Already searching ({filter_display})... {waiting_count} people waiting", show_alert=True)
        return False
    
    # Add to waiting list
    success, message = cm.add_to_waiting(user_id, user_data)
    if not success:
        if query:
            await query.answer(message, show_alert=True)
        return False
    
    # Find match
    match = cm.find_match(user_id)
    
    if match:
        # Create new chat
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
            [InlineKeyboardButton("🔄 Next Partner", callback_data="next"),
             InlineKeyboardButton("🚫 Block", callback_data="block")],
            [InlineKeyboardButton("👍 Rate Good", callback_data="rate_good"),
             InlineKeyboardButton("👎 Rate Bad", callback_data="rate_bad")],
            [InlineKeyboardButton("❌ Leave Chat", callback_data="leave")]
        ])
        
        if query:
            await query.edit_message_text(
                f"""
🎉 New Partner Found!

👤 Partner: {partner_nick}
🤝 Compatibility: {match.get('compatibility', 50)}%

💬 Start chatting now!
""",
                reply_markup=buttons
            )
        else:
            await context.bot.send_message(
                user_id,
                f"""
🎉 New Partner Found!

👤 Partner: {partner_nick}
🤝 Compatibility: {match.get('compatibility', 50)}%

💬 Start chatting now!
""",
                reply_markup=buttons
            )
        
        # Notify partner
        try:
            await context.bot.send_message(
                partner_id,
                f"""
🎉 Match Found!

👤 Partner: {my_nick}
🤝 Compatibility: {match.get('compatibility', 50)}%

💬 Start chatting now!
""",
                reply_markup=buttons
            )
        except:
            pass
        
        return True
    else:
        # No match found, show waiting message
        waiting_count = cm.get_waiting_count() - 1
        filter_display = user_data.get('search_filter_display', 'Random')
        
        cancel_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Search", callback_data="cancel_search")]
        ])
        
        if query:
            await query.edit_message_text(
                f"""
🔍 Searching ({filter_display})

👥 People waiting: {waiting_count}
⏱️ Estimated time: {max(30, waiting_count * 15)}s

Please wait...
""",
                reply_markup=cancel_btn
            )
        else:
            await context.bot.send_message(
                user_id,
                f"""
🔍 Searching ({filter_display})

👥 People waiting: {waiting_count}
⏱️ Estimated time: {max(30, waiting_count * 15)}s

Please wait...
""",
                reply_markup=cancel_btn
            )
        return False

# ==================== MAIN COMMANDS - SIMPLIFIED ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with auto-registration"""
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Update last active
    db.update_stats(user_id, 'last_active')
    
    user_data = db.get_user(user_id)
    
    if not user_data:
        # Auto-register the user
        user_data = auto_register_user(user_id, user)
        
        message = f"""
🎉 Welcome to Bondly Bot v{BOT_VERSION}

✅ You have been automatically registered!

📝 Your nickname: {user_data['nickname']}
⚤ Gender: Not specified (set with /gender)
🔍 Filter: Random (change with /filter)

You can start chatting immediately!

📱 Main Menu:
• Find Partner - Start searching
• Profile - View your profile
• Settings - Adjust preferences
• Help - Get help

Enjoy chatting! 😊
"""
    else:
        # Already registered
        message = f"""
🎉 Bondly Bot v{BOT_VERSION}

👋 Welcome back, {user_data.get('nickname', 'User')}!

Ready to chat with new people?

📱 Main Menu:
• Find Partner - Start searching
• Profile - View your profile
• Settings - Adjust preferences
• Help - Get help

👥 People waiting: {cm.get_waiting_count()}
"""
    
    # Main menu
    main_menu = [
        ["🔍 Find Partner", "📊 Statistics"],
        ["👤 Profile", "⚙️ Settings"],
        ["❓ Help"]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for partner - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    chat_id, chat = cm.get_chat(user_id)
    if chat:
        await update.message.reply_text("❌ You're already in a chat! Use /leave to exit first.")
        return
    
    if user_id in cm.waiting:
        waiting_count = cm.get_waiting_count() - 1
        filter_display = user_data.get('search_filter_display', 'Random')
        await update.message.reply_text(f"🔍 Already searching ({filter_display})... {waiting_count} people waiting")
        return
    
    search_msg = await update.message.reply_text("🔄 Starting search...")
    
    success, message = cm.add_to_waiting(user_id, user_data)
    
    if not success:
        await search_msg.edit_text(f"❌ {message}")
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
            [InlineKeyboardButton("🔄 Next Partner", callback_data="next"),
             InlineKeyboardButton("🚫 Block", callback_data="block")],
            [InlineKeyboardButton("👍 Rate Good", callback_data="rate_good"),
             InlineKeyboardButton("👎 Rate Bad", callback_data="rate_bad")],
            [InlineKeyboardButton("❌ Leave Chat", callback_data="leave")]
        ])
        
        await search_msg.edit_text(
            f"""
🎉 Match Found!

👤 Partner: {partner_nick}
🤝 Compatibility: {match.get('compatibility', 50)}%

💬 Start chatting now!
""",
            reply_markup=buttons
        )
        
        # Notify partner
        try:
            await context.bot.send_message(
                partner_id,
                f"""
🎉 Match Found!

👤 Partner: {my_nick}
🤝 Compatibility: {match.get('compatibility', 50)}%

💬 Start chatting now!
""",
                reply_markup=buttons
            )
        except:
            pass
    else:
        waiting_count = cm.get_waiting_count() - 1
        filter_display = user_data.get('search_filter_display', 'Random')
        
        cancel_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Search", callback_data="cancel_search")]
        ])
        
        await search_msg.edit_text(
            f"""
🔍 Searching ({filter_display})

👥 People waiting: {waiting_count}
⏱️ Estimated time: {max(30, waiting_count * 15)}s

Please wait...
""",
            reply_markup=cancel_btn
        )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media messages"""
    user_id = update.effective_user.id
    
    chat_id, chat = cm.get_chat(user_id)
    if not chat:
        await update.message.reply_text("❌ You're not in a chat. Press 'Find Partner' to search.")
        return
    
    partner = cm.get_partner(chat_id, user_id)
    if not partner:
        await update.message.reply_text("❌ Partner not found. The chat may have ended.")
        return
    
    user_data = db.get_user(user_id)
    nickname = user_data.get('nickname', 'User') if user_data else 'User'
    
    try:
        await context.bot.send_chat_action(chat_id=partner['id'], action="typing")
        
        if update.message.photo:
            photo = update.message.photo[-1]
            caption = update.message.caption or ""
            
            await context.bot.send_photo(
                partner['id'],
                photo.file_id,
                caption=f"📸 Photo from {nickname}: {caption}" if caption else f"📸 Photo from {nickname}"
            )
            
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
            
        elif update.message.video:
            video = update.message.video
            caption = update.message.caption or ""
            
            await context.bot.send_video(
                partner['id'],
                video.file_id,
                caption=f"🎬 Video from {nickname}: {caption}" if caption else f"🎬 Video from {nickname}"
            )
            
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
            
        elif update.message.voice:
            voice = update.message.voice
            
            await context.bot.send_voice(
                partner['id'],
                voice.file_id,
                caption=f"🎤 Voice message from {nickname}"
            )
            
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
            
        elif update.message.sticker:
            await context.bot.send_sticker(partner['id'], update.message.sticker.file_id)
            cm.record_message(chat_id, user_id, is_media=True)
            db.update_stats(user_id, 'media_sent')
        
        db.update_stats(partner['id'], 'messages_received')
        
    except Exception as e:
        logger.error(f"Failed to send media: {e}")
        await update.message.reply_text("❌ Failed to send media.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text in ["🔍 Find Partner", "📊 Statistics", "👤 Profile", "⚙️ Settings", "❓ Help"]:
        await handle_menu(update, context)
        return
    
    chat_id, chat = cm.get_chat(user_id)
    if not chat:
        await update.message.reply_text("❌ You're not in a chat. Press 'Find Partner' to search.")
        return
    
    partner = cm.get_partner(chat_id, user_id)
    if not partner:
        await update.message.reply_text("❌ Partner not found. The chat may have ended.")
        return
    
    user_data = db.get_user(user_id)
    nickname = user_data.get('nickname', 'User') if user_data else 'User'
    
    try:
        await context.bot.send_chat_action(chat_id=partner['id'], action="typing")
        
        await context.bot.send_message(partner['id'], f"{nickname}: {text}")
        
        cm.record_message(chat_id, user_id)
        
        db.update_stats(user_id, 'messages_sent')
        db.update_stats(partner['id'], 'messages_received')
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        await update.message.reply_text("❌ Failed to send message.")

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Leave chat command"""
    user_id = update.effective_user.id
    
    response = await leave_chat_from_callback(user_id, context)
    if response:
        await update.message.reply_text(response)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show profile - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    profile_text = format_profile(user_id, user_data)
    await update.message.reply_text(profile_text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    stats_text = format_stats(user_id, user_data)
    await update.message.reply_text(stats_text)

async def nickname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change nickname - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    if not context.args:
        current_nick = user_data.get('nickname', 'Not set')
        await update.message.reply_text(
            f"✏️ Change Nickname\n\n"
            f"Current: {current_nick}\n\n"
            "Usage: /nickname [new_nickname]\n"
            "Example: /nickname John"
        )
        return
    
    new_nick = ' '.join(context.args).strip()
    
    # Simple validation
    if not new_nick or len(new_nick) < 2:
        await update.message.reply_text("❌ Nickname must be at least 2 characters.")
        return
    
    if len(new_nick) > 25:
        await update.message.reply_text("❌ Nickname cannot exceed 25 characters.")
        return
    
    # Update nickname
    old_nick = user_data.get('nickname', '')
    user_data['nickname'] = new_nick
    
    # Save the updated user data
    db.save_user(user_id, user_data)
    
    await update.message.reply_text(f"✅ Nickname updated from '{old_nick}' to '{new_nick}'")

async def gender_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or change gender - OPTIONAL command"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    if not context.args:
        current_gender = user_data.get('gender_display', 'Not specified')
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨 Male", callback_data="set_gender_male"),
             InlineKeyboardButton("👩 Female", callback_data="set_gender_female")],
            [InlineKeyboardButton("⚧ Other", callback_data="set_gender_other"),
             InlineKeyboardButton("❓ Not specified", callback_data="set_gender_none")]
        ])
        
        await update.message.reply_text(
            f"⚤ Set Gender (Optional)\n\n"
            f"Current: {current_gender}\n\n"
            "This helps find better matches.\n"
            "You can skip or change later.\n\n"
            "Select your gender:",
            reply_markup=keyboard
        )
        return
    
    gender_text = ' '.join(context.args).lower()
    
    gender_map = {
        'male': {'value': 'male', 'display': 'Male'},
        'female': {'value': 'female', 'display': 'Female'},
        'other': {'value': 'other', 'display': 'Other'},
        'none': {'value': 'not_specified', 'display': 'Not specified'},
        'skip': {'value': 'not_specified', 'display': 'Not specified'}
    }
    
    if gender_text not in ['male', 'female', 'other', 'none', 'skip']:
        await update.message.reply_text(
            "❌ Invalid gender!\n\n"
            "Options: male, female, other, none\n"
            "Example: /gender female\n"
            "Or use: /gender skip"
        )
        return
    
    user_data['gender'] = gender_map[gender_text]['value']
    user_data['gender_display'] = gender_map[gender_text]['display']
    user_data['auto_registered'] = False
    db.save_user(user_id, user_data)
    
    await update.message.reply_text(
        f"✅ Gender Updated!\n\n"
        f"New gender: {gender_map[gender_text]['display']}"
    )

async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change search filter - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    if not context.args:
        current_filter = user_data.get('search_filter_display', 'Random')
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Random", callback_data="filter_random"),
             InlineKeyboardButton("👨 Male only", callback_data="filter_male")],
            [InlineKeyboardButton("👩 Female only", callback_data="filter_female")]
        ])
        
        await update.message.reply_text(
            f"🔍 Search Filter\n\n"
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
        await update.message.reply_text(
            "❌ Invalid filter!\n\n"
            "Options: random, male, female\n"
            "Example: /filter female"
        )
        return
    
    user_data['search_filter'] = filter_map[filter_text]['value']
    user_data['search_filter_display'] = filter_map[filter_text]['display']
    db.save_user(user_id, user_data)
    
    await update.message.reply_text(
        f"✅ Filter Updated!\n\n"
        f"New filter: {filter_map[filter_text]['display']}"
    )

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete account"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ You don't have an account!")
        return
    
    nickname = user_data.get('nickname', 'User')
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, delete everything", callback_data="confirm_delete")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")]
    ])
    
    await update.message.reply_text(
        f"🗑️ Delete account '{nickname}'?\n\n"
        "This will remove all your data.\n"
        "This action cannot be undone!",
        reply_markup=keyboard
    )

async def blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show blocked users - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
        return
    
    blocked = db.get_blocked_users(user_id)
    
    if not blocked:
        await update.message.reply_text("✅ You haven't blocked anyone yet.")
        return
    
    message = "🚫 Blocked Users\n\n"
    buttons = []
    
    for blocked_id, info in blocked.items():
        blocked_nick = info.get('nickname', 'Unknown')
        
        message += f"• {blocked_nick} (ID: {blocked_id})\n"
        
        buttons.append([InlineKeyboardButton(
            f"✅ Unblock {blocked_nick}",
            callback_data=f"unblock_{blocked_id}"
        )])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(message, reply_markup=keyboard)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings menu - with auto-registration if needed"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    # Auto-register if not registered
    if not user_data:
        user_data = auto_register_user(user_id, update.effective_user)
        await update.message.reply_text("✅ You have been automatically registered!")
    
    settings_text = f"""
⚙️ Settings

👤 Profile Settings:
/nickname [new] - Change nickname
/gender - Set gender (optional)
/filter - Change search filter

🔒 Privacy Settings:
/blocked - Blocked users

📊 Statistics:
/stats - Your statistics

🗑️ Account Management:
/delete - Delete account

❓ Bot Information:
/help - Help guide

📋 Current Settings:
• Nickname: {user_data.get('nickname', 'Not set')}
• Gender: {user_data.get('gender_display', 'Not specified')}
• Search Filter: {user_data.get('search_filter_display', 'Random')}

🏠 Back: /start
"""
    
    await update.message.reply_text(settings_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = f"""
❓ Bondly Bot v{BOT_VERSION} - Help

🚀 Quick Start:
Just use /start - You're automatically registered!

🎯 Main Commands:
/start - Start bot (auto-registers you)
/profile - Your profile
/stats - Statistics
/settings - Settings
/help - This message

⚙️ Profile Commands:
/nickname [new] - Change nickname
/gender - Set gender (optional)
/filter - Change search filter

💬 Chat Commands:
🔍 Find Partner - Search for chat
/leave - Exit chat
Send text, photos, videos, voice messages
Use buttons during chat

🔒 Privacy Commands:
/blocked - Manage blocked users
/delete - Delete account

📸 Media Support:
• Photos
• Videos
• Voice messages
• Stickers

💡 Tips:
• You're automatically registered with a nickname from your username
• Set your gender with /gender for better matches
• Use /filter to find specific genders
• Be respectful to others
• Use block feature if needed

🛠 Support:
For issues, contact the developer.
ID support: https://t.me/Bitcoin_00009

Happy chatting! 😊
"""
    
    await update.message.reply_text(help_text)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu buttons"""
    text = update.message.text
    
    if text == "🔍 Find Partner":
        await search(update, context)
    elif text == "📊 Statistics":
        await stats_command(update, context)
    elif text == "👤 Profile":
        await profile(update, context)
    elif text == "⚙️ Settings":
        await settings_command(update, context)
    elif text == "❓ Help":
        await help_command(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks - UPDATED VERSION with Next partner fix"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    try:
        if data == "cancel_search":
            cm.remove_from_waiting(user_id)
            await query.edit_message_text("✅ Search cancelled.")
        
        elif data == "next":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                # Notify current partner
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    try:
                        await context.bot.send_message(
                            partner['id'],
                            "🔄 Your partner wants to talk to someone else.\n\nPress 'Find Partner' to find someone new."
                        )
                    except:
                        pass
                
                # End current chat
                cm.end_chat(chat_id, "next")
                
                # Start new search immediately
                await start_search_for_user(user_id, context, query)
            else:
                await query.answer("You're not in a chat!", show_alert=True)
        
        elif data == "block":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    partner_nick = partner['data'].get('nickname', 'Unknown')
                    db.block_user(user_id, partner['id'], partner_nick)
                
                # Notify partner
                if partner:
                    try:
                        await context.bot.send_message(
                            partner['id'],
                            "🚫 Your partner blocked you.\n\nPress 'Find Partner' to find someone new."
                        )
                    except:
                        pass
                
                # End current chat
                cm.end_chat(chat_id, "blocked")
                
                # Start new search immediately
                await query.edit_message_text("✅ User blocked. Searching for new partner...")
                await start_search_for_user(user_id, context, query)
            else:
                await query.answer("You're not in a chat!", show_alert=True)
        
        elif data == "leave":
            # Use the corrected leave function
            await leave_chat_from_callback(user_id, context, query)
        
        elif data == "rate_good":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    db.update_stats(partner['id'], 'ratings_positive')
                    await query.edit_message_text("✅ Rating submitted: Good 👍")
        
        elif data == "rate_bad":
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                partner = cm.get_partner(chat_id, user_id)
                if partner:
                    db.update_stats(partner['id'], 'ratings_negative')
                    await query.edit_message_text("✅ Rating submitted: Bad 👎")
        
        elif data == "confirm_delete":
            user_data = db.get_user(user_id)
            nickname = user_data.get('nickname', 'User') if user_data else 'User'
            
            cm.remove_from_waiting(user_id)
            
            chat_id, chat = cm.get_chat(user_id)
            if chat:
                cm.end_chat(chat_id, "deleted")
            
            db.delete_user(user_id)
            
            await query.edit_message_text(
                f"✅ Account '{nickname}' deleted.\n\n"
                "Use /start to register again."
            )
        
        elif data == "cancel_delete":
            await query.edit_message_text("✅ Deletion cancelled.")
        
        elif data.startswith("unblock_"):
            blocked_id = data.split("_")[1]
            
            if db.unblock_user(user_id, int(blocked_id)):
                await query.edit_message_text("✅ User unblocked.")
            else:
                await query.edit_message_text("❌ User not found in blocked list.")
        
        elif data.startswith("filter_"):
            filter_type = data.split("_")[1]
            
            filter_map = {
                'random': {'value': 'random', 'display': 'Random'},
                'male': {'value': 'male', 'display': 'Male only'},
                'female': {'value': 'female', 'display': 'Female only'}
            }
            
            if filter_type in filter_map:
                user_data = db.get_user(user_id)
                if not user_data:
                    user_data = auto_register_user(user_id, query.from_user)
                
                user_data['search_filter'] = filter_map[filter_type]['value']
                user_data['search_filter_display'] = filter_map[filter_type]['display']
                db.save_user(user_id, user_data)
                
                await query.edit_message_text(
                    f"✅ Filter updated to {filter_map[filter_type]['display']}"
                )
        
        elif data.startswith("set_gender_"):
            gender_type = data.split("_")[2]
            
            gender_map = {
                'male': {'value': 'male', 'display': 'Male'},
                'female': {'value': 'female', 'display': 'Female'},
                'other': {'value': 'other', 'display': 'Other'},
                'none': {'value': 'not_specified', 'display': 'Not specified'}
            }
            
            if gender_type in gender_map:
                user_data = db.get_user(user_id)
                if not user_data:
                    user_data = auto_register_user(user_id, query.from_user)
                
                user_data['gender'] = gender_map[gender_type]['value']
                user_data['gender_display'] = gender_map[gender_type]['display']
                user_data['auto_registered'] = False
                db.save_user(user_id, user_data)
                
                await query.edit_message_text(
                    f"✅ Gender updated to {gender_map[gender_type]['display']}"
                )
    
    except Exception as e:
        logger.error(f"Callback error: {e}")
        try:
            await query.edit_message_text("❌ An error occurred. Please try again.")
        except:
            pass

# ==================== CLEANUP TASK ====================
async def cleanup_task(context: ContextTypes.DEFAULT_TYPE):
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
                await context.bot.send_message(
                    user_id,
                    "❌ Search cancelled due to inactivity.\n"
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
                        await context.bot.send_message(
                            user_info['id'],
                            "❌ Chat ended due to inactivity."
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
    print(f"BONDLY BOT v{BOT_VERSION} - ULTIMATE EDITION")
    print("="*60)
    print("Fixed: Username conversion (cleans @ symbol properly)")
    print("Fixed: Leave partner button (works from callback)")
    print("Fixed: Auto registration on all commands")
    print("Fixed: Next partner button (instantly connects to new partner)")
    print("="*60)
    print("Starting bot...")
    print("="*60)
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("nickname", nickname_command))
    app.add_handler(CommandHandler("gender", gender_command))
    app.add_handler(CommandHandler("filter", filter_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("blocked", blocked_command))
    app.add_handler(CommandHandler("settings", settings_command))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Menu buttons
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^(🔍 Find Partner|📊 Statistics|👤 Profile|⚙️ Settings|❓ Help)$'),
        handle_menu
    ))
    
    # Media handlers
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.VOICE | filters.Sticker.ALL,
        handle_media
    ))
    
    # Text messages (must be last)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text
    ))
    
    # Add job queue for cleanup
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(cleanup_task, interval=60, first=30)
    
    print("✅ Bot is ready!")
    print("="*60)
    print("🎯 Fixed Issues:")
    print("1. ✅ Username conversion: Cleans @ symbol properly")
    print("2. ✅ Leave partner button: Works from callback")
    print("3. ✅ Auto registration: Works on all commands")
    print("4. ✅ Next partner button: Instantly connects to new partner")
    print("="*60)
    
    # Run bot
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
