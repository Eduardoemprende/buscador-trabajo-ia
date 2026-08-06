"""
Página de diagnóstico — ver qué portales funcionan desde Streamlit Cloud
"""
import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

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

st.title("🔍 Diagnóstico de portales (nube)")
st.caption("Esto muestra qué portales son accesibles desde Streamlit Cloud")

if st.button("Probar conexiones"):
    pruebas = [
        ("Get on Board RSS", "https://www.getonbrd.com/empleos/marketing-y-comunicacion.rss"),
        ("Get on Board (categoría)", "https://www.getonbrd.com/empleos/marketing-y-comunicacion"),
        ("Get on Board (búsqueda)", "https://www.getonbrd.com/empleos?query=marketing"),
        ("Computrabajo", "https://www.computrabajo.cl/ofertas-de-trabajo/oferta-de-trabajo-de-marketing"),
        ("Chiletrabajos", "https://www.chiletrabajos.cl/encuentra-un-empleo?keyword=marketing"),
        ("Trabajando.cl", "https://www.trabajando.cl/buscar-trabajo?q=marketing"),
        ("Adzuna ES", "https://api.adzuna.com/v1/api/jobs/es/search/1?app_id=2ff10c7c&app_key=8fc13fca21fbed10e9cf5ba89fd4bb03&what=marketing&results_per_page=3"),
    ]

    for nombre, url in pruebas:
        try:
            r = requests.get(url, timeout=12, verify=False, headers=HEADERS, allow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")

            # Contar ofertas según portal
            if ".rss" in url:
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(r.content)
                    items = root.findall(".//item")
                    conteo = f"{len(items)} ofertas en RSS"
                except:
                    conteo = f"RSS parse error — {r.text[:100]}"
            elif "getonbrd" in url:
                items = soup.select('a[href*="/empleos/"][href*="-"]')
                items = [a for a in items if a.get("href","").count("/") >= 3]
                conteo = f"{len(items)} links de ofertas"
            elif "computrabajo" in url:
                items = soup.select("article.box_offer, article")
                conteo = f"{len(items)} artículos"
            elif "chiletrabajos" in url:
                items = soup.select("div.job-item, article, .oferta")
                conteo = f"{len(items)} items"
            elif "trabajando" in url:
                items = soup.select("article, .job-item, .aviso")
                conteo = f"{len(items)} items"
            elif "adzuna" in url:
                import json
                data = r.json()
                conteo = f"{len(data.get('results',[]))} ofertas"
            else:
                conteo = f"{len(r.text)} chars"

            color = "green" if r.status_code == 200 else "red"
            st.markdown(f"**{nombre}:** :{color}[{r.status_code}] — {conteo}")

        except Exception as e:
            st.error(f"**{nombre}:** ERROR — {str(e)[:200]}")
