# -*- coding: utf-8 -*-

import logging
import os
import io
import httpx
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE' # IMPORTANT: Replace with your real token

# --- TRANSLATIONS ---
MESSAGES = {
    'lang_set': {
        'ar': "✅ تم تعيين اللغة إلى العربية.",
        'en': "✅ Language has been set to English.",
    },
    'start': {
        'ar': (
            "أهلاً وسهلاً بك يا {user_mention}! �\n\n"
            "أنا بوت برمجة متطور أستخدم ذكاء Gemini لمساعدتك في مشاريعك.\n\n"
            "<b>الخطوة الأولى: الحصول على مفتاح Gemini API</b>\n"
            "1. اذهب إلى موقع [Google AI Studio](https://aistudio.google.com/).\n"
            "2. قم بتسجيل الدخول بحساب Google.\n"
            "3. اضغط على '<b>Get API key</b>' ثم '<b>Create API key</b>'.\n"
            "4. انسخ المفتاح الذي يظهر لك.\n\n"
            "<b>الخطوة الثانية: تعيين المفتاح في البوت</b>\n"
            "استخدم الأمر التالي لوضع مفتاحك:\n"
            "`/set_api_key YOUR_API_KEY`\n\n"
            "لتغيير اللغة، استخدم الأمر /language.\n"
            "للمساعدة، استخدم الأمر /help."
        ),
        'en': (
            "Welcome, {user_mention}! 🤖\n\n"
            "I'm an advanced coding bot using Gemini AI to help you with your projects.\n\n"
            "<b>Step 1: Get your Gemini API Key</b>\n"
            "1. Go to [Google AI Studio](https://aistudio.google.com/).\n"
            "2. Log in with your Google account.\n"
            "3. Click on '<b>Get API key</b>', then '<b>Create API key</b>'.\n"
            "4. Copy the key that appears.\n\n"
            "<b>Step 2: Set your key in the bot</b>\n"
            "Use the following command to set your key:\n"
            "`/set_api_key YOUR_API_KEY`\n\n"
            "To change the language, use /language.\n"
            "For help, use /help."
        ),
    },
    'help': {
        'ar': (
            "<b>✨ قائمة الأوامر والميزات ✨</b>\n\n"
            "🔑 <b>/set_api_key `KEY`</b>\n"
            "   لتعيين أو تحديث مفتاح Gemini API.\n\n"
            "👨‍💻 <b>/code `[lang]` `desc`</b>\n"
            "   لبدء مشروع جديد.\n\n"
            "💡 <b>الرد على رسالة الكود</b>\n"
            "   لطلب تحسينات أو إصلاحات.\n\n"
            "🗑️ <b>/new_project</b>\n"
            "   لمسح ذاكرة المشروع الحالي.\n\n"
            "🌐 <b>/language</b>\n"
            "   لتغيير لغة البوت."
        ),
        'en': (
            "<b>✨ Commands & Features ✨</b>\n\n"
            "🔑 <b>/set_api_key `KEY`</b>\n"
            "   To set or update your Gemini API key.\n\n"
            "👨‍💻 <b>/code `[lang]` `desc`</b>\n"
            "   To start a new project.\n\n"
            "💡 <b>Reply to a code message</b>\n"
            "   To request improvements or fixes.\n\n"
            "🗑️ <b>/new_project</b>\n"
            "   To clear the current project's memory.\n\n"
            "🌐 <b>/language</b>\n"
            "   To change the bot's language."
        ),
    },
    'api_key_needed': {
        'ar': "⚠️ لم تقم بتعيين مفتاح Gemini API. استخدم /set_api_key لوضعه.",
        'en': "⚠️ You haven't set your Gemini API key. Use /set_api_key to set it.",
    },
    'api_key_usage': {
        'ar': "الاستخدام غير صحيح. مثال: `/set_api_key YOUR_API_KEY`",
        'en': "Incorrect usage. Example: `/set_api_key YOUR_API_KEY`",
    },
    'api_key_set': {
        'ar': "✅ تم حفظ مفتاح Gemini API بنجاح!",
        'en': "✅ Gemini API key saved successfully!",
    },
    'new_project': {
        'ar': "🗑️ تم مسح ذاكرة المشروع.",
        'en': "🗑️ Project memory cleared.",
    },
    'code_prompt_needed': {
        'ar': "يرجى وصف المشروع بعد الأمر /code.",
        'en': "Please describe the project after the /code command.",
    },
    'no_project_to_improve': {
        'ar': "عذراً، لا يوجد مشروع حالي لتحسينه.",
        'en': "Sorry, there is no current project to improve.",
    },
    'generating_code': {
        'ar': "لحظات من فضلك، أقوم ببرمجة طلبك...",
        'en': "One moment please, I'm coding your request...",
    },
    'improving_code': {
        'ar': "لحظات من فضلك، أقوم بتحسين الكود...",
        'en': "One moment please, I'm improving the code...",
    },
    'code_error': {
        'ar': "عذراً، حدث خطأ تقني. تأكد من أن مفتاح API الخاص بك صحيح.",
        'en': "Sorry, a technical error occurred. Please ensure your API key is correct.",
    },
    'interactive_code_note': {
        'ar': "⚠️ **ملاحظة:** هذا الكود تفاعلي ويتطلب إدخالاً من المستخدم. لا يمكن تجربته مباشرة هنا.",
        'en': "⚠️ **Note:** This code is interactive and requires user input. It cannot be run directly here.",
    },
    'save_code_button': {'ar': "💾 حفظ الكود", 'en': "💾 Save Code"},
    'run_code_button': {'ar': "🚀 تجربة الكود", 'en': "🚀 Run Code"},
    'no_code_to_process': {'ar': "لا يوجد كود حالي لمعالجته.", 'en': "No current code to process."},
    'saving_file_error': {'ar': "عذراً، حدث خطأ أثناء إنشاء الملف.", 'en': "Sorry, an error occurred while creating the file."},
    'running_code': {'ar': "جاري تنفيذ الكود...", 'en': "Running code..."},
    'run_failed': {'ar': "فشلت خدمة تجربة الكود.", 'en': "The code execution service failed."},
    'run_error': {'ar': "عذراً، حدث خطأ تقني أثناء محاولة تجربة الكود.", 'en': "Sorry, a technical error occurred while trying to run the code."},
    'run_output': {'ar': "<b>الناتج:</b>", 'en': "<b>Output:</b>"},
    'run_errors': {'ar': "<b>أخطاء:</b>", 'en': "<b>Errors:</b>"},
    'no_output': {'ar': "لم ينتج الكود أي مخرجات.", 'en': "The code produced no output."},
    'run_result_header': {'ar': "--- 🚀 نتيجة تنفيذ الكود ---", 'en': "--- 🚀 Code Execution Result ---"},
    'choose_language': {'ar': "اختر لغة البوت:", 'en': "Choose the bot's language:"},
}

# --- LOGGING SETUP ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- HELPER FUNCTIONS ---

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Gets the user's current language, defaulting to Arabic."""
    return context.user_data.get('language', 'ar')

def get_text(key: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Gets the translated text for a given key based on user's language."""
    lang = get_lang(context)
    return MESSAGES.get(key, {}).get(lang, f"MISSING_TEXT: {key}")

# --- COMMAND HANDLERS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the welcome message and instructions."""
    user = update.effective_user
    welcome_message = get_text('start', context).format(user_mention=user.mention_html())
    await update.message.reply_html(welcome_message, disable_web_page_preview=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the help message with a list of commands."""
    await update.message.reply_html(get_text('help', context))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with language selection buttons."""
    keyboard = [
        [
            InlineKeyboardButton("العربية 🇦🇪", callback_data="set_lang_ar"),
            InlineKeyboardButton("English 🇬🇧", callback_data="set_lang_en"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text('choose_language', context), reply_markup=reply_markup)

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Updates the user's language choice."""
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split('_')[-1]
    context.user_data['language'] = lang_code
    await query.edit_message_text(text=get_text('lang_set', context))

async def set_api_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Saves the user's Gemini API key."""
    if not context.args:
        await update.message.reply_markdown_v2(get_text('api_key_usage', context))
        return
    context.user_data['gemini_api_key'] = context.args[0]
    await update.message.reply_text(get_text('api_key_set', context))

async def new_project_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the current project's conversation history."""
    context.user_data.pop('conversation_history', None)
    await update.message.reply_text(get_text('new_project', context))

# --- CORE CODE GENERATION LOGIC ---

def get_action_buttons(context: ContextTypes.DEFAULT_TYPE, is_interactive: bool = False) -> InlineKeyboardMarkup:
    """Creates action buttons, hiding the 'Run' button for interactive code."""
    keyboard_row = [InlineKeyboardButton(get_text('save_code_button', context), callback_data="save_code")]
    if not is_interactive:
        keyboard_row.append(InlineKeyboardButton(get_text('run_code_button', context), callback_data="run_code"))
    return InlineKeyboardMarkup([keyboard_row])

async def generate_or_improve_code(update: Update, context: ContextTypes.DEFAULT_TYPE, is_improvement: bool = False) -> None:
    """Generates new code or improves existing code based on user requests."""
    if 'gemini_api_key' not in context.user_data:
        await update.message.reply_text(get_text('api_key_needed', context))
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    history = context.user_data.get('conversation_history', [])
    
    try:
        genai.configure(api_key=context.user_data['gemini_api_key'])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if is_improvement:
            user_prompt = update.message.text
            if not history:
                await update.message.reply_text(get_text('no_project_to_improve', context))
                return
            await update.message.reply_text(get_text('improving_code', context))
            history.append({'role': 'user', 'parts': [user_prompt]})
            chat = model.start_chat(history=history[:-1])
            response = await chat.send_message_async(user_prompt)

        else: # New project
            if not context.args:
                await update.message.reply_text(get_text('code_prompt_needed', context))
                return
            
            await update.message.reply_text(get_text('generating_code', context))
            user_prompt = ' '.join(context.args)
            
            system_instruction = (
                "You are an expert programmer. Your ONLY task is to write complete, clean, and runnable code based on the user's request. "
                "IMPORTANT: YOU MUST ONLY OUTPUT THE RAW CODE. Do not include any explanations, introductions, markdown formatting like ```python, or any text outside of the code itself. "
                "If the project requires specific libraries, add a comment at the beginning of the code on how to install them (e.g., # pip install library_name)."
            )
            full_prompt = f"{system_instruction}\n\nUser's request: '{user_prompt}'"
            
            response = await model.generate_content_async(full_prompt)
            history = [{'role': 'user', 'parts': [full_prompt]}]

        generated_code = response.text.strip()
        
        history.append({'role': 'model', 'parts': [generated_code]})
        context.user_data['conversation_history'] = history
        is_interactive = "input(" in generated_code

        max_length = 4000
        for i in range(0, len(generated_code), max_length):
            chunk = generated_code[i:i + max_length]
            if chunk.startswith("```"):
                chunk = '\n'.join(chunk.split('\n')[1:])
            if chunk.endswith("```"):
                chunk = chunk[:-3].strip()

            reply_markup = get_action_buttons(context, is_interactive) if i + max_length >= len(generated_code) else None
            await update.message.reply_text(f"```\n{chunk}\n```", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

        if is_interactive:
            await update.message.reply_markdown_v2(get_text('interactive_code_note', context))
            
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        await update.message.reply_text(get_text('code_error', context))


async def handle_improvement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles requests to improve code when a user replies to the bot."""
    if update.message.reply_to_message and update.message.reply_to_message.from_user.is_bot:
        await generate_or_improve_code(update, context, is_improvement=True)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses for saving or running code."""
    query = update.callback_query
    await query.answer()

    if 'gemini_api_key' not in context.user_data:
        await context.bot.send_message(chat_id=query.message.chat_id, text=get_text('api_key_needed', context))
        return

    history = context.user_data.get('conversation_history', [])
    code_to_process = history[-1]['parts'][0] if history and history[-1]['role'] == 'model' else ""

    if not code_to_process:
        await context.bot.send_message(chat_id=query.message.chat_id, text=get_text('no_code_to_process', context))
        return

    if query.data == 'save_code':
        try:
            file_stream = io.BytesIO(code_to_process.encode('utf-8'))
            file_stream.name = 'coded_by_gemini.py'
            await context.bot.send_document(chat_id=query.message.chat_id, document=file_stream)
        except Exception as e:
            logger.error(f"File Save Error: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=get_text('saving_file_error', context))
    
    elif query.data == 'run_code':
        await context.bot.send_message(chat_id=query.message.chat_id, text=get_text('running_code', context))
        payload = {"language": "python", "version": "3.11.4", "files": [{"content": code_to_process}]}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post("[https://emkc.org/api/v2/piston/execute](https://emkc.org/api/v2/piston/execute)", json=payload, timeout=20.0)
            if response.status_code == 200:
                result = response.json()
                output_message = f"{get_text('run_result_header', context)}\n\n"
                stdout = result.get('run', {}).get('stdout', '').strip()
                stderr = result.get('run', {}).get('stderr', '').strip()
                if stdout: output_message += f"<b>{get_text('run_output', context)}</b>\n<pre>{stdout}</pre>\n"
                if stderr: output_message += f"<b>{get_text('run_errors', context)}</b>\n<pre>{stderr}</pre>\n"
                if not stdout and not stderr: output_message += get_text('no_output', context)
                await context.bot.send_message(chat_id=query.message.chat_id, text=output_message, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"{get_text('run_failed', context)} (Status: {response.status_code})")
        except Exception as e:
            logger.error(f"Run Code Error: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=get_text('run_error', context))

# --- MAIN FUNCTION ---

def main() -> None:
    """Starts the bot."""
    if 'YOUR_TELEGRAM_BOT_TOKEN_HERE' in TELEGRAM_BOT_TOKEN:
        print("!!! FATAL ERROR: Please set your TELEGRAM_BOT_TOKEN in the script.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("set_api_key", set_api_key_command))
    application.add_handler(CommandHandler("new_project", new_project_command))
    application.add_handler(CommandHandler("code", generate_or_improve_code))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, handle_improvement))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(save_code|run_code)$"))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern="^set_lang_"))

    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
