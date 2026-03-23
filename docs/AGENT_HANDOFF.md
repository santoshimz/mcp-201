# MCP-201 Agent Handoff

This document is the fastest way to onboard a new agent to `mcp-201`.

## What `mcp-201` does

`mcp-201` is a standalone image workflow system with two apps:

- a Python MCP backend that exposes image tools
- a Next.js frontend that lets a user upload images and invoke those tools through a prompt-first UI

The key behavior is prompt-driven workflow selection. Instead of hardcoding one route for every user action, `mcp-201` accepts a natural-language prompt and chooses one of these workflows:

- `crop_images`
- `colorize_images`
- `crop_then_colorize`

If a Gemini key is available, the backend uses AI planning to choose the workflow. If not, it falls back to a heuristic router.

## Repo layout

```text
mcp-201/
  backend/                     Python MCP server
  frontend/                    Next.js web UI
  examples/readme-assets/      README artwork
  scripts/                     root setup, run, test, deploy wrappers
  README.md                    high-level repo docs
  docs/AGENT_HANDOFF.md        this handoff doc
```

## Architecture

### High-level flow

1. A user opens the frontend and uploads one or more images.
2. The frontend sends the prompt, files, credential mode, and optional Gemini key to `frontend/app/api/run-workflow/route.ts`.
3. That server route normalizes files and calls the backend MCP tool `run_prompt_workflow`.
4. The backend planner chooses a workflow.
5. The backend executes one of the image workflows and returns structured output.
6. The frontend renders output images and planner warnings.

### Backend architecture

Main entrypoint:

- `backend/src/mcp_201_server.py`

Responsibilities:

- starts the FastMCP server
- exposes `crop_images`, `colorize_images`, and `run_prompt_workflow`
- mounts `/healthz`
- applies auth middleware and CORS

Important backend modules:

- `backend/src/server/tool_handlers.py`
  - validates payloads
  - decodes and verifies images
  - runs crop/colorize/composite workflows
  - attaches metadata like `selected_workflow` and `warnings`
- `backend/src/server/prompt_planner.py`
  - AI-first prompt routing
  - heuristic fallback when no planner key is available or the planner response fails
- `backend/src/server/request_models.py`
  - Pydantic schemas for image inputs, prompt requests, and tool responses
- `backend/src/server/config.py`
  - loads env configuration such as port, auth, CORS origins, limits, and default Gemini models
- `backend/src/server/credential_resolver.py`
  - enforces `server` vs `byok` credential mode
- `backend/src/server/auth.py`
  - optional bearer-token auth for the MCP endpoint
- `backend/src/skills/crop_images.py`
  - crop implementation
- `backend/src/skills/colorize_images.py`
  - Gemini-backed colorization implementation

### Frontend architecture

Main UI:

- `frontend/app/page.tsx`

Bridge from web UI to MCP:

- `frontend/app/api/run-workflow/route.ts`
- `frontend/lib/mcp-client.ts`

Responsibilities:

- collect prompt, files, credential mode, optional BYOK key, and optional model override
- convert uploads to base64 payloads
- connect to the MCP backend over Streamable HTTP
- call `run_prompt_workflow`
- render structured results and warnings

Important frontend note:

- the browser does not talk directly to Gemini
- the Next.js server route is the bridge between the browser and the MCP backend

## Public behavior and contracts

### MCP tools

The backend exposes these MCP tools:

- `crop_images(images)`
- `colorize_images(images, credential_mode, gemini_api_key, prompt, model)`
- `run_prompt_workflow(prompt, images, credential_mode, gemini_api_key, model)`

### Input constraints

From `backend/src/server/request_models.py` and config:

- supported input extensions: `.jpg`, `.jpeg`, `.png`, `.webp`
- filenames cannot contain path separators
- at least 1 image is required
- default max images: `5`
- default max file size per image: `6 MB`

### Credential modes

- `server`
  - backend uses `MCP_201_SERVER_GEMINI_API_KEY`
  - request must not include `geminiApiKey`
- `byok`
  - caller provides `geminiApiKey`
  - required for `colorize_images` and for prompt workflows when the caller wants their own key used

Planner credential behavior:

- if the request is `byok` and includes a key, the planner uses that key
- otherwise, if the server key exists, the planner uses the server key
- otherwise, routing falls back to heuristics

### Output shape

Tool responses include:

- `tool_name`
- `credential_mode` when relevant
- `selected_workflow` for prompt workflows
- `image_count`
- `outputs`
- `warnings`

Each output image includes:

- `filename`
- `content_base64`
- `media_type`

## Security model

Current security controls:

- optional bearer auth on all MCP routes except `/healthz`
- allowed origins are controlled by `MCP_201_ALLOWED_ORIGINS`
- input validation via Pydantic
- image verification with Pillow before processing
- separation between `server` and `byok` credential modes
- frontend redacts sensitive error content before returning it to the browser

Important operational guardrails:

- never commit `backend/.env`
- never log raw BYOK secrets
- if `MCP_201_REQUIRE_AUTH=true`, always set `MCP_201_AUTH_TOKEN`
- keep frontend `MCP_SHARED_AUTH_TOKEN` aligned with backend `MCP_201_AUTH_TOKEN`

## Local setup and usage

From the repo root:

```bash
./scripts/setup_local.sh
```

This:

- creates `backend/.venv`
- installs Python deps and editable backend package
- installs frontend Node deps

### Backend env

Create `backend/.env`:

```dotenv
MCP_201_SERVER_GEMINI_API_KEY=your_server_gemini_key
MCP_201_PLANNER_MODEL=gemini-2.5-flash
MCP_201_IMAGE_MODEL=gemini-3.1-flash-image-preview
MCP_201_REQUIRE_AUTH=false
MCP_201_PORT=8010
```

Optional:

```dotenv
MCP_201_ALLOWED_ORIGINS=http://localhost:3004
MCP_201_MAX_IMAGES=5
MCP_201_MAX_FILE_SIZE_BYTES=6291456
```

### Frontend env

Create `frontend/.env.local`:

```dotenv
MCP_SERVER_URL=http://localhost:8010/mcp
MCP_SHARED_AUTH_TOKEN=
NEXT_PUBLIC_APP_NAME=MCP-201 Web
```

### Run locally

```bash
./scripts/run_backend.sh
./scripts/run_frontend.sh
```

Or:

```bash
./scripts/run_all.sh
```

Default local URLs:

- backend MCP: `http://localhost:8010/mcp`
- backend health: `http://localhost:8010/healthz`
- frontend: `http://localhost:3004`

### Verify locally

Run automated checks:

```bash
./scripts/run_tests.sh
```

This runs:

- backend unit tests
- frontend lint

Manual verification path:

1. start backend and frontend
2. open the frontend
3. upload one or more images
4. run a prompt like `Crop this screenshot to the visible frame and then colorize it realistically.`
5. confirm `selected_workflow` and output images look correct

## Deployment

### Backend deployment target

The backend is designed for Railway.

Wrapper:

```bash
./scripts/deploy_backend.sh
```

Underlying backend deploy script:

- `backend/scripts/deploy_railway.sh`

Required backend env vars in Railway:

- `MCP_201_SERVER_GEMINI_API_KEY`
- `MCP_201_PLANNER_MODEL`
- `MCP_201_IMAGE_MODEL`
- `MCP_201_REQUIRE_AUTH`
- `MCP_201_AUTH_TOKEN` if auth is enabled
- `MCP_201_ALLOWED_ORIGINS`

Expected backend endpoint:

```text
https://your-railway-domain.up.railway.app/mcp
```

### Frontend deployment target

The frontend is designed for Vercel.

Wrapper:

```bash
./scripts/deploy_frontend.sh
```

Required frontend env vars in Vercel:

- `MCP_SERVER_URL`
- `MCP_SHARED_AUTH_TOKEN`
- optional `NEXT_PUBLIC_APP_NAME`

`MCP_SERVER_URL` should point to the deployed Railway MCP endpoint.

## How to extend the project

### Add a new image skill

1. add the implementation in `backend/src/skills/`
2. add or extend request and response models in `backend/src/server/request_models.py` if needed
3. add a tool handler in `backend/src/server/tool_handlers.py`
4. register a new MCP tool in `backend/src/mcp_201_server.py` if it should be callable directly
5. update `backend/src/server/prompt_planner.py` if prompt routing should be able to select it
6. update frontend UI and result rendering if the new workflow changes UX
7. add tests in `backend/tests/`

### Change planner behavior

Primary file:

- `backend/src/server/prompt_planner.py`

Common extension paths:

- improve the planner prompt contract
- tighten JSON parsing and confidence handling
- add support for additional workflows
- replace the planner backend while keeping the same `route_prompt()` contract

Important: preserve fallback behavior so the system still works when AI planning is unavailable.

### Change deployment topology

Common future work:

- move the frontend and backend to the same platform
- add preview environments
- add CI that runs `./scripts/run_tests.sh`
- add smoke tests after Railway/Vercel deploys
- move secrets to platform-managed secret files or secret stores

### Improve production readiness

Recommended next upgrades:

- add structured logging and request IDs
- add metrics around planner choice, fallback rate, and tool latency
- add stronger file-type validation and output size checks
- add rate limiting in front of the backend
- add end-to-end deployment smoke tests
- add a clearer trace view in the frontend for planner reasoning and workflow selection

## Known limitations

- planner fallback is heuristic and only understands the currently supported workflows
- the planner currently catches broad failures and silently falls back to heuristics
- the frontend is a small operator UI, not a multi-user product surface
- no persistent job queue or async processing exists yet
- image processing is synchronous in request time

## Good first tasks for the next agent

If a new agent is taking over deployment or productization, good first tasks are:

1. validate Railway and Vercel env vars against this doc
2. run `./scripts/run_tests.sh`
3. do one full local manual workflow test
4. add a deployment smoke test for the MCP endpoint and frontend route
5. add CI so every change runs backend tests plus frontend lint
6. improve observability around planner choice and heuristic fallback

## Fast file map

If an agent needs to jump straight into the codebase:

- backend app entry: `backend/src/mcp_201_server.py`
- workflow execution: `backend/src/server/tool_handlers.py`
- planner and fallback logic: `backend/src/server/prompt_planner.py`
- request and response schemas: `backend/src/server/request_models.py`
- auth middleware: `backend/src/server/auth.py`
- env settings: `backend/src/server/config.py`
- frontend UI: `frontend/app/page.tsx`
- frontend server route: `frontend/app/api/run-workflow/route.ts`
- MCP client bridge: `frontend/lib/mcp-client.ts`
- root setup and deploy wrappers: `scripts/`
