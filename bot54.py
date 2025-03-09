from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.request import HTTPXRequest
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio

# بيانات المستخدم (يتم تخزينها مؤقتًا في الذاكرة)
user_data = {}

# متغير للتحكم في عملية الإرسال
is_sending = False

# متغير لتتبع عدد الرسائل المرسلة
sent_messages_count = 0

# إعدادات البوت
TELEGRAM_TOKEN = "7774524020:AAGYnlBOfvgcfWbl6Y0LJVjQRZixpiQ7epg"  # استبدل بــ token الخاص ببوتك

# زيادة مهلة الاتصال
request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0)

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("إدارة الإيميلات", callback_data="manage_emails")],
        [InlineKeyboardButton("إضافة المستقبل", callback_data="set_receiver")],
        [InlineKeyboardButton("إضافة الموضوع", callback_data="set_subject")],
        [InlineKeyboardButton("إضافة الرسالة", callback_data="set_message")],
        [InlineKeyboardButton("عدد الرسائل", callback_data="set_message_count")],
        [InlineKeyboardButton("عدد الثواني", callback_data="set_sleep_time")],
        [InlineKeyboardButton("عرض البيانات", callback_data="show_data")],
        [InlineKeyboardButton("بدء الإرسال", callback_data="send")],
        [InlineKeyboardButton("إيقاف الإرسال", callback_data="stop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحبًا! أنا بوت لإرسال رسائل تلقائية. اختر أحد الخيارات:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    if query.data == "manage_emails":
        await manage_emails(query.message)

    elif query.data == "set_receiver":
        await query.message.reply_text("أرسل بريد المستقبل:")
        user_data[chat_id] = user_data.get(chat_id, {})  # الحفاظ على البيانات الحالية
        user_data[chat_id]["step"] = "set_receiver"

    elif query.data == "set_subject":
        await query.message.reply_text("أرسل الموضوع:")
        user_data[chat_id] = user_data.get(chat_id, {})  # الحفاظ على البيانات الحالية
        user_data[chat_id]["step"] = "set_subject"

    elif query.data == "set_message":
        await query.message.reply_text("أرسل الرسالة:")
        user_data[chat_id] = user_data.get(chat_id, {})  # الحفاظ على البيانات الحالية
        user_data[chat_id]["step"] = "set_message"

    elif query.data == "set_message_count":
        await query.message.reply_text("أرسل عدد الرسائل التي تريد إرسالها:")
        user_data[chat_id] = user_data.get(chat_id, {})  # الحفاظ على البيانات الحالية
        user_data[chat_id]["step"] = "set_message_count"

    elif query.data == "set_sleep_time":
        await query.message.reply_text("أرسل عدد الثواني بين كل رسالة:")
        user_data[chat_id] = user_data.get(chat_id, {})  # الحفاظ على البيانات الحالية
        user_data[chat_id]["step"] = "set_sleep_time"

    elif query.data == "show_data":
        await show_data(query.message)

    elif query.data == "send":
        await send_emails(query.message)

    elif query.data == "stop":
        await stop_sending(query.message)

    elif query.data.startswith("email_"):
        email_index = int(query.data.split("_")[1])
        await manage_email_options(query.message, email_index)

    elif query.data.startswith("delete_email_"):
        email_index = int(query.data.split("_")[2])
        await delete_email(query.message, email_index)

    elif query.data == "add_email":
        await query.message.reply_text("أرسل البريد الإلكتروني وكلمة المرور بهذا التنسيق:\nemail:password")
        user_data[chat_id] = user_data.get(chat_id, {})  # الحفاظ على البيانات الحالية
        user_data[chat_id]["step"] = "add_email"

async def manage_emails(message):
    chat_id = message.chat_id
    if chat_id not in user_data:
        user_data[chat_id] = {}  # تهيئة البيانات إذا لم تكن موجودة
    if "emails" not in user_data[chat_id]:
        user_data[chat_id]["emails"] = []

    keyboard = []
    for i, email_data in enumerate(user_data[chat_id]["emails"]):
        keyboard.append([InlineKeyboardButton(f"الإيميل {i+1}: {email_data['email']}", callback_data=f"email_{i}")])
    keyboard.append([InlineKeyboardButton("إضافة إيميل جديد", callback_data="add_email")])
    keyboard.append([InlineKeyboardButton("الرجوع", callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("إدارة الإيميلات:", reply_markup=reply_markup)

async def manage_email_options(message, email_index):
    chat_id = message.chat_id
    keyboard = [
        [InlineKeyboardButton("حذف الإيميل", callback_data=f"delete_email_{email_index}")],
        [InlineKeyboardButton("الرجوع", callback_data="manage_emails")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("اختر خيارًا:", reply_markup=reply_markup)

async def delete_email(message, email_index):
    chat_id = message.chat_id
    if "emails" in user_data.get(chat_id, {}):
        user_data[chat_id]["emails"].pop(email_index)
        await message.reply_text("تم حذف الإيميل بنجاح!")
    await manage_emails(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    if chat_id in user_data:
        if user_data[chat_id]["step"] == "add_email":
            try:
                email, password = text.split(":")
                if "emails" not in user_data[chat_id]:
                    user_data[chat_id]["emails"] = []
                user_data[chat_id]["emails"].append({"email": email.strip(), "password": password.strip()})
                user_data[chat_id]["step"] = None
                await update.message.reply_text("تم حفظ البريد الإلكتروني وكلمة المرور بنجاح!")
            except Exception as e:
                await update.message.reply_text("التنسيق غير صحيح. أرسل البريد الإلكتروني وكلمة المرور بهذا التنسيق:\nemail:password")

        elif user_data[chat_id]["step"] == "set_receiver":
            user_data[chat_id]["receiver"] = text.strip()
            user_data[chat_id]["step"] = None
            await update.message.reply_text(f"تم حفظ بريد المستقبل بنجاح: {text}")

        elif user_data[chat_id]["step"] == "set_subject":
            user_data[chat_id]["subject"] = text.strip()
            user_data[chat_id]["step"] = None
            await update.message.reply_text(f"تم حفظ الموضوع بنجاح: {text}")

        elif user_data[chat_id]["step"] == "set_message":
            user_data[chat_id]["message"] = text.strip()
            user_data[chat_id]["step"] = None
            await update.message.reply_text(f"تم حفظ الرسالة بنجاح: {text}")

        elif user_data[chat_id]["step"] == "set_message_count":
            try:
                message_count = int(text.strip())
                user_data[chat_id]["message_count"] = message_count
                user_data[chat_id]["step"] = None
                await update.message.reply_text(f"تم تعيين عدد الرسائل إلى: {message_count}")
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح.")

        elif user_data[chat_id]["step"] == "set_sleep_time":
            try:
                sleep_time = int(text.strip())
                user_data[chat_id]["sleep_time"] = sleep_time
                user_data[chat_id]["step"] = None
                await update.message.reply_text(f"تم تعيين عدد الثواني إلى: {sleep_time}")
            except ValueError:
                await update.message.reply_text("الرجاء إدخال رقم صحيح.")

async def show_data(message):
    chat_id = message.chat_id
    if chat_id in user_data:
        emails = user_data[chat_id].get("emails", [])
        receiver = user_data[chat_id].get("receiver", "غير محفوظ")
        subject = user_data[chat_id].get("subject", "غير محفوظ")
        message_text = user_data[chat_id].get("message", "غير محفوظ")
        message_count = user_data[chat_id].get("message_count", "غير محفوظ")
        sleep_time = user_data[chat_id].get("sleep_time", "غير محفوظ")

        emails_info = "\n".join([f"الإيميل {i+1}: {email['email']}" for i, email in enumerate(emails)])
        await message.reply_text(
            f"الإيميلات:\n{emails_info}\n"
            f"المستقبل: {receiver}\n"
            f"الموضوع: {subject}\n"
            f"الرسالة: {message_text}\n"
            f"عدد الرسائل: {message_count}\n"
            f"عدد الثواني: {sleep_time}"
        )
    else:
        await message.reply_text("لا توجد بيانات محفوظة.")

async def send_emails(message):
    global is_sending, sent_messages_count
    chat_id = message.chat_id

    # التحقق من وجود جميع البيانات المطلوبة
    required_fields = ["emails", "receiver", "subject", "message", "message_count", "sleep_time"]
    missing_fields = [field for field in required_fields if field not in user_data.get(chat_id, {})]

    if missing_fields:
        await message.reply_text(f"البيانات التالية مفقودة: {', '.join(missing_fields)}\nالرجاء إضافتها أولاً.")
        return

    # التحقق من صحة البريد الإلكتروني وكلمة المرور
    try:
        for email_data in user_data[chat_id]["emails"]:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(email_data["email"], email_data["password"])
            server.quit()
        await message.reply_text("تم التحقق من جميع الإيميلات وكلمات المرور بنجاح!")
    except smtplib.SMTPAuthenticationError:
        await message.reply_text("فشل تسجيل الدخول: أحد الإيميلات أو كلمات المرور غير صحيحة.")
        return
    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء التحقق من الإيميلات: {e}")
        return

    is_sending = True
    sent_messages_count = 0
    status_message = await message.reply_text("بدأت عملية الإرسال...\nعدد الرسائل المرسلة: 0")

    while is_sending and sent_messages_count < user_data[chat_id]["message_count"]:
        try:
            for email_data in user_data[chat_id]["emails"]:
                # إنشاء الرسالة
                msg = MIMEText(user_data[chat_id]["message"], "plain")
                msg["From"] = email_data["email"]
                msg["To"] = user_data[chat_id]["receiver"]
                msg["Subject"] = user_data[chat_id]["subject"]

                # إرسال الرسالة
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(email_data["email"], email_data["password"])
                server.sendmail(email_data["email"], user_data[chat_id]["receiver"], msg.as_string())
                server.quit()

            sent_messages_count += 1
            await status_message.edit_text(f"بدأت عملية الإرسال...\nعدد الرسائل المرسلة: {sent_messages_count}")
        except Exception as e:
            await message.reply_text(f"حدث خطأ أثناء إرسال الرسالة: {e}")
            is_sending = False

        await asyncio.sleep(user_data[chat_id]["sleep_time"])  # انتظر عدد الثواني المحدد

    is_sending = False
    await message.reply_text("تم إكمال عملية الإرسال.")

async def stop_sending(message):
    global is_sending
    is_sending = False
    await message.reply_text("تم إيقاف الإرسال.")

# إعداد البوت
if __name__ == "__main__":
    application = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

    # إضافة الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # بدء البوت
    application.run_polling()