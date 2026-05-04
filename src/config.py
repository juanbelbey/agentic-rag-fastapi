"""Configuracion minima del proyecto.

Responsabilidad de este modulo:
1) Cargar variables de entorno desde .env
2) Validar claves obligatorias
"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Configuracion tipada de la aplicacion."""

    openai_api_key: str


def load_settings() -> Settings:
    """Carga y valida configuracion obligatoria para correr el agente."""
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError(
            "Falta OPENAI_API_KEY. Crea/edita .env en la raiz del proyecto y agrega: "
            "OPENAI_API_KEY=tu_api_key"
        )

    return Settings(openai_api_key=openai_api_key)
