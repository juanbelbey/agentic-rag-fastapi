"""Evaluaciones con LLM-as-judge.

A diferencia de test_rules.py, estos tests usan un segundo LLM (el "juez") para
evaluar la calidad de las respuestas del agente. Son mas lentos y costosos:
requieren API key y hacen llamadas reales.

Por eso se corren solo en push a main (lo configura ci.yml, no este archivo).

Patron: LLM-as-judge
    pregunta → agente → respuesta del agente
                              │
                              ▼
                    juez (gpt-4o-mini)
                    recibe: pregunta + respuesta
                    devuelve: score 1-5
                              │
                        assert score >= 3
"""

import re

import pytest
from langchain_openai import ChatOpenAI


# ─── Configuracion del juez ───────────────────────────────────────────────────

JUDGE_MODEL = "gpt-4o-mini"

# Prompt para evaluar relevancia: ¿la respuesta responde la pregunta?
RELEVANCE_PROMPT = """\
Eres un evaluador de calidad de respuestas de agentes de IA.

Pregunta del usuario: {question}
Respuesta del agente: {response}

Evalua si la respuesta es relevante y util para la pregunta.
Responde SOLO con un numero del 1 al 5:
1 = completamente irrelevante
3 = parcialmente relevante
5 = completamente relevante y util

Numero:"""

# Prompt para evaluar alucinacion: ¿la respuesta inventa info fuera del contexto?
HALLUCINATION_PROMPT = """\
Eres un evaluador de fidelidad de respuestas de agentes de IA.

Contexto disponible para el agente: {context}
Respuesta del agente: {response}

Evalua si la respuesta se basa en el contexto sin inventar informacion.
Responde SOLO con un numero del 1 al 5:
1 = inventa informacion claramente fuera del contexto
3 = mezcla informacion real con suposiciones
5 = se basa completamente en el contexto disponible

Numero:"""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_judge() -> ChatOpenAI:
    """Crea el LLM juez. Lazy: se llama dentro de cada test, no al importar."""
    return ChatOpenAI(model=JUDGE_MODEL, temperature=0)


def extract_score(text: str) -> int:
    """Extrae el primer numero del 1 al 5 de la respuesta del juez."""
    match = re.search(r"[1-5]", text)
    if not match:
        raise ValueError(f"El juez no devolvio un score valido: {repr(text)}")
    return int(match.group())


# ─── Evaluaciones de relevancia ───────────────────────────────────────────────

class TestRelevanceEval:
    """Verifica que las respuestas del agente son relevantes para las preguntas.

    Usa invoke_agent (fixture de conftest.py) para invocar el grafo real.
    Usa get_judge() para evaluar la respuesta con un LLM separado.
    """

    def test_rag_response_is_relevant(self, invoke_agent):
        # El agente recibe una pregunta de busqueda y debe dar una respuesta util.
        question = "Como puedo solicitar un reembolso?"
        result = invoke_agent(question)
        response = result["messages"][-1].content

        judge = get_judge()
        prompt = RELEVANCE_PROMPT.format(question=question, response=response)
        score = extract_score(judge.invoke(prompt).content)

        assert score >= 3, (
            f"Respuesta poco relevante (score={score}/5).\n"
            f"Pregunta:   {question}\n"
            f"Respuesta:  {response}"
        )

    def test_ticket_response_is_relevant(self, invoke_agent):
        # El agente recibe un pedido de ticket y debe confirmar la creacion.
        question = "Necesito crear un ticket porque no puedo iniciar sesion"
        result = invoke_agent(question)
        response = result["messages"][-1].content

        judge = get_judge()
        prompt = RELEVANCE_PROMPT.format(question=question, response=response)
        score = extract_score(judge.invoke(prompt).content)

        assert score >= 3, (
            f"Respuesta poco relevante (score={score}/5).\n"
            f"Pregunta:   {question}\n"
            f"Respuesta:  {response}"
        )


# ─── Evaluaciones de alucinacion ─────────────────────────────────────────────

class TestHallucinationEval:
    """Verifica que el agente no inventa informacion fuera del contexto disponible.

    El contexto conocido es el string que devuelve el stub de rag_search.
    Si el agente afirma datos concretos que no estan en ese string, el juez
    deberia dar un score bajo.
    """

    def test_rag_response_does_not_hallucinate(self, invoke_agent):
        question = "Cuales son los pasos exactos para solicitar un reembolso?"

        # Este es el unico contexto que el agente tiene disponible via rag_search.
        known_context = (
            "Resultado simulado de RAG para la consulta: 'reembolso'. "
            "Documento encontrado: guia-interna-agentic-rag-fastapi.md"
        )

        result = invoke_agent(question)
        response = result["messages"][-1].content

        judge = get_judge()
        prompt = HALLUCINATION_PROMPT.format(context=known_context, response=response)
        score = extract_score(judge.invoke(prompt).content)

        assert score >= 3, (
            f"Posible alucinacion detectada (score={score}/5).\n"
            f"Contexto:   {known_context}\n"
            f"Respuesta:  {response}"
        )
