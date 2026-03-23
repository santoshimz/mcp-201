import { NextResponse } from "next/server"

import { normalizeUploadedFiles } from "../../../lib/file-utils"
import { callPromptWorkflow } from "../../../lib/mcp-client"
import { redactErrorMessage } from "../../../lib/redaction"

export const runtime = "nodejs"

export async function POST(request: Request) {
  let geminiApiKey: string | undefined

  try {
    const formData = await request.formData()
    const prompt = String(formData.get("prompt") || "").trim()
    const credentialMode = String(formData.get("credentialMode") || "server").trim().toLowerCase()
    geminiApiKey = String(formData.get("geminiApiKey") || "").trim() || undefined
    const model = String(formData.get("model") || "").trim() || undefined
    const files = formData.getAll("files").filter((value): value is File => value instanceof File)

    if (!prompt) {
      return NextResponse.json({ error: "Prompt is required." }, { status: 400 })
    }
    if (!["server", "byok"].includes(credentialMode)) {
      return NextResponse.json({ error: "credentialMode must be server or byok." }, { status: 400 })
    }
    if (credentialMode === "byok" && !geminiApiKey) {
      return NextResponse.json({ error: "geminiApiKey is required for byok." }, { status: 400 })
    }
    if (files.length === 0) {
      return NextResponse.json({ error: "At least one file is required." }, { status: 400 })
    }

    const images = await normalizeUploadedFiles(files)
    const result = await callPromptWorkflow({
      prompt,
      images,
      credentialMode: credentialMode as "server" | "byok",
      geminiApiKey,
      model,
    })

    return NextResponse.json(result)
  } catch (error) {
    const message = redactErrorMessage(error, [geminiApiKey])
    return NextResponse.json({ error: message }, { status: 500 })
  } finally {
    geminiApiKey = undefined
  }
}
