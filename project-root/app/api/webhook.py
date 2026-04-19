@router.post("/webhook")
async def telegram_webhook(request: Request):
    trace_id = str(uuid4())

    try:
        payload = await request.json()

        message = payload.get("message") or {}
        text = message.get("text")

        user = message.get("from") or {}
        user_id = str(user.get("id") or "unknown")

        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if not text:
            return {"ok": True}

        if not chat_id:
            return {"ok": False, "error": "missing_chat_id"}

        req = OrchestratorRequest(
            trace_id=trace_id,
            user_id=user_id,
            user_message=UserMessage(
                user_id=user_id,
                text=text
            )
        )

        result = await handle_request(req)

        # 🔥 FIRE-AND-FORGET SAFE LAYER
        try:
            await ResponseHandler.handle(
                response=result,
                chat_id=chat_id
            )
        except Exception as e:
            logger.log(
                "ERROR",
                "response_handler_failed",
                trace_id=trace_id,
                error=str(e)
            )

        return {"ok": True, "trace_id": trace_id}

    except Exception as e:
        logger.log("ERROR", "webhook_crash", trace_id=trace_id, error=str(e))
        return {"ok": False, "trace_id": trace_id}