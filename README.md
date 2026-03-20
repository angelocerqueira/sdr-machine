# SDR Machine

Plataforma completa de prospecção automatizada para agências digitais e freelancers. Encontra negócios locais no Google Maps, analisa seus sites, gera landing pages personalizadas com IA e cria mensagens de outreach prontas para WhatsApp.

## Como Funciona

O SDR Machine opera em um pipeline de 4 etapas:

```
Scraping → Enriquecimento → Geração de LP → Outreach
```

1. **Scraping** — Busca negócios locais no Google Maps via Apify (nome, telefone, site, rating, avaliações)
2. **Enriquecimento** — Analisa o site de cada lead (SSL, responsividade, PageSpeed, CTAs) e calcula um score de oportunidade (quanto pior o site, maior a oportunidade)
3. **Geração de LP** — Cria uma landing page personalizada para o negócio usando a API do Claude, servindo como demonstração de trabalho
4. **Outreach** — Gera sequência de 3 mensagens (inicial + 2 follow-ups) com links de WhatsApp prontos para envio

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Banco de Dados | PostgreSQL 16 |
| IA | Claude API (Anthropic) — geração de landing pages |
| Scraping | Apify (Google Places crawler) |
| Infra | Docker, Docker Compose, Railway (deploy) |

## Pré-requisitos

- Docker e Docker Compose
- Token da [Apify](https://apify.com) (para scraping do Google Maps)
- Chave de API da [Anthropic](https://console.anthropic.com) (para geração de LPs)
- Node.js 20+ (para desenvolvimento do frontend)

## Setup

### 1. Variáveis de ambiente

```bash
cp backend/.env.example backend/.env
```

Edite o `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sdr_machine
APIFY_TOKEN=seu_token_apify
ANTHROPIC_API_KEY=sua_chave_anthropic
BUSINESS_NAME=Nome da Sua Agência
YOUR_NAME=Seu Nome
YOUR_WHATSAPP=5549999999999
YOUR_EMAIL=seu@email.com
YOUR_WEBSITE=https://seusite.com
```

Para o frontend, crie `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Subir com Docker Compose

```bash
docker compose up -d
```

Isso inicia o PostgreSQL na porta `5432` e a API na porta `8000` com hot-reload.

### 3. Frontend (desenvolvimento)

```bash
cd frontend
npm install
npm run dev
```

Frontend disponível em `http://localhost:3000`.

## Arquitetura

```
sdr-machine/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS + routers
│   │   ├── config.py            # Settings via pydantic-settings (.env)
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py            # Job, Lead, OutreachMessage
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── leads.py         # CRUD de leads + servir LP como HTML
│   │   │   ├── dashboard.py     # Estatísticas agregadas
│   │   │   ├── pipeline.py      # Endpoints de pipeline + SSE streaming
│   │   │   └── settings.py      # Configurações (read-only)
│   │   └── pipeline/
│   │       ├── scraper.py       # Google Maps via Apify
│   │       ├── enricher.py      # Análise de site + score de oportunidade
│   │       ├── generator.py     # Geração de LP via Claude API
│   │       └── outreach.py      # Geração de mensagens WhatsApp
│   ├── alembic/                 # Migrations do banco
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/                 # Pages (Dashboard, Kanban, Lead detail, Jobs)
│       ├── components/          # Sidebar, KanbanBoard, PipelineControls, etc.
│       └── lib/                 # API client + TypeScript types
├── docker-compose.yml
└── Dockerfile                   # Build de produção (Railway)
```

## API

Base URL: `http://localhost:8000/api`

### Leads

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/leads` | Lista leads (filtros: `status`, `nicho`, `cidade`, `score_min`) |
| `GET` | `/api/leads/{id}` | Detalhe do lead |
| `GET` | `/api/leads/{id}/lp` | Renderiza a landing page gerada (HTML) |
| `GET` | `/api/leads/{id}/messages` | Mensagens de outreach do lead |
| `PATCH` | `/api/leads/{id}` | Atualiza status do lead |
| `DELETE` | `/api/leads/{id}` | Remove lead |

### Pipeline

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/pipeline/scrape` | Inicia scraping (nichos, cidades, max_results) |
| `POST` | `/api/pipeline/enrich` | Inicia enriquecimento de leads |
| `POST` | `/api/pipeline/generate` | Inicia geração de landing pages |
| `POST` | `/api/pipeline/outreach` | Inicia geração de mensagens |

### Jobs

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/jobs` | Lista jobs com paginação |
| `GET` | `/api/jobs/{id}` | Detalhe do job |
| `GET` | `/api/jobs/{id}/stream` | SSE stream de progresso em tempo real |

### Outros

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/dashboard/stats` | Estatísticas do dashboard |
| `GET` | `/api/settings` | Configurações atuais |

## Pipeline de Leads (Status)

Cada lead passa pelos seguintes status no board Kanban:

```
scraped → enriched → lp_generated → outreach_ready → outreach_sent → responded → in_call → closed → delivered
```

## Score de Oportunidade

O score (0-100) mede o quão ruim é a presença digital do lead — quanto maior, melhor a oportunidade de venda:

| Critério | Pontos |
|----------|--------|
| Sem website | 95 |
| Site fora do ar / erro SSL | 85 |
| Sem HTTPS | +15 |
| Não responsivo | +15 |
| Sem WhatsApp | +10 |
| Sem CTA | +10 |
| Sem Analytics | +8 |
| Sem chatbot | +8 |
| PageSpeed < 50 | +10 |
| Conteúdo escasso | +10 |
| Template genérico | +5 |
| Poucas imagens | +5 |

## Deploy

### Railway (Backend)

O `Dockerfile` na raiz está configurado para Railway. Ele roda as migrations do Alembic automaticamente no startup e usa a variável `PORT` do Railway.

### Vercel (Frontend)

O frontend Next.js pode ser deployado na Vercel apontando `NEXT_PUBLIC_API_URL` para a URL do backend no Railway.

## Configuração

Nichos e cidades-alvo são configuráveis via variáveis de ambiente ou pelo arquivo `.env`. Valores padrão:

**Nichos:** dentista, restaurante, salão de beleza, clínica estética, pet shop, academia, barbearia, clínica veterinária, pizzaria, loja de roupas

**Cidades:** Chapecó SC, Florianópolis SC, Joinville SC, Curitiba PR, Cascavel PR

## Testes

```bash
cd backend
pytest
```
