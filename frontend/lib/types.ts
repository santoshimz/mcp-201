export type CredentialMode = "server" | "byok"

export type DemoResultImage = {
  filename: string
  content_base64: string
  media_type: string
}

export type DemoResult = {
  tool_name: string
  credential_mode?: string | null
  selected_workflow?: string | null
  image_count: number
  outputs: DemoResultImage[]
  warnings: string[]
}
