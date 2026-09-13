import { Link } from 'react-router-dom'
import { getHealth } from '../services/api'
import { useApiStatus } from '../hooks/useApiStatus'

const FEATURES = [
  {
    title: 'Live Classroom Translation',
    desc: 'Speak in Hindi and help students understand the lesson in Santali.',
    cta: 'Start Translation',
    to: '/live-translation',
  },
  {
    title: 'FLN Learning',
    desc: 'Foundational literacy and numeracy activities for primary classrooms.',
    cta: 'Explore Lessons',
    to: '/lessons',
  },
  {
    title: 'Classroom Phrase Pack',
    desc: 'Quick everyday classroom instructions translated for students.',
    cta: 'Open Phrase Pack',
    to: '/phrases',
  },
  {
    title: 'Worksheet Creator',
    desc: 'Create printable bilingual learning activities for literacy and numeracy.',
    cta: 'Create Worksheet',
    to: '/worksheets',
  },
  {
    title: 'Visual Flashcards',
    desc: 'Picture-based vocabulary learning with Hindi, Santali and audio.',
    cta: 'Explore Flashcards',
    to: '/flashcards',
  },
]

const FLOW = [
  'Teacher speaks Hindi',
  'Engoror understands',
  'Translates to Santali',
  'Students read and hear Santali',
]

export default function Home() {
  const { data: health, error, loading } = useApiStatus(getHealth)

  const backendReady = Boolean(health && health.status === 'ok')

  return (
    <div className="engoror-home">
      <section className="hero-card">
        <span className="hero-badge">BUILT FOR LOW-CONNECTIVITY CLASSROOMS</span>

        <h1>
          Teach in your language.
          <br />
          Let every child learn in theirs.
        </h1>

        <p>
          An offline AI classroom companion that helps teachers communicate,
          teach and create learning material across language barriers.
        </p>

        <div className="hero-actions">
          <Link className="btn-primary" to="/live-translation">
            Start Teaching
          </Link>

          <Link className="btn-secondary-light" to="/lessons">
            Explore Lessons
          </Link>
        </div>

        <div className="hero-language-sample">
          <span className="hindi">१२३</span>
          <span>→</span>
          <span className="olchiki">᱑᱒᱓</span>
        </div>
      </section>

      <section className="home-section">
        <h2>Everything a multilingual classroom needs</h2>

        <div className="feature-grid">
          {FEATURES.map((item, index) => (
            <article
              key={item.title}
              className={`feature-card tone-${index % 2 === 0 ? 'green' : 'orange'}`}
            >
              <div className="feature-icon" aria-hidden="true">
                {index === 0 && '🎙️'}
                {index === 1 && '📚'}
                {index === 2 && '💬'}
                {index === 3 && '📝'}
                {index === 4 && '🧩'}
              </div>

              <h3>{item.title}</h3>
              <p>{item.desc}</p>

              <Link to={item.to}>{item.cta} →</Link>
            </article>
          ))}

          <article className="how-card">
            <p className="eyebrow">HOW ENGOROR WORKS</p>

            <ol>
              {FLOW.map((step, index) => (
                <li key={step}>
                  <span>{index + 1}</span>
                  {step}
                </li>
              ))}
            </ol>

            <p className="small-note">
              Runs locally on the teacher&apos;s computer after initial setup.
            </p>
          </article>
        </div>
      </section>

      <section className="home-section">
        <div className="status-card">
          <div>
            <p className="eyebrow">CLASSROOM STATUS</p>
            <h2>
              {loading
                ? 'Checking classroom service...'
                : backendReady
                  ? 'Engoror is ready for class'
                  : 'Engoror classroom service is not running'}
            </h2>

            <p className="muted">
              {backendReady
                ? 'Local backend, SQLite database and offline AI services are available.'
                : 'Start the local backend to use translation, lessons, worksheets and audio.'}
            </p>
          </div>

          <div
            className={`status-pill-large ${
              backendReady ? 'ready' : loading ? 'wait' : 'error'
            }`}
          >
            {backendReady ? '● Ready' : loading ? '● Checking' : '● Offline'}
          </div>
        </div>

        {error && (
          <details className="technical-error">
            <summary>Technical details</summary>
            <p>{String(error)}</p>
          </details>
        )}
      </section>
    </div>
  )
}