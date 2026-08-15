# scripts/generate_synthetic_corpus.py
"""Genera un corpus sintetico de PDFs con contenido tecnico original sobre
instrumentacion de campo (presion, caudal, temperatura) para agua potable y
saneamiento, con marcas y modelos ficticios.

Por que existe: el corpus real (docs/pdfs/, gitignored) son 11 manuales con
copyright de Emerson/Rosemount, Siemens Sitrans y Endress+Hauser -- un
reviewer del curso tiene que descargarlos a mano antes de poder correr
scripts/ingest.py. Segun Alexey Grigorev (creador del LLM Zoomcamp), generar
PDFs similares evita perder puntaje de reproducibility. Este script genera esa
alternativa: prueba piloto de 3 documentos, no reemplaza el corpus real.

El contenido de cada documento lo escribe gpt-4o-mini a partir de un prompt
que solo describe el dominio (tipo de instrumento, secciones esperadas) --
nunca copia ni parafrasea ningun manual real, y usa marcas/modelos inventados.
Se corre a mano:
    python -m scripts.generate_synthetic_corpus
"""

from pathlib import Path

from dotenv import load_dotenv
from fpdf import FPDF
from openai import OpenAI

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "pdfs_synthetic"

SYNTHETIC_NOTICE = (
    "SYNTHETIC SAMPLE -- fictional content generated for testing purposes, "
    "not a real manufacturer manual."
)

SYSTEM_PROMPT = (
    "You are a technical writer drafting an ORIGINAL field-instrumentation "
    "manual for a fictional manufacturer. You are NOT allowed to reproduce, "
    "paraphrase, or reference any real manufacturer's manual, model number, "
    "or brand (e.g. Emerson, Rosemount, Siemens, Sitrans, Endress+Hauser). "
    "Invent all brand names, model numbers, specifications, calibration "
    "steps, error codes, and maintenance procedures from scratch -- they "
    "just need to be internally consistent and read like a plausible "
    "technical manual for water/wastewater treatment field instrumentation. "
    "Write in English, in plain text (no markdown, no tables with pipes), "
    "structured with clear section headings written in ALL CAPS on their "
    "own line."
)

# El cliente de OpenAI se crea recien la primera vez que hace falta (mismo
# patron que src/ingestion.py._get_client) para no exigir OPENAI_API_KEY solo
# por importar este modulo.
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# Los 3 documentos de la prueba piloto: uno por tipo de instrumento (presion,
# caudal, temperatura), los tres tipos de instrumento que cubre el caso de uso
# de CORPUS_INSTRUMENTACION.MD. Marca ficticia comun ("FieldSense") para que
# los tres documentos se lean como una misma linea de productos, con modelos
# ficticios distintos por instrumento.
DOCUMENTS = [
    {
        "filename": "fieldsense_pt300_pressure_transmitter.pdf",
        "title": "FieldSense PT-300 Pressure Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'FieldSense PT-300', a fictional "
            "pressure transmitter used in water distribution networks and "
            "water treatment plants (e.g. pump station discharge pressure, "
            "filter differential pressure for backwash triggering). Include "
            "these sections: PRODUCT OVERVIEW, TECHNICAL SPECIFICATIONS "
            "(measurement range, accuracy, output signal, process "
            "connection, ingress protection, hazardous area certification), "
            "CALIBRATION PROCEDURE (zero and span adjustment), ERROR CODES "
            "(at least 5 codes with cause and resolution), and MAINTENANCE "
            "(routine checks and troubleshooting). Roughly 500-700 words."
        ),
    },
    {
        "filename": "fieldsense_ft450_flow_transmitter.pdf",
        "title": "FieldSense FT-450 Magnetic Flow Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'FieldSense FT-450', a "
            "fictional magnetic flow transmitter used for plant inlet/outlet "
            "flow, chlorine and coagulant dosing flow, and treated effluent "
            "flow monitoring in water and wastewater treatment plants. "
            "Include these sections: PRODUCT OVERVIEW, TECHNICAL "
            "SPECIFICATIONS (flow range, accuracy, electrode material, "
            "process connection, output signal, ingress protection), "
            "CALIBRATION PROCEDURE (empty-pipe and full-scale calibration), "
            "ERROR CODES (at least 5 codes with cause and resolution), and "
            "MAINTENANCE (electrode cleaning and troubleshooting). Roughly "
            "500-700 words."
        ),
    },
    {
        "filename": "fieldsense_tt120_temperature_transmitter.pdf",
        "title": "FieldSense TT-120 Temperature Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'FieldSense TT-120', a "
            "fictional temperature transmitter used in wastewater biological "
            "treatment (activated sludge process monitoring) and in pump "
            "motor overheating protection for predictive maintenance. "
            "Include these sections: PRODUCT OVERVIEW, TECHNICAL "
            "SPECIFICATIONS (measurement range, accuracy, sensor type, "
            "process connection, output signal), CALIBRATION PROCEDURE, "
            "ERROR CODES (at least 4 codes with cause and resolution), and "
            "MAINTENANCE (routine checks and troubleshooting). Roughly "
            "400-600 words."
        ),
    },
    # Documentos 4-11: dos marcas ficticias mas (AquaPress, Rivertek), para
    # llegar a 11 documentos -- el mismo numero y la misma mezcla que el
    # corpus real (docs/pdfs/): varios fabricantes, mezcla de manual
    # completo + quick start guide + datasheet, mayoria de presion con
    # algo de caudal, como en CORPUS_INSTRUMENTACION.MD.
    {
        "filename": "aquapress_ap210_pressure_transmitter_manual.pdf",
        "title": "AquaPress AP-210 Pressure Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'AquaPress AP-210', a "
            "fictional pressure transmitter used for pump station discharge "
            "pressure monitoring in water distribution networks. Include "
            "these sections: PRODUCT OVERVIEW, TECHNICAL SPECIFICATIONS "
            "(measurement range, accuracy, output signal, process "
            "connection, ingress protection), CALIBRATION PROCEDURE (zero "
            "and span adjustment), ERROR CODES (at least 5 codes with cause "
            "and resolution), and MAINTENANCE. Roughly 500-700 words."
        ),
    },
    {
        "filename": "aquapress_ap210_pressure_transmitter_quickstart.pdf",
        "title": "AquaPress AP-210 Pressure Transmitter -- Quick Start Guide",
        "user_prompt": (
            "Write a short quick start guide (not a full manual) for the "
            "'AquaPress AP-210' pressure transmitter: INSTALLATION STEPS, "
            "WIRING DIAGRAM DESCRIPTION (describe in words, no actual "
            "diagram), and BASIC STARTUP CHECK. Roughly 200-300 words."
        ),
    },
    {
        "filename": "aquapress_ap410_pressure_transmitter_hart_manual.pdf",
        "title": "AquaPress AP-410 Pressure Transmitter (HART) -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'AquaPress AP-410', a "
            "fictional HART-protocol pressure transmitter used for filter "
            "differential pressure monitoring in water treatment plants "
            "(used to trigger backwash cycles). Include these sections: "
            "PRODUCT OVERVIEW, TECHNICAL SPECIFICATIONS (measurement range, "
            "accuracy, HART protocol details, hazardous area certification), "
            "CALIBRATION PROCEDURE, ERROR CODES (at least 5 codes with cause "
            "and resolution), and MAINTENANCE. Roughly 500-700 words."
        ),
    },
    {
        "filename": "aquapress_ap410_pressure_transmitter_datasheet.pdf",
        "title": "AquaPress AP-410 Pressure Transmitter -- Datasheet",
        "user_prompt": (
            "Write a short product datasheet (not a full manual) for the "
            "'AquaPress AP-410' pressure transmitter: PRODUCT SUMMARY, KEY "
            "SPECIFICATIONS (as a plain list, no tables with pipes), and "
            "ORDERING INFORMATION (model code options). Roughly 200-300 "
            "words."
        ),
    },
    {
        "filename": "aquapress_ap600_diff_pressure_transmitter_manual.pdf",
        "title": "AquaPress AP-600 Differential Pressure Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'AquaPress AP-600', a "
            "fictional differential pressure transmitter used specifically "
            "for filter backwash triggering in water treatment plants. "
            "Include these sections: PRODUCT OVERVIEW, TECHNICAL "
            "SPECIFICATIONS, CALIBRATION PROCEDURE (zero and span "
            "adjustment for differential pressure), ERROR CODES (at least 5 "
            "codes with cause and resolution), and MAINTENANCE. Roughly "
            "500-700 words."
        ),
    },
    {
        "filename": "rivertek_rt2050_pressure_transmitter_manual.pdf",
        "title": "Rivertek RT-2050 Pressure Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'Rivertek RT-2050', a "
            "fictional pressure transmitter used for water treatment plant "
            "process pressure monitoring. Include these sections: PRODUCT "
            "OVERVIEW, TECHNICAL SPECIFICATIONS, CALIBRATION PROCEDURE, "
            "ERROR CODES (at least 5 codes with cause and resolution), and "
            "MAINTENANCE. Roughly 500-700 words."
        ),
    },
    {
        "filename": "rivertek_rt2050_pressure_transmitter_quickstart.pdf",
        "title": "Rivertek RT-2050 Pressure Transmitter -- Quick Start Guide",
        "user_prompt": (
            "Write a short quick start guide (not a full manual) for the "
            "'Rivertek RT-2050' pressure transmitter: INSTALLATION STEPS, "
            "WIRING DIAGRAM DESCRIPTION (describe in words), and BASIC "
            "STARTUP CHECK. Roughly 200-300 words."
        ),
    },
    {
        "filename": "rivertek_rt8700_flow_transmitter_manual.pdf",
        "title": "Rivertek RT-8700 Magnetic Flow Transmitter -- Technical Manual",
        "user_prompt": (
            "Write a technical manual for the 'Rivertek RT-8700', a "
            "fictional magnetic flow transmitter used for treated effluent "
            "flow monitoring discharged to the receiving water body in "
            "wastewater treatment plants. Include these sections: PRODUCT "
            "OVERVIEW, TECHNICAL SPECIFICATIONS (flow range, accuracy, "
            "electrode material, output signal), CALIBRATION PROCEDURE, "
            "ERROR CODES (at least 5 codes with cause and resolution), and "
            "MAINTENANCE (electrode cleaning). Roughly 500-700 words."
        ),
    },
]


def generate_content(user_prompt: str) -> str:
    """Pide a gpt-4o-mini el cuerpo del manual. Contenido 100% inventado por
    el modelo a partir de la descripcion del instrumento, nunca copiado."""
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


class SyntheticManualPDF(FPDF):
    """PDF con la leyenda SYNTHETIC SAMPLE en el footer de cada pagina."""

    def footer(self) -> None:
        # cell() en vez de multi_cell(): footer() se dispara en medio de un
        # multi_cell del cuerpo cuando el texto fuerza un salto de pagina, y
        # multi_cell() ahi adentro deja la posicion x del cursor en un estado
        # que rompe el multi_cell interrumpido al retomar en la pagina nueva
        # (fpdf.errors.FPDFException: "Not enough horizontal space...").
        # cell() no tiene ese efecto secundario.
        self.set_y(-15)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 4, SYNTHETIC_NOTICE, align="C")


def build_pdf(title: str, body: str, output_path: Path) -> None:
    pdf = SyntheticManualPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # Leyenda tambien bien visible al principio de la primera pagina, no solo
    # en el footer -- para que sea imposible de pasar por alto al abrir el PDF.
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(180, 0, 0)
    pdf.multi_cell(0, 6, SYNTHETIC_NOTICE, align="C")
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)

    # fpdf2's core fonts (Helvetica) solo soportan latin-1: el contenido lo
    # generamos en ingles, pero por las dudas reemplazamos cualquier caracter
    # fuera de ese rango en vez de romper la generacion del PDF.
    safe_body = body.encode("latin-1", errors="replace").decode("latin-1")
    for line in safe_body.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue
        # Heuristica simple para encabezados de seccion: linea corta en
        # mayusculas (el system prompt le pide al modelo que las escriba asi).
        if stripped.isupper() and len(stripped) < 60:
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 7, stripped)
            pdf.set_font("Helvetica", "", 11)
        else:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, stripped)

    pdf.output(str(output_path))


def main() -> None:
    load_dotenv()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for doc in DOCUMENTS:
        output_path = OUTPUT_DIR / doc["filename"]
        if output_path.exists():
            print(f"Ya existe, salteo: {output_path}")
            continue
        print(f"Generando contenido para {doc['filename']}...")
        content = generate_content(doc["user_prompt"])
        build_pdf(doc["title"], content, output_path)
        print(f"  -> {output_path}")

    print(f"Listo: {len(DOCUMENTS)} PDFs sinteticos en {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
