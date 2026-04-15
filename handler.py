from engine.orchestrator import process_request

async def handle_message(update, context):
    user_input = update.message.text

    response = await process_request(
        user_id=str(update.effective_user.id),
        message=user_input
    )

    # Убираем мусор вроде ** и лишних символов
    clean = sanitize_response(response)

    await update.message.reply_text(clean)


def sanitize_response(text: str) -> str:
    return text.replace("**", "").strip()