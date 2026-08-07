"""
Diagnóstico completo de Get on Board (getonbrd.com)
Corre con: python3 diagnostico_getonbrd.py
"""
import requests
import urllib3
from bs4 import BeautifulSoup
urllib3.disable_warnings()

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
CARGO = "marketing"

print("="*60)
print("DIAGNÓSTICO GET ON BOARD")
print("="*60)

r = requests.get(f"https://www.getonbrd.com/empleos?query={CARGO}", timeout=15, verify=False, headers=HEADERS)
print(f"Status: {r.status_code} | URL: {r.url}")

soup = BeautifulSoup(r.text, "html.parser")
links = soup.select('a[href*="/empleos/"]')
print(f"\nTotal links de ofertas: {len(links)}")

print("\n--- Primeras 10 ofertas ---")
vistos = set()
count = 0
for a in links:
    href = a.get("href", "")
    if href in vistos or not href:
        continue
    vistos.add(href)

    texto = a.get_text(separator=" | ", strip=True)
    if not href.startswith("http"):
        href = "https://www.getonbrd.com" + href

    # Intentar extraer título, empresa, modalidad
    partes = texto.split(" | ")
    titulo = partes[0] if partes else texto

    print(f"{count+1}. {titulo[:80]}")
    print(f"   URL: {href}")
    print(f"   Texto completo: {texto[:150]}")
    print()
    count += 1
    if count >= 10:
        break

print("\n--- Estructura de la primera tarjeta [class*=job] ---")
tarjetas = soup.select('[class*="job"]')
if tarjetas:
    t = tarjetas[0]
    print(f"Clase: {t.get('class')}")
    print(f"Texto: {t.get_text(separator=' | ', strip=True)[:300]}")
    # Buscar elementos internos
    for tag in ['h2','h3','h4','span','p']:
        els = t.select(tag)
        for el in els[:3]:
            txt = el.get_text(strip=True)
            if txt:
                print(f"  <{tag}>: {txt[:80]}")
