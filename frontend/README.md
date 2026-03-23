# MCP-201 Frontend

`frontend` is the small Next.js app for `mcp-201`. The browser never talks directly to Gemini or to local Python code. Instead:

1. the browser uploads files and the natural-language prompt
2. the Next.js server route connects to the `mcp-201` MCP server
3. it calls `run_prompt_workflow`
4. it renders the returned outputs and workflow metadata

## Environment variables

Create `frontend/.env.local`:

```dotenv
MCP_SERVER_URL=http://localhost:8010/mcp
MCP_SHARED_AUTH_TOKEN=
NEXT_PUBLIC_APP_NAME=MCP-201 Web
```

## Local development

From the repo root:

```bash
./scripts/setup_local.sh
./scripts/run_frontend.sh
```

Open:

```text
http://localhost:3004
```

## Deployment

Deploy this app to Vercel.

Set:

- `MCP_SERVER_URL`
- `MCP_SHARED_AUTH_TOKEN`
- optional `NEXT_PUBLIC_APP_NAME`

`MCP_SERVER_URL` should be the deployed backend endpoint, for example:

```text
https://your-railway-domain.up.railway.app/mcp
```
