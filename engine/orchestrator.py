async def process(self, user_id: int, text: str) -> str:
    try:
        user_id_str = str(user_id)
        text = (text or "").strip()

        # 0 ACCESS
        if self.access:
            allowed, msg = self.access.require_access(user_id_str)
            if not allowed:
                return msg

        # 1 ROUTER
        route = self.router.route(text)

        # 2 BRAIN (NEW CORE)
        brain = self.brain.analyze(text, route)

        # 3 MEMORY
        memory_context = {"recent": [], "semantic": []}
        if self.memory_enabled:
            memory_context = await self.memory_intelligence.build_context(
                user_id=user_id_str,
                text=text
            )

        # 4 CONTEXT
        context = await self.cognitive.build_context(
            user_id=user_id,
            text=text,
            memory=memory_context,
            brain=brain
        )

        # 5 REASONING
        reasoning = await self.reasoning.analyze(
            text=text,
            context=context,
            route=route,
            brain=brain
        )

        # 6 SOLVER
        response = await self.solver.solve(
            text=text,
            context=context,
            reasoning=reasoning,
            route=route
        )

        # 7 VERIFY (BRAIN)
        response = self.brain.verify(response, brain["domain"])

        # 8 MEMORY SAVE
        if self.memory_enabled:
            await self.memory_intelligence.update_memory(
                user_id=user_id_str,
                text=text,
                response=response
            )

        return response

    except Exception as e:
        logger.exception(f"[Orchestrator] Fatal: {e}")
        return self._fallback(text)