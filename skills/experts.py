"""
Skills de expertos para PiBot.
Skills predefinidas que encapsulan conocimiento especializado.
"""

from orchestrator.llm import chat_completion
from skills.base import register_skill


async def summarize_text(text: str, **kwargs) -> str:
    """Resume un texto largo en puntos clave."""
    messages = [
        {"role": "system", "content": "Resume el siguiente texto en puntos clave concisos en español."},
        {"role": "user", "content": text},
    ]
    return await chat_completion(messages, temperature=0.3)


async def translate_text(text: str, target_lang: str = "en", **kwargs) -> str:
    """Traduce texto al idioma indicado."""
    messages = [
        {"role": "system", "content": f"Traduce el siguiente texto a {target_lang}. Solo devuelve la traducción."},
        {"role": "user", "content": text},
    ]
    return await chat_completion(messages, temperature=0.2)


async def draft_email(context: str, tone: str = "profesional", **kwargs) -> str:
    """Redacta un borrador de correo electrónico."""
    messages = [
        {"role": "system", "content": (
            f"Redacta un correo electrónico con tono {tone} basado en el contexto proporcionado. "
            "Incluye asunto, saludo, cuerpo y despedida."
        )},
        {"role": "user", "content": context},
    ]
    return await chat_completion(messages, temperature=0.4)


async def analyze_data(data: str, question: str = "", **kwargs) -> str:
    """Analiza datos y responde preguntas sobre ellos."""
    messages = [
        {"role": "system", "content": "Analiza los datos proporcionados y responde de forma clara y concisa."},
        {"role": "user", "content": f"Datos:\n{data}\n\nPregunta: {question}" if question else f"Analiza estos datos:\n{data}"},
    ]
    return await chat_completion(messages, temperature=0.3)


# Registrar skills al importar el módulo
register_skill("summarize", "Resume textos largos en puntos clave", summarize_text, category="text")
register_skill("translate", "Traduce texto entre idiomas", translate_text, category="text")
register_skill("draft_email", "Redacta borradores de correo electrónico", draft_email, category="communication")
register_skill("analyze_data", "Analiza datos y responde preguntas", analyze_data, category="analytics")
