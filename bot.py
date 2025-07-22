import logging
logging.basicConfig(level=logging.DEBUG)

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

logging.basicConfig(level=logging.INFO)

ADMIN_ID = 1859111819

ASK_PHOTO, ASK_TEXT, ASK_REPEAT = range(3)

message_queue = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Пожалуйста, отправь фото.")
    return ASK_PHOTO

# Фото
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Это не фото. Пожалуйста, отправь фото.")
        return ASK_PHOTO

    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("✏️ Отлично! Теперь напиши текст к фото.")
    return ASK_TEXT

# Текст
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    photo = context.user_data.get("photo")
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name

    if not photo:
        await update.message.reply_text("❗ Ошибка: фото не найдено.")
        return ConversationHandler.END

    if user_id not in message_queue:
        message_queue[user_id] = {
            "username": username,
            "items": []
        }

    message_queue[user_id]["items"].append({
        "photo": photo,
        "text": text
    })

    count = len(message_queue[user_id]["items"])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📨 Вам отправлено {count} сообщение(й), хотите посмотреть?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ДА ✅", callback_data=f"approve_{user_id}")]
        ])
    )

    await update.message.reply_text(
        "✅ Сообщение отправлено админу на проверку.\n\n❓ Хочешь отправить ещё одно?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Да, хочу ещё", callback_data="repeat_yes")],
        ])
    )

    return ASK_REPEAT

# Обработка повторного выбора
async def handle_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "repeat_yes":
        await query.edit_message_text("📷 Хорошо! Отправь следующее фото.")
        return ASK_PHOTO
    else:
        await query.edit_message_text("👌 Хорошо, спасибо за отправку!")
        return ConversationHandler.END

# Кнопка ДА (админ)
async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("approve_"):
        return

    user_id = int(data.split("_")[1])
    if user_id not in message_queue or not message_queue[user_id]["items"]:
        await query.edit_message_text("Очередь пуста.")
        return

    item = message_queue[user_id]["items"].pop(0)
    username = message_queue[user_id]["username"]

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📨 ОТ: @{username}")
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=item["photo"], caption=item["text"])

    remaining = len(message_queue[user_id]["items"])
    if remaining > 0:
        await query.edit_message_text(
            text=f"📨 Осталось {remaining} сообщение(й), хотите посмотреть?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ДА ✅", callback_data=f"approve_{user_id}")]
            ])
        )
    else:
        del message_queue[user_id]
        await query.edit_message_text("✅ Все сообщения от этого пользователя просмотрены.")

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END

# MAIN
def main():
    application = ApplicationBuilder().token("8049203778:AAH_SXsDc_gwo5pEvQnsPOMzCn6tiHS9lQE").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            ASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
            ASK_REPEAT: [CallbackQueryHandler(handle_repeat, pattern="^repeat_.*")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_approve, pattern="^approve_"))

    application.run_polling()

if __name__ == "__main__":
    main()
