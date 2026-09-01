"""Tests de evaluacion usando los evaluadores reutilizables de la Capa 3."""

from evals.evaluators import abstention_evaluator, convergence_evaluator, relevance_evaluator


# ─── Evaluaciones de relevancia ───────────────────────────────────────────────

class TestRelevanceEval:
    """Verifica relevancia usando el evaluador compartido del proyecto."""

    def test_rag_response_is_relevant(self, invoke_agent):
        # El agente recibe una pregunta de busqueda y debe dar una respuesta util.
        question = "Que boton se debe presionar para realizar un ajuste a cero digital en un area peligrosa?"
        result = invoke_agent(question)
        response = result["messages"][-1].content

        score = relevance_evaluator(question, response)

        assert score >= 3, (
            f"Respuesta poco relevante (score={score}/5).\n"
            f"Pregunta:   {question}\n"
            f"Respuesta:  {response}"
        )

    def test_ticket_response_is_relevant(self, invoke_agent):
        # El agente recibe un pedido de ticket y debe confirmar la creacion.
        question = (
            "El transmisor Rosemount 3051 de la linea de impulsion esta "
            "descalibrado y necesito que un tecnico lo revise en planta, "
            "pueden generar un ticket?"
        )
        result = invoke_agent(question)
        response = result["messages"][-1].content

        score = relevance_evaluator(question, response)

        assert score >= 3, (
            f"Respuesta poco relevante (score={score}/5).\n"
            f"Pregunta:   {question}\n"
            f"Respuesta:  {response}"
        )


# ─── Abstencion ante preguntas fuera de dominio ───────────────────────────────

class TestAbstentionEval:
    """Smoke test de Nivel 2 (CI): el agente debe rechazar una pregunta fuera
    de dominio en vez de responderla (ver prompts/system_prompt_direct_answer.txt).

    Caso c023 del critical_eval_set (Windows 11) elegido a proposito: es la
    unica pregunta fuera_de_dominio que hoy se comporta bien de forma
    confiable -- "capital de Francia" (c022) sigue fallando (ver EXPERIMENTS.md,
    limitacion conocida) y usarla aca haria el test flaky/rojo a proposito.
    """

    def test_declines_out_of_domain_question(self, invoke_agent):
        question = "¿Cómo configuro las notificaciones de Windows 11?"
        result = invoke_agent(question)
        response = result["messages"][-1].content

        score = abstention_evaluator(question, response)

        assert score >= 3, (
            f"El agente no rechazo una pregunta fuera de dominio (score={score}/5).\n"
            f"Pregunta:   {question}\n"
            f"Respuesta:  {response}"
        )


# ─── Evaluaciones code-based sobre la traza ──────────────────────────────────

class TestTraceEval:
    """Verifica la convergencia usando la misma funcion del runner de evals.

    En esta capa no usamos trazas externas todavia, asi que medimos la
    convergencia con la cantidad de mensajes acumulados en la ejecucion.
    """

    def test_trace_records_multiple_steps(self, invoke_agent):
        question = "Que boton se debe presionar para realizar un ajuste a cero digital en un area peligrosa?"
        result = invoke_agent(question)
        steps = convergence_evaluator(result)

        assert steps >= 2, (
            "Se esperaban al menos 2 pasos en la traza "
            f"(mensaje humano + respuesta del agente), pero hubo {steps}."
        )
