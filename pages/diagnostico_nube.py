"""
Página de diagnóstico — solo para testing, borrar después
"""
import streamlit as st
import requests
import urllib3
urllib3.disable_warnings()

st.title("🔍 Diagnóstico de portales")

if st.button("Probar conexiones"):
    urls = [
        ("Get on Board API", "https://www.getonboard.com/api/v1/job_offers?q=marketing&per_page=3"),
        ("Get on Board Web", "https://www.getonboard.com/vacantes?q=marketing"),
        ("Chiletrabajos", "https://www.chiletrabajos.cl/trabajos/marketing"),
        ("Computrabajo", "https://www.computrabajo.cl/ofertas-de-trabajo/oferta-de-trabajo-de-marketing"),
    ]
    for nombre, url in urls:
        try:
            r = requests.get(url, timeout=10, verify=False, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            st.write(f"**{nombre}:** {r.status_code} — {r.text[:200]}")
        except Exception as e:
            st.error(f"**{nombre}:** ERROR — {e}")
