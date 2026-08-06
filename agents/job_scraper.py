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

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

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
    """Busca ofertas en getonbrd.com por categoría."""
    ofertas = []

    # Determinar categorías según cargo
    cargo_lower = cargo.lower()
    categorias = None
    for key in GETONBRD_CATEGORIAS:
        if key in cargo_lower:
            categorias = GETONBRD_CATEGORIAS[key]
            break
    if not categorias:
        categorias = GETONBRD_CATEGORIAS["default"]

    for categoria in categorias:
        url = f"https://www.getonbrd.com/empleos/{categoria}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code != 200:
                print(f"[GetOnBrd/{categoria}] Error {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Cada oferta está en un <a href="/empleos/..."> con h4 adentro
            vistos = set()
            tarjetas = soup.select('a[href*="/empleos/"][href*="-"]')

            for a in tarjetas:
                href = a.get("href", "")
                # Filtrar links de navegación y duplicados
                if not href or href.count("/") < 3:
                    continue
                # URL limpia sin parámetros
                href_limpio = href.split("?")[0]
                if href_limpio in vistos:
                    continue
                vistos.add(href_limpio)

                if not href_limpio.startswith("http"):
                    href_limpio = "https://www.getonbrd.com" + href_limpio

                texto = a.get_text(separator=" | ", strip=True)
                partes = [p.strip() for p in texto.split("|") if p.strip()]

                titulo = partes[0] if partes else ""
                if not titulo or len(titulo) < 3:
                    continue

                # Extraer modalidad y empresa del texto
                modalidad_oferta = "No especificada"
                empresa = "Ver en oferta"
                for p in partes[1:]:
                    if any(w in p.lower() for w in ["remote", "remoto", "full remote"]):
                        modalidad_oferta = "Remoto"
                    elif any(w in p.lower() for w in ["hybrid", "híbrido", "home"]):
                        modalidad_oferta = "Híbrido"
                    elif any(w in p.lower() for w in ["full time", "part time", "freelance"]):
                        continue
                    elif any(w in p.lower() for w in ["santiago", "remote", "remoto"]):
                        continue
                    elif len(p) > 2 and empresa == "Ver en oferta":
                        empresa = p

                if modalidad == "remote" and modalidad_oferta != "Remoto":
                    continue

                ofertas.append({
                    "fuente": "Get on Board",
                    "titulo": titulo[:100],
                    "empresa": empresa,
                    "ubicacion": "Chile / Remoto",
                    "modalidad": modalidad_oferta,
                    "descripcion": texto[:400],
                    "url": href_limpio,
                    "skills_requeridos": [],
                    "requisitos": texto,
                })

            print(f"[GetOnBrd/{categoria}] {len(ofertas)} ofertas")

        except Exception as e:
            print(f"[GetOnBrd/{categoria}] Error: {e}")

    return ofertas[:20]


# ─────────────────────────────────────────
# ADZUNA (API oficial — CL, AR, ES, GB, US)
# ─────────────────────────────────────────

def buscar_adzuna(cargo: str, modalidad: str = None) -> list[dict]:
    ofertas = []
    paises = ["es", "gb", "us"]  # CL y AR no tienen cobertura en Adzuna

    for pais in paises:
        url = f"https://api.adzuna.com/v1/api/jobs/{pais}/search/1"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what": cargo,
            "results_per_page": 10,
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                jobs = resp.json().get("results", [])
                print(f"[Adzuna/{pais.upper()}] {len(jobs)} ofertas")
                for job in jobs:
                    desc = job.get("description", "") or ""
                    es_remoto = any(w in (job.get("title","") + desc).lower() for w in ["remoto","remote","teletrabajo"])
                    if modalidad == "remote" and not es_remoto:
                        continue
                    ofertas.append({
                        "fuente": f"Adzuna ({pais.upper()})",
                        "titulo": job.get("title", ""),
                        "empresa": job.get("company", {}).get("display_name", "No especificada"),
                        "ubicacion": job.get("location", {}).get("display_name", "No especificada"),
                        "modalidad": "Remoto" if es_remoto else "Presencial",
                        "descripcion": desc[:600],
                        "url": job.get("redirect_url", ""),
                        "skills_requeridos": [],
                        "requisitos": desc,
                    })
        except Exception as e:
            print(f"[Adzuna/{pais.upper()}] Error: {e}")

    return ofertas


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
    # Usar búsqueda por texto para resultados más relevantes
    query = cargo.replace(" ", "+")
    url = f"https://www.chiletrabajos.cl/encuentra-un-empleo?action=search&filterSearch=Buscar&keyword={query}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
        if resp.status_code != 200:
            url = f"https://www.chiletrabajos.cl/trabajos/{cargo.replace(' ', '-').lower()}"
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
            if resp.status_code != 200:
                print(f"[Chiletrabajos] Error {resp.status_code}")
                return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Buscar JSON embebido
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data:
            data = json.loads(next_data.string or "{}")
            jobs = _extraer_jobs_recursivo(data)
            print(f"[Chiletrabajos] {len(jobs)} ofertas (JSON)")
            return jobs[:10]

        # Scraping HTML
        tarjetas = soup.select("div.job-item")
        for tarjeta in tarjetas[:15]:
            link_el = tarjeta.select_one("a[href]")
            titulo_el = tarjeta.select_one("h2, h3, a")
            empresa_el = tarjeta.select_one("[class*='empresa'], [class*='company'], strong")
            ubicacion_el = tarjeta.select_one("[class*='ciudad'], [class*='location'], [class*='ubicacion']")
            if not titulo_el or not link_el:
                continue
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.chiletrabajos.cl" + href
            ofertas.append({
                "fuente": "Chiletrabajos",
                "titulo": titulo_el.get_text(strip=True)[:100],
                "empresa": empresa_el.get_text(strip=True) if empresa_el else "Ver en oferta",
                "ubicacion": ubicacion_el.get_text(strip=True) if ubicacion_el else "Chile",
                "modalidad": "No especificada",
                "descripcion": tarjeta.get_text(strip=True)[:400],
                "url": href,
                "skills_requeridos": [],
                "requisitos": tarjeta.get_text(strip=True),
            })

        print(f"[Chiletrabajos] {len(ofertas)} ofertas")
    except Exception as e:
        print(f"[Chiletrabajos] Error: {e}")

    return ofertas


# ─────────────────────────────────────────
# COMPUTRABAJO.CL
# ─────────────────────────────────────────

def buscar_computrabajo(cargo: str, ciudad: str = None) -> list[dict]:
    ofertas = []
    query = cargo.replace(" ", "-").lower()
    url = f"https://www.computrabajo.cl/ofertas-de-trabajo/oferta-de-trabajo-de-{query}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
        if resp.status_code != 200:
            url = f"https://www.computrabajo.cl/trabajo-de-{query}"
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
            if resp.status_code != 200:
                print(f"[Computrabajo] Error {resp.status_code}")
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
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────

def buscar_ofertas(cargo: str, modalidad: str = None, ciudad: str = None, max_resultados: int = 30) -> list[dict]:
    if not cargo or cargo.strip() == "":
        cargo = "marketing"

    print(f"[Buscador] Buscando '{cargo}' | modalidad: {modalidad} | ciudad: {ciudad}")

    todas = []

    # Buscar en paralelo (secuencial por ahora)
    todas.extend(buscar_getonbrd(cargo, modalidad))
    todas.extend(buscar_adzuna(cargo, modalidad))
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

    print(f"[Buscador] Total: {len(unicas)} ofertas únicas")
    return unicas[:max_resultados]


if __name__ == "__main__":
    resultados = buscar_ofertas("marketing digital")
    print(f"\nTotal: {len(resultados)} ofertas\n")
    for i, o in enumerate(resultados, 1):
        print(f"{i}. {o['titulo']} — {o['empresa']} ({o['fuente']})")
        print(f"   {o['url']}\n")
