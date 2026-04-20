import { Link, Route, Routes } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import JobPage from './pages/JobPage'
import ReportPage from './pages/ReportPage'

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/">Image Insight</Link>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/jobs/:jobId" element={<JobPage />} />
          <Route path="/reports/:reportId" element={<ReportPage />} />
        </Routes>
      </main>
    </div>
  )
}
