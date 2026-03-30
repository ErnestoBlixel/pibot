"""
Interfaz de Telegram para PiBot.
Bot que recibe mensajes de texto y voz, y responde a través de Telegram.
"""

import structlog

from config import settings

logger = structlog.get_logger()


async def send_notification(text: str, chat_id: str | None = None) -> None:
    """Envía una notificación por Telegram."""
    import httpx

    target = chat_id or settings.TELEGRAM_CHAT_ID_ERNESTO
    if not target:
        logger.warning("telegram_no_chat_id")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json={"chat_id": target, "text": text, "parse_mode": "Markdown"})
        if resp.status_code != 200:
            logger.error("telegram_send_failed", status=resp.status_code, body=resp.text[:200])


async def start_bot() -> None:
    """Inicia el bot de Telegram con polling."""
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

    from security.whitelist import is_allowed
    from orchestrator.graph import process_message
    from services.stt import transcribe

    async def handle_text(update: Update, context) -> None:
        chat_id = str(update.effective_chat.id)
        if not is_allowed(chat_id):
            await update.message.reply_text("No tienes acceso a este bot.")
            return

        text = update.message.text
        session_id = f"tg_{chat_id}"
        logger.info("telegram_message", chat_id=chat_id, text=text[:80])

        result = await process_message(message=text, session_id=session_id, channel="telegram")
        try:
            await update.message.reply_text(result["text"], parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(result["text"])

    async def handle_voice(update: Update, context) -> None:
        chat_id = str(update.effective_chat.id)
        if not is_allowed(chat_id):
            await update.message.reply_text("No tienes acceso a este bot.")
            return

        voice = update.message.voice or update.message.audio
        if not voice:
            await update.message.reply_text("No pude procesar el audio.")
            return

        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()

        text = await transcribe(bytes(audio_bytes))
        if not text:
            await update.message.reply_text("No pude transcribir el audio.")
            return

        session_id = f"tg_{chat_id}"
        logger.info("telegram_voice", chat_id=chat_id, transcribed=text[:80])

        result = await process_message(message=text, session_id=session_id, channel="voice")
        await update.message.reply_text(f"[Transcripción] {text}\n\n{result['text']}", parse_mode="Markdown")

    async def cmd_start(update: Update, context) -> None:
        await update.message.reply_text(
            "Hola, soy Pi, el asistente de Blixel AI. ¿En qué puedo ayudarte?"
        )

    async def cmd_status(update: Update, context) -> None:
        chat_id = str(update.effective_chat.id)
        if not is_allowed(chat_id):
            return
        await update.message.reply_text("Sistema operativo. Todos los servicios activos.")

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("telegram_bot_starting")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Mantener el bot corriendo
    import asyncio
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
