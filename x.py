import os
import requests
import telebot
from telebot import types
import urllib.parse

# تهيئة البوت
API_TOKEN = '8063480436:AAEcm4RS38ESz55ov4LpZma6Dnv2J3nVJ1M'
bot = telebot.TeleBot(API_TOKEN)

# عنوان API الخدمة
API_URL = "http://145.223.80.56:5003/get?q="

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
    🚀 مرحبًا بك في بوت تحميل مقاطع الفيديو المرئية!
    
    يمكنك إرسال روابط من:
    - YouTube
    - Pinterest
    - X
    - Facebook 
    - Instagram
    - TikTok
    
    وسأقوم بتحميل الفيديو وإرساله لك.
    
    ⚠️ ملاحظة: تحميل مقطع يوتيوب يتجاوز طوله 8 دقائق او يكون عالي الجودة بما يساوي 1080 او اكثر فإن هذا سيعمل على تعطيل البوت وإعادة تشغيله ويرجع ذلك الى أن الاستضافة مجانية ولاتتحمل الضغط . 
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # التحقق من أن الرسالة تحتوي على رابط
    if not any(domain in message.text for domain in ['youtube', 'youtu.be', 'instagram', 'tiktok', 'facebook', 'X.com', 'pin.it']):
        bot.reply_to(message, "⚠️ الرابط غير مدعوم.")
        return
    
    try:
        # إعداد رسالة الانتظار
        wait_msg = bot.reply_to(message, "⏳ جاري معالجة الرابط، يرجى الانتظار...")
        
        # تشفير الرابط وإرسال الطلب إلى API
        encoded_url = urllib.parse.quote(message.text)
        response = requests.get(API_URL + encoded_url)
        data = response.json()
        
        if 'Download link' not in data:
            bot.edit_message_text("❌ تعذر تحميل الفيديو، يرجى المحاولة لاحقًا.", 
                                chat_id=message.chat.id, 
                                message_id=wait_msg.message_id)
            return
        
        download_url = data['Download link']
        
        # تحميل الفيديو مؤقتًا
        bot.edit_message_text("📥 جاري تحميل الفيديو...", 
                             chat_id=message.chat.id, 
                             message_id=wait_msg.message_id)
        
        video_data = requests.get(download_url, stream=True)
        
        # إرسال الفيديو للمستخدم
        bot.send_video(message.chat.id, video_data.raw, 
                      caption="✅ تم تحميل الفيديو بنجاح!",
                      reply_to_message_id=message.message_id)
        
        # حذف رسالة الانتظار
        bot.delete_message(message.chat.id, wait_msg.message_id)
        
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء معالجة طلبك. يرجى المحاولة لاحقًا.")

if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()