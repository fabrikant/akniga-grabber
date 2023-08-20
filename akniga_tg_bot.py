import akniga_dl
import shutil
import settings
import os
from pathlib import Path
import logging
from telegram import __version__ as TG_VER
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f'This example is not compatible with your current PTB version {TG_VER}. To view the '
        f'{TG_VER} version of this example, '
        f'visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html'
    )
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from telegram import MessageEntity

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def create_book_archive(url_book, archive_full_path, update, context):
    book_directory = akniga_dl.download_book(url_book, settings.work_path)
    book_path = Path(book_directory)
    author_path = book_path.parent.parent
    base_dir = book_path.parent.name + os.path.sep + book_path.name
    shutil.make_archive(os.path.splitext(archive_full_path)[0], "zip", author_path, base_dir)
    shutil.rmtree(book_directory, ignore_errors=True)
    if len(os.listdir(book_path.parent)) == 0:
        shutil.rmtree(book_path.parent, ignore_errors=True)
    return '{0} - {1}'.format(book_path.parent.name, book_path.name)


async def send_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url_book = update.message.text
    answer = (
        'Принята в работу ссылка: {0}\n Дождитесь загрузки!!! Не пытайтесь отправить ссылку еще раз!!!').format(url_book)
    await update.message.reply_text(answer)
    try:
        Path(settings.work_path).mkdir(exist_ok=True)
        archive_name = url_book.split("/")[-1]
        archive_full_path = Path(os.path.join(settings.work_path, archive_name+".zip"))

        if not os.path.exists(archive_full_path):
            book_caption = create_book_archive(url_book, archive_full_path, update, context)
            await update.message.reply_text('Загрузка успешно завершена: {0}'.format(book_caption))

        await update.message.reply_document(open(archive_full_path, 'rb'), archive_full_path.name)
    except Exception as message:
        print(message)
        await update.message.reply_text('При загрузке книги {1} произошла ошибка: {0}'.format(message, url_book))


async def intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Для загрузки книги, пришлите ссылку на неё. Ссылка должна начинаться с: {0}'
                                    .format(settings.site_url))


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(settings.TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & (
      filters.Entity(MessageEntity.URL) |
      filters.Entity(MessageEntity.TEXT_LINK)) & filters.Regex(r'('+settings.site_url+'\S)'), send_book))

    application.add_handler(MessageHandler(filters.ALL, intro))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
