import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ApiKeyInput from '../components/ApiKeyInput'
import { uploadImage } from '../api'
import { isDevMode, persistApiKey, resolveApiKey } from '../runtime'

export default function UploadPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const devMode = isDevMode(location.search)

  const [apiKey, setApiKey] = useState(() => resolveApiKey())
  const [webhookUrl, setWebhookUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const fileName = useMemo(() => file?.name || 'No file selected', [file])

  const onSubmit = async () => {
    setError('')
    if (!apiKey) {
      setError('App is not configured with an API key. Enable dev mode (?mode=dev) or set VITE_DEFAULT_API_KEY.')
      return
    }
    if (!file) {
      setError('Select an image first')
      return
    }

    setBusy(true)
    try {
      persistApiKey(apiKey)
      const uploaded = await uploadImage(apiKey, file, devMode ? (webhookUrl || undefined) : undefined)
      navigate(`/jobs/${uploaded.job_id}${devMode ? '?mode=dev' : ''}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h1>Upload Image</h1>
      <p className="muted">Upload a JPEG and start asynchronous analysis.</p>

      {devMode ? (
        <>
          <ApiKeyInput value={apiKey} onChange={setApiKey} />
          <label className="field">
            <span>Webhook URL (optional)</span>
            <input
              type="url"
              placeholder="http://host.docker.internal:8888/hook"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
          </label>
        </>
      ) : null}

      <label className="dropzone" htmlFor="upload-input">
        <input
          id="upload-input"
          type="file"
          accept="image/jpeg"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <strong>Drag and drop or click to select</strong>
        <span>{fileName}</span>
      </label>

      {error ? <pre className="error">{error}</pre> : null}

      <button type="button" onClick={onSubmit} disabled={busy}>
        {busy ? 'Uploading...' : 'Upload & Analyze'}
      </button>

      {devMode ? <p className="muted dev-note">Developer controls enabled.</p> : null}
    </section>
  )
}
