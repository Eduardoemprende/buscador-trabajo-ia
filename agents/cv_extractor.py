"""
AGENTE 1: Extractor de CV
------------------------
Recibe un PDF de CV y devuelve un perfil profesional estructurado.
Usa Claude para interpretar el texto y extraer los datos clave.
"""

import fitz  # pymupdf
import anthropic
import json
import os
from dotenv import load_dotenv
from pathlib import Path

# Busca el .env en la carpeta raíz del proyecto (un nivel arriba de /agents/)
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extraer_texto_pdf(ruta_pdf: str) -> str:
    """Lee el PDF y devuelve todo el texto plano."""
    doc = fitz.open(ruta_pdf)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    doc.close()
    return texto


def extraer_perfil(ruta_pdf: str) -> dict:
    """
    Toma la ruta de un PDF y devuelve el perfil del candidato.

    Retorna un dict con:
    - nombre
    - años_experiencia
    - cargo_actual
    - skills (lista)
    - industrias (lista)
    - ubicacion
    - idiomas (lista)
    - nivel_educacion
    - resumen
    """
    texto_cv = extraer_texto_pdf(ruta_pdf)

    respuesta = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Analiza este CV y extrae el perfil profesional en formato JSON.

CV:
{texto_cv}

Devuelve SOLO el JSON, sin explicaciones, con esta estructura exacta:
{{
    "nombre": "nombre completo",
    "años_experiencia": numero entero,
    "cargo_actual": "último cargo o cargo más relevante",
    "skills": ["skill1", "skill2"],
    "industrias": ["industria1", "industria2"],
    "ubicacion": "ciudad, país",
    "idiomas": ["Español - nativo", "Inglés - intermedio"],
    "nivel_educacion": "Universitario / Magíster / etc",
    "resumen": "resumen profesional en 2-3 oraciones"
}}"""
            }
        ]
    )

    texto = respuesta.content[0].text.strip()

    # Limpiar bloques markdown si Claude los agrega
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    return json.loads(texto.strip())


def extraer_perfil_desde_bytes(pdf_bytes: bytes) -> dict:
    """
    Versión para Streamlit: recibe bytes del PDF en vez de ruta.
    """
    ruta_temp = "/tmp/cv_temporal.pdf"
    with open(ruta_temp, "wb") as f:
        f.write(pdf_bytes)
    return extraer_perfil(ruta_temp)


# --- Prueba rápida desde terminal ---
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python cv_extractor.py ruta/a/tu_cv.pdf")
    else:
        perfil = extraer_perfil(sys.argv[1])
        print(json.dumps(perfil, ensure_ascii=False, indent=2))
