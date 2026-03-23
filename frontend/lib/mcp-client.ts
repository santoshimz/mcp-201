import { Client } from "@modelcontextprotocol/sdk/client/index.js"
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js"

import { redactErrorMessage } from "./redaction"

function normalizeServerUrl(rawUrl: string): URL {
  const value = rawUrl.trim()
  if (!value) {
    throw new Error("MCP_SERVER_URL is empty.")
  }

  const withProtocol =
    /^https?:\/\//i.test(value)
      ? value
      : /^(localhost|127\.0\.0\.1)(:\d+)?(\/.*)?$/i.test(value)
        ? `http://${value}`
        : `https://${value}`

  try {
    return new URL(withProtocol)
  } catch {
    throw new Error(
      "MCP_SERVER_URL is invalid. Set it to a full MCP endpoint like https://your-backend.up.railway.app/mcp"
    )
  }
}

export async function callPromptWorkflow(input: {
  prompt: string
  images: Array<{ filename: string; content_base64: string }>
  credentialMode: "server" | "byok"
  geminiApiKey?: string
  model?: string
}) {
  const serverUrl = process.env.MCP_SERVER_URL
  if (!serverUrl) {
    throw new Error("MCP_SERVER_URL is not configured.")
  }

  const authToken = process.env.MCP_SHARED_AUTH_TOKEN
  const headers = new Headers()
  if (authToken?.trim()) {
    headers.set("Authorization", `Bearer ${authToken.trim()}`)
  }

  const client = new Client({ name: "mcp-201-frontend", version: "0.1.0" })
  const transport = new StreamableHTTPClientTransport(normalizeServerUrl(serverUrl), {
    requestInit: { headers },
  })

  try {
    await client.connect(transport)
    const result = await client.callTool({
      name: "run_prompt_workflow",
      arguments: {
        prompt: input.prompt,
        images: input.images,
        credential_mode: input.credentialMode,
        gemini_api_key: input.geminiApiKey,
        model: input.model,
      },
    })

    if (result.isError) {
      throw new Error("MCP tool returned an error.")
    }

    if (result.structuredContent) {
      return result.structuredContent
    }

    throw new Error("MCP tool did not return structured content.")
  } catch (error) {
    throw new Error(redactErrorMessage(error, [input.geminiApiKey]))
  } finally {
    await transport.terminateSession().catch(() => undefined)
    await client.close().catch(() => undefined)
  }
}
