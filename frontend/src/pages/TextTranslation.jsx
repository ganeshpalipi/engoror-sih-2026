import { useState } from 'react'
import { apiPost, getTranslationModelStatus } from '../services/api'
import { useApiStatus } from '../hooks/useApiStatus'
import { statusClass } from '../utils/format'

const VALIDATION_NOTICE = 'AI-generated — Requires native-speaker validation'

export default function TextTranslation() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { data: modelStatus, error: statusError } = useApiStatus(getTranslationModelStatus)

  const canTranslate = input.trim().length > 0 && !loading
  const modelState = modelStatus?.translation

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
    <div>
      <h1>Text Translation</h1>
      <p className="hindi subtitle">हिंदी पाठ → संथाली (ओल चिकी)</p>
      <p className="muted">
        Runs fully on this device (AI4Bharat IndicTrans2). No cloud API is used.
      </p>

      {/* Status strip */}
      <div className="grid-cards" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="status-row">
            <span
              className={`status-dot ${
                modelState ? statusClass(modelState.status === 'ready' ? 'ok' : modelState.status) : 'wait'
              }`}
            />
            <span className="status-label">Model</span>
          </div>
          <p className="status-detail" style={{ marginBottom: 0 }}>
            {statusError
              ? 'Status unavailable'
              : modelState
                ? `${modelState.status} · ${modelState.device || '—'}`
                : 'Checking…'}
            {modelState?.detail ? ` · ${modelState.detail}` : ''}
          </p>
        </div>
        <div className="card">
          <div className="status-row">
            <span className="status-dot ok" />
            <span className="status-label">Offline / local</span>
          </div>
          <p className="status-detail" style={{ marginBottom: 0 }}>
            Runs locally — no cloud API
          </p>
        </div>
        <div className="card">
          <div className="status-row">
            <span className={`status-dot ${result ? 'ok' : 'wait'}`} />
            <span className="status-label">Translation latency</span>
          </div>
          <p className="status-detail" style={{ marginBottom: 0 }}>
            {result ? `${result.latency_ms} ms` : '—'}
          </p>
        </div>
      </div>

      {/* Input */}
      <form onSubmit={onTranslate} className="card" style={{ marginTop: 6 }}>
        <h2>Hindi Text</h2>
        <textarea
          className="hindi"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={5}
          placeholder="यहाँ हिंदी में लिखें… जैसे: अपनी किताब खोलो।"
          aria-label="Hindi text to translate"
          style={{
            width: '100%',
            padding: 12,
            fontSize: 17,
            borderRadius: 8,
            border: '1px solid var(--border)',
            resize: 'vertical',
          }}
        />
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <button type="submit" className="btn btn-primary" disabled={!canTranslate}>
            {loading ? 'Translating…' : 'Translate'}
          </button>
          <span className="muted" style={{ fontSize: 13 }}>
            {loading
              ? 'Running on this device — the first ever run loads/downloads the model (~1.2 GB, one time).'
              : 'Up to 10 lines per translation.'}
          </span>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="error-banner" role="alert">
          <strong>Translation failed.</strong> {error}
        </div>
      )}

      {/* Output */}
      {result && (
        <section className="card" style={{ marginTop: 16 }} aria-label="Translation result">
          <h2>Santali — Ol Chiki</h2>
          <p
            className="ol-chiki"
            style={{
              fontSize: 20,
              lineHeight: 1.8,
              whiteSpace: 'pre-wrap',
              background: 'var(--green-soft)',
              borderRadius: 8,
              padding: 14,
              border: '1px solid var(--border)',
              marginBottom: 10,
            }}
          >
            {result.translated_text}
          </p>
          <p>
            <span className="badge" style={{ marginBottom: 0 }}>{VALIDATION_NOTICE}</span>
          </p>
          <p className="status-detail" style={{ marginBottom: 0 }}>
            {result.latency_ms} ms · {result.model} · {result.offline ? 'local inference (offline)' : ''}
          </p>
        </section>
      )}
    </div>
  )
}
