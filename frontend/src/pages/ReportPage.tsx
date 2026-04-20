import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import ApiKeyInput from '../components/ApiKeyInput'
import { downloadReport, getReportHtml, getReportJson, type ReportResponse } from '../api'
import { isDevMode, persistApiKey, resolveApiKey } from '../runtime'

export default function ReportPage() {
  const { reportId = '' } = useParams()
  const location = useLocation()
  const devMode = isDevMode(location.search)

  const [apiKey, setApiKey] = useState(() => resolveApiKey())
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [htmlPreview, setHtmlPreview] = useState('')
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState('')

  useEffect(() => {
    if (!apiKey || !reportId) return
    persistApiKey(apiKey)

    const load = async () => {
      try {
        const [json, html] = await Promise.all([
          getReportJson(apiKey, reportId),
          getReportHtml(apiKey, reportId),
        ])
        setReport(json)
        setHtmlPreview(html)
        setError('')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load report')
      }
    }

    void load()
  }, [apiKey, reportId])

  const runDownload = async (accept: string, extension: string) => {
    if (!apiKey || !reportId) return
    setDownloading(extension)
    setError('')
    try {
      await downloadReport(apiKey, reportId, accept, `${reportId}.${extension}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloading('')
    }
  }

  return (
    <section className="panel wide">
      <h1>Report</h1>
      {devMode ? <ApiKeyInput value={apiKey} onChange={setApiKey} /> : null}

      <p><strong>Report ID:</strong> {reportId}</p>
      <p><strong>Job ID:</strong> {report?.job_id || '-'}</p>

      {error ? <pre className="error">{error}</pre> : null}

      <div className="row">
        <button type="button" disabled={!!downloading} onClick={() => runDownload('application/json', 'json')}>
          {downloading === 'json' ? 'Downloading...' : 'Download JSON'}
        </button>
        <button type="button" disabled={!!downloading} onClick={() => runDownload('text/markdown', 'md')}>
          {downloading === 'md' ? 'Downloading...' : 'Download Markdown'}
        </button>
        <button type="button" disabled={!!downloading} onClick={() => runDownload('application/pdf', 'pdf')}>
          {downloading === 'pdf' ? 'Downloading...' : 'Download PDF'}
        </button>
      </div>

      <h2>HTML Preview</h2>
      <iframe className="preview" title="Report preview" srcDoc={htmlPreview} />

      <div className="row">
        <Link to={devMode ? '/?mode=dev' : '/'}>Upload another</Link>
      </div>
    </section>
  )
}
