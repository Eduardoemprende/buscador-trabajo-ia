"""
AGENTE 2: Buscador de Ofertas
-----------------------------
Fuentes activas:
  - Chiletrabajos.cl   ✅ HTML estático
  - Computrabajo.cl    ✅ HTML estático (dominio: cl.computrabajo.com)
  - Indeed.cl          ✅ HTML estático
  - Laborum.cl         ⚠️  JS — requiere ScraperAPI render=true
  - Trabajando.cl      ⚠️  JS — requiere ScraperAPI render=true
  - Get on Board       ⚠️  JS — requiere ScraperAPI render=true
  - BNE (bne.gob.cl)   ⚠️  JS Angular — requiere ScraperAPI render=true (sin login, 84+ ofertas)
  - Remotive.com API   ✅ API pública (empleos remotos globales)
  - Jobicy.com API     ✅ API pública (empleos remotos globales)

Fuentes descartadas:
  - LinkedIn       — requiere login, no scrapeable legalmente
  - BNE            — búsqueda por keyword requiere login
  - Bumeran.cl     — redirige a Laborum.cl (mismo portal)
  - Indeed (403)   — usando cl.indeed.com que sí funciona
  - Adzuna         — bloqueado, solo España/UK/US

Jooble API (pendiente):
  - Agrega LinkedIn + múltiples portales
  - Registrarse en https://jooble.org/api/about para obtener key gratuita
  - Agregar JOOBLE_API_KEY en .env y Streamlit Secrets
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import urllib.parse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
JOOBLE_API_KEY  = os.getenv("JOOBLE_API_KEY", "")

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


def scraper_get(url: str, timeout: int = 25, render_js: bool = False) -> requests.Response:
    """
    Hace el request a través de ScraperAPI para evitar bloqueos.
    render_js=True: renderiza JavaScript (necesario para sitios React/Next.js).
    Costo: render_js=False usa 1 crédito; render_js=True usa 5-10 créditos.
    """
    if SCRAPER_API_KEY:
        encoded = urllib.parse.quote(url, safe="")
        proxy_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={encoded}"
        if render_js:
            proxy_url += "&render=true"
        return requests.get(proxy_url, headers=HEADERS, timeout=timeout, verify=False)
    else:
        return requests.get(url, headers=HEADERS, timeout=timeout, verify=False)


# ─────────────────────────────────────────
# CHILETRABAJOS.CL ✅
# ─────────────────────────────────────────

def buscar_chiletrabajos(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "+")
    query_dash = cargo.replace(" ", "-").lower()

    urls = [
        f"https://www.chiletrabajos.cl/trabajos/{query_dash}",
        f"https://www.chiletrabajos.cl/encuentra-un-empleo?keyword={query}",
    ]

    resp = None
    for url in urls:
        try:
            r = scraper_get(url, timeout=20)
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
            "descripcion": texto[:2000],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto[:2000],
        })

    print(f"[Chiletrabajos] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# COMPUTRABAJO ✅ (dominio correcto: cl.computrabajo.com)
# ─────────────────────────────────────────

def buscar_computrabajo(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    keyword_dash = cargo.replace(" ", "-").lower()
    keyword_plus = urllib.parse.quote(cargo)

    urls = [
        f"https://cl.computrabajo.com/trabajo-de-{keyword_dash}",
        f"https://cl.computrabajo.com/ofertas-de-trabajo/?q={keyword_plus}",
    ]

    resp = None
    for url in urls:
        try:
            r = scraper_get(url, timeout=25)
            print(f"[Computrabajo] {url} → {r.status_code} | {len(r.text)} chars")
            if r.status_code == 200 and len(r.text) > 5000:
                resp = r
                break
        except Exception as e:
            print(f"[Computrabajo] Error: {e}")

    if not resp:
        print("[Computrabajo] Sin respuesta válida")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tarjetas = soup.select("article.box_offer")
    print(f"[Computrabajo] {len(tarjetas)} tarjetas encontradas")

    for tarjeta in tarjetas[:20]:
        titulo_el = tarjeta.select_one("h2 a")
        if not titulo_el:
            continue
        titulo = titulo_el.get_text(strip=True)
        if not titulo or len(titulo) < 5:
            continue

        href = titulo_el.get("href", "")
        if href and not href.startswith("http"):
            href = "https://cl.computrabajo.com" + href.split("#")[0]

        empresa_el = tarjeta.select_one("p.fc_base a, [class*='company'] a, p a[href*='/empresas/']")
        empresa = empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta"

        ubicacion_el = tarjeta.select_one("p.fc_base span, [class*='location'], span[class*='city']")
        ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else (ciudad or "Chile")

        texto = tarjeta.get_text(separator=" ", strip=True)
        es_remoto = any(w in texto.lower() for w in ["remoto", "remote", "teletrabajo", "trabajo desde casa"])

        ofertas.append({
            "fuente": "Computrabajo",
            "titulo": titulo[:100],
            "empresa": empresa[:80],
            "ubicacion": ubicacion,
            "modalidad": "Remoto" if es_remoto else "No especificada",
            "descripcion": texto[:2000],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto[:2000],
        })

    print(f"[Computrabajo] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# INDEED.CL ✅ (nuevo — HTML estático)
# ─────────────────────────────────────────

def buscar_indeed(cargo: str, ciudad: str = None) -> list[dict]:
    """
    Indeed Chile — HTML semi-estático.
    Intenta 3 estrategias distintas para evitar detección de bots.
    """
    ofertas = []
    keyword = urllib.parse.quote(cargo)
    ciudad_query = urllib.parse.quote(ciudad or "Santiago de Chile")

    urls = [
        f"https://cl.indeed.com/jobs?q={keyword}&l={ciudad_query}",
        f"https://cl.indeed.com/jobs?q={keyword}&l=Santiago%2C+Regi%C3%B3n+Metropolitana",
        f"https://cl.indeed.com/empleos?q={keyword}&l={ciudad_query}",
    ]

    resp = None
    for url in urls:
        try:
            r = scraper_get(url, timeout=25)
            print(f"[Indeed] {url} → {r.status_code} | {len(r.text)} chars")
            # Indeed a veces devuelve 200 pero con página de captcha
            if r.status_code == 200 and len(r.text) > 10000 and "jobsearch" in r.text.lower():
                resp = r
                break
            elif r.status_code == 200 and len(r.text) > 10000:
                resp = r
                break
        except Exception as e:
            print(f"[Indeed] Error en {url}: {e}")

    if not resp:
        print("[Indeed] Sin respuesta válida — Indeed puede estar bloqueando ScraperAPI")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Estrategia 1: data-jk (atributo estable de Indeed)
    tarjetas = soup.select("[data-jk]")

    # Estrategia 2: clases de resultado conocidas
    if not tarjetas:
        tarjetas = soup.select(".job_seen_beacon, .result, .tapItem")

    # Estrategia 3: cualquier li con link a /pagepixels o /rc/clk (links internos de Indeed)
    if not tarjetas:
        tarjetas = soup.select("li:has(a[href*='/rc/clk']), li:has(a[href*='pagepixels'])")

    print(f"[Indeed] {len(tarjetas)} tarjetas encontradas")

    for tarjeta in tarjetas[:20]:
        titulo_el = tarjeta.select_one(
            "h2 a span[title], h2 a span, [class*='jobTitle'] span, h2 span"
        )
        if not titulo_el:
            continue
        titulo = titulo_el.get("title") or titulo_el.get_text(strip=True)
        if not titulo or len(titulo) < 5:
            continue

        link_el = tarjeta.select_one("h2 a, a[href*='/rc/clk'], a[href*='/pagepixels']")
        href = ""
        if link_el:
            raw = link_el.get("href", "")
            href = "https://cl.indeed.com" + raw if raw.startswith("/") else raw

        empresa_el = tarjeta.select_one(
            "[data-testid='company-name'], [class*='companyName'], span[class*='company']"
        )
        empresa = empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta"

        ubicacion_el = tarjeta.select_one(
            "[data-testid='text-location'], [class*='companyLocation'], div[class*='location']"
        )
        ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else (ciudad or "Chile")

        desc_el = tarjeta.select_one(
            "[data-testid='job-snippet'], [class*='snippet'], div[class*='summary']"
        )
        texto = tarjeta.get_text(separator=" ", strip=True)
        descripcion = desc_el.get_text(strip=True) if desc_el else texto[:500]
        es_remoto = any(w in texto.lower() for w in ["remoto", "remote", "teletrabajo", "híbrido", "hybrid"])

        ofertas.append({
            "fuente": "Indeed",
            "titulo": titulo[:100],
            "empresa": empresa[:80],
            "ubicacion": ubicacion,
            "modalidad": "Remoto" if es_remoto else "No especificada",
            "descripcion": descripcion[:2000],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto[:2000],
        })

    print(f"[Indeed] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# LABORUM.CL ⚠️ JS — ScraperAPI render=true
# ─────────────────────────────────────────

LABORUM_AREAS = {
    "marketing": "marketing-y-publicidad",
    "digital": "marketing-y-publicidad",
    "publicidad": "marketing-y-publicidad",
    "diseño": "diseno",
    "design": "diseno",
    "ux": "diseno",
    "data": "tecnologia-sistemas-y-telecomunicaciones",
    "software": "tecnologia-sistemas-y-telecomunicaciones",
    "developer": "tecnologia-sistemas-y-telecomunicaciones",
    "ventas": "comercial-ventas-y-negocios",
    "comercial": "comercial-ventas-y-negocios",
    "rrhh": "recursos-humanos-y-capacitacion",
    "recursos humanos": "recursos-humanos-y-capacitacion",
    "finanzas": "administracion-contabilidad-y-finanzas",
    "contabilidad": "administracion-contabilidad-y-finanzas",
    "administracion": "administracion-contabilidad-y-finanzas",
}

def buscar_laborum(cargo: str, ciudad: str = None) -> list[dict]:
    """
    Laborum.cl — SSR con JSON-LD embebido (schema.org ItemList).
    Los jobs están en <script type="application/ld+json"> con @type=ItemList.
    NO requiere ScraperAPI ni JS rendering — es HTML estático desde el servidor.
    URL: /empleos-area-{area}.html  (NO /area-{area}/empleos.html que da 404)
    """
    import json as json_lib

    ofertas = []
    cargo_lower = cargo.lower()
    area = next((v for k, v in LABORUM_AREAS.items() if k in cargo_lower), "marketing-y-publicidad")

    urls = [
        f"https://www.laborum.cl/empleos-area-{area}.html",
        f"https://www.laborum.cl/empleos.html",
    ]

    resp = None
    for url in urls:
        try:
            # Intento 1: request directo (funciona en Streamlit Cloud)
            r = requests.get(url, headers=HEADERS, timeout=25, verify=False)
            print(f"[Laborum] directo {url} → {r.status_code} | {len(r.text)} chars")
            if r.status_code == 200 and len(r.text) > 5000:
                resp = r
                break
        except Exception as e:
            print(f"[Laborum] Error directo: {e}")

        if not resp and SCRAPER_API_KEY:
            try:
                # Intento 2: ScraperAPI sin render (el JSON-LD está en el HTML estático)
                r = scraper_get(url, timeout=35, render_js=False)
                print(f"[Laborum] ScraperAPI {url} → {r.status_code} | {len(r.text)} chars")
                if r.status_code == 200 and len(r.text) > 5000:
                    resp = r
                    break
            except Exception as e:
                print(f"[Laborum] Error ScraperAPI: {e}")

    if not resp:
        print("[Laborum] Sin respuesta válida")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Parsear JSON-LD (schema.org ItemList) — fuente más estable y no depende de clases CSS
    items = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json_lib.loads(script.string or "")
            if data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
                break
        except Exception:
            continue

    print(f"[Laborum] {len(items)} items en JSON-LD")

    for item in items[:25]:
        titulo = item.get("name", "").strip()
        href   = item.get("url", "").strip()
        if not titulo or len(titulo) < 5 or not href:
            continue

        ofertas.append({
            "fuente": "Laborum",
            "titulo": titulo[:100],
            "empresa": "Ver en oferta",
            "ubicacion": ciudad or "Chile",
            "modalidad": "No especificada",
            "descripcion": titulo,   # sin descripción en JSON-LD; Claude evaluará con título
            "url": href,
            "skills_requeridos": [],
            "requisitos": titulo,
        })

    print(f"[Laborum] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# TRABAJANDO.CL ⚠️ JS — ScraperAPI render=true
# ─────────────────────────────────────────

def buscar_trabajando(cargo: str, ciudad: str = None) -> list[dict]:
    if not SCRAPER_API_KEY:
        print("[Trabajando] Sin ScraperAPI key — omitiendo")
        return []

    ofertas = []
    keyword = urllib.parse.quote(cargo)

    urls = [
        f"https://www.trabajando.cl/empleos?q={keyword}",
        f"https://www.trabajando.cl/empleo/buscar?q={keyword}",
        f"https://www.trabajando.cl/empleos/{cargo.replace(' ', '-').lower()}",
    ]

    resp = None
    for url in urls:
        try:
            r = scraper_get(url, timeout=35, render_js=True)
            print(f"[Trabajando] {url} → {r.status_code} | {len(r.text)} chars")
            if r.status_code == 200 and len(r.text) > 5000:
                resp = r
                break
        except Exception as e:
            print(f"[Trabajando] Error: {e}")

    if not resp:
        print("[Trabajando] Sin respuesta válida")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tarjetas = soup.select(
        "article, [class*='job-card'], [class*='jobcard'], [class*='oferta'], "
        "div[class*='aviso'], li[class*='empleo']"
    )
    print(f"[Trabajando] {len(tarjetas)} tarjetas encontradas")

    for tarjeta in tarjetas[:20]:
        titulo_el = tarjeta.select_one("h2, h3, a[href*='/empleo/']")
        if not titulo_el:
            continue
        titulo = titulo_el.get_text(strip=True)
        if not titulo or len(titulo) < 5:
            continue

        link_el = tarjeta.select_one("a[href]")
        href = ""
        if link_el:
            raw = link_el.get("href", "")
            href = "https://www.trabajando.cl" + raw if raw.startswith("/") else raw

        empresa_el = tarjeta.select_one("[class*='empresa'], [class*='company']")
        empresa = empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta"

        texto = tarjeta.get_text(separator=" ", strip=True)
        es_remoto = any(w in texto.lower() for w in ["remoto", "teletrabajo"])

        ofertas.append({
            "fuente": "Trabajando",
            "titulo": titulo[:100],
            "empresa": empresa[:80],
            "ubicacion": ciudad or "Chile",
            "modalidad": "Remoto" if es_remoto else "No especificada",
            "descripcion": texto[:2000],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto[:2000],
        })

    print(f"[Trabajando] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# GET ON BOARD ⚠️ JS — ScraperAPI render=true
# ─────────────────────────────────────────

GOB_CATEGORIAS = {
    "marketing": "digital-marketing",
    "digital": "digital-marketing",
    "publicidad": "advertising-media",
    "diseño": "design-ux",
    "ux": "design-ux",
    "datos": "data-science-analytics",
    "data": "data-science-analytics",
    "producto": "innovation-agile",
    "ventas": "sales",
    "software": "programming",
    "developer": "programming",
}

def buscar_getonboard(cargo: str) -> list[dict]:
    if not SCRAPER_API_KEY:
        print("[GetOnBoard] Sin ScraperAPI key — omitiendo")
        return []

    ofertas = []
    cargo_lower = cargo.lower()
    categoria = next((v for k, v in GOB_CATEGORIAS.items() if k in cargo_lower), "digital-marketing")
    keyword = urllib.parse.quote(cargo)

    urls = [
        f"https://www.getonbrd.com/jobs/{categoria}",
        f"https://www.getonbrd.com/jobs?query={keyword}",
        f"https://www.getonbrd.com/jobs",
    ]

    resp = None
    for url in urls:
        try:
            r = scraper_get(url, timeout=35, render_js=True)
            print(f"[GetOnBoard] {url} → {r.status_code} | {len(r.text)} chars")
            if r.status_code == 200 and len(r.text) > 5000:
                resp = r
                break
        except Exception as e:
            print(f"[GetOnBoard] Error: {e}")

    if not resp:
        print("[GetOnBoard] Sin respuesta válida")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tarjetas = soup.select(
        "article, [class*='job-card'], [class*='JobCard'], [class*='job_item'], "
        "li[class*='job'], div[class*='position']"
    )
    print(f"[GetOnBoard] {len(tarjetas)} tarjetas encontradas")

    for tarjeta in tarjetas[:20]:
        titulo_el = tarjeta.select_one("h2, h3, [class*='title'], a[href*='/jobs/']")
        if not titulo_el:
            continue
        titulo = titulo_el.get_text(strip=True)
        if not titulo or len(titulo) < 5:
            continue

        link_el = tarjeta.select_one("a[href*='/jobs/'], a[href]")
        href = ""
        if link_el:
            raw = link_el.get("href", "")
            href = "https://www.getonbrd.com" + raw if raw.startswith("/") else raw

        empresa_el = tarjeta.select_one("[class*='company'], [class*='empresa'], span[class*='name']")
        empresa = empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta"

        texto = tarjeta.get_text(separator=" ", strip=True)
        es_remoto = any(w in texto.lower() for w in ["remoto", "remote", "teletrabajo"])

        ofertas.append({
            "fuente": "Get on Board",
            "titulo": titulo[:100],
            "empresa": empresa[:80],
            "ubicacion": "Chile",
            "modalidad": "Remoto" if es_remoto else "No especificada",
            "descripcion": texto[:2000],
            "url": href,
            "skills_requeridos": [],
            "requisitos": texto[:2000],
        })

    print(f"[GetOnBoard] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# BNE — Bolsa Nacional de Empleo ⚠️ JS — ScraperAPI render=true
# Sin login. URL: bne.gob.cl/ofertas?mostrar=empleo&textoLibre={keyword}
# Detalle de oferta: bne.gob.cl/oferta/{id}
# ─────────────────────────────────────────

def buscar_bne(cargo: str, ciudad: str = None) -> list[dict]:
    if not SCRAPER_API_KEY:
        print("[BNE] Sin ScraperAPI key — omitiendo")
        return []

    ofertas = []
    keyword = urllib.parse.quote(cargo)
    url = (
        f"https://bne.gob.cl/ofertas?mostrar=empleo"
        f"&textoLibre={keyword}"
        f"&numResultadosPorPagina=20"
        f"&clasificarYPaginar=true"
    )

    try:
        r = scraper_get(url, timeout=40, render_js=True)
        print(f"[BNE] {url} → {r.status_code} | {len(r.text)} chars")
        if r.status_code != 200 or len(r.text) < 3000:
            print("[BNE] Sin respuesta válida")
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        tarjetas = soup.select("article")
        print(f"[BNE] {len(tarjetas)} tarjetas encontradas")

        for tarjeta in tarjetas[:20]:
            # Título y link: el anchor dentro del article
            link_el = tarjeta.select_one("a[href*='/oferta/']")
            if not link_el:
                link_el = tarjeta.select_one("a[href]")
            if not link_el:
                continue
            titulo = link_el.get_text(strip=True)
            if not titulo or len(titulo) < 5:
                continue

            href = link_el.get("href", "")
            if href.startswith("/"):
                href = "https://bne.gob.cl" + href

            # Empresa y ubicación: texto en párrafos y spans
            textos = [el.get_text(strip=True) for el in tarjeta.select("p, span, div") if el.get_text(strip=True)]
            empresa = "Ver en oferta"
            ubicacion_raw = ciudad or "Chile"

            for t in textos:
                # La empresa suele estar en mayúsculas (ej: "OMIL PROVIDENCIA")
                if t.isupper() and len(t) > 5 and empresa == "Ver en oferta":
                    empresa = t[:80]
                # Ubicación tiene formato "Región - Ciudad"
                if " - " in t and any(reg in t for reg in ["Metropolitana", "Valparaíso", "Antofagasta", "Los Lagos", "Los Ríos", "Biobío", "Araucanía"]):
                    ubicacion_raw = t

            texto = tarjeta.get_text(separator=" ", strip=True)
            es_remoto = any(w in texto.lower() for w in ["remoto", "teletrabajo", "trabajo a distancia"])

            ofertas.append({
                "fuente": "BNE (Bolsa Nacional de Empleo)",
                "titulo": titulo[:100],
                "empresa": empresa[:80],
                "ubicacion": ubicacion_raw,
                "modalidad": "Remoto" if es_remoto else "No especificada",
                "descripcion": texto[:2000],
                "url": href,
                "skills_requeridos": [],
                "requisitos": texto[:2000],
            })

    except Exception as e:
        print(f"[BNE] Error: {e}")

    print(f"[BNE] {len(ofertas)} ofertas extraídas")
    return ofertas


# ─────────────────────────────────────────
# JOOBLE API (pendiente — agrega LinkedIn)
# Para activar: registrar en https://jooble.org/api/about
# Agregar JOOBLE_API_KEY en .env y Streamlit Secrets
# ─────────────────────────────────────────

def buscar_jooble(cargo: str, ciudad: str = None) -> list[dict]:
    if not JOOBLE_API_KEY:
        print("[Jooble] Sin API key — omitiendo. Registrar en https://jooble.org/api/about")
        return []

    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {
        "keywords": cargo,
        "location": ciudad or "Chile",
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        print(f"[Jooble] Status: {resp.status_code}")
        if resp.status_code != 200:
            return []
        jobs = resp.json().get("jobs", [])
        print(f"[Jooble] {len(jobs)} ofertas")
        ofertas = []
        for job in jobs[:20]:
            desc = BeautifulSoup(job.get("snippet", ""), "html.parser").get_text(strip=True)
            ofertas.append({
                "fuente": "Jooble (LinkedIn/Multi)",
                "titulo": job.get("title", "")[:100],
                "empresa": job.get("company", "Ver en oferta")[:80],
                "ubicacion": job.get("location", ciudad or "Chile"),
                "modalidad": "Remoto" if "remoto" in desc.lower() or "remote" in desc.lower() else "No especificada",
                "descripcion": desc[:2000],
                "url": job.get("link", ""),
                "skills_requeridos": [],
                "requisitos": desc[:2000],
            })
        return ofertas
    except Exception as e:
        print(f"[Jooble] Error: {e}")
        return []


# ─────────────────────────────────────────
# REMOTIVE.COM — API gratuita, empleos remotos
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
}

def buscar_remotive(cargo: str) -> list[dict]:
    cargo_lower = cargo.lower()
    categoria = next((v for k, v in REMOTIVE_CATEGORIAS.items() if k in cargo_lower), "marketing")
    url = f"https://remotive.com/api/remote-jobs?category={categoria}&limit=20"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        print(f"[Remotive] Status: {resp.status_code}")
        if resp.status_code != 200:
            return []
        jobs = resp.json().get("jobs", [])
        print(f"[Remotive] {len(jobs)} ofertas")
        ofertas = []
        for job in jobs:
            desc = BeautifulSoup(job.get("description", ""), "html.parser").get_text(separator=" ", strip=True)[:2000]
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
# JOBICY.COM — API gratuita, empleos remotos
# ─────────────────────────────────────────

def buscar_jobicy(cargo: str) -> list[dict]:
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
            desc = BeautifulSoup(job.get("jobDescription", ""), "html.parser").get_text(separator=" ", strip=True)[:2000]
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
                  "ecommerce", "crm", "email", "inbound", "performance", "pauta", "ads"],
    "ventas": ["venta", "vendedor", "comercial", "sales", "ejecutivo comercial", "prospect"],
    "diseño": ["diseño", "design", "ux", "ui", "grafico", "creativo", "visual", "multimedia"],
    "data": ["data", "analista", "analytics", "business intelligence", "sql", "machine learning"],
    "producto": ["producto", "product manager", "product owner", "roadmap"],
    "rrhh": ["recursos humanos", "reclutamiento", "talent", "people", "gestión de personas"],
    "finanzas": ["finanz", "contab", "contador", "control de gestion", "tesorero"],
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
    print(f"[Buscador] ScraperAPI: {'✅ activo' if SCRAPER_API_KEY else '❌ sin key'}")
    print(f"[Buscador] Jooble API: {'✅ activo' if JOOBLE_API_KEY else '⚠️ sin key (registrar en jooble.org/api/about)'}")

    todas = []

    # Fuentes HTML estático (siempre activas)
    todas.extend(buscar_chiletrabajos(cargo, ciudad))
    todas.extend(buscar_computrabajo(cargo, ciudad))
    todas.extend(buscar_indeed(cargo, ciudad))

    # Fuentes JS (requieren ScraperAPI render=true)
    todas.extend(buscar_laborum(cargo, ciudad))
    todas.extend(buscar_trabajando(cargo, ciudad))
    todas.extend(buscar_getonboard(cargo))
    todas.extend(buscar_bne(cargo, ciudad))

    # APIs de empleos remotos (siempre activas)
    todas.extend(buscar_remotive(cargo))
    todas.extend(buscar_jobicy(cargo))

    # Jooble (LinkedIn + multi-portales) si tiene key
    todas.extend(buscar_jooble(cargo, ciudad))

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
    print(f"\n[Buscador] {len(unicas)} únicas → {len(relevantes)} relevantes para '{cargo}'")
    fuentes = {}
    for o in relevantes:
        f = o.get("fuente", "?")
        fuentes[f] = fuentes.get(f, 0) + 1
    print(f"[Buscador] Por fuente: {fuentes}")

    return relevantes[:max_resultados]


if __name__ == "__main__":
    resultados = buscar_ofertas("marketing digital")
    print(f"\nTotal: {len(resultados)} ofertas\n")
    for i, o in enumerate(resultados, 1):
        print(f"{i}. [{o['fuente']}] {o['titulo']} — {o['empresa']}")
        print(f"   {o['url']}\n")
