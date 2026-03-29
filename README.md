# PiBot v1.2

Orquestador multi-agente autónomo para Blixel AI.
Cerebro en Python, músculo en n8n, accesible por Telegram (texto, voz, archivos) y dashboard web.

**68 ficheros · 142 tests · 8 workflows n8n**

---

## 1. Qué es

Un sistema que centraliza las operaciones diarias de Blixel AI sobre 9 plataformas.
No es un chatbot — es un asistente operativo que:

- **Ejecuta acciones reales**: envía emails, crea facturas, publica en redes, gestiona tareas
- **Decide con criterio**: clasifica intención, evalúa urgencia, pide confirmación cuando toca
- **Recuerda todo**: memoria semántica con embeddings, búsqueda por similitud
- **Actúa sin que le pidan**: analiza datos cada 30min, alerta sobre anomalías, genera briefings
- **Se auto-corrige**: detecta patrones de error, propone mejoras de prompts, espera aprobación
- **Tiene expertos**: 6 skills especializados (presupuestos, n8n, email marketing, IA, sistemas, proyectos)
- **Gestiona n8n**: crea, lista y activa workflows programáticamente
- **Acepta archivos**: en Telegram y dashboard, los indexa en memoria
- **Dashboard visual**: panel web con chat, audit log, alertas, workflows, memoria — con modo demo

---

## 2. Arquitectura

```
Ernesto / Marta
      │
┌─────▼──────┐     ┌──────────┐
│  Telegram   │     │ Dashboard │  /dashboard
│ texto+voz+  │     │   web     │
│  archivos   │     └─────┬────┘
└──────┬──────┘           │
       │            ┌─────▼──────────────────────────────┐
       └───────────►│           PiBot (Pi)                │
                    │                                     │
                    │  Router: skill → agente → chat      │
                    │  Security: whitelist/confirm/deny    │
                    │  Memory: PostgreSQL + pgvector       │
                    │  Background: proactivo + meta-agente │
                    └──────────┬──────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         ┌────▼───┐     ┌─────▼────┐     ┌────▼────┐
         │  n8n   │     │ Postgres │     │  Redis  │
         │webhooks│     │ pgvector │     │         │
         └────┬───┘     └──────────┘     └─────────┘
              │
    ┌─────┬──┴──┬───────┬──────┬───────┬────────┬─────────┐
  Gmail  YT   Meta    WP   Holded  Notion   Notion    Calendar
                                   Tasks     CRM
```

---

## 3. Estructura del código

```
pibot/
├── main.py                         FastAPI v1.2
├── config.py                       pydantic-settings
├── heartbeat.py                    Cron cada 30min
│
├── orchestrator/                   CEREBRO
│   ├── graph.py                    LangGraph StateGraph
│   ├── llm.py                      Cliente OpenRouter
│   ├── router.py                   Routing: skill → agente → conversacional
│   └── prompts.py                  System prompts
│
├── agents/                         8 CLIENTES N8N
│   ├── base.py                     AgentClient: HTTP + retry
│   ├── gmail.py, youtube.py, meta.py, wordpress.py
│   ├── holded.py, notion_tasks.py, notion_crm.py, calendar.py
│
├── skills/                         6 EXPERTOS
│   ├── base.py                     Framework de skills
│   └── experts.py                  project, n8n, email, budget, ai, sysadmin
│
├── services/                       SERVICIOS
│   ├── stt.py, tts.py              Voz (Whisper + TTS)
│   ├── alerts.py                   4 niveles de urgencia
│   ├── proactive.py                6 checks periódicos
│   ├── meta_agent.py               Auto-corrección de prompts
│   ├── n8n_api.py                  CRUD workflows n8n
│   └── files.py                    Upload + indexación
│
├── security/                       SEGURIDAD
│   ├── whitelist.py                auto / confirm / denied
│   ├── audit.py                    Log inmutable
│   └── confirmation.py             Redis + Telegram
│
├── memory/                         PERSISTENCIA
│   ├── postgres.py                 8 tablas
│   ├── redis_client.py             Sesiones + TTL
│   └── embeddings.py               pgvector 1536D
│
├── interfaces/
│   ├── telegram_bot.py             Texto + voz + archivos
│   └── websocket.py                Tiempo real
│
├── api/routes.py                   22 endpoints
├── static/dashboard.html           Panel visual + modo demo
├── n8n-workflows/                  8 workflows importables
├── tests/                          142 tests
│
├── docker-compose.yml              4 servicios
├── Dockerfile, init.sql, init-n8n.sql
└── .env.example, .env.production
```

---

## 4. Deploy paso a paso

### Requisitos previos
- VPS con EasyPanel (o Docker Compose)
- Cuenta GitHub
- API key OpenRouter (openrouter.ai)
- API key OpenAI (para voz)
- Bot Telegram (@BotFather)

### Paso 1 — Subir a GitHub

```bash
cd pibot
git init && git add -A
git commit -m "PiBot v1.2"
gh repo create pibot --private --source=. --push
```

### Paso 2 — Crear proyecto EasyPanel

**+ Create Project** → nombre: `pibot`

### Paso 3 — PostgreSQL

1. **+ Service** → Database → Postgres
2. Image: `pgvector/pgvector:pg16`, DB: `pibot`, User: `pibot`
3. Terminal:
```bash
psql -U pibot -d pibot
CREATE DATABASE n8n OWNER pibot;
```
4. Pegar `init.sql` → verificar con `\dt` (8 tablas)

### Paso 4 — Redis

**+ Service** → Database → Redis → `redis:7-alpine`

### Paso 5 — n8n

1. **+ Service** → App → Docker Image: `n8nio/n8n:latest`, Port: 5678
2. Environment:
```
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres.pibot.internal
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=pibot
DB_POSTGRESDB_PASSWORD=TU_PASSWORD
GENERIC_TIMEZONE=Europe/Madrid
```
3. Dominio: `n8n.TU_DOMINIO`
4. Importar 8 workflows → configurar credenciales → activar

### Paso 6 — PiBot

1. **+ Service** → App → GitHub: `pibot`, Dockerfile
2. Environment:
```
DATABASE_URL=postgresql+asyncpg://pibot:PASSWORD@postgres.pibot.internal:5432/pibot
REDIS_URL=redis://redis.pibot.internal:6379/0
N8N_BASE_URL=http://n8n.pibot.internal:5678
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
AGENT_AUTH_TOKEN=genera_con_openssl_rand_hex_32
ENVIRONMENT=production
```
3. Dominio: `pi.TU_DOMINIO`

### Paso 7 — Verificar

```bash
curl https://pi.TU_DOMINIO/health
# Dashboard: https://pi.TU_DOMINIO/dashboard
# Telegram: /start al bot
```

### Orden: PostgreSQL → Redis → n8n → PiBot

---

## 5. Dashboard

Accede a `/dashboard` o abre `static/dashboard.html` directamente.

**Modo demo**: si cancelas el prompt del token, el dashboard se carga con datos ficticios para previsualizar la interfaz sin backend.

Secciones: Overview, Audit Log, Alertas, Workflows n8n, Skills, Memoria semántica, Prompts, Chat con Pi.

---

## 6. API — 22 endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/dashboard` | Panel visual |
| POST | `/message` | Procesar mensaje |
| POST | `/confirm` | Confirmar acción |
| GET | `/history/{session}` | Historial |
| GET | `/audit` | Audit log |
| GET | `/memory/search` | Búsqueda semántica |
| GET | `/alerts` | Alertas |
| GET/POST | `/prompts/*` | Gestión de prompts |
| GET | `/skills` | Skills expertos |
| GET/POST | `/n8n/*` | CRUD workflows n8n |
| POST | `/upload` | Subir archivo |
| WS | `/ws` | WebSocket tiempo real |

---

## 7. Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
# 142 passed
```
