from engine.router import Router
from engine.cognitive import Cognitive
from engine.reasoning import Reasoning
from engine.solver import Solver
from engine.score import Scorer
from engine.selfcorrection import SelfCorrection
from engine.selfimprove import SelfImprove


class Orchestrator:
    def __init__(self):
        self.router = Router()
        self.cognitive = Cognitive()
        self.reasoning = Reasoning()
        self.solver = Solver()
        self.scorer = Scorer()
        self.corrector = SelfCorrection()
        self.improver = SelfImprove()

    async def process(self, user_id: int, text: str) -> str:
        # 1. Определение типа задачи
        route = self.router.route(text)

        # 2. Когнитивная обработка (контекст)
        context = await self.cognitive.build_context(user_id, text)

        # 3. Логическое рассуждение
        reasoning = await self.reasoning.analyze(text, context, route)

        # 4. Генерация ответа
        response = await self.solver.solve(text, context, reasoning, route)

        # 5. Оценка качества
        score = self.scorer.evaluate(response)

        # 6. Самокоррекция
        response = self.corrector.correct(response, score)

        # 7. Самоулучшение
        response = self.improver.improve(response, score)

        return response