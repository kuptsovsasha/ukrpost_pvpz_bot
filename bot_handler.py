import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from barcode_handler import BarcodeHandler
from database import Database
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class BotHandler:
    """
    Class to handle all bot interactions and conversations.
    """

    # Define conversation states
    PHOTO_OR_TEXT, ACTION, PAYMENT, CONFIRMATION = range(4)

    def __init__(self):
        # Initialize the database and barcode handler
        self.db = Database()
        self.barcode_handler = BarcodeHandler()

        # Define the custom keyboard
        self.custom_keyboard = [
            [KeyboardButton('Початок'), KeyboardButton('Скасувати')]
        ]
        self.reply_markup = ReplyKeyboardMarkup(self.custom_keyboard, resize_keyboard=True)

    def register_handlers(self, application):
        """
        Registers all the handlers with the application.
        """
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start),
                MessageHandler(filters.Regex('^Початок$'), self.start)
            ],
            states={
                self.PHOTO_OR_TEXT: [
                    MessageHandler(filters.PHOTO, self.photo_or_text_handler),
                    MessageHandler(filters.TEXT & (~filters.COMMAND), self.photo_or_text_handler),
                    MessageHandler(filters.Regex('^Скасувати$'), self.cancel)
                ],
                self.ACTION: [
                    CallbackQueryHandler(self.action_handler),
                    MessageHandler(filters.Regex('^Скасувати$'), self.cancel)
                ],
                self.PAYMENT: [
                    MessageHandler(filters.TEXT & (~filters.COMMAND), self.payment_handler),
                    MessageHandler(filters.Regex('^Скасувати$'), self.cancel)
                ],
                self.CONFIRMATION: [
                    CallbackQueryHandler(self.confirmation_handler),
                    MessageHandler(filters.Regex('^Скасувати$'), self.cancel)
                ],
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                MessageHandler(filters.Regex('^Скасувати$'), self.cancel)
            ],
        )
        application.add_handler(conv_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Starts the conversation and asks the user to send a barcode.
        """
        await update.message.reply_text(
            'Будь ласка надішліть фото з ШК або введіть ШК вручну.',
            reply_markup=self.reply_markup
        )
        return self.PHOTO_OR_TEXT

    def validate_barcode(self, barcode: str) -> bool:
        """
        Validates the format of the barcode.
        """
        return 8 <= len(barcode) <= 20

    async def prompt_for_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Prompts the user to select an action for the package.
        """
        keyboard = [
            [InlineKeyboardButton("Доставлено", callback_data='delivered')],
            [InlineKeyboardButton("Повернено", callback_data='returned')],
            [InlineKeyboardButton("Оплата", callback_data='payment')],
            [InlineKeyboardButton("Скасувати", callback_data='cancel')]
        ]
        reply_markup_inline = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text('Виберіть дію з посилкою:', reply_markup=reply_markup_inline)
        elif update.callback_query:
            await update.callback_query.edit_message_text('Виберіть дію з посилкою:', reply_markup=reply_markup_inline)
        return self.ACTION

    async def photo_or_text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the barcode input from the user, either via photo or text.
        """
        if update.message.photo:
            # Handle photo input
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            barcode = self.barcode_handler.extract_barcode(photo_bytes)
            if barcode:
                if self.db.barcode_exists(barcode):
                    await update.message.reply_text('Цей ШК уже був опрацьований', reply_markup=self.reply_markup)
                    return self.PHOTO_OR_TEXT
                else:
                    context.user_data['barcode'] = barcode
                    return await self.prompt_for_action(update, context)
            else:
                await update.message.reply_text(
                    'Не знайдено ШК на фото. Спробуйте ще чи введіть ШК вручну.',
                    reply_markup=self.reply_markup
                )
                return self.PHOTO_OR_TEXT
        elif update.message.text:
            # Handle text input
            barcode = update.message.text.strip()
            if barcode.lower() == 'скасувати':
                await self.cancel(update, context)
                return ConversationHandler.END
            if self.validate_barcode(barcode):
                if self.db.barcode_exists(barcode):
                    await update.message.reply_text('Цей ШК уже був опрацьований.', reply_markup=self.reply_markup)
                    return self.PHOTO_OR_TEXT
                else:
                    context.user_data['barcode'] = barcode
                    return await self.prompt_for_action(update, context)
            else:
                await update.message.reply_text('Не коректний ШК. Спробуйте знову.', reply_markup=self.reply_markup)
                return self.PHOTO_OR_TEXT
        else:
            await update.message.reply_text('Надішліть фото або введіть ШК вручну.', reply_markup=self.reply_markup)
            return self.PHOTO_OR_TEXT

    async def action_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the action selected by the user.
        """
        query = update.callback_query
        await query.answer()
        action = query.data
        if action == 'cancel':
            await self.cancel(update, context)
            return ConversationHandler.END
        context.user_data['action'] = action
        if action == 'payment':
            await query.edit_message_text(text="Введіть суму:")
            return self.PAYMENT
        else:
            barcode = context.user_data['barcode']
            confirmation_text = f"Підтвердьте деталі:\nШК: {barcode}\nДія: {action.capitalize()}"
            keyboard = [
                [InlineKeyboardButton("Підтвердити", callback_data='confirm')],
                [InlineKeyboardButton("Скасувати", callback_data='cancel')]
            ]
            reply_markup_inline = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=confirmation_text, reply_markup=reply_markup_inline)
            return self.CONFIRMATION

    async def payment_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the payment amount input by the user.
        """
        payment_amount = update.message.text
        if payment_amount.lower() == 'скасувати':
            await self.cancel(update, context)
            return ConversationHandler.END
        try:
            payment_amount = float(payment_amount)
            context.user_data['payment_amount'] = payment_amount
            barcode = context.user_data['barcode']
            action = context.user_data['action']
            confirmation_text = (
                f"Підтвердьте деталі:\n"
                f"ШК: {barcode}\n"
                f"Дія: {action.capitalize()}\n"
                f"Сума: {payment_amount}"
            )
            keyboard = [
                [InlineKeyboardButton("Підтвердити", callback_data='confirm')],
                [InlineKeyboardButton("Скасувати", callback_data='cancel')]
            ]
            reply_markup_inline = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(confirmation_text, reply_markup=reply_markup_inline)
            return self.CONFIRMATION
        except ValueError:
            await update.message.reply_text(
                "Не коректна інформація. Введіть цифрове значення.",
                reply_markup=self.reply_markup
            )
            return self.PAYMENT

    async def confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the confirmation of the details provided by the user.
        """
        query = update.callback_query
        await query.answer()
        if query.data == 'confirm':
            barcode = context.user_data['barcode']
            action = context.user_data['action']
            payment_amount = context.user_data.get('payment_amount', 0)

            # Collect user info
            user = update.effective_user
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }

            self.db.save_package(barcode, action, payment_amount, user_data)
            await query.edit_message_text(text="Інформація збережена успішно!")
            # Send a new message with the custom keyboard
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Натисніть 'Початок' для внесення нового ШК.",
                reply_markup=self.reply_markup
            )
            return ConversationHandler.END
        elif query.data == 'cancel':
            await self.cancel(update, context)
            return ConversationHandler.END
        else:
            await query.edit_message_text(text="Не коректний вибір.")
            return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Cancels the current operation and resets the conversation.
        """
        if update.callback_query:
            # Handle the cancel action from an inline button
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text='Операцію скасовано.'
            )
            # Send a new message with the custom keyboard
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Натисніть 'Початок' щоб спробувати знову.",
                reply_markup=self.reply_markup
            )
        elif update.message:
            # Handle the cancel action from a text message
            await update.message.reply_text(
                'Операцію скасовано.',
                reply_markup=self.reply_markup
            )
        return ConversationHandler.END
