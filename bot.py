import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import sqlite3
import re
from datetime import datetime

TOKEN = '8084001355:AAHteV_bl0y7J0Q-WLY-jQR409qyvl8ayeE'
ADMIN_PASSWORD = 'Harshit@1234'
ADMIN_PANEL_USERS = set()
MIN_WITHDRAW = 2
REFER_BONUS = 0.5
SIGNUP_BONUS = 1
PAYOUT_CHANNEL = '@tR_PayOutChannel'
SUPPORT_USER = "@Ankush_Malik"

conn = sqlite3.connect('referbot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, referred_by INTEGER, upi TEXT, joined INTEGER DEFAULT 0, got_signup_bonus INTEGER DEFAULT 0, signup_time TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS refs (user_id INTEGER PRIMARY KEY, refer_code TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS withdraws (user_id INTEGER, amount REAL, upi TEXT, time TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS refer_rewards (user_id INTEGER PRIMARY KEY, rewarded INTEGER DEFAULT 0)''')
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

def get_refer_code(uid):
    return f"REF{uid}"

def get_channels():
    cursor.execute("SELECT channel_id FROM channels")
    return [x[0] for x in cursor.fetchall()]

def is_joined_all(user_id):
    channels = get_channels()
    joined = True
    not_joined = []
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                joined = False
                not_joined.append(ch)
        except:
            joined = False
            not_joined.append(ch)
    return joined, not_joined

def main_menu_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton('💸 Withdraw'), KeyboardButton('🎁 Refer & Earn'))
    markup.row(KeyboardButton('🏦 Set UPI ID'), KeyboardButton('💰 Balance'))
    markup.row(KeyboardButton('📊 Stats'), KeyboardButton('🆘 Help'))
    markup.row(KeyboardButton('✨ Features'))
    return markup

def features_inline_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💸 Withdraw Guide", callback_data="feature_withdraw"))
    markup.add(InlineKeyboardButton("🎁 Referral System", callback_data="feature_refer"))
    markup.add(InlineKeyboardButton("🔒 Security Info", callback_data="feature_security"))
    markup.add(InlineKeyboardButton("🏦 UPI Info", callback_data="feature_upi"))
    markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_main_menu"))
    return markup

def admin_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton('📊 Stats', callback_data='admin_stats'), InlineKeyboardButton('📢 Broadcast', callback_data='admin_broadcast'))
    markup.row(InlineKeyboardButton('➕ Set Channels', callback_data='admin_addch'), InlineKeyboardButton('➖ Remove Channels', callback_data='admin_rmch'))
    markup.row(InlineKeyboardButton('➕ Add Balance', callback_data='admin_addbal'), InlineKeyboardButton('➖ Remove Balance', callback_data='admin_rmbal'))
    markup.add(InlineKeyboardButton('⬅️ Admin Menu / Exit', callback_data='admin_back'))
    return markup

def join_channels_markup(user_id):
    markup = InlineKeyboardMarkup()
    for ch in get_channels():
        markup.add(InlineKeyboardButton(f"🔗 Join {ch}", url=f"https://t.me/{ch.replace('@','')}", callback_data='joinch'))
    markup.add(InlineKeyboardButton('✅ Joined All', callback_data='verify_join'))
    return markup

def set_upi_markup(existing_upi=None):
    markup = InlineKeyboardMarkup()
    if existing_upi:
        markup.add(InlineKeyboardButton("✏️ Change UPI ID", callback_data="change_upi"))
    return markup

def give_bonus_and_referral_notify(user_id):
    cursor.execute("SELECT joined, got_signup_bonus, referred_by FROM users WHERE user_id=?", (user_id,))
    d = cursor.fetchone()
    if not d:
        return False
    joined, got_signup_bonus, referred_by = d
    if joined == 0 and got_signup_bonus == 0:
        joined, _ = is_joined_all(user_id)
        if joined:
            cursor.execute("UPDATE users SET joined=1, got_signup_bonus=1, balance=balance+? WHERE user_id=?", (SIGNUP_BONUS, user_id))
            # Only reward the referrer if not already rewarded for this user
            if referred_by and referred_by != user_id:
                cursor.execute("SELECT rewarded FROM refer_rewards WHERE user_id=?", (user_id,))
                already_rewarded = cursor.fetchone()
                if not already_rewarded:
                    cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (REFER_BONUS, referred_by))
                    cursor.execute("INSERT INTO refer_rewards (user_id, rewarded) VALUES (?, 1)", (user_id,))
                    conn.commit()
                    try:
                        bot.send_message(referred_by, f"🎉 <b>You earned ₹{REFER_BONUS:.2f} Referral Bonus!</b>\nA new user joined all channels using your link. Keep sharing to earn more! 💸")
                    except:
                        pass
            conn.commit()
            return True
    return False

def send_main_menu(user_id, text):
    bot.send_message(user_id, text, reply_markup=main_menu_markup())

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.from_user.id
    args = m.text.split()
    referred_by = None
    if len(args) > 1:
        try:
            code = args[1]
            cursor.execute("SELECT user_id FROM refs WHERE refer_code=?", (code,))
            d = cursor.fetchone()
            if d and d[0] != user_id:
                referred_by = d[0]
        except: pass
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, referred_by, balance, joined, got_signup_bonus, signup_time) VALUES (?, ?, 0, 0, 0, ?)", (user_id, referred_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        cursor.execute("INSERT INTO refs (user_id, refer_code) VALUES (?, ?)", (user_id, get_refer_code(user_id)))
        conn.commit()
    joined, notj = is_joined_all(user_id)
    if not joined:
        msg = f"🔒 <b>Join All Channels to Unlock Menu</b>:\n\n"
        for ch in get_channels():
            msg += f"🔗 {ch}\n"
        msg += "\nAfter joining all, tap <b>✅ Joined All</b>."
        bot.send_message(user_id, msg, reply_markup=join_channels_markup(user_id))
    else:
        give_bonus_and_referral_notify(user_id)
        send_main_menu(user_id, f"<b>Welcome 🇮🇳 Levi!</b>\n\n🏆 Explore our Refer & Earn program!\n💎 Earn ₹{REFER_BONUS} per referral\n🎉 Join, refer, and withdraw easily!\n")

@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join(call):
    user_id = call.from_user.id
    joined, notj = is_joined_all(user_id)
    if joined:
        gave = give_bonus_and_referral_notify(user_id)
        bot.delete_message(user_id, call.message.message_id)
        if gave:
            bot.send_message(user_id, f"🎉 <b>Congrats! You received ₹{SIGNUP_BONUS} Sign Up Bonus.</b>")
        send_main_menu(user_id, "✅ <b>All Done! Welcome to the Main Menu.</b>")
    else:
        msg = "⛔ <b>Please join ALL channels first!</b>\n"
        for ch in notj:
            msg += f"🔗 {ch}\n"
        bot.answer_callback_query(call.id, "Join all channels before proceeding.", show_alert=True)
        bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=join_channels_markup(user_id))

@bot.message_handler(func=lambda m: m.text == '🎁 Refer & Earn')
def send_refer(m):
    user_id = m.from_user.id
    code = get_refer_code(user_id)
    msg = f"🎁 <b>Your Referral Link:</b>\n\n👉 https://t.me/{bot.get_me().username}?start={code}\n\n💸 Earn ₹{REFER_BONUS} per friend who joins and completes channel join!\n"
    bot.send_message(user_id, msg, reply_markup=main_menu_markup())

@bot.message_handler(func=lambda m: m.text == '💰 Balance')
def bal(m):
    user_id = m.from_user.id
    cursor.execute("SELECT balance, upi FROM users WHERE user_id=?", (user_id,))
    d = cursor.fetchone()
    if d:
        bal, upi = d
        msg = f"💰 <b>Your Balance:</b> ₹{bal:.2f}\n🏦 <b>UPI:</b> {upi or 'Not set'}"
        bot.send_message(user_id, msg, reply_markup=main_menu_markup())

@bot.message_handler(func=lambda m: m.text == '🏦 Set UPI ID')
def set_upi(m):
    user_id = m.from_user.id
    cursor.execute("SELECT upi FROM users WHERE user_id=?", (user_id,))
    user_upi = cursor.fetchone()
    if user_upi and user_upi[0]:
        bot.send_message(user_id, f"⚠️ <b>Your Existing UPI ID:</b> <code>{user_upi[0]}</code>\n\nYou can change it below.", reply_markup=set_upi_markup(user_upi[0]))
        return
    msg = "🏦 <b>Send your UPI ID</b>\n\nExample: <code>instantupibot@fam</code>\n\nUPI must contain <b>@</b> and must be unique."
    bot.send_message(user_id, msg, reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m, process_upi)

@bot.callback_query_handler(func=lambda call: call.data == "change_upi")
def change_upi(call):
    user_id = call.from_user.id
    bot.send_message(user_id, "✏️ <b>Send your new UPI ID</b>\n\n(Existing UPI will be replaced, must be unique)", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(call.message, process_upi_change)

def process_upi_change(m):
    user_id = m.from_user.id
    upi = m.text.strip().replace(' ', '')
    if not re.match(r'^[\w\.\-]+@[\w]+$', upi):
        bot.send_message(user_id, "❌ <b>Invalid UPI. Try again:</b>")
        bot.register_next_step_handler(m, process_upi_change)
        return
    cursor.execute("SELECT user_id FROM users WHERE upi=?", (upi,))
    exist = cursor.fetchone()
    if exist and exist[0] != user_id:
        bot.send_message(user_id, "🚫 <b>This UPI is already used by another user. Try another!</b>")
        bot.register_next_step_handler(m, process_upi_change)
        return
    cursor.execute("UPDATE users SET upi=? WHERE user_id=?", (upi, user_id))
    conn.commit()
    bot.send_message(user_id, f"✅ <b>Your UPI is now:</b> <code>{upi}</code>", reply_markup=main_menu_markup())

def process_upi(m):
    user_id = m.from_user.id
    upi = m.text.strip().replace(' ', '')
    if not re.match(r'^[\w\.\-]+@[\w]+$', upi):
        bot.send_message(user_id, "❌ <b>Invalid UPI. Try again:</b>")
        bot.register_next_step_handler(m, process_upi)
        return
    cursor.execute("SELECT user_id FROM users WHERE upi=?", (upi,))
    exist = cursor.fetchone()
    if exist and exist[0] != user_id:
        bot.send_message(user_id, "🚫 <b>This UPI is already used by another user. Try another!</b>")
        bot.register_next_step_handler(m, process_upi)
        return
    cursor.execute("UPDATE users SET upi=? WHERE user_id=?", (upi, user_id))
    conn.commit()
    bot.send_message(user_id, f"✅ <b>Your UPI is now:</b> <code>{upi}</code>", reply_markup=main_menu_markup())

@bot.message_handler(func=lambda m: m.text == '💸 Withdraw')
def withdraw(m):
    user_id = m.from_user.id
    cursor.execute("SELECT balance, upi FROM users WHERE user_id=?", (user_id,))
    d = cursor.fetchone()
    if d:
        bal, upi = d
        if not upi:
            bot.send_message(user_id, "🏦 <b>Set your UPI first using the menu!</b>", reply_markup=main_menu_markup())
            return
        if bal < MIN_WITHDRAW:
            bot.send_message(user_id, f"❌ <b>Insufficient balance (Min ₹{MIN_WITHDRAW})</b>", reply_markup=main_menu_markup())
            return
        msg = f"💸 <b>Enter amount to withdraw</b> (Min ₹{MIN_WITHDRAW}, Max ₹{bal:.2f}):"
        bot.send_message(user_id, msg, reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(m, lambda msg: process_withdraw(msg, bal, upi))
    else:
        bot.send_message(user_id, "❌ <b>User not found</b>", reply_markup=main_menu_markup())

def process_withdraw(m, bal, upi):
    user_id = m.from_user.id
    try:
        amt = float(m.text)
        if amt < MIN_WITHDRAW or amt > bal:
            bot.send_message(user_id, f"❌ <b>Enter valid amount (Min ₹{MIN_WITHDRAW}, Max ₹{bal:.2f})</b>")
            bot.register_next_step_handler(m, lambda mm: process_withdraw(mm, bal, upi))
            return
        cursor.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amt, user_id))
        cursor.execute("INSERT INTO withdraws (user_id, amount, upi, time) VALUES (?, ?, ?, ?)", (user_id, amt, upi, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        msg = f"✅ <b>Withdraw request sent:</b> ₹{amt:.2f}\nUPI: <code>{upi}</code>\n\n⏳ Payment will be made within 1 hour."
        bot.send_message(user_id, msg, reply_markup=main_menu_markup())
        admin_msg = f"💸 <b>NEW WITHDRAW REQUEST</b> 💸\n\n👤 User: <a href='tg://user?id={user_id}'>{user_id}</a>\n💳 UPI: <code>{upi}</code>\n💰 Amount: ₹{amt:.2f}\n📅 Time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n\n🔖 <b>Process payout ASAP!</b>"
        bot.send_message(PAYOUT_CHANNEL, admin_msg, disable_web_page_preview=True)
    except:
        bot.send_message(user_id, "❌ <b>Enter valid amount!</b>")
        bot.register_next_step_handler(m, lambda mm: process_withdraw(mm, bal, upi))

@bot.message_handler(commands=['admin'])
def admin_login(m):
    bot.send_message(m.chat.id, "🔐 Send admin password:")
    bot.register_next_step_handler(m, process_admin_pw)

def process_admin_pw(m):
    user_id = m.from_user.id
    if m.text.strip() == ADMIN_PASSWORD:
        ADMIN_PANEL_USERS.add(user_id)
        bot.send_message(user_id, "✅ <b>Admin Panel Access Granted</b>", reply_markup=admin_menu_markup())
    else:
        bot.send_message(user_id, "❌ <b>Incorrect password!</b>")

@bot.message_handler(func=lambda m: m.text == '📊 Stats')
def stats(m):
    user_id = m.from_user.id
    if user_id in ADMIN_PANEL_USERS:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE joined=1")
        joined_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(balance) FROM users")
        total_bal = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM withdraws")
        total_withdraws = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(amount) FROM withdraws")
        total_withdraw_amt = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM channels")
        chs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT upi) FROM users WHERE upi IS NOT NULL")
        unique_upis = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM refer_rewards")
        refer_rewards = cursor.fetchone()[0]
        msg = f"""<b>📊 Deep Bot Stats (Admin)</b>
👥 Total Users: {total_users}
✅ Users Joined All: {joined_users}
💰 Total Balance: ₹{total_bal:.2f}
💸 Total Withdraws: {total_withdraws} (₹{total_withdraw_amt:.2f})
🔗 Channels: {chs}
🏦 Unique UPI: {unique_upis}
💎 Referral Rewards Given: {refer_rewards}
"""
        bot.send_message(user_id, msg, reply_markup=main_menu_markup())
    else:
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        bal = (cursor.fetchone() or [0])[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
        refs = cursor.fetchone()[0]
        msg = f"""<b>📊 Your Stats</b>
💰 Balance: ₹{bal:.2f}
👫 Referrals: {refs}
"""
        bot.send_message(user_id, msg, reply_markup=main_menu_markup())

@bot.message_handler(func=lambda m: m.text == '🆘 Help')
def help_cmd(m):
    msg = f"""<b>🆘 Bot Help</b>

🏆 <b>Refer & Earn Program</b>
• Earn ₹{REFER_BONUS} per successful referral.
• Sign-up Bonus: ₹{SIGNUP_BONUS} (after joining all channels).
• <b>Minimum Withdrawal:</b> ₹{MIN_WITHDRAW}
• <b>Payment Time:</b> Within 1 hour after request.
• <b>UPI ID:</b> Must be unique and can be changed anytime.

<b>How to use</b>
1. Join all channels required.
2. Set your UPI ID (must have '@', can be changed).
3. Refer friends with your link.
4. Withdraw your earnings.

<b>For more info or support:</b> {SUPPORT_USER}
"""
    bot.send_message(m.chat.id, msg, reply_markup=main_menu_markup())

@bot.message_handler(func=lambda m: m.text == '✨ Features')
def features(m):
    bot.send_message(m.from_user.id, "✨ <b>Bot Features</b>:\n\n• High Security\n• Instant Referral Rewards\n• Fast Withdrawals\n• Secure UPI Validation\n• Admin Panel & Broadcast\n• Automated Channel Join Check\n\nSelect a feature below for more info:", reply_markup=features_inline_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('feature_') or call.data == 'back_main_menu')
def features_info(call):
    if call.data == "feature_withdraw":
        txt = "💸 <b>Withdraw Guide</b>\n\n• Minimum ₹2 required.\n• Set UPI (unique).\n• Withdraw requests are paid to your UPI within 1 hour."
    elif call.data == "feature_refer":
        txt = "🎁 <b>Referral System</b>\n\n• Share your unique referral link.\n• Earn ₹0.5 for every friend who joins all channels."
    elif call.data == "feature_security":
        txt = "🔒 <b>Security Info</b>\n\n• Each UPI can only be used by one user.\n• Channel join checks are automatic.\n• No one can bypass the system."
    elif call.data == "feature_upi":
        txt = "🏦 <b>UPI Info</b>\n\n• Your UPI must contain '@'.\n• You can change your UPI anytime from the menu."
    elif call.data == "back_main_menu":
        send_main_menu(call.from_user.id, "<b>Welcome 🇮🇳 Levi!</b>")
        return
    bot.edit_message_text(txt, call.from_user.id, call.message.message_id, reply_markup=features_inline_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_actions(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_PANEL_USERS:
        bot.answer_callback_query(call.id, "Admin only", show_alert=True)
        return
    if call.data == 'admin_stats':
        stats(call.message)
    elif call.data == 'admin_broadcast':
        bot.edit_message_text("📢 <b>Send broadcast message (HTML supported):</b>", user_id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_broadcast)
    elif call.data == 'admin_addch':
        bot.edit_message_text("➕ <b>Send channel username to add (with @):</b>", user_id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_add_channel)
    elif call.data == 'admin_rmch':
        chlist = get_channels()
        if not chlist:
            bot.answer_callback_query(call.id, "No channels to remove", show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        for c in chlist:
            markup.add(InlineKeyboardButton(f"❌ {c}", callback_data=f'delch|{c}'))
        bot.edit_message_text("➖ <b>Select channel to remove:</b>", user_id, call.message.message_id, reply_markup=markup)
    elif call.data == 'admin_addbal':
        bot.edit_message_text("💰 <b>Send user_id and amount to add (user_id amount):</b>", user_id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_add_balance)
    elif call.data == 'admin_rmbal':
        bot.edit_message_text("💸 <b>Send user_id and amount to remove (user_id amount):</b>", user_id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_remove_balance)
    elif call.data == 'admin_back':
        bot.send_message(user_id, "Admin Menu Closed.", reply_markup=main_menu_markup())

def admin_broadcast(m):
    cursor.execute("SELECT user_id FROM users")
    for uid in cursor.fetchall():
        try:
            bot.send_message(uid[0], m.text, reply_markup=main_menu_markup())
        except: pass
    bot.send_message(m.from_user.id, "✅ <b>Broadcast sent!</b>", reply_markup=admin_menu_markup())

def admin_add_channel(m):
    ch = m.text.strip()
    if not ch.startswith('@'):
        bot.send_message(m.from_user.id, "❌ <b>Channel must start with @</b>")
        bot.register_next_step_handler(m, admin_add_channel)
        return
    cursor.execute("INSERT OR IGNORE INTO channels (channel_id) VALUES (?)", (ch,))
    conn.commit()
    bot.send_message(m.from_user.id, f"✅ <b>Added:</b> {ch}", reply_markup=admin_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('delch|'))
def del_channel(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_PANEL_USERS:
        bot.answer_callback_query(call.id, "Admin only", show_alert=True)
        return
    ch = call.data.split('|')[1]
    cursor.execute("DELETE FROM channels WHERE channel_id=?", (ch,))
    conn.commit()
    bot.answer_callback_query(call.id, f"Removed {ch}", show_alert=True)
    bot.edit_message_text("✅ <b>Channel removed.</b>", user_id, call.message.message_id, reply_markup=admin_menu_markup())

def admin_add_balance(m):
    try:
        user_id, amount = m.text.split()
        user_id = int(user_id)
        amount = float(amount)
        cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        conn.commit()
        bot.send_message(m.from_user.id, f"✅ Added ₹{amount} to {user_id}", reply_markup=admin_menu_markup())
    except:
        bot.send_message(m.from_user.id, "❌ Usage: <code>user_id amount</code>", reply_markup=admin_menu_markup())

def admin_remove_balance(m):
    try:
        user_id, amount = m.text.split()
        user_id = int(user_id)
        amount = float(amount)
        cursor.execute("UPDATE users SET balance=MAX(0, balance-?) WHERE user_id=?", (amount, user_id))
        conn.commit()
        bot.send_message(m.from_user.id, f"✅ Removed ₹{amount} from {user_id}", reply_markup=admin_menu_markup())
    except:
        bot.send_message(m.from_user.id, "❌ Usage: <code>user_id amount</code>", reply_markup=admin_menu_markup())

@bot.message_handler(func=lambda m: True)
def catch_all(m):
    user_id = m.from_user.id
    cursor.execute("SELECT joined FROM users WHERE user_id=?", (user_id,))
    d = cursor.fetchone()
    if not d or d[0]==0:
        joined, _ = is_joined_all(user_id)
        if not joined:
            msg = f"🔒 <b>Join All Channels to Unlock Menu</b>:\n\n"
            for ch in get_channels():
                msg += f"🔗 {ch}\n"
            msg += "\nAfter joining all, tap <b>✅ Joined All</b>."
            bot.send_message(user_id, msg, reply_markup=join_channels_markup(user_id))
            return
        else:
            give_bonus_and_referral_notify(user_id)
            send_main_menu(user_id, "<b>Welcome 🇮🇳 Levi!</b>")
            return
    send_main_menu(user_id, "🔸 <b>Use the menu below to continue.</b>")

bot.infinity_polling()