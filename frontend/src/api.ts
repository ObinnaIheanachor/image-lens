const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export type UploadResponse = {
  job_id: string
  status: string
  status_url: string
  created_at: string
}

export type JobResponse = {
  job_id: string
  status: 'queued' | 'processing' | 'done' | 'failed' | 'deleted'
  attempt_count: number
  report_id: string | null
  report_url: string | null
  error: { code: string; message: string } | null
  created_at: string
  updated_at: string
}

export type ReportResponse = {
  report_id: string
  job_id: string
  result: {
    summary: string
    tags: string[]
    confidence: number
    analyzer_version: string
  }
  created_at: string
}

export type RecentUploadItem = {
  job_id: string
  status: string
  report_id: string | null
  created_at: string
  updated_at: string
}

export type RecentUploadsResponse = {
  items: RecentUploadItem[]
  next_cursor: string | null
}

function headers(apiKey: string, accept?: string): HeadersInit {
  const h: HeadersInit = {
    Authorization: `Bearer ${apiKey}`,
  }
  if (accept) {
    h['Accept'] = accept
  }
  return h
}

async function parseError(resp: Response): Promise<never> {
  const text = await resp.text()
  throw new Error(text || `HTTP ${resp.status}`)
}

export async function uploadImage(apiKey: string, file: File, webhookUrl?: string): Promise<UploadResponse> {
  const body = new FormData()
  body.append('file', file)
  if (webhookUrl) body.append('webhook_url', webhookUrl)

  const resp = await fetch(`${API_BASE}/api/v1/uploads`, {
    method: 'POST',
    headers: headers(apiKey),
    body,
  })
  if (!resp.ok) return parseError(resp)
  return resp.json()
}

export async function getJob(apiKey: string, jobId: string): Promise<JobResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`, {
    headers: headers(apiKey),
  })
  if (!resp.ok) return parseError(resp)
  return resp.json()
}

export async function retryJob(apiKey: string, jobId: string): Promise<JobResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/jobs/${jobId}/retry`, {
    method: 'POST',
    headers: headers(apiKey),
  })
  if (!resp.ok) return parseError(resp)
  return resp.json()
}

export async function getReportJson(apiKey: string, reportId: string): Promise<ReportResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/reports/${reportId}`, {
    headers: headers(apiKey, 'application/json'),
  })
  if (!resp.ok) return parseError(resp)
  return resp.json()
}

export async function getReportHtml(apiKey: string, reportId: string): Promise<string> {
  const resp = await fetch(`${API_BASE}/api/v1/reports/${reportId}`, {
    headers: headers(apiKey, 'text/html'),
  })
  if (!resp.ok) return parseError(resp)
  return resp.text()
}

export async function downloadReport(apiKey: string, reportId: string, accept: string, fileName: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/v1/reports/${reportId}`, {
    headers: headers(apiKey, accept),
  })
  if (!resp.ok) return parseError(resp)

  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export async function listRecentUploads(
  apiKey: string,
  limit = 10,
  cursor?: string,
): Promise<RecentUploadsResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) params.set('cursor', cursor)

  const resp = await fetch(`${API_BASE}/api/v1/reports?${params.toString()}`, {
    headers: headers(apiKey, 'application/json'),
  })
  if (!resp.ok) return parseError(resp)
  return resp.json()
}
