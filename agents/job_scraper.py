"""
AGENTE 2: Buscador de Ofertas
-----------------------------
Busca ofertas de trabajo usando la API de Adzuna.
Devuelve una lista estandarizada de ofertas listas para evaluar.
"""

import requests
import os
from pathlib import Path
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cargar variables de entorno
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def buscar_adzuna(cargo: str, modalidad: str = None, ciudad: str = None, max_resultados: int = 20) -> list[dict]:
    """
    Busca ofertas en Adzuna API.
    Cubre Chile (cl) y opcionalmente otros países.
    """
    ofertas = []

    # Adzuna tiene cobertura limitada en Chile, también buscamos en Argentina y España
    paises = ["cl", "ar", "es"]

    for pais in paises:
        url = f"https://api.adzuna.com/v1/api/jobs/{pais}/search/1"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what": cargo,
            "results_per_page": max_resultados,
            "content-type": "application/json",
        }

        if ciudad:
            params["where"] = ciudad

        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("results", [])
                print(f"[Adzuna/{pais.upper()}] {len(jobs)} ofertas encontradas")

                for job in jobs:
                    # Detectar si es remoto
                    titulo = job.get("title", "")
                    descripcion = job.get("description", "")
                    es_remoto = any(word in (titulo + descripcion).lower() for word in ["remoto", "remote", "teletrabajo", "trabajo desde casa"])

                    if modalidad == "remote" and not es_remoto:
                        continue

                    ofertas.append({
                        "fuente": f"Adzuna ({pais.upper()})",
                        "titulo": titulo,
                        "empresa": job.get("company", {}).get("display_name", "No especificada"),
                        "ubicacion": job.get("location", {}).get("display_name", "No especificada"),
                        "modalidad": "Remoto" if es_remoto else "Presencial",
                        "descripcion": descripcion[:600],
                        "url": job.get("redirect_url", ""),
                        "skills_requeridos": [],
                        "requisitos": descripcion,
                        "salario_min": job.get("salary_min"),
                        "salario_max": job.get("salary_max"),
                    })
            else:
                print(f"[Adzuna/{pais.upper()}] Error {resp.status_code}")
        except Exception as e:
            print(f"[Adzuna/{pais.upper()}] Error: {e}")

    return ofertas


def buscar_ofertas(cargo: str, modalidad: str = None, ciudad: str = None, max_resultados: int = 30) -> list[dict]:
    """
    Función principal — busca ofertas en todas las fuentes disponibles.
    """
    if not cargo or cargo.strip() == "":
        cargo = "marketing"

    print(f"[Buscador] Buscando '{cargo}' | modalidad: {modalidad} | ciudad: {ciudad}")

    todas = buscar_adzuna(cargo, modalidad, ciudad, max_resultados)

    # Eliminar duplicados por URL
    vistas = set()
    unicas = []
    for o in todas:
        key = o.get("url") or o.get("titulo", "")
        if key and key not in vistas:
            vistas.add(key)
            unicas.append(o)

    print(f"[Buscador] Total: {len(unicas)} ofertas únicas")
    return unicas[:max_resultados]


if __name__ == "__main__":
    resultados = buscar_ofertas("marketing digital")
    print(f"\nTotal: {len(resultados)} ofertas\n")
    for i, o in enumerate(resultados, 1):
        print(f"{i}. {o['titulo']} — {o['empresa']} ({o['ubicacion']})")
        print(f"   {o['url']}\n")
