from aiogram import Router, types
from app.engine.agent import Agent


router = Router()


class Handlers:
    def __init__(self, agent: Agent):
        self.agent = agent

    def register(self):
        router.message.register(self.on_message)
        return router

    async def on_message(self, message: types.Message):
        user_id = str(message.from_user.id)
        text = message.text or ""

        response = await self.agent.run(user_id=user_id, text=text)

        await message.answer(response)