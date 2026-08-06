# 🎯 Buscador de Trabajo con IA — Instrucciones

## ¿Qué hace esta app?
1. Subes tu CV en PDF
2. La IA extrae tu perfil automáticamente
3. Busca ofertas en Get on Board según tu cargo y filtros
4. Evalúa cada oferta contra tu perfil y te devuelve las mejores rankeadas

---

## Instalación (solo la primera vez)

### Paso 1 — Instalar Python
Si no tienes Python: https://www.python.org/downloads/
Versión recomendada: 3.11 o superior

### Paso 2 — Abrir Terminal en esta carpeta
1. Abre Terminal (Cmd + Espacio → "Terminal")
2. Escribe: `cd ~/Desktop/"Eduardo Claude"/"busqueda de trabajo con IA"`
3. Enter

### Paso 3 — Instalar las librerías
```bash
pip install -r requirements.txt
```

### Paso 4 — Configurar tu API Key
1. Ve a https://console.anthropic.com → API Keys → Create Key
2. Copia el archivo `.env.example` y renómbralo `.env`
3. Abre `.env` y reemplaza el valor con tu API key real

```bash
cp .env.example .env
```

Luego edita `.env` con cualquier editor de texto.

---

## Correr la app

```bash
streamlit run app.py
```

Se abrirá automáticamente en tu navegador en http://localhost:8501

---

## Estructura del proyecto

```
busqueda de trabajo con IA/
├── app.py                    ← Interfaz web (aquí corres la app)
├── requirements.txt          ← Librerías necesarias
├── .env                      ← Tu API key (no compartir)
├── .env.example              ← Plantilla de configuración
└── agents/
    ├── cv_extractor.py       ← Agente 1: Lee tu CV
    ├── job_scraper.py        ← Agente 2: Busca ofertas
    ├── job_evaluator.py      ← Agente 3: Evalúa el fit
    └── orchestrator.py       ← Orquestador: coordina todo
```

---

## Uso desde terminal (sin interfaz web)

```bash
python agents/orchestrator.py tu_cv.pdf "marketing manager" remote Santiago
```

---

## Problemas comunes

**Error: "ANTHROPIC_API_KEY not set"**
→ Asegúrate de haber creado el archivo `.env` con tu API key

**Error al instalar pymupdf**
→ Prueba: `pip install pymupdf --upgrade`

**No encuentra ofertas**
→ Prueba un cargo más genérico (ej: "marketing" en vez de "marketing digital B2B")
