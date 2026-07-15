# PENDIENTE — Corpus RAG: Agua Potable y Saneamiento (Instrumentación de Campo)

## Contexto

Tópico elegido para reemplazar el corpus mínimo actual (`docs/langgraph-intro.txt`,
16 chunks) por uno real que justifique portar el framework de evaluación de M4
(ground truth, Hit Rate, MRR, tuning de `k` en RRF).

**Caso de uso:** asistente de soporte técnico para operadores y técnicos de
sistemas municipales de agua potable y saneamiento — plantas potabilizadoras,
redes de distribución y plantas de tratamiento cloacal — que consultan
instrumentación de campo (transmisores de presión, caudal y temperatura)
durante controles diarios, mantenimiento y dosificación química.

**Por qué esta industria (y no un dominio genérico):**
- Experiencia real, no elegida por conveniencia: 2 años como consultor técnico
  en agua potable — plantas potabilizadoras, controles diarios del servicio,
  redes de distribución — y tratamiento cloacal para la Municipalidad de
  Monte Vera. En una entrevista se responde en primera persona, con casos
  concretos, no "elegí este tema porque encajaba".
- Encaja con el nicho que ya tenías anotado como diferenciador propio:
  infraestructura crítica.
- Es un dominio menos saturado que los demos típicos de RAG industrial
  (oil & gas, planta química genérica).

**Dónde encaja cada instrumento dentro de este caso de uso:**
- **Presión** — monitoreo de red de distribución, presión de descarga en
  estaciones de bombeo, presión diferencial en filtros de la potabilizadora
  (indica cuándo hace falta retrolavado).
- **Caudal** — caudal de ingreso/salida de planta, dosificación de cloro y
  coagulante/floculante, caudal en red de distribución, caudal de efluente
  cloacal hacia el cuerpo receptor.
- **Temperatura** — en tratamiento cloacal incide en la eficiencia del proceso
  biológico (lodos activados, digestión); en bombeo se usa para proteger
  motores (alerta de sobrecalentamiento) — mantenimiento predictivo.
- Multi-fabricante (Emerson/Rosemount, Siemens Sitrans, Endress+Hauser) fuerza
  metadata filtering por fabricante/modelo — reusa una skill real de tu
  trabajo en Valkimia (GEAI: "búsqueda guiada por metadata").
- Caso de uso de soporte natural para el agente ya diseñado en el ROADMAP:
  preguntas de calibración, códigos de error, rangos de medición → si el
  agente no resuelve, dispara `create_ticket(summary, category)`.

---

## Ejemplos de consultas (para diseñar ground truth y system prompt)

- "¿Cuál es el rango de calibración del transmisor de presión en la estación
  de bombeo de red X?"
- "Código de error en un caudalímetro magnético durante la dosificación de
  cloro — ¿qué significa y cómo se resuelve?"
- "¿Cómo se hace el ajuste de cero de un transmisor de presión después de
  mantenimiento en un filtro de la potabilizadora?"
- "¿Qué temperatura de proceso indica una anomalía en el tratamiento
  biológico cloacal?"
- "¿Qué certificación necesita el instrumento para instalarse en una zona
  con riesgo de atmósfera explosiva (Ex)?"

## Categorías sugeridas para `create_ticket`

- `falla_instrumento_campo` — el instrumento no responde según manual,
  requiere intervención física.
- `anomalia_proceso_biologico` — lectura fuera de rango en tratamiento
  cloacal, posible impacto en eficiencia del tratamiento.
- `mantenimiento_bombeo` — alerta de temperatura/vibración en motor de
  bombeo, mantenimiento predictivo.
- `consulta_fuera_de_manual` — la pregunta no está cubierta por la
  documentación ingerida, requiere escalamiento a soporte humano.

---

## Checklist de descarga

Marcar `[x]` a medida que se descargan. Todos los links son de dominio oficial
del fabricante (no re-hosts de terceros tipo ManualsLib/Scribd).

### Emerson / Rosemount (presión y caudal — red de distribución, bombeo)

**Nota (2026-07-14):** los links originales de esta sección devolvían HTTP 400/404
(URLs con codificación de caracteres corrupta — `%EF%BF%BD` en vez de tildes reales,
`%F3` en vez de `%C3%B3`). Verificados uno por uno con `curl`; reemplazados por
versiones en inglés confirmadas con HTTP 200 (las equivalentes en español casi todas
dan 404 en el dominio de Emerson — el manual de 2051 sí tiene versión ES que funciona,
enlazada más abajo).

- [x] Rosemount 2051 — Reference Manual (HART, 4-20 mA) — EN, confirmado 200
      https://www.emerson.com/documents/automation/manual-rosemount-2051-pressure-transmitter-en-89532.pdf
      → `docs/pdfs/emerson_rosemount-2051_manual_en.pdf`
- [x] Rosemount 2051 / 2051CF — Quick Start Guide — EN, confirmado 200
      https://www.emerson.com/documents/automation/quick-start-guide-rosemount-2051-pressure-transmitter-2051cf-series-flowmeter-4-20-ma-hart-1-5-vdc-low-power-hart-protocol-rev-5-7-en-193436.pdf
      → `docs/pdfs/emerson_rosemount-2051_quickstart_en.pdf`
- [x] Rosemount 3051 — Manual (HART) — EN, confirmado 200
      https://www.emerson.com/documents/automation/manual-rosemount-3051-pressure-transmitter-en-89452.pdf
      → `docs/pdfs/emerson_rosemount-3051_manual_en.pdf`
- [x] Rosemount 3051 / 3051CF — Quick Start Guide — EN, confirmado 200
      https://www.emerson.com/documents/automation/quick-start-guide-rosemount-3051-pressure-transmitter-3051cf-series-flow-meter-en-89454.pdf
      → `docs/pdfs/emerson_rosemount-3051_quickstart_en.pdf`
- [x] Rosemount 8732EM — Caudalímetro magnético, Reference Manual (HART) — EN,
      confirmado 200 — típico en dosificación de planta y medición de red
      https://www.emerson.com/documents/automation/reference-manual-rosemount-8732em-transmitter-hart-protocol-reference-manual-en-78020.pdf
      → `docs/pdfs/emerson_rosemount-8732em_manual_en.pdf`

No se descargó el bonus en español del 3051 (redundante con el manual EN ya
descargado; no aporta volumen nuevo al corpus).

### Siemens Sitrans (presión — filtros y estaciones de bombeo)

- [x] SITRANS P300 — Instrucciones de servicio (ES)
      https://cache.industry.siemens.com/dl/files/531/22145531/att_57249/v1/A5E00359576-02es_P300HART.pdf
      → `docs/pdfs/siemens_sitrans-p300_manual_es.pdf`
- [x] SITRANS P DS III / P410 con HART — Instrucciones de servicio (ES)
      https://cache.industry.siemens.com/dl/files/485/109477485/att_849208/v1/A5E00053220-10es_DS3_HART_Ex_OI_es-ES.pdf
      → `docs/pdfs/siemens_sitrans-p-dsIII-p410_manual_es.pdf`
- [x] SITRANS P320 / P420 — Service Manual (EN)
      https://cache.industry.siemens.com/dl/files/247/109954247/att_1264010/v1/A5E44914141en_P320P420_SM_en-US.pdf
      → `docs/pdfs/siemens_sitrans-p320-p420_manual_en.pdf`
- [x] SITRANS P320 / P420 — Ficha sinopsis (ES)
      https://cache.industry.siemens.com/dl/files/052/109765052/att_1165332/v1/sitransp_p320_p420_fi01_es.pdf
      → `docs/pdfs/siemens_sitrans-p320-p420_datasheet_es.pdf`

### Endress+Hauser (temperatura y caudal — proceso biológico y bombeo)

- [x] iTEMP TMT36 — Operating Instructions (temperatura, EN — aplicable a
      protección de bombeo y proceso biológico cloacal)
      https://bdih-download.endress.com/files/DLA/005056A500261EDEB3FEA42E979B6BFF/BA02289TEN_0123-00.pdf
      → `docs/pdfs/endresshauser_itemp-tmt36_manual_en.pdf`
- [x] Proline Promag 55 — Operating Instructions (caudalímetro, EN —
      dosificación y medición de efluente)
      https://portal.endress.com/wa001/dla/5000022/8068/000/02/BA119DEN_1009.pdf
      → `docs/pdfs/endresshauser_promag-55_manual_en.pdf`
- [ ] Ampliar vía Downloads / Device Viewer oficial (buscar por código de
      producto, sumar 2-3 modelos más de presión/caudal para balancear con
      Emerson y Siemens) — no descargado, opcional si el ground truth queda corto:
      https://www.us.endress.com/en/downloads

**Total descargado y verificado (2026-07-14): 11 PDFs, 3 fabricantes, 3 tipos de
instrumento, 5 Emerson + 4 Siemens + 2 Endress+Hauser.** Los 11 son `%PDF` válidos
(verificado con `curl -I` para los links y firma de archivo local), en
`docs/pdfs/` (agregada a `.gitignore` — no se comitean). Suficiente para un primer
corpus real; el ítem de Endress+Hauser "Ampliar" queda opcional si el ground truth
generado en el paso 4 queda corto en volumen (menos de ~150 preguntas).

---

## Compliance — qué sí y qué no

Los tres fabricantes (Emerson, Siemens, Endress+Hauser) publican esta
documentación como material de referencia para clientes/ingenieros — pero la
mantienen con copyright. Emerson lo deja explícito en sus Términos de Uso:
contenido protegido, prohibida la reproducción/redistribución sin
consentimiento escrito. Es el lenguaje estándar de cualquier documentación
técnica corporativa (Siemens y E+H tienen cláusulas equivalentes).

**Permitido (esto es):**
- Descargar los PDFs y usarlos para desarrollo/demo — ingesta local o en tu
  Supabase, generación de embeddings, indexado. Es el uso previsto de material
  de soporte técnico.
- Que el agente cite fragmentos con fuente al responder (grounding) — análogo
  a cómo un buscador muestra snippets.

**Evitar:**
- Comitear los PDFs originales (o el texto completo extraído) al repo público
  de GitHub — eso sí es redistribución del material con copyright.
- Crawlear en bloque todo el catálogo de un fabricante de forma automatizada
  y agresiva — para ~12-20 archivos puntuales no hace falta, y evita problemas
  de rate-limiting/bot-detection.

**Mitigación en el repo:**
1. Carpeta fuente de PDFs (ej. `data/pdfs/` o similar) va en `.gitignore`.
2. El repo público solo versiona el script de ingesta, no los archivos fuente.
3. Este archivo (o su contenido resumido) va al README como nota de sourcing:
   de dónde salen los documentos, con links a las páginas oficiales.
4. Preferir siempre el dominio oficial del fabricante sobre re-hosts de
   terceros (ManualsLib, Scribd, etc.) — cadena de custodia más limpia.

---

## Próximos pasos

1. ~~Descargar los PDFs del checklist a la carpeta fuente (gitignored).~~ ✅
   Hecho 2026-07-14 — 11 PDFs en `docs/pdfs/`, renombrados por fabricante/modelo/
   tipo/idioma, `docs/pdfs/` agregada a `.gitignore`.
2. Extender `scripts/ingest.py` con soporte real de PDFs (hoy solo lee `.txt` —
   ver pendiente en ROADMAP) para chunking + embeddings + insert en pgvector.
   **Siguiente paso concreto.**
3. Actualizar el system prompt del agente y el README con el caso de uso:
   soporte técnico para operadores de agua potable y saneamiento (incluir
   la experiencia real de 2 años como consultor técnico, plantas
   potabilizadoras + redes + tratamiento cloacal Municipalidad de Monte Vera).
4. Generar ground truth con LLM + structured output (patrón HW4: modelo
   Pydantic `Questions`, 5 preguntas por chunk/documento, etiquetadas por
   `source`/fabricante/modelo), usando los ejemplos de consulta de este
   documento como referencia de estilo/tono.
5. Portar `hit_rate` / `mrr` / `evaluate()` a `evals/retrieval_metrics.py`.
6. Correr el barrido de `k` de RRF contra el ground truth real y decidir si
   el `k=60` default de `src/ingestion.py:104` se ajusta.
