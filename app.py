"""
INTERFAZ WEB — Buscador de Trabajo con IA
------------------------------------------
Corre con: streamlit run app.py
"""

import streamlit as st
import sys
import os

# Desactivar proxies que bloquean conexiones de Python
for var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
    os.environ.pop(var, None)

# Inyectar secrets de Streamlit Cloud como variables de entorno
try:
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
except Exception:
    pass  # En local no hay secrets, usa el .env

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.orchestrator import buscar_trabajo

# ─────────────────────────────────────────
# CONFIGURACIÓN DE LA PÁGINA
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Buscador de Trabajo con IA",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Buscador de Trabajo con IA")
st.markdown("Sube tu CV y la IA busca y evalúa ofertas de trabajo según tu perfil.")

# ─────────────────────────────────────────
# SIDEBAR — FILTROS
# ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Filtros de búsqueda")

    cargo_buscado = st.text_input(
        "¿Qué cargo buscas?",
        placeholder="ej: Marketing Manager, Data Analyst...",
        help="Si lo dejas vacío, se usa tu cargo actual del CV"
    )

    modalidad = st.selectbox(
        "Modalidad",
        options=["Cualquiera", "Remoto", "Híbrido", "Presencial"],
        index=0
    )

    ciudad = st.text_input(
        "Ciudad (opcional)",
        placeholder="ej: Santiago, Buenos Aires...",
    )

    requisitos_no_cumple = st.text_area(
        "Requisitos que sabes que NO cumples (opcional)",
        placeholder="ej: inglés avanzado, Python, 10 años de experiencia...",
        help="Separa cada requisito con una coma"
    )

    max_ofertas = st.slider("Máximo de ofertas a buscar", 10, 50, 20)

    st.divider()
    st.caption("Powered by Claude AI + Get on Board")

# ─────────────────────────────────────────
# ÁREA PRINCIPAL
# ─────────────────────────────────────────
cv_file = st.file_uploader(
    "📄 Sube tu CV en PDF",
    type=["pdf"],
    help="Tu CV se procesa localmente y no se almacena"
)

buscar_btn = st.button("🔍 Buscar trabajos", type="primary", use_container_width=True)

# ─────────────────────────────────────────
# PROCESO PRINCIPAL
# ─────────────────────────────────────────
if buscar_btn:
    if not cv_file:
        st.error("⚠️ Por favor sube tu CV antes de buscar.")
        st.stop()

    # Preparar parámetros
    mod_map = {"Cualquiera": None, "Remoto": "remote", "Híbrido": "hybrid", "Presencial": "onsite"}
    mod_valor = mod_map.get(modalidad)
    ciudad_valor = ciudad.strip() if ciudad.strip() else None
    cargo_valor = cargo_buscado.strip() if cargo_buscado.strip() else None
    no_cumple = [r.strip() for r in requisitos_no_cumple.split(",")] if requisitos_no_cumple.strip() else []

    # Ejecutar con progress bar
    with st.spinner("Leyendo tu CV..."):
        progress = st.progress(0, text="Extrayendo perfil del CV...")

        try:
            pdf_bytes = cv_file.read()
            progress.progress(20, text="Perfil extraído. Buscando ofertas...")

            # Llamar al orquestador
            # Necesitamos interceptar el progreso, así que lo hacemos en pasos
            from agents.cv_extractor import extraer_perfil_desde_bytes
            from agents.job_scraper import buscar_ofertas
            from agents.job_evaluator import evaluar_todas

            # Paso 1: Extraer perfil
            perfil = extraer_perfil_desde_bytes(pdf_bytes)
            progress.progress(33, text=f"Perfil de {perfil.get('nombre', 'candidato')} extraído. Buscando ofertas...")

            # Paso 2: Buscar ofertas
            cargo = cargo_valor or perfil.get("cargo_actual", "")
            ofertas = buscar_ofertas(cargo=cargo, modalidad=mod_valor, ciudad=ciudad_valor, max_resultados=max_ofertas)
            progress.progress(66, text=f"{len(ofertas)} ofertas encontradas. Evaluando con IA...")

            # Paso 3: Evaluar
            resultados = evaluar_todas(perfil=perfil, ofertas=ofertas, requisitos_no_cumple=no_cumple)
            progress.progress(100, text="¡Listo!")

        except Exception as e:
            st.error(f"❌ Error durante la búsqueda: {str(e)}")
            st.exception(e)
            st.stop()

    # ─────────────────────────────────────────
    # MOSTRAR PERFIL EXTRAÍDO
    # ─────────────────────────────────────────
    st.divider()

    with st.expander("👤 Tu perfil extraído del CV", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Nombre:** {perfil.get('nombre', 'N/A')}")
            st.markdown(f"**Cargo:** {perfil.get('cargo_actual', 'N/A')}")
            st.markdown(f"**Experiencia:** {perfil.get('años_experiencia', 0)} años")
            st.markdown(f"**Ubicación:** {perfil.get('ubicacion', 'N/A')}")
            st.markdown(f"**Educación:** {perfil.get('nivel_educacion', 'N/A')}")
        with col2:
            st.markdown(f"**Skills:** {', '.join(perfil.get('skills', []))}")
            st.markdown(f"**Idiomas:** {', '.join(perfil.get('idiomas', []))}")
            st.markdown(f"**Industrias:** {', '.join(perfil.get('industrias', []))}")
        st.markdown(f"**Resumen:** {perfil.get('resumen', 'N/A')}")

    # ─────────────────────────────────────────
    # MOSTRAR RESULTADOS
    # ─────────────────────────────────────────
    st.subheader(f"🏆 {len(resultados)} ofertas que califican para ti")
    st.caption(f"De {len(ofertas)} ofertas encontradas | Ordenadas por % de fit")

    if not resultados:
        st.warning("No se encontraron ofertas que califiquen con tu perfil. Intenta con un cargo más general o sin filtros de modalidad.")
        st.stop()

    for i, r in enumerate(resultados, 1):
        oferta = r["oferta"]
        puntaje = r["puntaje"]

        # Color del puntaje
        if puntaje >= 80:
            color = "🟢"
        elif puntaje >= 65:
            color = "🟡"
        else:
            color = "🟠"

        with st.container(border=True):
            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"### {i}. {oferta['titulo']}")
                st.markdown(f"**{oferta['empresa']}** · {oferta['modalidad']} · {oferta['ubicacion']} · *{oferta['fuente']}*")

            with col2:
                st.metric(label="Fit", value=f"{color} {puntaje}%")

            st.markdown(f"_{r['explicacion']}_")

            col_f, col_b = st.columns(2)
            with col_f:
                if r.get("fortalezas"):
                    st.markdown("**✅ Fortalezas:**")
                    for f in r["fortalezas"]:
                        st.markdown(f"- {f}")
            with col_b:
                if r.get("brechas"):
                    st.markdown("**⚠️ Brechas:**")
                    for b in r["brechas"]:
                        st.markdown(f"- {b}")

            if r.get("recomendacion"):
                st.info(f"💡 **Consejo:** {r['recomendacion']}")

            st.link_button("Ver oferta completa →", oferta["url"], use_container_width=False)
