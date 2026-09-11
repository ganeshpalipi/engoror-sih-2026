import { getHealth } from '../services/api'
import { useApiStatus } from '../hooks/useApiStatus'
import { statusClass } from '../utils/format'

const PIPELINE_STEPS = [
  'Teacher speaks Hindi',
  'Offline Hindi ASR',
  'Hindi text',
  'Hindi → Santhali MT',
  'Ol Chiki text',
  'Offline Santhali TTS',
  'Students hear Santhali',
]

const ROADMAP = [
  { phase: 'Phase 1', label: 'Folder structure, FastAPI + Vite skeletons, health endpoint, SQLite config', done: true },
  { phase: 'Phase 2', label: 'SQLite tables + seed data + real Hindi → Santhali translation (IndicTrans2, local)', done: true },
  { phase: 'Phase 3', label: 'Offline Hindi ASR module', done: false },
  { phase: 'Phase 4', label: 'Offline Santhali TTS module', done: false },
  { phase: 'Phase 5', label: 'Full speech-to-speech pipeline with latency tracking', done: false },
  { phase: 'Phase 6', label: 'Frontend pages connected to live APIs', done: false },
  { phase: 'Phase 7–9', label: 'Phrase pack, FLN lessons, worksheets, flashcards, offline sync', done: false },
  { phase: 'Phase 10', label: 'Testing, latency measurement and optimisation', done: false },
]

export default function Home() {
  const { data: health, error, loading } = useApiStatus(getHealth)

  return (
    <div>
      <h1>RootVerse — Classroom Language Bridge</h1>
      <p className="hindi subtitle">हिंदी शिक्षक की आवाज़ → संथाली छात्रों के लिए आवाज़</p>
      <p className="muted">
        Offline-first AI bridge for mother-tongue-based primary education.
        Prototype language: Santhali, written in Ol Chiki script.
      </p>

      {/* Core pipeline */}
      <section className="card" aria-label="Translation pipeline">
        <h2>Core pipeline</h2>
        <ol className="pipeline">
          {PIPELINE_STEPS.map((step, i) => (
            <li key={step} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className="pipeline-step">
                <span className="step-num" aria-hidden="true">{i + 1}</span>
                {step}
              </span>
              {i < PIPELINE_STEPS.length - 1 && (
                <span className="pipeline-arrow" aria-hidden="true">→</span>
              )}
            </li>
          ))}
        </ol>
        <p className="muted" style={{ marginBottom: 0 }}>
          Every stage runs offline on the teacher&apos;s Windows laptop after a one-time
          model download. No cloud API is used in the core pipeline.
        </p>
      </section>

      {/* Live backend status (proves the React app talks to FastAPI) */}
      <section aria-label="Backend status" style={{ marginTop: 18 }}>
        <h2>Backend status</h2>

        {loading && (
          <div className="card status-row">
            <span className="status-dot wait" aria-hidden="true" />
            <span>Checking backend…</span>
          </div>
        )}

        {error && (
          <div className="error-banner" role="alert">
            <strong>Backend not reachable.</strong> {error}
          </div>
        )}

        {health && (
          <div className="grid-cards">
            <div className="card">
              <div className="status-row">
                <span className={`status-dot ${statusClass(health.components.api.status)}`} />
                <span className="status-label">Backend API</span>
              </div>
              <p className="status-detail" style={{ marginBottom: 0 }}>
                {health.components.api.detail}
              </p>
            </div>

            <div className="card">
              <div className="status-row">
                <span className={`status-dot ${statusClass(health.components.database.status)}`} />
                <span className="status-label">Database (SQLite)</span>
              </div>
              <p className="status-detail" style={{ marginBottom: 0 }}>
                {health.components.database.detail}
              </p>
            </div>

            <div className="card">
              <div className="status-row">
                <span className={`status-dot ${health.offline_mode ? 'ok' : 'wait'}`} />
                <span className="status-label">Offline mode</span>
              </div>
              <p className="status-detail" style={{ marginBottom: 0 }}>
                {health.offline_mode ? 'ON — no cloud dependency' : 'OFF'}
              </p>
            </div>

            <div className="card">
              <div className="status-row">
                <span className="status-label">{health.app}</span>
              </div>
              <p className="status-detail" style={{ marginBottom: 0 }}>
                Version {health.version} · overall: {health.status}
              </p>
            </div>
          </div>
        )}
      </section>

      {/* Build roadmap */}
      <section className="card" aria-label="Build roadmap" style={{ marginTop: 18 }}>
        <h2>Build plan (docs/PROJECT_PLAN.md)</h2>
        <ul className="roadmap">
          {ROADMAP.map((item) => (
            <li key={item.phase}>
              <span className="phase-tag">{item.phase}</span>
              <span className={item.done ? 'check' : 'pending'}>
                {item.done ? '✓ ' : '• '}
                {item.label}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
