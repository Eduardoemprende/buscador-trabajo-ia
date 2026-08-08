# ESTADO DEL PROYECTO — Buscador de Trabajo con IA

## URLs importantes
- **App en producción:** https://buscador-trabajo-ia-lofwra3zhwuxvplwsmimjt.streamlit.app/
- **GitHub:** https://github.com/Eduardoemprende/buscador-trabajo-ia

## Stack
- Python + Streamlit (frontend y lógica)
- Anthropic API (Claude Opus para extraer CV, Claude Haiku para evaluar ofertas)
- ScraperAPI (proxy rotativo con JS rendering para portales bloqueados)
- GitHub → Streamlit Cloud (deploy automático)

## Credenciales (en .env local Y en Streamlit Secrets)
- ANTHROPIC_API_KEY — en .env y Streamlit Secrets
- SCRAPER_API_KEY = ab69ca426738cba4be217b51cd4406d1 — en .env y Streamlit Secrets
- JOOBLE_API_KEY — pendiente: registrar en https://jooble.org/api/about (gratis, agrega LinkedIn)

## Estructura de archivos
```
busqueda de trabajo con IA/
├── app.py                      # UI principal Streamlit
├── agents/
│   ├── cv_extractor.py         # Agente 1: extrae perfil del CV (Claude Opus)
│   ├── job_scraper.py          # Agente 2: busca ofertas en portales
│   ├── job_evaluator.py        # Agente 3: evalúa fit (Claude Haiku, threshold 50%)
│   └── orchestrator.py         # Coordina los 3 agentes
├── pages/
│   └── diagnostico_nube.py     # Página de diagnóstico (borrar cuando todo funcione)
├── requirements.txt
├── .env                        # Local solamente, NO está en GitHub
└── ESTADO_PROYECTO.md          # Este archivo
```

## Fuentes de trabajo — Estado actual (agosto 2026)

### ✅ HTML estático — siempre funcionan
| Portal | URL de búsqueda | Observaciones |
|--------|----------------|---------------|
| **Chiletrabajos.cl** | `/trabajos/{keyword}` | Confirmado 200 OK |
| **Computrabajo** | `cl.computrabajo.com/trabajo-de-{keyword}` | ⚠️ Dominio correcto: cl.computrabajo.com (no www.computrabajo.cl) |
| **Indeed.cl** | `cl.indeed.com/jobs?q={keyword}&l=Santiago` | ✅ Nuevo, 15+ ofertas relevantes, HTML estático |
| **Remotive.com API** | API pública sin key | Empleos remotos globales |
| **Jobicy.com API** | API pública sin key | Empleos remotos globales |

### ⚠️ Requieren JS / validación en producción
| Portal | URL correcta | Estado |
|--------|----------------|--------|
| **Laborum.cl** | `/empleos-area-{area}.html` | CSR puro. ScraperAPI bloqueado ("blocked-by-allowlist"). Código intenta request directo primero → **probar si funciona desde Streamlit Cloud**. URL área marketing: `/empleos-area-marketing-y-publicidad.html` ✅ confirmada |
| **Trabajando.cl** | `/empleos?q={keyword}` | URL confirmada, selectores y acceso por validar en producción |
| **Get on Board** | `/jobs/{categoria}` | API cerró (401), usando scrape web con render=true |
| **BNE** | `bne.gob.cl/ofertas?mostrar=empleo&textoLibre={keyword}&numResultadosPorPagina=20&clasificarYPaginar=true` | Sin login ✅ 84 ofertas de marketing. Página Angular, requiere render=true. Detalle: `/oferta/{id}` |

### ⏳ Pendiente de activar (requiere registro gratuito)
| Portal | Acción requerida |
|--------|----------------|
| **Jooble API** | Registrar en https://jooble.org/api/about → agregar JOOBLE_API_KEY en .env y Streamlit Secrets. Agrega LinkedIn + múltiples portales. |

### ❌ Descartados definitivamente
| Portal | Razón |
|--------|-------|
| LinkedIn | Requiere login, no scrapeable legalmente |
| BNE (bne.gob.cl) | Búsqueda por keyword requiere login de usuario |
| Bumeran.cl | Redirige a Laborum.cl — mismo portal |
| Indeed (403) | Reemplazado por cl.indeed.com que sí funciona |
| Adzuna | Solo España/UK/US |

## Cómo funciona ScraperAPI
- **Sin render=true**: 1 crédito, para HTML estático (Chiletrabajos, Computrabajo, Indeed)
- **Con render=true**: 5-10 créditos, renderiza JS (Laborum, Trabajando, GOB)
- Free tier: 5.000 requests/mes
- URL: `http://api.scraperapi.com?api_key={KEY}&url={url_encoded}&render=true`

## Evaluador de ofertas
- Modelo: Claude Haiku (velocidad)
- Threshold: >= 50% de fit para aparecer en resultados (era 40%)
- Contexto por oferta: 2500 chars de descripción (era 1000)

## Pre-filtro de relevancia
Antes de evaluar con Claude, el código filtra por keywords del área.
Para "marketing" solo pasan ofertas con: marketing, digital, SEO, community, publicidad, etc.
Evita gastar tokens en ofertas irrelevantes.

## Próximos pasos (en orden)
1. **Commit y deploy** del job_scraper.py (Laborum refactorizado) → verificar en producción si Streamlit Cloud puede acceder a Laborum directamente
2. **Si Laborum sigue fallando en producción**: evaluar upgrade ScraperAPI o switch a Zenrows/Bright Data que sí soportan Laborum
3. **Trabajando.cl y GOB**: mismo proceso — verificar acceso desde Streamlit Cloud, ajustar si es necesario
4. **Registrar en Jooble API** → agregar JOOBLE_API_KEY → agrega LinkedIn y más fuentes
5. **Borrar diagnostico_nube.py** cuando todo funcione bien

## Hallazgos técnicos importantes (agosto 2026)
- **Laborum URL correcta**: `/empleos-area-{area}.html` (la antigua `/area-{area}/empleos.html` da 404)
- **Laborum es CSR**: HTML crudo no tiene jobs. JS los inyecta. JSON-LD generado por React.
- **ScraperAPI bloquea Laborum**: "blocked-by-allowlist" — problema de plan, no de código
- **Sandbox de desarrollo**: proxy local bloquea Laborum y otras URLs — no refleja comportamiento de Streamlit Cloud
- **Selectores DOM de Laborum**: `a[href*="/empleos/"]` → `.parent` → `h2`=título, `h3[1]`=empresa, `h3[2]`=ubicación, `h3[3]`=modalidad ✅ confirmados

## Último commit
"Laborum refactor: URL /empleos-area-{area}.html, request directo primero + ScraperAPI fallback, JSON-LD parsing" — agosto 2026
