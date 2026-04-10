# Autenticacao

## Visao Geral

O SDR Machine utiliza o [Better Auth](https://www.better-auth.com/) como solucao de autenticacao. O Better Auth e uma biblioteca open-source que gerencia sessoes, cookies e tabelas de usuario diretamente no PostgreSQL compartilhado com a aplicacao.

A autenticacao opera em duas camadas independentes:

| Camada | Tecnologia | Responsabilidade |
|--------|-----------|------------------|
| **Frontend** | Better Auth client + Next.js middleware | Verifica a presenca do cookie de sessao antes de renderizar paginas protegidas. Redireciona para `/login` se nao autenticado. |
| **Backend** | `AuthMiddleware` (Starlette) | Valida o token de sessao contra a tabela `session` no banco de dados. Retorna `401` se invalido ou expirado. |

O Better Auth server-side roda **dentro do Next.js** (em `src/lib/auth.ts`), nao no FastAPI. O backend FastAPI apenas consome os dados de sessao que o Better Auth gravou no PostgreSQL.

### Tabelas gerenciadas pelo Better Auth

O Better Auth cria e gerencia automaticamente as seguintes tabelas no PostgreSQL:

- `user` -- usuarios cadastrados (email, senha hash, etc.)
- `session` -- sessoes ativas com `token` e `expiresAt`
- `account` -- contas vinculadas (email/password e provedores OAuth)
- `verification` -- tokens de verificacao de email

---

## Frontend Auth

### Better Auth Server (`src/lib/auth.ts`)

A instancia do Better Auth server e configurada com:

```typescript
export const auth = betterAuth({
  database: new Pool({ connectionString: process.env.DATABASE_URL }),
  emailAndPassword: { enabled: true },
  session: {
    expiresIn: 60 * 60 * 24 * 30,  // 30 dias
    updateAge: 60 * 60 * 24,        // renova a cada 1 dia
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5,               // 5 minutos
    },
  },
  advanced: {
    cookies: {
      session_data: {
        attributes: { httpOnly: false },
      },
    },
  },
});
```

Pontos importantes:

- **`session.expiresIn`**: sessoes duram 30 dias.
- **`session.updateAge`**: a sessao e renovada automaticamente se o usuario acessar a aplicacao apos 24h desde a ultima renovacao.
- **`cookieCache`**: o Better Auth cria um cookie `session_data` nao-HttpOnly que contem dados da sessao em base64. Esse cookie e usado pelo frontend para extrair o token e enviar como `Authorization: Bearer` nas chamadas cross-origin ao backend.
- **`httpOnly: false`** no `session_data`: necessario para que o JavaScript consiga ler o cookie e montar o header `Authorization` para o backend FastAPI (que roda em outra origem).

### Better Auth Client (`src/lib/auth-client.ts`)

O client e criado sem configuracao adicional:

```typescript
import { createAuthClient } from "better-auth/react";
export const authClient = createAuthClient();
```

Ele se conecta automaticamente ao endpoint `/api/auth/*` do Next.js e fornece metodos como `signIn.email()` e `signOut()`.

### Route Handler (`src/app/api/auth/[...all]/route.ts`)

O catch-all route handler do Next.js delega todas as requisicoes de auth para o Better Auth:

```typescript
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";
export const { GET, POST } = toNextJsHandler(auth);
```

Isso cria endpoints como:
- `POST /api/auth/sign-in/email` -- login
- `POST /api/auth/sign-up/email` -- cadastro
- `POST /api/auth/sign-out` -- logout
- `GET /api/auth/get-session` -- verificar sessao

### Next.js Middleware (`src/middleware.ts`)

O middleware do Next.js roda em **toda requisicao** (exceto assets estaticos) e decide se o usuario pode acessar a rota:

```typescript
const PUBLIC_PATHS = ["/login", "/lp"];

function isPublicPath(pathname: string): boolean {
  if (pathname === "/favicon.ico") return true;
  if (pathname.startsWith("/_next")) return true;
  if (pathname.startsWith("/api/")) return true;
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}
```

Logica de decisao:

1. **Rota publica** (`/login`, `/lp/*`, `/api/*`, `/_next/*`, `/favicon.ico`) -- passa sem verificacao.
2. **`/login` com sessao ativa** -- redireciona para `/` (dashboard).
3. **Rota protegida sem sessao** -- redireciona para `/login`.

A verificacao usa `getSessionCookie(request)` do Better Auth, que le o cookie `better-auth.session_token` da requisicao.

### Pagina de Login (`src/app/login/page.tsx`)

A pagina de login e um formulario simples com email e senha. Usa `authClient.signIn.email()` para autenticar:

```typescript
const { error: authError } = await authClient.signIn.email({
  email,
  password,
});
```

Apos login bem-sucedido, redireciona para `/` com `router.push("/")` e `router.refresh()`.

Em caso de erro, exibe a mensagem retornada pelo Better Auth ou o fallback "Email ou senha incorretos".

### Botao de Logout (`src/components/sign-out-button.tsx`)

O componente `SignOutButton` chama `authClient.signOut()` e redireciona para `/login`:

```typescript
async function handleSignOut() {
  await authClient.signOut();
  router.push("/login");
  router.refresh();
}
```

O botao e renderizado no layout principal com o texto "Sair".

---

## Backend Auth

### AuthMiddleware (`backend/app/middleware/auth.py`)

O backend utiliza um middleware Starlette customizado (`AuthMiddleware`) que valida sessoes diretamente no banco de dados. Ele **nao** depende do Better Auth como biblioteca -- apenas consulta a tabela `session` que o Better Auth criou.

#### Registro do Middleware

Em `main.py`, o middleware e registrado com os paths publicos:

```python
app.add_middleware(
    AuthMiddleware,
    database_url=app_settings.database_url,
    public_paths=["/api/health", "/api/leads/p/", "/docs", "/openapi.json"],
)
```

#### Fluxo de Validacao

1. **OPTIONS preflight** -- sempre passa (CORS).
2. **Paths publicos** -- verifica se o path comeca com algum prefixo de `public_paths`. Se sim, passa.
3. **Extracao do token** -- tenta, nesta ordem:
   - Header `Authorization: Bearer <token>`
   - Cookie `__Secure-better-auth.session_token` (HTTPS)
   - Cookie `better-auth.session_token` (HTTP/localhost)
4. **Parse do token** -- o cookie do Better Auth tem formato `token.signature`. O middleware extrai apenas a parte antes do ponto.
5. **Consulta ao banco** -- executa SQL direto na tabela `session`:
   ```sql
   SELECT "expiresAt" FROM "session" WHERE "token" = :token
   ```
6. **Verificacao de expiracao** -- compara `expiresAt` com `datetime.now(UTC)`. Lida com datetimes naive e aware, e com strings ISO (caso do SQLite nos testes).
7. **Resultado** -- se valido, a requisicao segue. Se invalido, retorna:
   ```json
   { "detail": "Nao autenticado" }
   ```
   Com status code `401`.

#### Conexao com o Banco

O middleware cria seu proprio `SQLAlchemy Engine` (separado do engine da aplicacao) usando a mesma `DATABASE_URL`. Isso evita dependencia do sistema de dependency injection do FastAPI, ja que middlewares Starlette nao participam dele.

Para SQLite (usado nos testes), configura `check_same_thread=False` automaticamente.

---

## Fluxo Completo

Abaixo esta o fluxo completo de autenticacao, desde o acesso inicial ate as chamadas autenticadas a API:

```
1. Usuario acessa https://app.exemplo.com/kanban
         |
2. Next.js Middleware intercepta
         |
3. isPublicPath("/kanban") → false
         |
4. getSessionCookie(request) → null (primeiro acesso)
         |
5. Redireciona para /login (HTTP 307)
         |
6. Usuario preenche email e senha e submete o formulario
         |
7. authClient.signIn.email({ email, password })
         |
8. POST /api/auth/sign-in/email → Better Auth valida credenciais
         |
9. Better Auth cria registro na tabela "session" e seta cookies:
   - better-auth.session_token (HttpOnly)
   - better-auth.session_data (nao-HttpOnly, base64 com dados da sessao)
         |
10. router.push("/") → redireciona para o dashboard
         |
11. Next.js Middleware intercepta "/"
         |
12. getSessionCookie(request) → cookie presente → passa
         |
13. Pagina renderiza e chama fetchAPI("/api/dashboard/stats")
         |
14. fetchAPI() le o cookie session_data, extrai o token,
    e envia como Authorization: Bearer <token>
         |
15. Backend AuthMiddleware:
    - Extrai token do header Authorization
    - Consulta tabela "session" no PostgreSQL
    - Verifica se nao expirou
    - Permite a requisicao → retorna dados do dashboard
```

### Tratamento de 401 no Frontend

Quando o backend retorna `401`, o `fetchAPI()` em `api.ts` executa um `forceLogout()`:

1. Limpa todos os cookies que contem "better-auth" no nome.
2. Redireciona para `/login` via `window.location.replace()`.
3. Usa uma flag `redirectingToLogin` para evitar redirects duplicados quando multiplas chamadas paralelas recebem 401 simultaneamente.

---

## Rotas Publicas

### Frontend (Next.js Middleware)

| Path | Motivo |
|------|--------|
| `/login` | Pagina de login |
| `/lp/*` | Preview publico de landing pages |
| `/api/*` | Rotas internas do Next.js (auth endpoints, etc.) |
| `/_next/*` | Assets estaticos do Next.js |
| `/favicon.ico` | Favicon |

### Backend (AuthMiddleware)

| Prefixo | Motivo |
|---------|--------|
| `/api/health` | Health check (monitoramento, Railway) |
| `/api/leads/p/` | Acesso publico a leads e LPs por `public_id` (links compartilhados em outreach) |
| `/docs` | Documentacao Swagger UI (desenvolvimento) |
| `/openapi.json` | Schema OpenAPI (desenvolvimento) |

---

## Configuracao

### Variaveis de Ambiente

| Variavel | Onde | Descricao |
|----------|------|-----------|
| `DATABASE_URL` | Backend `.env` e Frontend `.env.local` | Connection string do PostgreSQL. O Better Auth (frontend) e o AuthMiddleware (backend) precisam acessar o mesmo banco para compartilhar a tabela `session`. |
| `NEXT_PUBLIC_API_URL` | Frontend `.env.local` | URL do backend. Determina se as requisicoes sao cross-origin (afeta como cookies sao enviados). |
| `FRONTEND_URL` | Backend `.env` | URL do frontend. Adicionada aos CORS origins para permitir chamadas cross-origin com credenciais. |

### CORS

O backend configura CORS em `main.py` para permitir credenciais cross-origin:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,   # localhost:3000 + FRONTEND_URL
    allow_credentials=True,       # permite envio de cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_credentials=True` e essencial para que o navegador envie os cookies do Better Auth nas requisicoes cross-origin ao backend.

### Ordem dos Middlewares

Em FastAPI/Starlette, middlewares sao executados na ordem **inversa** ao registro. No `main.py`:

1. `CORSMiddleware` (registrado primeiro → executa por ultimo na ida, primeiro na volta)
2. `AuthMiddleware` (registrado depois → executa primeiro na ida)

Na pratica, para uma requisicao que chega:
1. `AuthMiddleware` valida a sessao
2. `CORSMiddleware` adiciona os headers CORS na resposta

### Sessao e Cookies

| Parametro | Valor | Descricao |
|-----------|-------|-----------|
| Duracao da sessao | 30 dias | `session.expiresIn` no Better Auth |
| Renovacao | A cada 24h de uso | `session.updateAge` |
| Cookie cache | 5 minutos | `cookieCache.maxAge` -- evita consultas ao banco a cada requisicao |
| Cookie `session_token` | HttpOnly | Nao acessivel via JS |
| Cookie `session_data` | **Nao** HttpOnly | Acessivel via JS para extrair o token e enviar como Bearer |
| Prefixo em HTTPS | `__Secure-` | O Better Auth adiciona o prefixo automaticamente em conexoes HTTPS |
