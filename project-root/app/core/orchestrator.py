async def handle_request(req: OrchestratorRequest, memory: MemoryService | None = None):

    trace_id = req.trace_id

    try:
        req.user_message.normalize()

        text = req.user_message.text
        user_id = req.user_message.user_id

        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        if not text:
            raise ValueError("Empty input")

        # -------------------------
        # MEMORY
        # -------------------------
        context = []
        if memory and getattr(memory, "build_context", None):
            try:
                context = memory.build_context(user_id) or []
            except Exception as e:
                logger.log("WARN", "memory_load_failed", trace_id=trace_id, error=str(e))

        # -------------------------
        # INTENT
        # -------------------------
        intent_result = classify_intent(text)
        task_type = getattr(intent_result, "task_type", None) or "general"

        # -------------------------
        # MODEL
        # -------------------------
        model, intent_result = resolve_model(text)

        # -------------------------
        # PROMPT
        # -------------------------
        prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model,
            task_type=task_type
        )

        # -------------------------
        # LOOP
        # -------------------------
        max_attempts = 2
        final_answer = None
        last_response = ""

        for attempt in range(max_attempts):

            logger.log("INFO", "llm_attempt", trace_id=trace_id, attempt=attempt)

            response = await run_llm(
                model=model,
                prompt=prompt,
                trace_id=trace_id
            )

            last_response = (response.content or "").strip()

            check = ReasoningVerifier.verify(
                task_type=task_type,
                question=text,
                answer=last_response
            )

            if check["is_valid"]:
                final_answer = last_response
                break

            logger.log("WARN", "verifier_failed", trace_id=trace_id, issues=check["issues"])

            prompt = Corrector.build_repair_prompt(
                question=text,
                answer=last_response,
                issues=check["issues"],
                context=context
            )

        final_answer = final_answer or last_response or "Unable to generate response."

        # -------------------------
        # MEMORY
        # -------------------------
        if memory and getattr(memory, "store", None):
            try:
                memory.store.append_message(user_id, "user", text)
                memory.store.append_message(user_id, "assistant", final_answer)
            except Exception as e:
                logger.log("ERROR", "memory_save_failed", trace_id=trace_id, error=str(e))

        # -------------------------
        # EVAL
        # -------------------------
        evaluation = Evaluator.evaluate(
            task_type=task_type,
            question=text,
            answer=final_answer
        )

        # -------------------------
        # SUPABASE
        # -------------------------
        try:
            store = SupabaseStore.get_instance()

            event = Reflection.build_event(
                user_id=user_id,
                question=text,
                answer=final_answer,
                model=model,
                task_type=task_type,
                evaluation=evaluation,
                trace_id=trace_id
            )

            store.insert_reflection("cognition_logs", event)

        except Exception as e:
            logger.log("ERROR", "cognition_log_failed", trace_id=trace_id, error=str(e))

        return SuccessResponse(
            data=final_answer,
            trace_id=trace_id,
            model=model,
            intent=intent_result.intent,
            task_type=task_type,
            reasoning_valid=getattr(evaluation, "is_valid", None),
            confidence=getattr(evaluation, "score", None)
        )

    except Exception as e:

        logger.log("ERROR", "orchestrator_crash", trace_id=trace_id, error=str(e))

        return ErrorResponse(
            error={"message": str(e)},
            trace_id=trace_id
        )