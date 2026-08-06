"""
AGENTE 2: Buscador de Ofertas
-----------------------------
Fuentes activas (confirmadas desde Streamlit Cloud):
  - Chiletrabajos.cl  ✅
  - Computrabajo.cl   (intentando)
  - Laborum.cl        (intentando)

Fuentes descartadas (bloqueadas desde cloud):
  - Get on Board (404), Trabajando.cl (404), Indeed (403), Adzuna (bloqueado)
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ─────────────────────────────────────────
# CHILETRABAJOS.CL ✅ confirmado funciona
# ─────────────────────────────────────────

def buscar_chiletrabajos(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "+")
    query_dash = cargo.replace(" ", "-").lower()

    # Probar primero URL de categoría (más relevante), luego keyword
    urls = [
        f"https://www.chiletrabajos.cl/trabajos/{query_dash}",
        f"https://www.chiletrabajos.cl/encuentra-un-empleo?keyword={query}",
    ]

    resp = None
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12, verify=False, allow_redirects=True)
            print(f"[Chiletrabajos] {url} → {r.status_code}")
            if r.status_code == 200:
                resp = r
                break
        except Exception as e:
            print(f"[Chiletrabajos] Error: {e}")

    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tarjetas = soup.select("div.job-item")
    print(f"[Chiletrabajos] {len(tarjetas)} tarjetas")

    for tarjeta in tarjetas[:25]:
        titulo_el = tarjeta.select_one("h2.title a, h2 a.font-weight-bold, h2 a")
        if not titulo_el:
            continue
        titulo = titulo_el.get_text(strip=True)
        href = titulo_el.get("href", "")
        if not titulo or len(titulo) < 5:
            continue

        empresa = "Ver en oferta"
        meta_els = tarjeta.select("h3.meta")
        if meta_els:
            texto_meta = meta_els[0].get_text(separator=" ", strip=True)
            empresa = texto_meta.split(",")[0].strip() if "," in texto_meta else texto_meta

        ciudad_el = tarjeta.select_one("h3.meta a[href*='/ciudad/']")
        ubicacion = ciudad_el.get_text(strip=True) if ciudad_el else "Chile"

        texto = tarjeta.get_text(separator=" ", strip=True)
        es_remoto = any(w in texto.lower() for w in ["remoto", "remote", "teletrabajo"])

        ofertas.append({
            "fuente": "Chiletrabajos",
            "titulo": titulo[:100],
            "empresa": empresa[:80],
            "ubicacion": ubicacion,
            "modalidad": "Remoto" if es_remoto else "No especificada",
            "descripcion": texto[:500],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto,
        })

    print(f"[Chiletrabajos] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# COMPUTRABAJO.CL
# ─────────────────────────────────────────

def buscar_computrabajo(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query_dash = cargo.replace(" ", "-").lower()
    query_plus = cargo.replace(" ", "+")

    urls = [
        f"https://www.computrabajo.cl/trabajo-de-{query_dash}",
        f"https://www.computrabajo.cl/ofertas-de-trabajo/?q={query_plus}",
        f"https://www.computrabajo.cl/empleos-en-chile-de-{query_dash}",
        f"https://www.computrabajo.cl/ofertas-de-trabajo/oferta-de-trabajo-de-{query_dash}",
    ]

    resp = None
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12, verify=False, allow_redirects=True)
            print(f"[Computrabajo] {url} → {r.status_code}")
            if r.status_code == 200 and len(r.text) > 5000:
                resp = r
                break
        except Exception as e:
            print(f"[Computrabajo] Error: {e}")

    if not resp:
        print("[Computrabajo] Sin URL válida")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tarjetas = soup.select("article.box_offer, article[data-r], .offerItem, article")

    for tarjeta in tarjetas[:15]:
        titulo_el = tarjeta.select_one("h2, h3, .title_offer, [class*='title']")
        link_el = tarjeta.select_one("a[href]")
        empresa_el = tarjeta.select_one(".name_company, [class*='company'], [class*='empresa']")
        ubicacion_el = tarjeta.select_one(".city, [class*='location'], [class*='ciudad']")
        if not titulo_el:
            continue
        titulo = titulo_el.get_text(strip=True)
        if not titulo or len(titulo) < 5:
            continue
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.computrabajo.cl" + href
        texto = tarjeta.get_text(separator=" ", strip=True)
        ofertas.append({
            "fuente": "Computrabajo",
            "titulo": titulo[:100],
            "empresa": empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta",
            "ubicacion": ubicacion_el.get_text(strip=True) if ubicacion_el else "Chile",
            "modalidad": "Remoto" if "remoto" in texto.lower() else "No especificada",
            "descripcion": texto[:500],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto,
        })

    print(f"[Computrabajo] {len(ofertas)} ofertas")
    return ofertas


# ─────────────────────────────────────────
# LABORUM.CL
# ─────────────────────────────────────────

def buscar_laborum(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "-").lower()
    query_plus = cargo.replace(" ", "%20")

    urls = [
        f"https://www.laborum.cl/empleos-busqueda-{query}.html",
        f"https://www.laborum.cl/empleos?q={query_plus}",
    ]

    resp = None
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12, verify=False, allow_redirects=True)
            print(f"[Laborum] {url} → {r.status_code}")
            if r.status_code == 200 and len(r.text) > 3000:
                resp = r
                break
        except Exception as e:
            print(f"[Laborum] Error: {e}")

    if not resp:
        print("[Laborum] Sin URL válida")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tarjetas = soup.select("article.aviso, .aviso, [class*='aviso'], [class*='job-card'], li.offer")

    for tarjeta in tarjetas[:15]:
        titulo_el = tarjeta.select_one("h2, h3, .title, [class*='title'], a[href*='/empleos/']")
        link_el = tarjeta.select_one("a[href*='/empleos/'], a[href*='/aviso/'], a[href]")
        empresa_el = tarjeta.select_one("[class*='empresa'], [class*='company'], .empresa")
        if not titulo_el:
            continue
        titulo = titulo_el.get_text(strip=True)
        if not titulo or len(titulo) < 5:
            continue
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.laborum.cl" + href
        texto = tarjeta.get_text(separator=" ", strip=True)
        ofertas.append({
            "fuente": "Laborum",
            "titulo": titulo[:100],
            "empresa": empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta",
            "ubicacion": "Chile",
            "modalidad": "Remoto" if "remoto" in texto.lower() else "No especificada",
            "descripcion": texto[:500],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto,
        })

    print(f"[Laborum] {len(ofertas)} ofertas")
    return ofertas


# ─────────────────────────────────────────
# REMOTIVE.COM — API gratuita, sin key, empleos remotos
# ─────────────────────────────────────────

REMOTIVE_CATEGORIAS = {
    "marketing": "marketing",
    "diseño": "design",
    "data": "data",
    "producto": "product",
    "ingenieria": "software-dev",
    "ventas": "sales",
    "rrhh": "hr",
    "finanzas": "finance",
    "default": "marketing",
}

def buscar_remotive(cargo: str) -> list[dict]:
    cargo_lower = cargo.lower()
    categoria = "marketing"
    for key, val in REMOTIVE_CATEGORIAS.items():
        if key in cargo_lower:
            categoria = val
            break

    url = f"https://remotive.com/api/remote-jobs?category={categoria}&limit=30"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        print(f"[Remotive] Status: {resp.status_code}")
        if resp.status_code != 200:
            return []
        jobs = resp.json().get("jobs", [])
        print(f"[Remotive] {len(jobs)} ofertas")
        ofertas = []
        for job in jobs:
            desc = BeautifulSoup(job.get("description", ""), "html.parser").get_text(separator=" ", strip=True)[:600]
            ofertas.append({
                "fuente": "Remotive (Remoto)",
                "titulo": job.get("title", "")[:100],
                "empresa": job.get("company_name", "Ver en oferta"),
                "ubicacion": job.get("candidate_required_location", "Remoto / Global"),
                "modalidad": "Remoto",
                "descripcion": desc,
                "url": job.get("url", ""),
                "skills_requeridos": job.get("tags", []),
                "requisitos": desc,
            })
        return ofertas
    except Exception as e:
        print(f"[Remotive] Error: {e}")
        return []


# ─────────────────────────────────────────
# JOBICY.COM — API gratuita, sin key, empleos remotos
# ─────────────────────────────────────────

def buscar_jobicy(cargo: str) -> list[dict]:
    # Jobicy tiene categorías fijas
    cargo_lower = cargo.lower()
    tag = "marketing"
    if "diseño" in cargo_lower or "design" in cargo_lower:
        tag = "design"
    elif "data" in cargo_lower:
        tag = "data"
    elif "software" in cargo_lower or "developer" in cargo_lower:
        tag = "engineering"

    url = f"https://jobicy.com/api/v2/remote-jobs?tag={tag}&count=20"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        print(f"[Jobicy] Status: {resp.status_code}")
        if resp.status_code != 200:
            return []
        jobs = resp.json().get("jobs", [])
        print(f"[Jobicy] {len(jobs)} ofertas")
        ofertas = []
        for job in jobs:
            desc = BeautifulSoup(job.get("jobDescription", ""), "html.parser").get_text(separator=" ", strip=True)[:600]
            ofertas.append({
                "fuente": "Jobicy (Remoto)",
                "titulo": job.get("jobTitle", "")[:100],
                "empresa": job.get("companyName", "Ver en oferta"),
                "ubicacion": job.get("jobGeo", "Remoto / Global"),
                "modalidad": "Remoto",
                "descripcion": desc,
                "url": job.get("url", ""),
                "skills_requeridos": job.get("jobIndustry", []),
                "requisitos": desc,
            })
        return ofertas
    except Exception as e:
        print(f"[Jobicy] Error: {e}")
        return []


# ─────────────────────────────────────────
# PRE-FILTRO DE RELEVANCIA
# ─────────────────────────────────────────

KEYWORDS_RELEVANCIA = {
    "marketing": ["marketing", "digital", "contenido", "community manager", "seo", "sem",
                  "comunicacion", "publicidad", "growth", "redes sociales", "campañ", "brand",
                  "ecommerce", "crm", "email", "inbound", "performance", "pauta"],
    "ventas": ["venta", "vendedor", "comercial", "sales", "ejecutivo comercial", "prospect"],
    "diseño": ["diseño", "design", "ux", "ui", "grafico", "creativo", "visual", "multimedia"],
    "data": ["data", "analista", "analytics", "business intelligence", "sql", "machine learning"],
    "producto": ["producto", "product manager", "product owner", "roadmap"],
    "rrhh": ["recursos humanos", "reclutamiento", "talent", "people", "gestión de personas"],
    "finanzas": ["finanz", "contab", "contador", "control de gestion", "tesorero"],
    "enfermeria": ["enferm", "salud", "clinica", "hospital", "paciente", "medic", "nurse"],
    "ingenieria": ["ingeniero", "ingenieria", "software", "developer", "programador", "devops"],
    "administracion": ["administraci", "admin", "secretaria", "asistente", "back office"],
}

def _oferta_es_relevante(oferta: dict, cargo: str) -> bool:
    titulo = oferta.get("titulo", "").lower()
    descripcion = oferta.get("descripcion", "").lower()
    texto = titulo + " " + descripcion

    # Palabras del cargo en el título (más estricto)
    palabras_cargo = [p for p in cargo.lower().split() if len(p) > 3]
    for palabra in palabras_cargo:
        if palabra in titulo:
            return True

    # Keywords del área en título o descripción
    cargo_lower = cargo.lower()
    keywords = []
    for key, words in KEYWORDS_RELEVANCIA.items():
        if key in cargo_lower:
            keywords = words
            break

    if not keywords:
        keywords = palabras_cargo

    return any(kw in texto for kw in keywords)


# ─────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────

def buscar_ofertas(cargo: str, modalidad: str = None, ciudad: str = None, max_resultados: int = 30) -> list[dict]:
    if not cargo or cargo.strip() == "":
        cargo = "marketing"

    print(f"\n[Buscador] '{cargo}' | modalidad={modalidad} | ciudad={ciudad}")

    todas = []
    todas.extend(buscar_chiletrabajos(cargo, ciudad))
    todas.extend(buscar_computrabajo(cargo, ciudad))
    todas.extend(buscar_laborum(cargo, ciudad))
    todas.extend(buscar_remotive(cargo))
    todas.extend(buscar_jobicy(cargo))

    # Deduplicar por URL
    vistas = set()
    unicas = []
    for o in todas:
        key = o.get("url") or o.get("titulo", "")
        if key and key not in vistas:
            vistas.add(key)
            unicas.append(o)

    # Filtro de modalidad
    if modalidad == "remote":
        unicas = [o for o in unicas if o.get("modalidad") == "Remoto"]

    # Pre-filtro de relevancia
    relevantes = [o for o in unicas if _oferta_es_relevante(o, cargo)]
    print(f"[Buscador] {len(unicas)} únicas → {len(relevantes)} relevantes para '{cargo}'")

    return relevantes[:max_resultados]


if __name__ == "__main__":
    resultados = buscar_ofertas("marketing digital")
    print(f"\nTotal: {len(resultados)} ofertas\n")
    for i, o in enumerate(resultados, 1):
        print(f"{i}. {o['titulo']} — {o['empresa']} ({o['fuente']})")
        print(f"   {o['url']}\n")
