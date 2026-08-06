"""
AGENTE ORQUESTADOR
------------------
Coordina los 3 agentes (extractor, buscador, evaluador).
Es el cerebro que recibe los inputs del usuario y devuelve los resultados finales.

Flujo:
  PDF del CV
      ↓
  [Agente 1] Extrae perfil
      ↓
  [Agente 2] Busca ofertas según cargo + filtros
      ↓
  [Agente 3] Evalúa y rankea ofertas vs perfil
      ↓
  Lista final de ofertas que califican
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.cv_extractor import extraer_perfil, extraer_perfil_desde_bytes
from agents.job_scraper import buscar_ofertas
from agents.job_evaluator import evaluar_todas


def buscar_trabajo(
    pdf_path: str = None,
    pdf_bytes: bytes = None,
    cargo_buscado: str = None,
    modalidad: str = None,
    ciudad: str = None,
    requisitos_no_cumple: list[str] = None,
    max_ofertas: int = 30,
) -> dict:
    """
    Función principal: recibe el CV y los filtros, devuelve las mejores ofertas.

    Parámetros:
    - pdf_path: ruta al PDF del CV (para uso desde terminal)
    - pdf_bytes: bytes del PDF (para uso desde Streamlit)
    - cargo_buscado: qué cargo buscar (si None, usa el cargo actual del CV)
    - modalidad: "remote" | "hybrid" | "onsite" | None
    - ciudad: ciudad donde buscar | None
    - requisitos_no_cumple: lista de cosas que el usuario sabe que no cumple
    - max_ofertas: cuántas ofertas buscar antes de filtrar

    Retorna:
    {
        "perfil": dict,               # Perfil extraído del CV
        "ofertas_encontradas": int,   # Total de ofertas antes de filtrar
        "ofertas_califican": int,     # Total después de filtrar
        "resultados": [               # Lista rankeada de ofertas que califican
            {
                "puntaje": int,
                "califica": bool,
                "fortalezas": [str],
                "brechas": [str],
                "explicacion": str,
                "recomendacion": str,
                "oferta": {titulo, empresa, modalidad, ubicacion, url, fuente}
            }
        ]
    }
    """

    # ── PASO 1: Extraer perfil del CV ──────────────────────────────
    print("\n═══════════════════════════════════════════")
    print("  BUSCADOR DE TRABAJO CON IA")
    print("═══════════════════════════════════════════")
    print("\n[1/3] Leyendo tu CV...")

    if pdf_bytes:
        perfil = extraer_perfil_desde_bytes(pdf_bytes)
    elif pdf_path:
        perfil = extraer_perfil(pdf_path)
    else:
        raise ValueError("Debes proporcionar pdf_path o pdf_bytes")

    print(f"  ✓ Perfil extraído: {perfil.get('nombre')} — {perfil.get('cargo_actual')}")
    print(f"  ✓ Skills: {', '.join(perfil.get('skills', [])[:5])}")

    # ── PASO 2: Determinar qué cargo buscar ───────────────────────
    cargo = cargo_buscado or perfil.get("cargo_actual", "")
    if not cargo:
        raise ValueError("No se pudo determinar el cargo a buscar. Especifícalo manualmente.")

    # ── PASO 3: Buscar ofertas ─────────────────────────────────────
    print(f"\n[2/3] Buscando ofertas para '{cargo}'...")
    if modalidad:
        print(f"  Filtro modalidad: {modalidad}")
    if ciudad:
        print(f"  Filtro ciudad: {ciudad}")

    ofertas = buscar_ofertas(
        cargo=cargo,
        modalidad=modalidad,
        ciudad=ciudad,
        max_resultados=max_ofertas
    )

    if not ofertas:
        print("  ⚠ No se encontraron ofertas. Intenta con un cargo más general.")
        return {
            "perfil": perfil,
            "ofertas_encontradas": 0,
            "ofertas_califican": 0,
            "resultados": []
        }

    print(f"  ✓ {len(ofertas)} ofertas encontradas")

    # ── PASO 4: Evaluar y rankear ──────────────────────────────────
    print(f"\n[3/3] Evaluando ofertas con IA...")

    resultados = evaluar_todas(
        perfil=perfil,
        ofertas=ofertas,
        requisitos_no_cumple=requisitos_no_cumple or []
    )

    # ── RESUMEN FINAL ──────────────────────────────────────────────
    print("\n═══════════════════════════════════════════")
    print(f"  RESULTADOS: {len(resultados)} ofertas que califican")
    print("═══════════════════════════════════════════\n")

    for i, r in enumerate(resultados, 1):
        o = r["oferta"]
        print(f"  {i}. [{r['puntaje']}%] {o['titulo']} — {o['empresa']}")
        print(f"     {o['modalidad']} | {o['ubicacion']}")
        print(f"     {r['explicacion']}")
        print(f"     → {o['url']}\n")

    return {
        "perfil": perfil,
        "ofertas_encontradas": len(ofertas),
        "ofertas_califican": len(resultados),
        "resultados": resultados
    }


# ─────────────────────────────────────────
# Prueba desde terminal
# ─────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python orchestrator.py ruta/cv.pdf [cargo] [modalidad] [ciudad]")
        print("Ejemplo: python orchestrator.py mi_cv.pdf 'marketing manager' remote Santiago")
        sys.exit(1)

    pdf = sys.argv[1]
    cargo = sys.argv[2] if len(sys.argv) > 2 else None
    mod = sys.argv[3] if len(sys.argv) > 3 else None
    ciu = sys.argv[4] if len(sys.argv) > 4 else None

    buscar_trabajo(pdf_path=pdf, cargo_buscado=cargo, modalidad=mod, ciudad=ciu)
