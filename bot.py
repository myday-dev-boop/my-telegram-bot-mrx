"""
Telegram AI-бот — помощник для учеников
English Trainer + Math Trainer
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import google.generativeai as genai

# ── логирование ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Gemini ────────────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini = genai.GenerativeModel("gemini-2.5-flash")

# ── история диалогов ─────────────────────────────────────────
histories: dict[int, list] = {}

# ── ссылки на приложения (вставь свои после публикации) ───────
ENGLISH_APP_URL = os.environ.get("ENGLISH_APP_URL", "https://ваш-english.netlify.app")
MATH_APP_URL    = os.environ.get("MATH_APP_URL",    "https://ваш-math.netlify.app")

# ── системный промпт ─────────────────────────────────────────
SYSTEM = f"""Ты дружелюбный AI-помощник для учеников школы и студентов 1–2 курса.
Ты помогаешь изучать английский язык и математику.
Ученики занимаются в приложениях: English Trainer и Math Trainer.

ПО АНГЛИЙСКОМУ ты помогаешь с:
- Временами (Present/Past/Future Simple, Continuous, Perfect, Perfect Continuous)
- Условными предложениями (Conditionals 0, 1, 2, 3, mixed)
- Пассивным залогом (Passive Voice)
- Косвенной речью (Reported Speech)
- Артиклями и предлогами
- Фразовыми глаголами (Phrasal verbs)
- Коллокациями (make/do, heavy/strong)
- Идиомами и синонимами (уровень B1–B2)
- Словообразованием (Word Formation)

ПО МАТЕМАТИКЕ ты помогаешь с:
- Арифметикой (сложение, вычитание, умножение, деление)
- Дробями и процентами
- Уравнениями (линейные, квадратные)
- Алгеброй: степени, логарифмы, функции, прогрессии
- Геометрией: площади, периметры, углы, теорема Пифагора, объёмы
- Тригонометрией
- Производными

ПРАВИЛА:
- Отвечай на языке ученика (русский или казахский).
- Объясняй просто и понятно, как хороший учитель.
- При решении задач показывай пошаговое решение.
- После объяснения предлагай попрактиковаться.
- Хвали за правильные ответы, мягко исправляй ошибки.
- Если ученик написал свой ответ — проверь и объясни почему правильно/неправильно.
- Используй примеры из реальной жизни.
- Будь кратким, но понятным.
"""

# ── главное меню ─────────────────────────────────────────────
MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🇬🇧 Английский", callback_data="menu_eng"),
        InlineKeyboardButton("📐 Математика",   callback_data="menu_math"),
    ],
    [
        InlineKeyboardButton("✏️ Проверь мой ответ", callback_data="menu_check"),
        InlineKeyboardButton("📖 Объясни тему",       callback_data="menu_explain"),
    ],
    [
        InlineKeyboardButton("🔗 Открыть English Trainer", url=ENGLISH_APP_URL),
        InlineKeyboardButton("🔗 Открыть Math Trainer",    url=MATH_APP_URL),
    ],
])

# ── меню английского ─────────────────────────────────────────
ENG_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⏳ Времена",             callback_data="eng_tenses"),
        InlineKeyboardButton("🧩 Грамматика",          callback_data="eng_grammar"),
    ],
    [
        InlineKeyboardButton("📝 Use of English",       callback_data="eng_exam"),
        InlineKeyboardButton("💬 Лексика (B1–B2)",      callback_data="eng_vocab"),
    ],
    [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
])

# ── меню математики ──────────────────────────────────────────
MATH_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔢 Арифметика/Счёт",   callback_data="math_arith"),
        InlineKeyboardButton("➗ Дроби/Проценты",     callback_data="math_frac"),
    ],
    [
        InlineKeyboardButton("🟰 Уравнения",          callback_data="math_eq"),
        InlineKeyboardButton("📐 Геометрия",           callback_data="math_geo"),
    ],
    [
        InlineKeyboardButton("🧮 Алгебра (10–11)",    callback_data="math_alg"),
        InlineKeyboardButton("📊 Задачи",              callback_data="math_word"),
    ],
    [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
])

# ── тексты подсказок при выборе темы ─────────────────────────
TOPIC_INIT = {
    # английский
    "eng_tenses":  ("⏳ *Английские времена*\n\n"
                    "Выбери что объяснить или задай вопрос:\n"
                    "• Present / Past / Future Simple\n"
                    "• Continuous, Perfect, Perfect Continuous\n\n"
                    "Напиши например: _объясни Past Perfect_ "
                    "или _составь предложение в Present Continuous_"),
    "eng_grammar": ("🧩 *Грамматика*\n\n"
                    "Что объяснить?\n"
                    "• Conditionals (if-предложения)\n"
                    "• Passive Voice (пассивный залог)\n"
                    "• Reported Speech (косвенная речь)\n\n"
                    "Например: _объясни 2nd conditional_ "
                    "или _переведи в passive: They built the house_"),
    "eng_exam":    ("📝 *Use of English*\n\n"
                    "Помогу с:\n"
                    "• Артикли и предлоги\n"
                    "• Word Formation (словообразование)\n"
                    "• Найди ошибку в предложении\n\n"
                    "Напиши предложение или задай вопрос!"),
    "eng_vocab":   ("💬 *Лексика B1–B2*\n\n"
                    "Спроси про:\n"
                    "• Phrasal verbs (give up, take off...)\n"
                    "• Collocations (make/do, heavy/strong)\n"
                    "• Идиомы (piece of cake, break a leg)\n"
                    "• Синонимы\n\n"
                    "Например: _что значит 'spill the beans'?_"),
    # математика
    "math_arith":  ("🔢 *Арифметика и счёт*\n\n"
                    "Напиши пример или задачу:\n"
                    "Например: _объясни как умножать дроби_ "
                    "или _сколько будет 125 × 8?_"),
    "math_frac":   ("➗ *Дроби и проценты*\n\n"
                    "Напиши что не понятно:\n"
                    "Например: _как найти 15% от 240?_ "
                    "или _объясни сложение дробей с разными знаменателями_"),
    "math_eq":     ("🟰 *Уравнения*\n\n"
                    "Напиши уравнение — решим вместе:\n"
                    "Например: _2x + 5 = 13_ "
                    "или _x² - 9 = 0_"),
    "math_geo":    ("📐 *Геометрия*\n\n"
                    "Задай вопрос или напиши задачу:\n"
                    "Например: _площадь треугольника со сторонами 3,4,5_ "
                    "или _объясни теорему Пифагора_"),
    "math_alg":    ("🧮 *Алгебра (10–11 класс)*\n\n"
                    "Помогу с:\n"
                    "• Логарифмы, функции\n"
                    "• Прогрессии\n"
                    "• Тригонометрия\n"
                    "• Производные\n\n"
                    "Напиши тему или задачу:"),
    "math_word":   ("📊 *Задачи*\n\n"
                    "Напиши условие задачи — решим пошагово!\n"
                    "Например: _Поезд едет 90 км/ч. "
                    "За сколько часов проедет 360 км?_"),
    # общие
    "menu_check":  ("✏️ *Проверка ответа*\n\n"
                    "Напиши задание и свой ответ — проверю и объясню!"),
    "menu_explain":("📖 *Объяснение темы*\n\n"
                    "Напиши тему которую нужно объяснить:"),
}

TOPIC_CONTEXT = {
    "eng_tenses":  "Ученик хочет изучать английские времена (tenses).",
    "eng_grammar": "Ученик хочет изучать грамматику английского: conditionals, passive, reported speech.",
    "eng_exam":    "Ученик хочет практиковать Use of English: артикли, предлоги, словообразование.",
    "eng_vocab":   "Ученик хочет изучать лексику B1-B2: phrasal verbs, collocations, idioms.",
    "math_arith":  "Ученик хочет заниматься арифметикой и счётом.",
    "math_frac":   "Ученик хочет изучать дроби и проценты.",
    "math_eq":     "Ученик хочет решать уравнения.",
    "math_geo":    "Ученик хочет изучать геометрию.",
    "math_alg":    "Ученик хочет изучать алгебру (10-11 класс): логарифмы, тригонометрия, производные.",
    "math_word":   "Ученик хочет решать текстовые задачи.",
    "menu_check":  "Ученик хочет проверить правильность своего ответа.",
    "menu_explain":"Ученик хочет объяснение какой-то темы.",
}


# ── /start ────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    histories[uid] = []
    name = update.effective_user.first_name or "ученик"
    await update.message.reply_text(
        f"👋 Привет, {name}!\n\n"
        "Я AI-помощник для учеников.\n"
        "Помогу разобраться с *английским* и *математикой*:\n"
        "объясню, решу, проверю твой ответ.\n\n"
        "Выбери раздел или просто напиши вопрос 👇",
        reply_markup=MAIN_MENU,
        parse_mode="Markdown"
    )


# ── /help ─────────────────────────────────────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Что я умею:*\n\n"
        "🇬🇧 *Английский:*\n"
        "• Объясняю времена и грамматику\n"
        "• Разбираю conditionals, passive, reported speech\n"
        "• Помогаю с фразовыми глаголами и идиомами\n"
        "• Готовлю к Use of English\n\n"
        "📐 *Математика:*\n"
        "• Решаю уравнения пошагово\n"
        "• Объясняю геометрию и алгебру\n"
        "• Помогаю с задачами на проценты и движение\n\n"
        "✏️ *Проверяю твои ответы и объясняю ошибки*\n\n"
        "*/start* — главное меню\n"
        "*/clear* — начать новый диалог\n"
        "*/app* — ссылки на приложения\n"
        "*/help* — эта справка",
        parse_mode="Markdown"
    )


# ── /clear ────────────────────────────────────────────────────
async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_user.id] = []
    await update.message.reply_text(
        "✅ Диалог очищен!\n"
        "Выбери тему или задай вопрос:",
        reply_markup=MAIN_MENU
    )


# ── /app ──────────────────────────────────────────────────────
async def cmd_app(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *Наши приложения:*\n\n"
        f"🇬🇧 English Trainer: {ENGLISH_APP_URL}\n"
        f"📐 Math Trainer: {MATH_APP_URL}\n\n"
        "Открывай в браузере и тренируйся!\n"
        "Можно добавить на главный экран телефона.",
        parse_mode="Markdown"
    )


# ── кнопки ───────────────────────────────────────────────────
async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data == "menu_eng":
        await query.edit_message_text(
            "🇬🇧 *Английский язык*\nВыбери раздел:",
            reply_markup=ENG_MENU, parse_mode="Markdown"
        )
    elif data == "menu_math":
        await query.edit_message_text(
            "📐 *Математика*\nВыбери раздел:",
            reply_markup=MATH_MENU, parse_mode="Markdown"
        )
    elif data == "back_main":
        await query.edit_message_text(
            "Главное меню — выбери раздел:",
            reply_markup=MAIN_MENU
        )
    elif data in TOPIC_INIT:
        # добавляем контекст в историю
        hist = histories.setdefault(uid, [])
        hist.append({"role":"user","parts":[TOPIC_CONTEXT[data]]})
        hist.append({"role":"model","parts":["Отлично, готов помочь! Жду твой вопрос."]})
        await query.edit_message_text(
            TOPIC_INIT[data],
            parse_mode="Markdown"
        )


# ── основной обработчик сообщений ─────────────────────────────
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_text = update.message.text

    await ctx.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        hist = histories.setdefault(uid, [])

        # первое сообщение — добавляем системный промпт
        if not hist:
            msg = (f"[Инструкция для тебя]:\n{SYSTEM}\n\n"
                   f"Вопрос ученика: {user_text}")
        else:
            msg = user_text

        hist.append({"role": "user", "parts": [msg]})

        # запрос к Gemini с историей
        chat = gemini.start_chat(history=hist[:-1])
        response = chat.send_message(hist[-1]["parts"][0])
        answer = response.text

        hist.append({"role": "model", "parts": [answer]})

        # ограничиваем историю (30 сообщений)
        if len(hist) > 30:
            histories[uid] = hist[-30:]

        # добавляем кнопку "Ещё вопрос?" раз в 5 сообщений
        n = len([h for h in hist if h["role"] == "user"])
        reply_markup = None
        if n % 5 == 0:
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="back_main_msg"),
                InlineKeyboardButton("🔗 Приложения",   callback_data="apps_link"),
            ]])

        # Telegram не принимает сообщения длиннее 4096 символов — режем на части
        chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
        for idx, chunk in enumerate(chunks):
            # кнопки показываем только под последней частью
            markup = reply_markup if idx == len(chunks) - 1 else None
            try:
                await update.message.reply_text(
                    chunk,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            except Exception:
                await update.message.reply_text(chunk, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка у {uid}: {e}")
        await update.message.reply_text(
            "❌ Что-то пошло не так. Попробуй ещё раз!\n"
            "Если не помогает — напиши /clear"
        )


# ── дополнительные callback для кнопок в сообщениях ─────────
async def on_inline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "back_main_msg":
        await q.message.reply_text(
            "Главное меню:", reply_markup=MAIN_MENU
        )
    elif q.data == "apps_link":
        await q.message.reply_text(
            f"📱 English Trainer: {ENGLISH_APP_URL}\n"
            f"📐 Math Trainer: {MATH_APP_URL}"
        )


# ── запуск ────────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Не задан TELEGRAM_TOKEN!")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("clear",   cmd_clear))
    app.add_handler(CommandHandler("app",     cmd_app))
    app.add_handler(CallbackQueryHandler(on_button, pattern="^(menu_|eng_|math_|back_main$)"))
    app.add_handler(CallbackQueryHandler(on_inline,  pattern="^(back_main_msg|apps_link)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
