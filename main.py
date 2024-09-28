import os
from telegram.ext import (
    ApplicationBuilder,
)
from bot_handler import BotHandler
from dotenv import load_dotenv


def main():
    # Load environment variables from .env file
    load_dotenv()
    # Get the bot token from an environment variable or configuration file
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("No bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_handler = BotHandler()
    bot_handler.register_handlers(application)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == '__main__':
    main()
