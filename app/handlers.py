"""Telegram command and Business-update handlers."""
import difflib
import html
import logging
import re
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app.database import Database

logger = logging.getLogger(__name__)


def _safe_text(value: str | None, limit: int) -> str:
    if not value:
        return "[Matn mavjud emas yoki matnli kontent emas]"
    value = value.replace("\x00", "")
    if len(value) > limit:
        return value[:limit] + "\n… [qisqartirildi]"
    return value


def _source_name(chat) -> str:
    title = getattr(chat, "title", None)
    username = getattr(chat, "username", None)
    if title:
        return title
    if username:
        return f"@{username}"
    if chat.type == ChatType.PRIVATE:
        return "Shaxsiy chat"
    return str(chat.id)


def _message_link(chat, message_id: int) -> str | None:
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
        username = getattr(chat, "username", None)
        if username:
            return f"https://t.me/{username}/{message_id}"
    return None


def _tokens(text: str) -> list[str]:
    # Keep words, punctuation and whitespace as separate tokens so the diff
    # preserves the original text layout as closely as possible.
    return re.findall(r"\w+|[^\w\s]|\s+", text, flags=re.UNICODE)


def _html_escaped(text: str) -> str:
    return html.escape(text, quote=False)


def make_new_version_diff(old_text: str, new_text: str, limit: int) -> str:
    """HTML-formatted new text: inserted/replaced words bold; deletions shown as ellipsis."""
    old_tokens = _tokens(old_text)
    new_tokens = _tokens(new_text)
    matcher = difflib.SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    pieces: list[str] = []
    # Place deletion markers near the point where the removed text used to be.
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            pieces.extend(_html_escaped(t) for t in new_tokens[j1:j2])
        elif tag == "insert":
            changed = "".join(new_tokens[j1:j2])
            pieces.append("<b>" + _html_escaped(changed) + "</b>")
        elif tag == "replace":
            changed = "".join(new_tokens[j1:j2])
            pieces.append("<b>" + _html_escaped(changed) + "</b>")
        elif tag == "delete":
            # Requirement: show a visible ellipsis when old text was removed.
            pieces.append("<b>...</b>")
    rendered = "".join(pieces)
    if len(rendered) > limit:
        rendered = rendered[:max(0, limit - 30)] + "\n… [matn qisqartirildi]"
    return rendered or "[Bo'sh xabar]"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Men Telegram Business xabar hodisalari haqida bildirishnoma beraman.\n\n"
        "Ulash tartibi:\n"
        "1. Telegram Settings → Telegram Business → Chatbots bo'limini oching.\n"
        "2. Ushbu botni tanlang.\n"
        "3. Chatlar va ruxsatlarni diqqat bilan tekshiring.\n"
        "4. Ulanishni tasdiqlang va botga /start yuboring.\n"
        "5. /status buyrug'i bilan ulanish holatini ko'ring.\n\n"
        "Imkoniyatlar:\n"
        "• Yangi xabar haqida bildirishnoma\n"
        "• Tahrirdan oldingi va keyingi matnni taqqoslash\n"
        "• O'chirilgan xabar matnini bazadagi oldingi nusxadan ko'rsatish\n\n"
        "Muhim: bot faqat Telegram yuborgan, ruxsat berilgan hodisalarni oladi. "
        "Bot ulanganidan oldingi xabarlar bazada bo'lmasligi mumkin."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "/start — yo'riqnoma\n"
            "/status — Business ulanishlaringiz holati\n"
            "/help — yordam\n\n"
            "Eski matnni solishtirish uchun bot xabarni birinchi marta ko'rganida "
            "uning nusxasini SQLite bazasida saqlaydi. Bot ilgari ko'rmagan "
            "xabarni tahrirlash/o'chirish hodisasida eski matn mavjud bo'lmasligi mumkin."
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    db: Database = context.application.bot_data["db"]
    rows = db.list_connections(user.id)
    if not rows:
        await message.reply_text(
            "Hozircha Business ulanishi qayd etilmagan. "
            "Business Chatbots sozlamasida botni ulang va ruxsatlarni tekshiring."
        )
        return
    lines = ["Business ulanish holati:"]
    for index, row in enumerate(rows, 1):
        enabled = "Faol" if row["is_enabled"] else "O'chirilgan"
        read_right = row["can_read_messages"]
        read_label = "ha" if read_right == 1 else "yo'q" if read_right == 0 else "noma'lum"
        lines.append(
            f"{index}. Holat: {enabled}\n"
            f"   Xabarlarni o'qish huquqi: {read_label}\n"
            f"   Yangilangan: {row['updated_at']}"
        )
    await message.reply_text("\n\n".join(lines))



def _media_info(message) -> tuple[str | None, str | None, str | None]:
    """Return (media type, reusable Telegram file_id, readable label)."""
    candidates = (
        ("photo", getattr(message, "photo", None)),
        ("video", getattr(message, "video", None)),
        ("document", getattr(message, "document", None)),
        ("animation", getattr(message, "animation", None)),
        ("audio", getattr(message, "audio", None)),
        ("voice", getattr(message, "voice", None)),
        ("video_note", getattr(message, "video_note", None)),
        ("sticker", getattr(message, "sticker", None)),
    )
    for kind, value in candidates:
        if value:
            if kind == "photo":
                file_id = value[-1].file_id  # largest available photo size
            else:
                file_id = value.file_id
            label_map = {
                "photo": "RASM",
                "video": "VIDEO",
                "document": "FAYL",
                "animation": "GIF/ANIMATSIYA",
                "audio": "AUDIO",
                "voice": "OVOZLI XABAR",
                "video_note": "VIDEO XABAR",
                "sticker": "STIKER",
            }
            return kind, file_id, label_map[kind]
    if getattr(message, "contact", None):
        return "contact", None, "KONTAKT"
    if getattr(message, "location", None):
        return "location", None, "LOKATSIYA"
    if getattr(message, "venue", None):
        return "venue", None, "JOY MANZILI"
    return None, None, None


async def _send_cached_media(bot, chat_id: int, media_type: str | None, file_id: str | None) -> bool:
    """Resend media using its Telegram file_id; no local download/storage required."""
    if not media_type or not file_id:
        return False
    try:
        if media_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=file_id)
        elif media_type == "video":
            await bot.send_video(chat_id=chat_id, video=file_id)
        elif media_type == "document":
            await bot.send_document(chat_id=chat_id, document=file_id)
        elif media_type == "animation":
            await bot.send_animation(chat_id=chat_id, animation=file_id)
        elif media_type == "audio":
            await bot.send_audio(chat_id=chat_id, audio=file_id)
        elif media_type == "voice":
            await bot.send_voice(chat_id=chat_id, voice=file_id)
        elif media_type == "video_note":
            await bot.send_video_note(chat_id=chat_id, video_note=file_id)
        elif media_type == "sticker":
            await bot.send_sticker(chat_id=chat_id, sticker=file_id)
        else:
            return False
        return True
    except TelegramError:
        logger.exception("Could not resend cached %s media to owner %s", media_type, chat_id)
        return False


async def _copy_media_to_owner(bot, owner_id: int, message, media_type: str | None,
                               file_id: str | None) -> bool:
    """Copy the original message (preserving caption/format) with file_id fallback."""
    if not media_type:
        return False
    try:
        await bot.copy_message(
            chat_id=owner_id,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )
        return True
    except TelegramError:
        logger.warning("copy_message failed; trying cached file_id for media type %s", media_type)
        return await _send_cached_media(bot, owner_id, media_type, file_id)


async def _send_html(bot, chat_id: int, text: str) -> None:
    # Telegram message limit is 4096 chars; keep room for markup/entities.
    if len(text) > 3900:
        text = text[:3850] + "\n… [bildirishnoma qisqartirildi]"
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def process_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db: Database = context.application.bot_data["db"]
    settings = context.application.bot_data["settings"]

    connection = update.business_connection
    if connection:
        rights = connection.rights
        db.upsert_connection(
            connection_id=connection.id,
            owner_user_id=connection.user.id,
            is_enabled=connection.is_enabled,
            can_reply=getattr(rights, "can_reply", None) if rights else None,
            can_read_messages=getattr(rights, "can_read_messages", None) if rights else None,
        )
        # Connection events are stored silently. The owner only receives
        # notifications for actual message edits and deletions.
        logger.info("Business connection update received; enabled=%s", connection.is_enabled)
        return

    message = update.business_message or update.edited_business_message
    if message:
        connection_id = message.business_connection_id
        record = db.get_connection(connection_id)
        if not record or not record["is_enabled"]:
            logger.info("Ignoring message for unknown/disabled connection.")
            return

        chat = message.chat
        sender = message.from_user
        sender_label = (
            f"{sender.full_name} (ID: {sender.id})" if sender else "Noma'lum yuboruvchi"
        )
        media_type, file_id, media_label = _media_info(message)
        content_text = message.text or message.caption
        if content_text:
            current_text = _safe_text(content_text, 20000)
        elif media_label:
            current_text = f"[{media_label}]"
        else:
            current_text = "[Matnli bo'lmagan xabar yoki qo'llab-quvvatlanmaydigan kontent]"
        is_edit = update.edited_business_message is not None
        old = db.get_message_snapshot(connection_id, chat.id, message.message_id)

        # Save the reusable Telegram file_id as well as the last text/caption.
        # Telegram file_id can be resent later if the original message is deleted.
        db.save_message_snapshot(
            connection_id=connection_id,
            chat_id=chat.id,
            message_id=message.message_id,
            owner_user_id=record["owner_user_id"],
            chat_title=_source_name(chat),
            sender_label=sender_label,
            message_text=current_text,
            media_type=media_type,
            file_id=file_id,
        )

        # Ordinary incoming Business messages are only cached for later audit.
        # Do not send a notification or copy their media to the owner.
        if not is_edit:
            logger.debug("Saved new Business message silently: chat=%s message=%s", chat.id, message.message_id)
            return

        # An edit event that contains no actual text/caption/media-type change
        # is ignored to avoid unnecessary notifications.
        if (old and old["message_text"] == current_text
                and old.get("media_type") == media_type and old.get("file_id") == file_id):
            logger.debug("Ignoring edit event without a detectable content change: message=%s", message.message_id)
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        link = _message_link(chat, message.message_id)
        link_line = (
            f"\nXabar havolasi: {html.escape(link)}"
            if link else "\nXabar havolasi: bu chat uchun umumiy havola mavjud emas."
        )

        # Copy media to the owner's bot chat so photos, videos, documents, audio,
        # animations, voice messages and stickers are delivered as actual media.
        media_copied = False
        if media_type:
            media_copied = await _copy_media_to_owner(
                context.bot, record["owner_user_id"], message, media_type, file_id
            )

        if is_edit:
            if old and (old["message_text"] != current_text
                    or old.get("media_type") != media_type or old.get("file_id") != file_id):
                old_text = old["message_text"]
                new_diff = make_new_version_diff(old_text, current_text, settings.max_message_chars)
                notification = (
                    "✏️ <b>FOYDALANUVCHI XABARNI TAHRIRLADI</b>\n\n"
                    f"Manba: {html.escape(_source_name(chat))}\n"
                    f"Chat ID: <code>{chat.id}</code>\n"
                    f"Yuboruvchi: {html.escape(sender_label)}\n"
                    f"Xabar ID: <code>{message.message_id}</code>\n"
                    f"Vaqt: {timestamp}\n"
                    + (f"Kontent turi: {html.escape(media_label or 'MATN')}\n" if media_label else "")
                    + "\n📜 <b>ESKI HOLATI:</b>\n"
                    f"<pre>{html.escape(_safe_text(old_text, settings.max_message_chars))}</pre>\n"
                    "🆕 <b>YANGI HOLATI:</b>\n"
                    f"{new_diff}\n\n"
                    "Yangi/almashtirilgan qismlar <b>qalin</b>, o'chirilgan qism <b>...</b> bilan ko'rsatiladi."
                    + ("\n📎 Media alohida yuborildi." if media_copied else "")
                    + link_line
                )
            else:
                notification = (
                    "✏️ <b>FOYDALANUVCHI XABARNI TAHRIRLADI</b>\n\n"
                    f"Manba: {html.escape(_source_name(chat))}\n"
                    f"Chat ID: <code>{chat.id}</code>\n"
                    f"Yuboruvchi: {html.escape(sender_label)}\n"
                    f"Xabar ID: <code>{message.message_id}</code>\n"
                    f"Kontent: {html.escape(media_label or 'MATN')}\n\n"
                    "⚠️ Eski nusxa bazada topilmadi yoki matn o'zgarmagan. "
                    "Joriy matn/kontent:\n"
                    f"<pre>{html.escape(_safe_text(current_text, settings.max_message_chars))}</pre>"
                    + ("\n📎 Media alohida yuborildi." if media_copied else "")
                    + link_line
                )
        try:
            await _send_html(context.bot, record["owner_user_id"], notification)
        except TelegramError:
            logger.exception("Failed to deliver Business message notification.")
        return

    deleted = update.deleted_business_messages
    if deleted:
        record = db.get_connection(deleted.business_connection_id)
        if not record or not record["is_enabled"]:
            return

        for message_id in deleted.message_ids:
            snapshot = db.delete_message_snapshot(
                deleted.business_connection_id, deleted.chat.id, message_id
            )
            chat_name = snapshot["chat_title"] if snapshot else _source_name(deleted.chat)
            old_text = snapshot["message_text"] if snapshot else None
            sender_label = snapshot["sender_label"] if snapshot else "Noma'lum"
            media_type = snapshot.get("media_type") if snapshot else None
            file_id = snapshot.get("file_id") if snapshot else None
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            link = _message_link(deleted.chat, message_id)
            link_line = (
                f"\nXabar havolasi: {html.escape(link)}"
                if link else "\nXabar havolasi: bu chat uchun umumiy havola mavjud emas."
            )

            media_restored = await _send_cached_media(
                context.bot, record["owner_user_id"], media_type, file_id
            ) if media_type and file_id else False

            if old_text is not None:
                body = (
                    "🗑 <b>FOYDALANUVCHI XABARNI O'CHIRDI</b>\n\n"
                    f"Manba: {html.escape(chat_name)}\n"
                    f"Chat ID: <code>{deleted.chat.id}</code>\n"
                    f"Xabar yuboruvchi (saqlangan ma'lumot): {html.escape(sender_label)}\n"
                    f"Xabar ID: <code>{message_id}</code>\n"
                    f"Vaqt: {timestamp}\n"
                    + (f"Kontent turi: {html.escape(media_type.upper())}\n" if media_type else "")
                    + "\n📜 <b>O'CHIRILGAN XABAR MATNI (bazadagi nusxa):</b>\n"
                    f"<pre>{html.escape(_safe_text(old_text, settings.max_message_chars))}</pre>"
                    + ("\n📎 Saqlangan media nusxasi ham yuborildi." if media_restored else
                       "\n⚠️ Media nusxasini yuborib bo'lmadi yoki media saqlanmagan." if media_type else "")
                    + link_line
                )
            else:
                body = (
                    "🗑 <b>FOYDALANUVCHI XABARNI O'CHIRDI</b>\n\n"
                    f"Manba: {html.escape(_source_name(deleted.chat))}\n"
                    f"Chat ID: <code>{deleted.chat.id}</code>\n"
                    f"Xabar ID: <code>{message_id}</code>\n"
                    f"Vaqt: {timestamp}\n\n"
                    "⚠️ Xabar matni bazada topilmadi; bot uni avval ko'rmagan bo'lishi mumkin."
                    + link_line
                )
            try:
                await _send_html(context.bot, record["owner_user_id"], body)
            except TelegramError:
                logger.exception("Failed to deliver deletion notification.")
