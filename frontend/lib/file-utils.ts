import { Buffer } from "node:buffer"

const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"])

export async function normalizeUploadedFiles(files: File[]) {
  const normalized = []
  for (const file of files) {
    if (!allowedTypes.has(file.type)) {
      throw new Error(`${file.name} is not a supported image type.`)
    }

    const bytes = await file.arrayBuffer()
    normalized.push({
      filename: file.name,
      content_base64: Buffer.from(bytes).toString("base64"),
    })
  }
  return normalized
}
