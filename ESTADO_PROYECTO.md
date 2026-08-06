# Estado del Proyecto: App SaaS Búsqueda de Trabajo con IA

## Descripción General
Web app SaaS que ayuda al usuario a encontrar trabajo usando IA.
- El usuario sube su CV (PDF)
- La app extrae su perfil automáticamente (experiencia, skills, ubicación, años)
- El usuario define filtros: modalidad (remoto/híbrido), ciudad, requisitos que no cumple
- La app busca ofertas en Get on Board, LinkedIn, Chiletrabajos, y otras webs con agentes IA en paralelo
- Cada oferta se evalúa automáticamente contra el perfil del usuario
- Se devuelven solo las que califican, rankeadas por fit, con explicación

## Perfil Técnico del Desarrollador
- Nunca ha desarrollado una app antes
- Conocimiento básico de APIs
- Quiere aprender mientras construye
- Mac Desktop

## Stack Tecnológico (decidido)
- **Frontend/UI:** Streamlit (Python, fácil para no desarrolladores)
- **Backend/IA:** Python + Anthropic API (Claude)
- **Extracción CV:** PyPDF2 o similar
- **Scraping/búsqueda:** Agentes IA en paralelo

## Lo que está HECHO ✅
1. Definición del proyecto y arquitectura general
2. Instalación del entorno (Python, pip, dependencias)
3. API Key de Anthropic configurada en archivo `.env`
4. Archivo `app.py` creado con Streamlit
5. Extractor de CV funcionando (lee PDF y extrae perfil con Claude)
6. Buscador de ofertas con API de Adzuna (reemplazó Get on Board que estaba caído)
7. Evaluador de fit funcionando (compara perfil vs oferta, da % y explica brechas)
8. App completa corriendo en http://localhost:8501 ✅

## Credenciales en .env
- ANTHROPIC_API_KEY — API de Claude (extracción CV + evaluación)
- ADZUNA_APP_ID=2ff10c7c
- ADZUNA_APP_KEY=8fc13fca21fbed10e9cf5ba89fd4bb03

## Problema resuelto: proxy SSL
Para correr la app siempre usar:
```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && streamlit run app.py
```

## App en la nube ☁️
URL: https://buscador-trabajo-ia-lofwra3zhwuxvplwsmimjt.streamlit.app
GitHub: https://github.com/Eduardoemprende/buscador-trabajo-ia

## Próximos pasos posibles ⏭️
- Agregar más fuentes de trabajo con mejor cobertura en Chile (Trabajando.com, Laborum.cl)
- Mejorar el UI/diseño
- Guardar historial de búsquedas
- Agregar login de usuarios para versión SaaS

## Carpeta del Proyecto
Guardar todos los archivos del proyecto en: Desktop > "Eduardo Claude" > "busqueda de trabajo con IA"

## Historial de Chats
- Chat 1: "roadmap paso a paso" — Arquitectura, setup del entorno, API key, primera corrida de app.py
- Chat 2 (este): Retomando desde aquí

---
*Actualizar este archivo al final de cada sesión de trabajo*
