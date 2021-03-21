import datetime
import json
import logging
import os
from pathlib import Path

from PIL import Image
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.absolute()
RUSSIA1_SOURCE_IMAGE = str(BASE_DIR / 'sources/russia1.jpg')
EXAMPLE_IMAGE = str(BASE_DIR / 'sources/floppa.jpg')


class Russia1bot:
	def __init__(self):
		self.photos_cache = dict()
		self.bot = None

	def _get_photos_of(self, user_id: int):
		if user_id in self.photos_cache:
			return self.photos_cache[user_id]
		self.photos_cache[user_id] = self.bot.get_user_profile_photos(user_id)
		return self.photos_cache[user_id]

	def start(self, update: Update, context: CallbackContext) -> None:
		logger.info(f'Start from {update.effective_user}')
		user_photos = self._get_photos_of(update.effective_user.id)
		if user_photos and len(user_photos.photos):
			result_filename = self._transform_photo(update.effective_user.id, user_photos.photos[0])
			with open(result_filename, 'rb') as f:
				markup = None
				if len(user_photos.photos) > 1:
					markup = InlineKeyboardMarkup([[InlineKeyboardButton('🔄 Другой аватар', callback_data=f'roll_1')]])
				update.message.reply_photo(photo=f, reply_markup=markup)
				update.message.reply_text('Привет! Я умею вот так ⬆️ с любым фото, просто пришли мне что-нибудь')
				return

		with open(f'files/example.jpg', 'rb') as f:
			update.message.reply_photo(photo=f, caption='Привет! Я умею вот так ⬆️ с любым фото, просто пришли мне что-нибудь')

	def process_avatar(self, update: Update, context: CallbackContext) -> None:
		photo_id = int(update.callback_query.data.split('_')[-1])
		logger.info(f'Processing avatar#{photo_id} from {update.effective_user}')
		user_photos = self._get_photos_of(update.effective_user.id)
		if photo_id >= len(user_photos.photos):
			photo_id = 0
		result_filename = self._transform_photo(update.effective_user.id, user_photos.photos[photo_id])
		with open(result_filename, 'rb') as f:
			markup = InlineKeyboardMarkup([[InlineKeyboardButton(f'🔄 Другой аватар', callback_data=f'roll_{photo_id + 1}')]])
			update.effective_message.edit_media(media=InputMediaPhoto(media=f), reply_markup=markup)

	def echo(self, update: Update, _: CallbackContext) -> None:
		if update.message:
			update.message.reply_text(f'Privet {json.dumps(update.effective_message.to_dict(), indent=1, ensure_ascii=False)}')

	def _combine_photo(self, file_name: str, result_filename: str = None) -> str:
		img = Image.open(file_name)
		img.thumbnail((550, 304))
		img_w, img_h = img.size

		result = Image.open(RUSSIA1_SOURCE_IMAGE)
		result.paste(img, (225 - int(img_w / 2) + int(550 / 2), 63 - int(img_h / 2) + int(304 / 2)))
		result_filename = result_filename or file_name.replace('.jpg', '-result.jpg')
		result.save(result_filename)
		return result_filename

	def _find_largest_photo(self, photo_set):
		return list(sorted(photo_set, key=lambda item: item.file_size, reverse=True))[0]

	def _transform_photo(self, user_id, photo_set) -> str:
		largest_file = self._find_largest_photo(photo_set)
		file_name = f'files/pic{user_id}-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}-{largest_file.file_unique_id}.jpg'
		largest_file.get_file().download(file_name)
		return self._combine_photo(file_name)

	def process_photo(self, update: Update, context: CallbackContext) -> None:
		logger.info(f'Process photo from {update.effective_user}')
		src_file = update.message.effective_attachment
		result_filename = self._transform_photo(update.effective_user.id, src_file)
		with open(result_filename, 'rb') as f:
			update.message.reply_photo(photo=f)

	def purge_cache(self, context: CallbackContext):
		logger.info(f'Cleaning {len(self.photos_cache)} cache entries...')
		self.photos_cache = dict()

	def explanation(self, update: Update, _: CallbackContext):
		if update and update.effective_user:
			logger.info(f'Explaining for {update.effective_user}')
			_.bot.sendMessage(chat_id=update.effective_user.id, text='Мне подойдёт фото. Отправь пожалуйста мне любое фото')

	def start_bot(self) -> None:
		"""Start the bot."""
		updater = Updater(os.environ['TOKEN'], request_kwargs=dict(connect_timeout=10, read_timeout=10))
		self.bot = updater.bot

		dispatcher = updater.dispatcher

		dispatcher.add_handler(CommandHandler("start", self.start))

		dispatcher.add_handler(MessageHandler(Filters.photo, self.process_photo))
		dispatcher.add_handler(CallbackQueryHandler(self.process_avatar, pattern='^roll_([0-9]+)$', pass_user_data=True))
		dispatcher.add_handler(MessageHandler(Filters.all, self.explanation))

		dispatcher.job_queue.run_repeating(self.purge_cache, interval=3600, first=3600)
		# todo delete old images

		updater.start_polling()

		# Run the bot until you press Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT. This should be used most of the time, since
		# start_polling() is non-blocking and will stop the bot gracefully.
		updater.idle()


if __name__ == '__main__':
	Russia1bot().start_bot()
