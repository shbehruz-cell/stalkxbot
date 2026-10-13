"""Application entry point."""
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, TypeHandler

from app.config import load_settings
from app.database import Database
from app.handlers import help_command, process_update, start, status


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger(__name__)
    db = Database(settings.database_path)

    # Concurrent update handling and a larger HTTP connection pool help when
    # several connected Business accounts generate updates at the same time.
    app = (
        Application.builder()
        .token(settings.bot_token)
        .concurrent_updates(16)
        .connection_pool_size(32)
        .pool_timeout(10.0)
        .build()
    )
    app.bot_data["db"] = db
    app.bot_data["settings"] = settings

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))

    # Handles Business connection, message, edit, and deletion updates.
    # Command handlers are in the default group; this handler runs in group 1.
    app.add_handler(TypeHandler(Update, process_update), group=1)

    logger.info("Starting Telegram Business Audit Bot polling.")
    app.run_polling(
        allowed_updates=[
            "message",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ],
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
