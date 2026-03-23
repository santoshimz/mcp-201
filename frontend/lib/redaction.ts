const REDACTED = "[REDACTED]"

const FIELD_VALUE_PATTERNS = [
  /("?(?:geminiApiKey|gemini_api_key|authorization|api[_ -]?key)"?\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,}\]]+)/gi,
  /((?:geminiApiKey|gemini_api_key|authorization|api[_ -]?key)\s+)([^\s,}\]]+)/gi,
]

export function redactSecrets(value: string, secrets: Array<string | undefined> = []) {
  let redacted = value

  for (const secret of secrets) {
    const normalized = secret?.trim()
    if (!normalized) {
      continue
    }
    redacted = redacted.split(normalized).join(REDACTED)
  }

  for (const pattern of FIELD_VALUE_PATTERNS) {
    redacted = redacted.replace(pattern, `$1${REDACTED}`)
  }

  return redacted
}

export function redactErrorMessage(error: unknown, secrets: Array<string | undefined> = []) {
  const message = error instanceof Error ? error.message : "Request failed."
  return redactSecrets(message, secrets)
}
