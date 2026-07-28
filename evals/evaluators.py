"""Evaluadores reutilizables para la Capa 3.

Este modulo concentra la logica de evaluacion para que tests/ y run_evals.py
usen exactamente las mismas funciones.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

from langchain_openai import ChatOpenAI
from langsmith import traceable  # Decorador opcional para instrumentar funciones con LangSmith

JUDGE_MODEL = "gpt-4o-mini"

RELEVANCE_PROMPT = """\
Eres un evaluador de calidad de respuestas de agentes de IA.

Pregunta del usuario: {question}
Respuesta del agente: {answer}

Evalua si la respuesta es relevante y util para la pregunta.
Responde SOLO con un numero del 1 al 5:
1 = completamente irrelevante
3 = parcialmente relevante
5 = completamente relevante y util

Numero:"""

ACCURACY_PROMPT = """\
Eres un evaluador de precision tecnica de un agente de soporte de instrumentacion.

Pregunta: {question}
Respuesta de referencia (correcta): {expected_answer}
Respuesta del agente: {answer}

Evalua si la respuesta del agente es tecnicamente correcta comparada con la
referencia. No exijas texto identico -- alcanza con que transmita la misma
informacion tecnica (rangos, pasos, condiciones) sin contradecirla ni inventar datos.
Responde SOLO con un numero del 1 al 5:
1 = incorrecta o contradice la referencia
3 = parcialmente correcta, le falta o sobra informacion relevante
5 = correcta, coincide en el contenido tecnico con la referencia

Numero:"""


def get_judge() -> ChatOpenAI:
    """Crea el LLM juez de forma lazy para evitar fallos al importar."""
    return ChatOpenAI(model=JUDGE_MODEL, temperature=0)


def extract_score(text: str) -> int:
    """Extrae el primer score valido del 1 al 5 desde la salida del juez.

    Lanza ValueError si no se encuentra un digito 1-5.
    """
    match = re.search(r"[1-5]", text)
    if not match:
        raise ValueError(f"El juez no devolvio un score valido: {repr(text)}")
    return int(match.group())


# Implementacion usando un wrapper para instrumentacion opt-in con LangSmith.
def _relevance_evaluator(question: str, answer: str) -> int:
    """Devuelve un score 1-5 sobre la relevancia de una respuesta.

    Implementacion "pura" que siempre funciona sin depender de LangSmith.
    """
    judge = get_judge()
    prompt = RELEVANCE_PROMPT.format(question=question, answer=answer)
    score_text = judge.invoke(prompt).content
    return extract_score(score_text)


# Si la variable de entorno LANGCHAIN_API_KEY existe, decoramos la funcion
# con `traceable` para que LangSmith pueda rastrear las invocaciones.
# Si no existe, dejamos la funcion sin decorar (fallo silencioso).
if os.getenv("LANGCHAIN_API_KEY"):
    relevance_evaluator = traceable(_relevance_evaluator)
else:
    relevance_evaluator = _relevance_evaluator


def _accuracy_evaluator(question: str, expected_answer: str, answer: str) -> int:
    """Devuelve un score 1-5 sobre la precision tecnica de una respuesta.

    A diferencia de relevance_evaluator, compara contra una expected_answer de
    referencia (golden set) en vez de juzgar la respuesta en el vacio.
    """
    judge = get_judge()
    prompt = ACCURACY_PROMPT.format(question=question, expected_answer=expected_answer, answer=answer)
    score_text = judge.invoke(prompt).content
    return extract_score(score_text)


if os.getenv("LANGCHAIN_API_KEY"):
    accuracy_evaluator = traceable(_accuracy_evaluator)
else:
    accuracy_evaluator = _accuracy_evaluator


def citation_evaluator(answer: str) -> bool:
    """Verifica si la respuesta menciona una fuente o documento.

    En esta capa el agente aun no cita formalmente, asi que la regla es simple:
    detectar palabras indicativas de fuente o documento.
    """
    normalized = answer.lower()
    citation_markers = (
        "fuente",
        "source",
        "documento",
        "doc",
        "guia",
        "manual",
        ".md",
        ".pdf",
    )
    # Retorna True si alguno de los marcadores aparece en el texto
    return any(marker in normalized for marker in citation_markers)


def convergence_evaluator(trace: Any) -> int:
    """Cuenta cuantos pasos tomo el agente hasta llegar a una respuesta final.

    Acepta varias formas de trace para no acoplarse al formato exacto:
    - dict con clave "messages"
    - lista/iterable de mensajes
    - cualquier iterable de eventos
    """
    if isinstance(trace, dict) and "messages" in trace:
        messages = trace["messages"]
    elif isinstance(trace, Iterable) and not isinstance(trace, (str, bytes)):
        messages = list(trace)
    else:
        raise TypeError("Trace no compatible para convergence_evaluator")

    return len(messages)