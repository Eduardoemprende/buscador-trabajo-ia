"""
AGENTE 2: Buscador de Ofertas
-----------------------------
Busca ofertas en múltiples portales: Adzuna, Trabajando.com, Chiletrabajos, Computrabajo.
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
# GET ON BOARD (getonbrd.com)
# ─────────────────────────────────────────

# Mapa de cargo -> categorías relevantes en Get on Board
GETONBRD_CATEGORIAS = {
    "marketing": ["marketing-y-comunicacion", "gestion-y-empresa"],
    "marketing digital": ["marketing-y-comunicacion"],
    "diseño": ["diseno-ux-ui"],
    "diseño ux": ["diseno-ux-ui"],
    "ventas": ["gestion-y-empresa", "marketing-y-comunicacion"],
    "business development": ["gestion-y-empresa"],
    "producto": ["producto", "gestion-y-empresa"],
    "data": ["datos-big-data-business-intelligence"],
    "programacion": ["programacion"],
    "default": ["marketing-y-comunicacion", "gestion-y-empresa"],
}

def buscar_getonbrd(cargo: str, modalidad: str = None) -> list[dict]:
    """Busca ofertas en getonbrd.com via RSS (no requiere JavaScript)."""
    ofertas = []

    cargo_lower = cargo.lower()
    categorias = None
    for key in GETONBRD_CATEGORIAS:
        if key in cargo_lower:
            categorias = GETONBRD_CATEGORIAS[key]
            break
    if not categorias:
        categorias = GETONBRD_CATEGORIAS["default"]

    import xml.etree.ElementTree as ET

    for categoria in categorias:
        url = f"https://www.getonbrd.com/empleos/{categoria}.rss"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code != 200:
                print(f"[GetOnBrd RSS/{categoria}] Error {resp.status_code}")
                continue

            root = ET.fromstring(resp.content)
            ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
            items = root.findall(".//item")
            print(f"[GetOnBrd RSS/{categoria}] {len(items)} items en RSS")

            for item in items:
                titulo = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                descripcion = (item.findtext("description") or
                               item.findtext("content:encoded", namespaces=ns) or "").strip()

                if not titulo or not link:
                    continue

                # Detectar modalidad desde descripción
                desc_lower = descripcion.lower()
                if any(w in desc_lower for w in ["remoto", "remote", "full remote", "teletrabajo"]):
                    modalidad_oferta = "Remoto"
                elif any(w in desc_lower for w in ["híbrido", "hybrid"]):
                    modalidad_oferta = "Híbrido"
                else:
                    modalidad_oferta = "No especificada"

                if modalidad == "remote" and modalidad_oferta != "Remoto":
                    continue

                # Empresa suele estar en el título: "Cargo | Empresa"
                empresa = "Ver en oferta"
                if " | " in titulo:
                    partes = titulo.split(" | ")
                    titulo = partes[0].strip()
                    empresa = partes[1].strip() if len(partes) > 1 else empresa

                # Limpiar HTML de descripción
                desc_soup = BeautifulSoup(descripcion, "html.parser")
                texto_limpio = desc_soup.get_text(separator=" ", strip=True)[:600]

                ofertas.append({
                    "fuente": "Get on Board",
                    "titulo": titulo[:100],
                    "empresa": empresa,
                    "ubicacion": "Chile / Remoto",
                    "modalidad": modalidad_oferta,
                    "descripcion": texto_limpio,
                    "url": link,
                    "skills_requeridos": [],
                    "requisitos": texto_limpio,
                })

        except Exception as e:
            print(f"[GetOnBrd RSS/{categoria}] Error: {e}")

    print(f"[GetOnBrd RSS] Total: {len(ofertas)} ofertas")
    return ofertas[:20]




# ─────────────────────────────────────────
# TRABAJANDO.COM
# ─────────────────────────────────────────

def buscar_trabajando(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "+")
    url = f"https://www.trabajando.cl/empleos-{cargo.replace(' ', '-').lower()}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
        if resp.status_code != 200:
            # Fallback con búsqueda
            url2 = f"https://www.trabajando.cl/buscar-trabajo?q={query}"
            resp = requests.get(url2, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
            if resp.status_code != 200:
                print(f"[Trabajando.cl] Error {resp.status_code}")
                return []

        soup = BeautifulSoup(resp.text, "html.parser")

        tarjetas = soup.select("article, .job-item, .oferta, [class*='job'], [class*='oferta'], li[class*='item'], .aviso")

        if not tarjetas:
            # Intentar con __NEXT_DATA__ o JSON embebido
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                data = json.loads(next_data.string or "{}")
                jobs = _extraer_jobs_recursivo(data)
                for job in jobs[:10]:
                    ofertas.append(job)
                print(f"[Trabajando.com] {len(ofertas)} ofertas (JSON)")
                return ofertas

        for tarjeta in tarjetas[:10]:
            titulo_el = tarjeta.select_one("h2, h3, h4, [class*='title'], [class*='nombre']")
            link_el = tarjeta.select_one("a[href]")
            empresa_el = tarjeta.select_one("[class*='empresa'], [class*='company']")
            if not titulo_el or not link_el:
                continue
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.trabajando.com" + href
            ofertas.append({
                "fuente": "Trabajando.com",
                "titulo": titulo_el.get_text(strip=True),
                "empresa": empresa_el.get_text(strip=True) if empresa_el else "No especificada",
                "ubicacion": "Chile",
                "modalidad": "No especificada",
                "descripcion": tarjeta.get_text(strip=True)[:400],
                "url": href,
                "skills_requeridos": [],
                "requisitos": tarjeta.get_text(strip=True),
            })

        print(f"[Trabajando.com] {len(ofertas)} ofertas")
    except Exception as e:
        print(f"[Trabajando.com] Error: {e}")

    return ofertas


# ─────────────────────────────────────────
# CHILETRABAJOS.CL
# ─────────────────────────────────────────

def buscar_chiletrabajos(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "+")
    url = f"https://www.chiletrabajos.cl/encuentra-un-empleo?keyword={query}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
        print(f"[Chiletrabajos] Status: {resp.status_code}")
        if resp.status_code not in [200, 301, 302]:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        tarjetas = soup.select("div.job-item")
        print(f"[Chiletrabajos] {len(tarjetas)} tarjetas encontradas")

        for tarjeta in tarjetas[:20]:
            # Estructura confirmada: h2.title a tiene título y URL
            titulo_el = tarjeta.select_one("h2.title a, h2 a.font-weight-bold")
            if not titulo_el:
                continue

            titulo = titulo_el.get_text(strip=True)
            href = titulo_el.get("href", "")
            if not titulo or len(titulo) < 5:
                continue

            # Empresa: primer h3.meta (texto antes del link de ciudad)
            empresa = "Ver en oferta"
            meta_els = tarjeta.select("h3.meta")
            if meta_els:
                # Extraer solo el texto directo del h3, sin los links
                texto_meta = meta_els[0].get_text(separator=" ", strip=True)
                # Remover ciudad (suele estar al final separada por coma)
                empresa = texto_meta.split(",")[0].strip() if "," in texto_meta else texto_meta

            # Ciudad: link dentro de h3.meta que apunta a /ciudad/
            ciudad_el = tarjeta.select_one("h3.meta a[href*='/ciudad/']")
            ubicacion = ciudad_el.get_text(strip=True) if ciudad_el else "Chile"

            texto_completo = tarjeta.get_text(separator=" ", strip=True)
            es_remoto = any(w in texto_completo.lower() for w in ["remoto", "remote", "teletrabajo"])

            ofertas.append({
                "fuente": "Chiletrabajos",
                "titulo": titulo[:100],
                "empresa": empresa[:80],
                "ubicacion": ubicacion,
                "modalidad": "Remoto" if es_remoto else "No especificada",
                "descripcion": texto_completo[:400],
                "url": href,
                "skills_requeridos": [],
                "requisitos": texto_completo,
            })

        print(f"[Chiletrabajos] {len(ofertas)} ofertas extraídas")
    except Exception as e:
        print(f"[Chiletrabajos] Error: {e}")

    return ofertas


# ─────────────────────────────────────────
# COMPUTRABAJO.CL
# ─────────────────────────────────────────

def buscar_computrabajo(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "+")
    query_dash = cargo.replace(" ", "-").lower()

    # Probar varias URLs hasta encontrar una que devuelva 200
    urls_a_probar = [
        f"https://www.computrabajo.cl/trabajo-de-{query_dash}",
        f"https://www.computrabajo.cl/ofertas-de-trabajo/?q={query}&l=Chile",
        f"https://www.computrabajo.cl/empleos-en-chile-de-{query_dash}",
    ]

    resp = None
    for url in urls_a_probar:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12, verify=False, allow_redirects=True)
            print(f"[Computrabajo] {url} → {r.status_code}")
            if r.status_code == 200:
                resp = r
                break
        except Exception as e:
            print(f"[Computrabajo] Error en {url}: {e}")

    try:
        if not resp or resp.status_code != 200:
            print(f"[Computrabajo] Sin URL válida")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Computrabajo usa estructura de articles con clase box_offer
        tarjetas = soup.select("article.box_offer, .offerItem, [class*='offer'], article")

        for tarjeta in tarjetas[:10]:
            titulo_el = tarjeta.select_one("h2, h3, .title_offer, [class*='title']")
            link_el = tarjeta.select_one("a[href]")
            empresa_el = tarjeta.select_one(".name_company, [class*='company'], [class*='empresa']")
            ubicacion_el = tarjeta.select_one(".city, [class*='location'], [class*='ciudad']")
            if not titulo_el:
                continue
            href = link_el.get("href", "") if link_el else ""
            if href and not href.startswith("http"):
                href = "https://www.computrabajo.cl" + href
            ofertas.append({
                "fuente": "Computrabajo",
                "titulo": titulo_el.get_text(strip=True),
                "empresa": empresa_el.get_text(strip=True) if empresa_el else "No especificada",
                "ubicacion": ubicacion_el.get_text(strip=True) if ubicacion_el else "Chile",
                "modalidad": "No especificada",
                "descripcion": tarjeta.get_text(strip=True)[:400],
                "url": href,
                "skills_requeridos": [],
                "requisitos": tarjeta.get_text(strip=True),
            })

        print(f"[Computrabajo] {len(ofertas)} ofertas")
    except Exception as e:
        print(f"[Computrabajo] Error: {e}")

    return ofertas


# ─────────────────────────────────────────
# HELPER: extraer jobs de JSON recursivo
# ─────────────────────────────────────────

def _extraer_jobs_recursivo(data, profundidad=0) -> list[dict]:
    if profundidad > 6:
        return []
    ofertas = []
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and any(k in data[0] for k in ["title", "titulo", "nombre", "cargo"]):
            for job in data:
                o = _normalizar_job(job)
                if o:
                    ofertas.append(o)
        else:
            for item in data:
                ofertas.extend(_extraer_jobs_recursivo(item, profundidad + 1))
    elif isinstance(data, dict):
        for key in ["jobs", "ofertas", "results", "data", "items", "vacantes", "pageProps", "props"]:
            if key in data:
                ofertas.extend(_extraer_jobs_recursivo(data[key], profundidad + 1))
        if not ofertas:
            for val in data.values():
                if isinstance(val, (dict, list)):
                    ofertas.extend(_extraer_jobs_recursivo(val, profundidad + 1))
    return ofertas


def _normalizar_job(job: dict) -> dict | None:
    titulo = job.get("title") or job.get("titulo") or job.get("nombre") or job.get("cargo", "")
    if not titulo:
        return None
    empresa = job.get("company", job.get("empresa", {}))
    if isinstance(empresa, dict):
        empresa = empresa.get("name", empresa.get("nombre", "No especificada"))
    return {
        "fuente": job.get("source", "Portal de empleo"),
        "titulo": titulo,
        "empresa": str(empresa) if empresa else "No especificada",
        "ubicacion": job.get("location", job.get("ubicacion", job.get("ciudad", "Chile"))),
        "modalidad": "Remoto" if job.get("remote", job.get("remoto")) else "No especificada",
        "descripcion": (job.get("description", job.get("descripcion", "")) or "")[:600],
        "url": job.get("url", job.get("link", job.get("href", ""))),
        "skills_requeridos": [],
        "requisitos": job.get("description", job.get("descripcion", "")) or "",
    }


# ─────────────────────────────────────────
# PRE-FILTRO DE RELEVANCIA
# ─────────────────────────────────────────

# Palabras clave relacionadas por área (para filtrar ofertas irrelevantes)
KEYWORDS_RELEVANCIA = {
    "marketing": ["marketing", "digital", "contenido", "community", "seo", "sem", "marca",
                  "comunicacion", "publicidad", "growth", "redes sociales", "campañ", "brand",
                  "e-commerce", "ecommerce", "crm", "email", "inbound", "performance"],
    "ventas": ["venta", "vendedor", "comercial", "sales", "ejecutivo", "cliente", "negocio"],
    "diseño": ["diseño", "design", "ux", "ui", "grafico", "creativo", "visual"],
    "data": ["data", "analista", "analytics", "bi", "business intelligence", "sql", "python"],
    "producto": ["producto", "product", "manager", "pm", "roadmap"],
    "rrhh": ["rrhh", "recursos humanos", "hr", "reclutamiento", "talent"],
    "finanzas": ["finanz", "contab", "contador", "tesorero", "control de gestion"],
    "enfermeria": ["enferm", "salud", "clinica", "hospital", "paciente", "medic"],
    "ingenieria": ["ingeniero", "ingenieria", "software", "developer", "programador"],
}

def _oferta_es_relevante(oferta: dict, cargo: str) -> bool:
    """Verifica si la oferta es relevante para el cargo buscado."""
    titulo = oferta.get("titulo", "").lower()
    descripcion = oferta.get("descripcion", "").lower()
    texto = titulo + " " + descripcion

    # Buscar palabras del cargo directamente en el título
    palabras_cargo = cargo.lower().split()
    for palabra in palabras_cargo:
        if len(palabra) > 3 and palabra in titulo:
            return True

    # Buscar en lista de keywords relacionados
    cargo_lower = cargo.lower()
    keywords = []
    for key, words in KEYWORDS_RELEVANCIA.items():
        if key in cargo_lower:
            keywords = words
            break

    if not keywords:
        # Si no hay match exacto, usar palabras del cargo
        keywords = palabras_cargo

    # Al menos 1 keyword debe aparecer en título o descripción
    return any(kw in texto for kw in keywords)


# ─────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────

def buscar_ofertas(cargo: str, modalidad: str = None, ciudad: str = None, max_resultados: int = 30) -> list[dict]:
    if not cargo or cargo.strip() == "":
        cargo = "marketing"

    print(f"[Buscador] Buscando '{cargo}' | modalidad: {modalidad} | ciudad: {ciudad}")

    todas = []

    todas.extend(buscar_getonbrd(cargo, modalidad))
    todas.extend(buscar_trabajando(cargo, ciudad))
    todas.extend(buscar_chiletrabajos(cargo, ciudad))
    todas.extend(buscar_computrabajo(cargo, ciudad))

    # Eliminar duplicados por URL
    vistas = set()
    unicas = []
    for o in todas:
        key = o.get("url") or o.get("titulo", "")
        if key and key not in vistas:
            vistas.add(key)
            unicas.append(o)

    # Pre-filtrar por relevancia antes de gastar tokens en evaluación
    relevantes = [o for o in unicas if _oferta_es_relevante(o, cargo)]
    print(f"[Buscador] {len(unicas)} ofertas únicas → {len(relevantes)} relevantes para '{cargo}'")

    return relevantes[:max_resultados]


if __name__ == "__main__":
    resultados = buscar_ofertas("marketing digital")
    print(f"\nTotal: {len(resultados)} ofertas\n")
    for i, o in enumerate(resultados, 1):
        print(f"{i}. {o['titulo']} — {o['empresa']} ({o['fuente']})")
        print(f"   {o['url']}\n")
