"""
Script de diagnóstico — prueba todos los portales de empleo
Corre con: python3 diagnostico.py
"""
import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings()

load_dotenv(Path(__file__).parent / ".env")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-CL,es;q=0.9",
}

CARGO = "marketing digital"

def probar(nombre, url, selector, base_url=""):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
        print(f"\n{'='*50}")
        print(f"[{nombre}] Status: {resp.status_code} | URL final: {resp.url}")
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            tarjetas = soup.select(selector)
            print(f"[{nombre}] Tarjetas encontradas: {len(tarjetas)}")
            for t in tarjetas[:3]:
                titulo = t.select_one("h2, h3, h4, a")
                link = t.select_one("a[href]")
                print(f"  - {titulo.get_text(strip=True)[:70] if titulo else 'N/A'}")
                print(f"    {link.get('href','') if link else 'N/A'}")
        else:
            print(f"[{nombre}] ERROR: {resp.status_code}")
    except Exception as e:
        print(f"[{nombre}] EXCEPCIÓN: {e}")

# ── Chiletrabajos ──
probar(
    "Chiletrabajos",
    f"https://www.chiletrabajos.cl/trabajos/{CARGO.replace(' ', '-')}",
    "div.job-item"
)

# ── Computrabajo ──
probar(
    "Computrabajo",
    f"https://www.computrabajo.cl/ofertas-de-trabajo/oferta-de-trabajo-de-{CARGO.replace(' ', '-')}",
    "article.box_offer, .offerItem, article"
)

# ── Trabajando.cl ──
probar(
    "Trabajando.cl",
    f"https://www.trabajando.cl/empleos-{CARGO.replace(' ', '-')}",
    "article, .job-item, .oferta, [class*='job'], .aviso"
)

# ── Chiletrabajos búsqueda ──
probar(
    "Chiletrabajos (búsqueda)",
    f"https://www.chiletrabajos.cl/encuentra-un-empleo?action=search&filterSearch=Buscar&keyword={CARGO.replace(' ', '+')}",
    "div.job-item"
)

# ── Adzuna CL ──
app_id = os.getenv("ADZUNA_APP_ID")
app_key = os.getenv("ADZUNA_APP_KEY")
for pais in ["cl", "ar", "es"]:
    try:
        url = f"https://api.adzuna.com/v1/api/jobs/{pais}/search/1"
        resp = requests.get(url, params={"app_id": app_id, "app_key": app_key, "what": CARGO, "results_per_page": 5}, timeout=15, verify=False)
        data = resp.json()
        jobs = data.get("results", [])
        print(f"\n[Adzuna/{pais.upper()}] Status: {resp.status_code} | Ofertas: {len(jobs)}")
        for j in jobs[:2]:
            print(f"  - {j.get('title','')[:70]}")
    except Exception as e:
        print(f"\n[Adzuna/{pais.upper()}] Error: {e}")

print("\n" + "="*50)
print("Diagnóstico completo.")
