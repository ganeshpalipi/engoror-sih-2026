import { useState } from 'react'
import { apiPost, getTranslationModelStatus } from '../services/api'
import { useApiStatus } from '../hooks/useApiStatus'

const VALIDATION_NOTICE = 'AI-generated — Requires native-speaker validation'

export default function TextTranslation() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: modelStatus, error: statusError } =
    useApiStatus(getTranslationModelStatus)

  const modelState = modelStatus?.translation
  const canTranslate = input.trim().length > 0 && !loading

  async function onTranslate(e) {
    e.preventDefault()

    if (!canTranslate) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const data = await apiPost('/api/translate/text', {
        text: input,
        source_language: 'hin_Deva',
        target_language: 'sat_Olck',
      })

      setResult(data)
    } catch (err) {
      setError(err.message || 'Translation failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="eng-text-page">
      <header className="eng-page-head">
        <p className="eyebrow">ENGOROR LANGUAGE TOOL</p>

        <h1>Text Translation</h1>

        <p>
          Type a classroom sentence in Hindi and translate it into Santali
          written in Ol Chiki script.
        </p>
      </header>

      <div className="eng-text-flow">
        <span>Hindi text</span>
        <span className="eng-text-arrow">→</span>
        <span>Santali (Ol Chiki)</span>
      </div>

      <form onSubmit={onTranslate} className="eng-text-card">
        <div className="eng-text-card-head">
          <div>
            <p className="eng-result-label">TEACHER TEXT</p>
            <h2>Write in Hindi</h2>
          </div>

          <span className="eng-local-badge">● Runs locally</span>
        </div>

        <textarea
          className="hindi eng-text-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={5}
          placeholder="यहाँ हिंदी में लिखें… जैसे: अपनी किताब खोलो।"
          aria-label="Hindi text to translate"
        />

        <div className="eng-text-actions">
          <button
            type="submit"
            className="eng-translate-button"
            disabled={!canTranslate}
          >
            {loading ? 'Translating...' : 'Translate to Santali'}
          </button>

          <span>Up to 10 lines per translation.</span>
        </div>

        {loading && (
          <div className="eng-processing">
            <span className="eng-spinner" />

            <div>
              <strong>Translating locally...</strong>
              <p>
                Engoror is converting the Hindi text into Santali on this
                computer.
              </p>
            </div>
          </div>
        )}
      </form>

      {error && (
        <div className="eng-friendly-error" role="alert">
          <strong>Translation could not be completed.</strong>
          <span>{error}</span>
        </div>
      )}

      {result && (
        <section className="eng-text-result">
          <div className="eng-text-result-head">
            <div>
              <p className="eng-result-label">FOR THE STUDENTS</p>
              <h2>Santali Translation</h2>
            </div>

            <span className="eng-success-pill">✓ Translation ready</span>
          </div>

          <div className="eng-santali-text ol-chiki">
            {result.translated_text}
          </div>

          <span className="eng-validation">
            {VALIDATION_NOTICE}
          </span>
        </section>
      )}

      <details className="eng-tech-details eng-text-tech">
        <summary>Technical details</summary>

        <div className="eng-tech-grid">
          <div>
            <strong>Translation model</strong>
            <span>
              {statusError
                ? 'Status unavailable'
                : modelState?.status || 'Checking'}
            </span>
          </div>

          <div>
            <strong>Device</strong>
            <span>{modelState?.device || 'Local CPU'}</span>
          </div>

          <div>
            <strong>Internet dependency</strong>
            <span>None during inference</span>
          </div>

          <div>
            <strong>Latency</strong>
            <span>{result ? `${result.latency_ms} ms` : 'Not measured yet'}</span>
          </div>
        </div>

        {result?.model && (
          <p className="eng-tech-model">
            Model: {result.model}
          </p>
        )}
      </details>
    </div>
  )
}