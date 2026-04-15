from aiogram import Router, types
from aiogram.filters import CommandStart

from engine.orchestrator import Orchestrator

router = Router()
orchestrator = Orchestrator()


@router.message(CommandStart())
async def start(message: types.Message):
    await message.answer("🚀 AI System Online")


@router.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    user_input = message.text

    result = await orchestrator.handle(
        user_input=user_input,
        user_id=user_id
    )

    response = result.get("response", "")

    if not response:
        response = "⚠️ No response generated"

    await message.answer(response)