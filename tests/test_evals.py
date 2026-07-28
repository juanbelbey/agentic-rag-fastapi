"""Tests de evaluacion usando los evaluadores reutilizables de la Capa 3."""

from evals.evaluators import convergence_evaluator, relevance_evaluator


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
