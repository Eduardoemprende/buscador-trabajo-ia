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
        ("Chiletrabajos", "https://www.chiletrabajos.cl/encuentra-un-empleo?keyword=marketing"),
        ("Indeed Chile", "https://cl.indeed.com/jobs?q=marketing&l=Santiago"),
        ("Bumeran Chile", "https://www.bumeran.cl/empleos-busqueda-marketing.html"),
        ("Computrabajo", "https://www.computrabajo.cl/ofertas-de-trabajo/oferta-de-trabajo-de-marketing"),
        ("Trabajando.cl (búsqueda)", "https://www.trabajando.cl/buscar-trabajo?q=marketing"),
        ("Get on Board RSS", "https://www.getonbrd.com/empleos/marketing-y-comunicacion.rss"),
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
                    conteo = f"RSS parse error — {r.content[:80]}"
            elif "chiletrabajos" in url:
                items = soup.select("div.job-item, article, .oferta, [class*='job'], [class*='oferta']")
                conteo = f"{len(items)} items | Tags: " + ", ".join(set(i.name for i in items[:5]))
                if items:
                    st.code(str(items[0])[:800], language="html")
            elif "indeed" in url:
                items = soup.select("div.job_seen_beacon, .jobsearch-ResultsList li, [class*='job_']")
                conteo = f"{len(items)} ofertas"
            elif "bumeran" in url:
                items = soup.select("article, .aviso, [class*='aviso'], [class*='job']")
                conteo = f"{len(items)} ofertas"
            elif "computrabajo" in url:
                items = soup.select("article.box_offer, article")
                conteo = f"{len(items)} artículos"
            elif "trabajando" in url:
                items = soup.select("article, .job-item, .aviso, [class*='job']")
                conteo = f"{len(items)} items"
            elif "getonbrd" in url:
                items = soup.select('a[href*="/empleos/"][href*="-"]')
                items = [a for a in items if a.get("href","").count("/") >= 3]
                conteo = f"{len(items)} links de ofertas"
            else:
                conteo = f"{len(r.text)} chars"

            color = "green" if r.status_code == 200 else "red"
            st.markdown(f"**{nombre}:** :{color}[{r.status_code}] — {conteo}")

        except Exception as e:
            st.error(f"**{nombre}:** ERROR — {str(e)[:200]}")
