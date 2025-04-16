#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import telebot
from telebot import types
import subprocess
import psutil
import time
import shutil

# إعدادات الأساسية
BOT_TOKEN = '7809842301:AAHyLkq_AvC0bR_Pdh8eZNs12r63YRnCtBg'
MAIN_DIR = os.path.expanduser("~/telegram_bot/")  # سيحول ~ إلى المسار الكامل
UPLOAD_DIR = os.path.join(MAIN_DIR, "uploads")

if not os.path.exists(MAIN_DIR):
    os.makedirs(MAIN_DIR, exist_ok=True)  # exist_ok=True لتجنب الأخطاء إذا المجلد موجود
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}   # chat_id -> current directory
user_state = {}  # chat_id -> state info
running_bots = {}  # bot filename -> subprocess instance

def is_safe_path(path):
    abs_path = os.path.abspath(path)
    return os.path.commonpath([abs_path, MAIN_DIR]) == MAIN_DIR

def get_current_dir(chat_id):
    return user_data.get(chat_id, MAIN_DIR)

def set_current_dir(chat_id, path):
    if is_safe_path(path):
        user_data[chat_id] = path
    else:
        user_data[chat_id] = MAIN_DIR

def show_main_menu(chat_id, text="القائمة الرئيسية:"):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📁 إدارة الملفات", callback_data="menu_files"),
        types.InlineKeyboardButton("🤖 إدارة البوتات", callback_data="menu_bots")
    )
    markup.add(
        types.InlineKeyboardButton("🖥 Terminal", callback_data="menu_terminal"),
        types.InlineKeyboardButton("📊 معلومات السيرفر", callback_data="menu_server")
    )
    bot.send_message(chat_id, text, reply_markup=markup)

def show_files_menu(chat_id, text="إدارة الملفات:"):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📂 عرض الملفات", callback_data="files_list"),
        types.InlineKeyboardButton("📤 رفع ملف", callback_data="upload_file"),
        types.InlineKeyboardButton("📥 تحميل ملف", callback_data="download_file")
    )
    markup.add(types.InlineKeyboardButton("◀️ رجوع", callback_data="menu_main"))
    bot.send_message(chat_id, text, reply_markup=markup)

def show_directory_listing(chat_id):
    current_dir = get_current_dir(chat_id)
    try:
        items = os.listdir(current_dir)
        items.sort()
    except Exception as e:
        bot.send_message(chat_id, f"خطأ في قراءة المجلد: {str(e)}")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    if current_dir != MAIN_DIR:
        markup.add(types.InlineKeyboardButton("📂 .. (رجوع)", callback_data="dir_up"))
    
    for item in items:
        item_path = os.path.join(current_dir, item)
        if os.path.isdir(item_path):
            btn = types.InlineKeyboardButton(f"📁 {item}", callback_data=f"dir_menu:{item}")
        else:
            btn = types.InlineKeyboardButton(f"📄 {item}", callback_data=f"file_menu:{item}")
        markup.add(btn)
    
    markup.add(
        types.InlineKeyboardButton("➕ إنشاء ملف", callback_data="create_file"),
        types.InlineKeyboardButton("➕ إنشاء مجلد", callback_data="create_dir")
    )
    markup.add(
        types.InlineKeyboardButton("📤 رفع ملف", callback_data="upload_file"),
        types.InlineKeyboardButton("📥 تحميل ملف", callback_data="download_file"),
        types.InlineKeyboardButton("◀️ رجوع", callback_data="menu_files")
    )
    bot.send_message(chat_id, f"المحتويات في:\n{current_dir}", reply_markup=markup)

def show_file_submenu(chat_id, filename):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👀 عرض", callback_data=f"view_file:{filename}"),
        types.InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_file:{filename}")
    )
    markup.add(
        types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_file:{filename}"),
        types.InlineKeyboardButton("✏️ إعادة تسمية", callback_data=f"rename_file:{filename}")
    )
    markup.add(types.InlineKeyboardButton("◀️ رجوع", callback_data="files_list"))
    bot.send_message(chat_id, f"خيارات الملف: {filename}", reply_markup=markup)

def show_dir_submenu(chat_id, dirname):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 فتح", callback_data=f"open_dir:{dirname}"),
        types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_dir:{dirname}")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ إعادة تسمية", callback_data=f"rename_dir:{dirname}")
    )
    markup.add(types.InlineKeyboardButton("◀️ رجوع", callback_data="files_list"))
    bot.send_message(chat_id, f"خيارات المجلد: {dirname}", reply_markup=markup)

def show_bot_toggle_menu(chat_id):
    current_dir = get_current_dir(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if current_dir != MAIN_DIR:
        markup.add(types.InlineKeyboardButton("📂 .. (رجوع)", callback_data="bot_dir_up"))
    # عرض المجلدات الفرعية
    try:
        items = os.listdir(current_dir)
    except Exception as e:
        bot.send_message(chat_id, f"خطأ في قراءة المجلد: {str(e)}")
        return
    for item in items:
        item_path = os.path.join(current_dir, item)
        if os.path.isdir(item_path):
            markup.add(types.InlineKeyboardButton(f"📁 {item}", callback_data=f"bot_open_dir:{item}"))
    # عرض ملفات البوت
    bot_files = [f for f in items if f.endswith('.py')]
    for bot_file in bot_files:
        status = "🟢" if bot_file in running_bots else "🔴"
        markup.add(types.InlineKeyboardButton(
            f"{status} {bot_file}",
            callback_data=f"toggle_bot:{bot_file}"
        ))
    
    markup.add(types.InlineKeyboardButton("◀️ رجوع", callback_data="menu_main"))
    bot.send_message(chat_id, f"مسار البوت الحالي:\n{current_dir}\nاختر البوت أو المجلد:", reply_markup=markup)

def show_terminal_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ تنفيذ أمر", callback_data="terminal_execute"))
    markup.add(types.InlineKeyboardButton("⛔ إنهاء الجلسة", callback_data="terminal_exit"))
    bot.send_message(chat_id, "Terminal:", reply_markup=markup)

def show_server_info(chat_id):
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(MAIN_DIR)
        uptime = time.time() - psutil.boot_time()
        info = (
            f"📊 معلومات السيرفر:\n"
            f"• المعالج: {cpu}%\n"
            f"• الذاكرة: {memory.percent}%\n"
            f"• التخزين: {disk.percent}%\n"
            f"• وقت التشغيل: {time.strftime('%H:%M:%S', time.gmtime(uptime))}"
        )
    except Exception as e:
        info = f"خطأ في الحصول على المعلومات: {str(e)}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ رجوع", callback_data="menu_main"))
    bot.send_message(chat_id, info, reply_markup=markup)

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    set_current_dir(chat_id, MAIN_DIR)
    user_state.pop(chat_id, None)
    bot.send_message(chat_id, f"مرحبا!\nالمسار الحالي: {MAIN_DIR}")
    show_main_menu(chat_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

    try:
        if data == "menu_main":
            user_state.pop(chat_id, None)
            show_main_menu(chat_id)
        
        elif data == "menu_files":
            user_state.pop(chat_id, None)
            show_files_menu(chat_id)
        
        elif data == "menu_bots":
            user_state.pop(chat_id, None)
            show_bot_toggle_menu(chat_id)
        
        elif data == "menu_terminal":
            user_state.pop(chat_id, None)
            show_terminal_menu(chat_id)
        
        elif data == "menu_server":
            user_state.pop(chat_id, None)
            show_server_info(chat_id)
        
        elif data == "files_list":
            show_directory_listing(chat_id)
        
        elif data == "dir_up":
            current_dir = get_current_dir(chat_id)
            parent_dir = os.path.dirname(current_dir)
            set_current_dir(chat_id, parent_dir)
            show_directory_listing(chat_id)
        
        elif data.startswith("dir_menu:"):
            dirname = data.split(":", 1)[1]
            show_dir_submenu(chat_id, dirname)
        
        elif data.startswith("file_menu:"):
            filename = data.split(":", 1)[1]
            show_file_submenu(chat_id, filename)
        
        elif data.startswith("open_dir:"):
            dirname = data.split(":", 1)[1]
            current_dir = get_current_dir(chat_id)
            new_path = os.path.join(current_dir, dirname)
            if is_safe_path(new_path):
                set_current_dir(chat_id, new_path)
                show_directory_listing(chat_id)
            else:
                bot.send_message(chat_id, "مسار غير مسموح به!")
        
        elif data.startswith("delete_file:"):
            filename = data.split(":", 1)[1]
            current_dir = get_current_dir(chat_id)
            file_path = os.path.join(current_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                bot.send_message(chat_id, f"تم حذف الملف: {filename}")
            show_directory_listing(chat_id)
        
        elif data.startswith("delete_dir:"):
            dirname = data.split(":", 1)[1]
            current_dir = get_current_dir(chat_id)
            dir_path = os.path.join(current_dir, dirname)
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                bot.send_message(chat_id, f"تم حذف المجلد: {dirname}")
            show_directory_listing(chat_id)
        
        elif data.startswith("toggle_bot:"):
            bot_file = data.split(":", 1)[1]
            current_dir = get_current_dir(chat_id)
            file_path = os.path.join(current_dir, bot_file)
            
            if bot_file in running_bots:
                process = running_bots[bot_file]
                process.kill()
                del running_bots[bot_file]
                bot.send_message(chat_id, f"تم إيقاف البوت: {bot_file}")
            else:
                process = subprocess.Popen(["python", file_path])
                running_bots[bot_file] = process
                bot.send_message(chat_id, f"تم تشغيل البوت: {bot_file}")
            
            show_bot_toggle_menu(chat_id)
        
        elif data.startswith("view_file:"):
            filename = data.split(":", 1)[1]
            current_dir = get_current_dir(chat_id)
            file_path = os.path.join(current_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content:
                    content = "الملف فارغ."
                bot.send_message(chat_id, f"محتوى الملف {filename}:\n{content[:4000]}")
            except Exception as e:
                bot.send_message(chat_id, f"خطأ: {str(e)}")
            show_directory_listing(chat_id)
        
        elif data.startswith("edit_file:"):
            filename = data.split(":", 1)[1]
            user_state[chat_id] = {"action": "edit_file", "filename": filename}
            current_dir = get_current_dir(chat_id)
            file_path = os.path.join(current_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = ""
            bot.send_message(chat_id, f"أرسل النص الجديد للملف {filename}:\nالمحتوى الحالي:\n{content}")
        
        elif data.startswith("rename_file:"):
            filename = data.split(":", 1)[1]
            user_state[chat_id] = {"action": "rename_file", "old": filename}
            bot.send_message(chat_id, f"أرسل الاسم الجديد للملف {filename}:")
        
        elif data.startswith("rename_dir:"):
            dirname = data.split(":", 1)[1]
            user_state[chat_id] = {"action": "rename_dir", "old": dirname}
            bot.send_message(chat_id, f"أرسل الاسم الجديد للمجلد {dirname}:")
        
        elif data == "create_file":
            user_state[chat_id] = {"action": "create_file"}
            bot.send_message(chat_id, "أرسل اسم الملف الجديد:")
        
        elif data == "create_dir":
            user_state[chat_id] = {"action": "create_dir"}
            bot.send_message(chat_id, "أرسل اسم المجلد الجديد:")
        
        elif data == "terminal_execute":
            user_state[chat_id] = {"action": "terminal"}
            bot.send_message(chat_id, "أرسل الأمر الذي تريد تنفيذه:")
        
        elif data == "terminal_exit":
            user_state.pop(chat_id, None)
            show_main_menu(chat_id, "تم إنهاء جلسة التيرمينال.")
        
        elif data == "bot_dir_up":
            current_dir = get_current_dir(chat_id)
            parent_dir = os.path.dirname(current_dir)
            set_current_dir(chat_id, parent_dir)
            show_bot_toggle_menu(chat_id)
        
        elif data.startswith("bot_open_dir:"):
            dirname = data.split(":", 1)[1]
            current_dir = get_current_dir(chat_id)
            new_path = os.path.join(current_dir, dirname)
            if is_safe_path(new_path):
                set_current_dir(chat_id, new_path)
                show_bot_toggle_menu(chat_id)
            else:
                bot.send_message(chat_id, "مسار غير مسموح به!")
        
        elif data == "upload_file":
            user_state[chat_id] = "uploading"
            bot.send_message(chat_id, "📤 أرسل الملف الذي تريد رفعه.")
        
        elif data == "download_file":
            show_download_menu(chat_id)
        
        elif data.startswith("download:"):
            filename = data.split(":", 1)[1]
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(file_path):
                bot.send_document(chat_id, open(file_path, "rb"))
            else:
                bot.send_message(chat_id, "⚠️ الملف غير موجود.")
        
        else:
            bot.send_message(chat_id, "عملية غير معروفة!")
    
    except Exception as e:
        bot.send_message(chat_id, f"حدث خطأ: {str(e)}")
    
    bot.answer_callback_query(call.id)

def show_download_menu(chat_id):
    try:
        files = os.listdir(UPLOAD_DIR)
        if not files:
            bot.send_message(chat_id, "⚠️ لا توجد ملفات متاحة للتحميل.")
            return show_files_menu(chat_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        for file in files:
            markup.add(types.InlineKeyboardButton(f"📄 {file}", callback_data=f"download:{file}"))
        markup.add(types.InlineKeyboardButton("◀️ رجوع", callback_data="menu_files"))
        bot.send_message(chat_id, "📥 اختر ملفًا لتحميله:", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء جلب الملفات: {str(e)}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    if user_state.get(chat_id) == "uploading":
        file_info = bot.get_file(message.document.file_id)
        file_path = file_info.file_path
        downloaded_file = bot.download_file(file_path)
        save_path = os.path.join(UPLOAD_DIR, message.document.file_name)
        with open(save_path, 'wb') as f:
            f.write(downloaded_file)
        bot.send_message(chat_id, f"✅ تم رفع الملف بنجاح: {message.document.file_name}")
        show_files_menu(chat_id)
        user_state.pop(chat_id, None)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    state = user_state.get(chat_id, {})

    try:
        if state.get("action") == "terminal":
            current_dir = get_current_dir(chat_id)
            process = subprocess.run(
                text.split(),
                cwd=current_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            output = ""
            if process.stdout:
                output += f"STDOUT:\n{process.stdout}\n"
            if process.stderr:
                output += f"STDERR:\n{process.stderr}"
            
            if not output:
                output = "لا يوجد نتيجة"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⛔ إنهاء الجلسة", callback_data="terminal_exit"))
            bot.send_message(chat_id, output[:4000], reply_markup=markup)
        
        elif state.get("action") == "edit_file":
            filename = state["filename"]
            current_dir = get_current_dir(chat_id)
            file_path = os.path.join(current_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            bot.send_message(chat_id, f"تم تحديث الملف: {filename}")
            user_state.pop(chat_id, None)
            show_directory_listing(chat_id)
        
        elif state.get("action") == "rename_file":
            old_name = state["old"]
            current_dir = get_current_dir(chat_id)
            new_path = os.path.join(current_dir, text)
            if is_safe_path(new_path):
                os.rename(os.path.join(current_dir, old_name), new_path)
                bot.send_message(chat_id, f"تم التغيير من {old_name} إلى {text}")
            else:
                bot.send_message(chat_id, "مسار غير مسموح به!")
            user_state.pop(chat_id, None)
            show_directory_listing(chat_id)
        
        elif state.get("action") == "rename_dir":
            old_name = state["old"]
            current_dir = get_current_dir(chat_id)
            old_path = os.path.join(current_dir, old_name)
            new_path = os.path.join(current_dir, text)
            if is_safe_path(new_path):
                os.rename(old_path, new_path)
                bot.send_message(chat_id, f"تم التغيير من {old_name} إلى {text}")
            else:
                bot.send_message(chat_id, "مسار غير مسموح به!")
            user_state.pop(chat_id, None)
            show_directory_listing(chat_id)
        
        elif state.get("action") == "create_file":
            current_dir = get_current_dir(chat_id)
            file_path = os.path.join(current_dir, text)
            if is_safe_path(file_path):
                open(file_path, "a").close()
                bot.send_message(chat_id, f"تم إنشاء الملف: {text}")
            else:
                bot.send_message(chat_id, "مسار غير مسموح به!")
            user_state.pop(chat_id, None)
            show_directory_listing(chat_id)
        
        elif state.get("action") == "create_dir":
            current_dir = get_current_dir(chat_id)
            new_dir_path = os.path.join(current_dir, text)
            if is_safe_path(new_dir_path):
                os.makedirs(new_dir_path, exist_ok=True)
                bot.send_message(chat_id, f"تم إنشاء المجلد: {text}")
            else:
                bot.send_message(chat_id, "مسار غير مسموح به!")
            user_state.pop(chat_id, None)
            show_directory_listing(chat_id)
        
        else:
            bot.send_message(chat_id, "يرجى استخدام الأزرار للتنقل")
    
    except Exception as e:
        bot.send_message(chat_id, f"حدث خطأ: {str(e)}")

if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
