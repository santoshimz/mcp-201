"use client"

import { FormEvent, useState } from "react"
import Image from "next/image"

import type { CredentialMode, DemoResult } from "../lib/types"

const defaultPrompt = "Crop this screenshot to the visible frame and then colorize it realistically."

export default function HomePage() {
  const [credentialMode, setCredentialMode] = useState<CredentialMode>("server")
  const [geminiApiKey, setGeminiApiKey] = useState("")
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [model, setModel] = useState("")
  const [files, setFiles] = useState<File[]>([])
  const [result, setResult] = useState<DemoResult | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const appName = process.env.NEXT_PUBLIC_APP_NAME || "MCP-201 Web"

  const submitDisabled = loading || files.length === 0 || !prompt.trim() || (credentialMode === "byok" && !geminiApiKey.trim())

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setResult(null)
    setLoading(true)

    try {
      const formData = new FormData()
      formData.set("prompt", prompt)
      formData.set("credentialMode", credentialMode)
      if (geminiApiKey) {
        formData.set("geminiApiKey", geminiApiKey)
      }
      if (model.trim()) {
        formData.set("model", model.trim())
      }
      for (const file of files) {
        formData.append("files", file)
      }

      const response = await fetch("/api/run-workflow", {
        method: "POST",
        body: formData,
      })
      const payload = (await response.json()) as DemoResult | { error: string }
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Request failed.")
      }
      setResult(payload as DemoResult)
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Request failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="hero-eyebrow">Independent MCP client</p>
          <h1>{appName}</h1>
          <p className="hero-description">
            This frontend talks only to the mcp-201 backend and runs as part of the same standalone repo.
          </p>
        </div>
        <div className="hero-note">
          <strong>Flow</strong>
          <p>Browser form to Next.js route to MCP tool call to AI workflow planning to backend outputs.</p>
        </div>
      </section>

      <section className="workspace">
        <form className="panel" onSubmit={handleSubmit}>
          <label className="field">
            <span>Prompt</span>
            <textarea
              rows={5}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Describe the workflow you want to run."
            />
          </label>

          <label className="field">
            <span>Images</span>
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
              multiple
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            />
          </label>

          <div className="row">
            <button
              type="button"
              className={credentialMode === "server" ? "choice active" : "choice"}
              onClick={() => setCredentialMode("server")}
            >
              Server key
            </button>
            <button
              type="button"
              className={credentialMode === "byok" ? "choice active" : "choice"}
              onClick={() => setCredentialMode("byok")}
            >
              BYOK
            </button>
          </div>

          {credentialMode === "byok" ? (
            <label className="field">
              <span>Gemini API key</span>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(event) => setGeminiApiKey(event.target.value)}
                autoComplete="off"
              />
            </label>
          ) : null}

          <label className="field">
            <span>Model override</span>
            <input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Optional" />
          </label>

          <button className="primary-button" type="submit" disabled={submitDisabled}>
            {loading ? "Running..." : "Run workflow"}
          </button>

          {error ? <p className="error">{error}</p> : null}
        </form>

        <aside className="panel">
          <h2>Results</h2>
          {result ? (
            <>
              <p><strong>Workflow:</strong> {result.selected_workflow}</p>
              <p><strong>Images:</strong> {result.image_count}</p>
              <p><strong>Outputs:</strong> {result.outputs.length}</p>
              {result.warnings.length ? (
                <ul>
                  {result.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
              <div className="result-grid">
                {result.outputs.map((output) => (
                  <article className="result-card" key={output.filename}>
                    <Image
                      src={`data:${output.media_type};base64,${output.content_base64}`}
                      alt={output.filename}
                      width={640}
                      height={480}
                      unoptimized
                    />
                    <p>{output.filename}</p>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <p>No results yet.</p>
          )}
        </aside>
      </section>
    </main>
  )
}
