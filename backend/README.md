# MCP-201 Backend

`backend` is the independent Python MCP server for `mcp-201`. It exposes its own crop, colorize, and prompt-driven workflow tools, and it uses AI planning for prompt routing when a Gemini key is available.

## Routing behavior

`mcp-201` uses AI planning first and falls back to heuristics only if no planner key is available or the model output is invalid.

## Environment variables

Create `backend/.env`:

```dotenv
MCP_201_SERVER_GEMINI_API_KEY=your_server_gemini_key
MCP_201_PLANNER_MODEL=gemini-2.5-flash
MCP_201_IMAGE_MODEL=gemini-3.1-flash-image-preview
MCP_201_REQUIRE_AUTH=false
MCP_201_PORT=8010
```

## Local development

From the repo root:

```bash
./scripts/setup_local.sh
./scripts/run_backend.sh
```

Default endpoints:

- MCP: `http://localhost:8010/mcp`
- health: `http://localhost:8010/healthz`

## Railway deployment

One-time setup:

```bash
npm install -g @railway/cli
railway login
cd backend
railway link
```

Set required variables:

```bash
railway variables set MCP_201_SERVER_GEMINI_API_KEY=your_server_gemini_key
railway variables set MCP_201_PLANNER_MODEL=gemini-2.5-flash
railway variables set MCP_201_IMAGE_MODEL=gemini-3.1-flash-image-preview
railway variables set MCP_201_REQUIRE_AUTH=true
railway variables set MCP_201_AUTH_TOKEN=your_long_random_token
```

Deploy:

```bash
./scripts/deploy_railway.sh
```

Your final MCP endpoint will look like:

```text
https://your-railway-domain.up.railway.app/mcp
```
