# src/schemas.py
"""Modelos Pydantic centralizados del sistema.

Cada modelo es un contrato en un borde del sistema:
- ChatRequest / ChatResponse : borde usuario <-> API
- TicketInput               : borde LLM -> tool create_ticket
- RAGResult                 : borde tool rag_search -> agente
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload de entrada del endpoint /chat."""
    message: str = Field(..., min_length=1, description="Mensaje del usuario")
    thread_id: str = Field(..., min_length=1, description="ID de conversacion")


class ChatResponse(BaseModel):
    """Payload de salida del endpoint /chat."""
    thread_id: str
    response: str
    tool_calls_used: list[str] = Field(
        default_factory=list,
        description="Nombres de las tools invocadas en esta respuesta"
    )


class TicketInput(BaseModel):
    """Args schema para la tool create_ticket.
    
    LangChain usa este modelo para dos cosas:
    1. Generar el JSON schema que le manda al LLM (para que sepa qué campos enviar)
    2. Validar los argumentos antes de ejecutar la función
    """
    summary: str = Field(..., min_length=5, max_length=300,
                         description="Descripcion del problema o solicitud")
    category: Literal[
        "field_instrument_failure",
        "biological_process_anomaly",
        "pump_maintenance",
        "undocumented_query",
    ] = Field(..., description="Categoria del ticket")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Prioridad del ticket"
    )


class RAGResult(BaseModel):
    """Estructura de respuesta de rag_search.
    
    Hoy el stub devuelve un string libre. Este modelo prepara
    la forma correcta para cuando llegue el RAG real en Capa 5.
    """
    content: str = Field(..., min_length=1, description="Contenido del chunk recuperado")
    source: str = Field(..., description="Nombre del documento fuente")
    score: Optional[float] = Field(
        default=None, ge=0.0,
        description="Score de fusion RRF (Reciprocal Rank Fusion) sobre el ranking de "
                     "vector search + keyword search -- no es similitud coseno ni ts_rank"
    )