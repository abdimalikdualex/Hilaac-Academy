"""Course-aware AI study assistant with OpenAI + offline fallback."""
import json
import logging
import re
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

SUGGESTED_PROMPTS = {
    "en": [
        "Explain this lesson in simple terms",
        "Summarize this topic",
        "Give me practice questions",
        "Help me understand this assignment",
    ],
    "so": [
        "Ii sharax casharkan si fudud",
        "Soo koob mawduucan",
        "I sii su'aalo tababar ah",
        "I caawi inaan fahmo shaqadan",
    ],
}


def _lang_code(student) -> str:
    from apps.core.i18n import normalize_language

    if student and getattr(student, "is_authenticated", False):
        return normalize_language(getattr(student, "language_preference", "en"))
    return "en"


def build_course_context(level, lesson=None) -> str:
    lines = [
        f"Course: {level.language.name} — {level.name}",
        f"Description: {(level.description or '')[:800]}",
    ]
    if level.learning_objectives:
        lines.append(f"Objectives: {level.learning_objectives[:500]}")
    for module in level.modules.all().order_by("order"):
        lines.append(f"Module {module.order}: {module.title}")
        for ls in module.lessons.filter(is_published=True).order_by("order")[:12]:
            lines.append(f"  - Lesson: {ls.title} ({ls.get_lesson_type_display()}, {ls.duration_minutes} min)")
            if ls.description:
                lines.append(f"    {ls.description[:200]}")
    if lesson:
        lines.append(f"\nCurrent lesson: {lesson.title}")
        if lesson.description:
            lines.append(lesson.description[:600])
        if lesson.content:
            lines.append(lesson.content[:800])
    return "\n".join(lines)


def _fallback_response(question: str, context: str, lang: str) -> str:
    q = question.lower()
    if lang == "so":
        if any(w in q for w in ("sharax", "explain", "fahm")):
            return (
                "Waxaan ku caawin karaa fahamka casharka. Akhri casharka, ka dib ii sheeg qaybta aad ku adagtahay. "
                "Haddii aad rabto sharaxaad qoto dheer, ku dar API key OpenAI si Hilaac AI uu si toos ah uga jawaabo."
            )
        if any(w in q for w in ("koob", "summar")):
            return "Soo koobid: Dib u eeg casharrada koorsada kore si aad u aragto mawduucyada muhiimka ah."
        if any(w in q for w in ("su'aal", "practice", "imtixaan", "quiz")):
            return (
                "Su'aalo tababar ah:\n1. Waa maxay ujeeddada casharkan?\n"
                "2. Sharax erayada muhiimka ah.\n3. Tusaale nolosha dhabta ah ma bixin kartaa?"
            )
        return (
            "Waxaan ahay Hilaac AI. Weydii su'aalo ku saabsan casharka ama koorsada. "
            "Ku dar OPENAI_API_KEY si aad u hesho jawaabo caqli badan."
        )
    if any(w in q for w in ("explain", "what is", "help me understand")):
        return (
            "I can help you understand this lesson. Review the lesson content, then tell me which part is unclear. "
            "Add an OpenAI API key in settings for full AI-powered explanations."
        )
    if any(w in q for w in ("summar", "overview", "recap")):
        return "Summary: Review the module lessons listed in your course — focus on key terms and main ideas from each lesson."
    if any(w in q for w in ("practice", "question", "quiz", "test")):
        return (
            "Practice questions:\n1. What is the main goal of this lesson?\n"
            "2. Define the key vocabulary.\n3. Give a real-life example."
        )
    return (
        "I'm Hilaac AI, your study assistant for this course. Ask me to explain, summarize, or create practice questions. "
        "Configure OPENAI_API_KEY for richer AI answers."
    )


def _call_openai(question: str, context: str, lang: str) -> Optional[str]:
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        return None
    try:
        import urllib.request

        model = getattr(settings, "AI_TUTOR_MODEL", "gpt-4o-mini")
        system = (
            "You are Hilaac AI, a helpful tutor for Hilaac Academy online courses. "
            "Answer based on the course context provided. Be clear, educational, and encouraging. "
            f"Respond in {'Somali (Af-Soomaali)' if lang == 'so' else 'English'}."
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Course context:\n{context}\n\nStudent question: {question}"},
            ],
            "max_tokens": 800,
            "temperature": 0.6,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("OpenAI tutor request failed")
        return None


def ask_tutor(question: str, student, level, lesson=None) -> dict:
    question = (question or "").strip()
    if not question or len(question) > 2000:
        return {"error": "Invalid question", "answer": ""}
    question = re.sub(r"\s+", " ", question)
    lang = _lang_code(student)
    context = build_course_context(level, lesson)
    answer = _call_openai(question, context, lang)
    if not answer:
        answer = _fallback_response(question, context, lang)
    return {"answer": answer, "language": lang, "suggestions": SUGGESTED_PROMPTS.get(lang, SUGGESTED_PROMPTS["en"])}
