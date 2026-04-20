import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import ApiKeyInput from '../components/ApiKeyInput'
import { getJob, retryJob, type JobResponse } from '../api'
import { isDevMode, persistApiKey, resolveApiKey } from '../runtime'

export default function JobPage() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const devMode = isDevMode(location.search)

  const [apiKey, setApiKey] = useState(() => resolveApiKey())
  const [job, setJob] = useState<JobResponse | null>(null)
  const [error, setError] = useState('')
  const [retryBusy, setRetryBusy] = useState(false)

  useEffect(() => {
    if (!apiKey || !jobId) return
    persistApiKey(apiKey)

    let stopped = false
    const tick = async () => {
      try {
        const next = await getJob(apiKey, jobId)
        if (stopped) return
        setJob(next)
        setError('')

        if (next.status === 'done' && next.report_id) {
          navigate(`/reports/${next.report_id}${devMode ? '?mode=dev' : ''}`)
        }
      } catch (err) {
        if (!stopped) {
          setError(err instanceof Error ? err.message : 'Polling failed')
        }
      }
    }

    void tick()
    const handle = setInterval(tick, 1500)
    return () => {
      stopped = true
      clearInterval(handle)
    }
  }, [apiKey, jobId, navigate, devMode])

  const onRetry = async () => {
    if (!apiKey || !jobId) return
    setRetryBusy(true)
    setError('')
    try {
      const next = await retryJob(apiKey, jobId)
      setJob(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retry failed')
    } finally {
      setRetryBusy(false)
    }
  }

  return (
    <section className="panel">
      <h1>Job Status</h1>
      {devMode ? <ApiKeyInput value={apiKey} onChange={setApiKey} /> : null}

      <p><strong>Job ID:</strong> {jobId}</p>
      <p><strong>Status:</strong> {job?.status || 'loading'}</p>
      <p><strong>Attempts:</strong> {job?.attempt_count ?? '-'}</p>

      {job?.error ? (
        <pre className="error">{job.error.code}: {job.error.message}</pre>
      ) : null}
      {error ? <pre className="error">{error}</pre> : null}

      <div className="row">
        <Link to={devMode ? '/?mode=dev' : '/'}>Back to Upload</Link>
        {job?.status === 'failed' ? (
          <button type="button" disabled={retryBusy} onClick={onRetry}>
            {retryBusy ? 'Retrying...' : 'Retry Job'}
          </button>
        ) : null}
      </div>
    </section>
  )
}
