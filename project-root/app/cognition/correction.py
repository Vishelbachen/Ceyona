from typing import Optional


class Corrector:
    """
    Repairs low-quality LLM outputs.
    Does NOT re-decide model or intent.
    """

    @staticmethod
    def should_correct(evaluation) -> bool:
        return not evaluation.is_valid

    @staticmethod
    def build_repair_prompt(question: str, answer: str, issues: list) -> str:
        return (
            "You must improve the following answer.\n\n"
            f"QUESTION:\n{question}\n\n"
            f"CURRENT ANSWER:\n{answer}\n\n"
            f"ISSUES:\n{', '.join(issues)}\n\n"
            "Rules:\n"
            "- fix logical errors\n"
            "- improve clarity\n"
            "- keep original intent\n"
            "- do NOT add unnecessary text\n"
        )