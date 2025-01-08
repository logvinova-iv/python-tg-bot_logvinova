import telegram
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler, MessageHandler, \
    filters, ConversationHandler, CallbackContext, InlineQueryHandler
from telegram.ext.filters import Language

from Task.util import load_prompt, send_text_buttons, send_audio_mess
from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler)

# Для обработки переменных окружения
import os
from dotenv import load_dotenv

# модуль для создания временных файлов и каталогов
import tempfile
import speech_to_text
# Google Text-to-Speech, для преобразования текста в речь
import gtts

# Игнорирование некоторых предупреждений от библиотеки Telegram (в т.ч. предупреждение, возникающее от
# ConversationHandler, в котором есть CallbackQueryHandler)
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


# Дублирует то, что написал пользователь при его нахождении не в каком-либо режиме
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # получает сообщение, написанное пользователем
    text = update.message.text
    # отправляет в чат это же сообщение
    message = await send_text(update, context, f"Вы написали: {text}")


# Выходит из предыдущего режима, "отжимает" кнопку "Закончить" и высвечивает главное меню
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)


# Аналогичен функции stop, но для ConversationHandler
async def stop_hendler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)
    return ConversationHandler.END


# Загружает главное меню бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Главное меню',
        'random': 'Узнать случайный интересный факт 🧠',
        'gpt': 'Задать вопрос чату GPT 🤖',
        'talk': 'Поговорить с известной личностью 👤',
        'quiz': 'Поучаствовать в квизе ❓',
        'translate': 'Перевести текст',
        'voice': 'диалог с ChatGPT аудиосообщениями 🎙'
    })


# Режим рандомного факта, при выборе в меню 'random': 'Узнать случайный интересный факт 🧠'
async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'random')
    message = await send_text(update, context, "Секунду, думаю...")
    promt = load_prompt("random")
    answer = await chat_gpt.send_question(promt, "")
    # message = await message.edit_text(answer)
    await message.delete()
    await send_text_buttons(update, context, answer, {
        'random_more': 'Хочу еще факт!',
        'stop': 'Закончить'
    })


# Режим "Хочу еще факт" (продолжает random)
async def random_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await random(update, context)


# Режим общения с чатом GPT (с использованием ConversationHandler)
async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = load_message("gpt")
    chat_gpt.set_prompt(load_prompt('gpt'))
    await send_image(update, context, 'gpt')
    await send_text(update, context, text)
    # Возвращает состояние RESPONSE_GPT, которое вызывает функцию response_gpt
    return RESPONSE_GPT


# Отвечает на вопрос пользователя в режиме gpt
async def response_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    res = await chat_gpt.add_message(question)
    await send_text_buttons(update, context, res, {
        'stop_hendler': 'Закончить'
    })


# Режим общения с известной личностью (с использованием ConversationHandler)
async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, "talk")
    talk = load_message("talk")
    # text = await send_text(update, context, talk)
    await send_text_buttons(update, context, talk, {
        'talk_cobain': 'Курт Кобейн',
        'talk_queen': 'Елизавета II',
        'talk_hawking': 'Джон Толкиен',
        'talk_nietzsche': 'Фридрих Ницше',
        'talk_tolkien': 'Стивен Хокинг'
    })
    # Возвращает состояние TALK_WITH, которое вызывает функцию talk_with
    return TALK_WITH


# Отправляет чату gpt промт с выбранной личностью и просит поздороваться с пользователем в стиле выбранной личности
async def talk_with(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    chat_gpt.set_prompt(load_prompt(data))
    greet = await chat_gpt.add_message("Представься и поздоровайся со мной")
    await send_image(update, context, data)
    await send_text(update, context, greet)
    return PERSON_RESPONSE


# Отправляет чату gpt вопрос от пользователя известной личности и отвечает пользователю в стиле выбранной личности
async def person_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    answer = await chat_gpt.add_message(text)
    await send_text_buttons(update, context, answer, {
        'stop_hendler': 'Закончить',
    })


# Режим квиза, три темы на выбор с подсчетом правильных ответов
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_gpt.set_prompt(load_prompt('quiz'))
    context.user_data['score'] = 0
    await send_text_buttons(update, context, "Выбери тему квиза", {
        'quiz_prog': "Программирование",
        'quiz_math': "Математика",
        'quiz_biology': "Биология"
    })
    return THEME


# Отправка чату gpt выбранной темы и получение вопроса от него
async def quiz_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    question = await chat_gpt.add_message(update.callback_query.data)
    await send_text(update, context, question)
    return ANSWER


# async def quiz_diff(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     pass


# Получение ответа от пользователя и его проверка на правильность, подсчет очков
async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    answer = await chat_gpt.add_message(text)
    if answer == 'Правильно!':
        context.user_data['score'] = context.user_data.get('score', 0) + 1
    await send_text_buttons(update, context, answer + '\n\nВаш счет: ' + str(
        context.user_data['score']), {
                                'quiz_more': 'Еще вопрос',
                                'quiz_change': 'Сменить тему',
                                'stop_hendler': 'Закончить',
                            })
    return CHOOSE


# Ответные дествия на 'quiz_more' и 'quiz_change'
async def quiz_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # await update.callback_query.answer()
    if update.callback_query.data == 'quiz_change':
        # "отжимает" кнопку 'Сменить тему', чтобы не светилась
        await update.callback_query.answer()
        return await quiz(update, context)
    else:
        return THEME


# Режим переводчика с выбором 3 языков
async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'translate')
    chat_gpt.set_prompt(load_prompt('translate'))
    await send_text_buttons(update, context, "Выбери язык, на который хочешь перевести текст", buttons={
        'translate_en': "Английский",
        'translate_ger': "Немецкий",
        'translate_hrv': "Хорватский"
    })
    return LANG


# Переход в данную функцию после выбора конкретного языка, отправка чату gpt промта с уже выбранным конкретным языком, на который нужно переводить
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    question = await chat_gpt.add_message(update.callback_query.data)
    await send_text(update, context, 'Введите текст, который хотите перевести:')
    return TEXT


# Перевод введенного текста
async def translated_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    transl_text = await chat_gpt.add_message(text)
    await send_text_buttons(update, context, "Готовый перевод:\n" + transl_text, {
        'change_language': 'Сменить язык',
        'stop_hendler': 'Закончить'
    })
    return CHANGE


# Ответные дествия на 'change_language': 'Сменить язык'
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return await translate(update, context)


# Режим общения с чатом gpt аудиосообщениями
async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'voice')
    await send_text(update, context, 'Задайте вопрос чату gpt голосовым сообщением')
    chat_gpt.set_prompt(load_prompt('voice'))
    return VOICE


async def voice_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем объект с аудио-файлом, отправленным пользователем
    file = await context.bot.getFile(update.message.voice.file_id)
    # Создаем временный файл для сохранения аудио
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    # Скачиваем аудио-файл и сохраняем его во временный файл
    await file.download_to_drive(temp_file.name)
    # Ставим указатель в начало файла
    temp_file.seek(0)
    text = speech_to_text.ogg_to_text(temp_file.read())
    # await send_text(update, context, text)
    answer = await chat_gpt.add_message(text)
    text_to_audio = gtts.gTTS(answer, lang='ru')
    text_to_audio.save(r'C:\Users\Public\PycharmProj\TG_BOT\Task\temp\temp.mp3')
    keyboard = [
        [
            InlineKeyboardButton("Закончить", callback_data="stop_hendler")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_audio_mess(update, context, r'C:\Users\Public\PycharmProj\TG_BOT\Task\temp\temp.mp3', reply_markup)
    os.remove(r'C:\Users\Public\PycharmProj\TG_BOT\Task\temp\temp.mp3')


# Использование переменных окружения (для хранения токенов)
load_dotenv()
token_gpt = os.getenv("CHAT_GPT_TOKEN")
token_bot = os.getenv("BOT_TOKEN")
chat_gpt = ChatGptService(token_gpt)
app = ApplicationBuilder().token(token_bot).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('random', random))

TALK_WITH, PERSON_RESPONSE = range(2)
app.add_handler(ConversationHandler(entry_points=[CommandHandler('talk', talk)], allow_reentry=True,
                                    states={
                                        TALK_WITH: [CallbackQueryHandler(talk_with, '^talk_.*')],
                                        PERSON_RESPONSE: [
                                            MessageHandler(filters.TEXT & ~filters.COMMAND, person_response)]
                                    },
                                    fallbacks=[CallbackQueryHandler(stop_hendler, 'stop_hendler')]
                                    ))
RESPONSE_GPT = 1
app.add_handler(ConversationHandler(entry_points=[CommandHandler('gpt', gpt)], allow_reentry=True,
                                    states={
                                        RESPONSE_GPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, response_gpt)]},
                                    fallbacks=[CallbackQueryHandler(stop_hendler, 'stop_hendler')]
                                    ))

THEME, CHOOSE, ANSWER = range(3)
app.add_handler(ConversationHandler(entry_points=[CommandHandler('quiz', quiz)], allow_reentry=True,
                                    states={
                                        THEME: [CallbackQueryHandler(quiz_theme, '^quiz_.*')],
                                        CHOOSE: [CallbackQueryHandler(quiz_theme, 'quiz_more'),
                                                 CallbackQueryHandler(quiz, 'quiz_change')],
                                        ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_answer)]
                                    },
                                    fallbacks=[CallbackQueryHandler(stop_hendler, 'stop_hendler')]
                                    ))

LANG, TEXT, CHANGE = range(3)
app.add_handler(ConversationHandler(entry_points=[CommandHandler('translate', translate)], allow_reentry=True,
                                    states={
                                        LANG: [CallbackQueryHandler(language, '^translate_.*')],
                                        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, translated_text)],
                                        CHANGE: [CallbackQueryHandler(change_language, 'change_language')]},
                                    fallbacks=[CallbackQueryHandler(stop_hendler, 'stop_hendler')]
                                    ))

VOICE = 1
app.add_handler(ConversationHandler(entry_points=[CommandHandler('voice', voice)], allow_reentry=True,
                                    states={
                                        TEXT: [MessageHandler(filters.VOICE, voice_mode)]},
                                    fallbacks=[CallbackQueryHandler(stop_hendler, 'stop_hendler')]
                                    ))

app.add_handler(CallbackQueryHandler(stop, 'stop'))
app.add_handler(CallbackQueryHandler(random_more, '^random_.*'))
app.add_handler(CallbackQueryHandler(default_callback_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

app.run_polling()
