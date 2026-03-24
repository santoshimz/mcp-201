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
  const [activeOutputIndex, setActiveOutputIndex] = useState<number | null>(null)
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

  const activeOutput = activeOutputIndex !== null && result ? result.outputs[activeOutputIndex] : null

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

        <aside className="panel results-panel">
          <div className="results-header">
            <div>
              <p className="results-eyebrow">Output gallery</p>
              <h2>Results</h2>
            </div>
            {result ? <p className="results-count">{result.outputs.length} image{result.outputs.length === 1 ? "" : "s"}</p> : null}
          </div>
          {result ? (
            <>
              <div className="result-meta">
                <div className="result-stat">
                  <span>Workflow</span>
                  <strong>{result.selected_workflow}</strong>
                </div>
                <div className="result-stat">
                  <span>Inputs</span>
                  <strong>{result.image_count}</strong>
                </div>
                <div className="result-stat">
                  <span>Outputs</span>
                  <strong>{result.outputs.length}</strong>
                </div>
              </div>
              {result.warnings.length ? (
                <ul className="warning-list">
                  {result.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
              <div className="result-grid">
                {result.outputs.map((output, index) => {
                  const outputSrc = `data:${output.media_type};base64,${output.content_base64}`

                  return (
                  <article className="result-card" key={output.filename}>
                    <button
                      type="button"
                      className="result-preview-button"
                      onClick={() => setActiveOutputIndex(index)}
                    >
                      <div className="result-preview">
                        <Image
                          src={outputSrc}
                          alt={output.filename}
                          width={1200}
                          height={900}
                          unoptimized
                        />
                      </div>
                      <span className="result-preview-hint">Click to expand</span>
                    </button>
                    <div className="result-card-footer">
                      <div>
                        <p>{output.filename}</p>
                        <span>Output {index + 1}</span>
                      </div>
                      <a href={outputSrc} download={output.filename} className="download-link">
                        Download
                      </a>
                    </div>
                  </article>
                  )
                })}
              </div>
            </>
          ) : (
            <p className="empty-results">Run a workflow to see polished output previews here.</p>
          )}
        </aside>
      </section>

      {activeOutput ? (
        <div className="lightbox" role="dialog" aria-modal="true" aria-label="Expanded output preview">
          <button type="button" className="lightbox-backdrop" onClick={() => setActiveOutputIndex(null)} aria-label="Close preview" />
          <div className="lightbox-content">
            <button type="button" className="lightbox-close" onClick={() => setActiveOutputIndex(null)}>
              Close
            </button>
            <div className="lightbox-image-shell">
              <Image
                src={`data:${activeOutput.media_type};base64,${activeOutput.content_base64}`}
                alt={activeOutput.filename}
                width={1600}
                height={1200}
                unoptimized
              />
            </div>
            <div className="lightbox-caption">
              <strong>{activeOutput.filename}</strong>
              <a
                href={`data:${activeOutput.media_type};base64,${activeOutput.content_base64}`}
                download={activeOutput.filename}
                className="download-link"
              >
                Download
              </a>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  )
}
