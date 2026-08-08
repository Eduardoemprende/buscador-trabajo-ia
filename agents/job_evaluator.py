"""
AGENTE 3: Evaluador de Ofertas
-------------------------------
Compara cada oferta contra el perfil del candidato.
Asigna un puntaje de fit (0-100) y explica por qué califica o no.
"""

import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def evaluar_oferta(perfil: dict, oferta: dict, requisitos_no_cumple: list[str] = None) -> dict:
    """
    Evalúa qué tan bien califica un candidato para una oferta.

    Parámetros:
    - perfil: dict del candidato (salida del cv_extractor)
    - oferta: dict de la oferta (salida del job_scraper)
    - requisitos_no_cumple: lista de requisitos que el usuario sabe que no cumple

    Retorna:
    {
        "puntaje": int (0-100),
        "califica": bool (True si puntaje >= 60),
        "fortalezas": [str],
        "brechas": [str],
        "explicacion": str,
        "recomendacion": str
    }
    """
    no_cumple_texto = ""
    if requisitos_no_cumple:
        no_cumple_texto = f"\nEl candidato ya sabe que NO cumple con: {', '.join(requisitos_no_cumple)}"

    prompt = f"""Eres un experto en recursos humanos. Evalúa qué tan bien califica este candidato para la oferta de trabajo.

PERFIL DEL CANDIDATO:
- Nombre: {perfil.get('nombre', 'N/A')}
- Años de experiencia: {perfil.get('años_experiencia', 0)}
- Cargo actual: {perfil.get('cargo_actual', 'N/A')}
- Skills: {', '.join(perfil.get('skills', []))}
- Industrias: {', '.join(perfil.get('industrias', []))}
- Ubicación: {perfil.get('ubicacion', 'N/A')}
- Idiomas: {', '.join(perfil.get('idiomas', []))}
- Educación: {perfil.get('nivel_educacion', 'N/A')}
- Resumen: {perfil.get('resumen', 'N/A')}
{no_cumple_texto}

OFERTA DE TRABAJO:
- Título: {oferta.get('titulo', 'N/A')}
- Empresa: {oferta.get('empresa', 'N/A')}
- Modalidad: {oferta.get('modalidad', 'N/A')}
- Ubicación: {oferta.get('ubicacion', 'N/A')}
- Descripción/Requisitos: {oferta.get('requisitos', oferta.get('descripcion', 'N/A'))[:2500]}

Evalúa y devuelve SOLO este JSON, sin explicaciones adicionales:
{{
    "puntaje": numero del 0 al 100,
    "califica": true o false (true si puntaje >= 40),
    "fortalezas": ["razón 1 por qué califica", "razón 2"],
    "brechas": ["cosa que le falta 1", "cosa que le falta 2"],
    "explicacion": "evaluación en 2-3 oraciones directas",
    "recomendacion": "consejo específico para esta postulación en 1 oración"
}}"""

    respuesta = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Usamos Haiku para velocidad (evalúa muchas ofertas)
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = respuesta.content[0].text.strip()

    # Limpiar bloques markdown
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    resultado = json.loads(texto.strip())

    # Agregar datos de la oferta al resultado para tener todo junto
    resultado["oferta"] = {
        "titulo": oferta.get("titulo"),
        "empresa": oferta.get("empresa"),
        "modalidad": oferta.get("modalidad"),
        "ubicacion": oferta.get("ubicacion"),
        "url": oferta.get("url"),
        "fuente": oferta.get("fuente"),
    }

    return resultado


def evaluar_todas(perfil: dict, ofertas: list[dict], requisitos_no_cumple: list[str] = None) -> list[dict]:
    """
    Evalúa todas las ofertas y devuelve solo las que califican,
    ordenadas de mayor a menor puntaje.

    Parámetros:
    - perfil: dict del candidato
    - ofertas: lista de ofertas del job_scraper
    - requisitos_no_cumple: requisitos que el usuario sabe que no cumple

    Retorna lista de evaluaciones filtradas y rankeadas.
    """
    resultados = []
    total = len(ofertas)

    for i, oferta in enumerate(ofertas, 1):
        print(f"[Evaluador] Evaluando {i}/{total}: {oferta.get('titulo', 'N/A')}...")
        try:
            evaluacion = evaluar_oferta(perfil, oferta, requisitos_no_cumple)
            resultados.append(evaluacion)
        except Exception as e:
            print(f"  → Error evaluando oferta: {e}")
            continue

    # Filtrar: solo las que califican (puntaje >= 45)
    califican = [r for r in resultados if r.get("puntaje", 0) >= 40]

    # Ordenar de mayor a menor puntaje
    califican.sort(key=lambda x: x.get("puntaje", 0), reverse=True)

    print(f"\n[Evaluador] {len(califican)} de {total} ofertas califican.")
    return califican


# ─────────────────────────────────────────
# Prueba rápida desde terminal
# ─────────────────────────────────────────
if __name__ == "__main__":
    # Perfil de prueba
    perfil_test = {
        "nombre": "Eduardo Ruiz",
        "años_experiencia": 8,
        "cargo_actual": "Especialista en Marketing Digital",
        "skills": ["Marketing Digital", "SEO", "Google Ads", "Meta Ads", "Estrategia de contenido"],
        "industrias": ["Marketing", "E-commerce", "Consultoría"],
        "ubicacion": "Santiago, Chile",
        "idiomas": ["Español - nativo", "Inglés - intermedio"],
        "nivel_educacion": "Universitario - Ingeniería Comercial",
        "resumen": "Especialista en marketing digital con 8 años de experiencia en estrategia y ejecución de campañas."
    }

    oferta_test = {
        "titulo": "Marketing Manager",
        "empresa": "Empresa Tech",
        "modalidad": "Remoto",
        "ubicacion": "Santiago, Chile",
        "requisitos": "Buscamos Marketing Manager con experiencia en digital, Google Ads y Meta. Inglés intermedio deseable.",
        "url": "https://ejemplo.com/oferta/1",
        "fuente": "Get on Board"
    }

    resultado = evaluar_oferta(perfil_test, oferta_test)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
