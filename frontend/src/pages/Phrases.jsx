import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '../services/api'
import { formatMs } from '../utils/format'

const VALIDATION_NOTICE = 'AI-generated — Requires native-speaker validation'

export default function Phrases() {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [category, setCategory] = useState('')
  const [busy, setBusy] = useState({}) // { [phraseId]: 'translate' | 'audio' }
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiGet('/api/phrases')
      .then((d) => {
        if (active) setData(d)
      })
      .catch((e) => {
        if (active) setLoadError(e.message || 'Could not load phrases')
      })
    return () => {
      active = false
    }
  }, [])

  const visible = useMemo(() => {
    const rows = data?.phrases || []
    return rows.filter((p) => !category || p.category === category)
  }, [data, category])

  function replacePhrase(updated) {
    setData((d) => ({
      ...d,
      phrases: d.phrases.map((p) => (p.id === updated.id ? updated : p)),
    }))
  }

  function setBusyFor(id, kind) {
    setBusy((b) => ({ ...b, [id]: kind }))
  }
  function clearBusyFor(id) {
    setBusy((b) => {
      const next = { ...b }
      delete next[id]
      return next
    })
  }

  async function onTranslate(phrase) {
    setBusyFor(phrase.id, 'translate')
    setError('')
    setMessage('')
    try {
      const resp = await apiPost(`/api/phrases/${phrase.id}/translate`, {})
      replacePhrase(resp.phrase)
      setMessage(
        `Santali generated in ${formatMs(resp.translation_latency_ms)} (offline model). ${VALIDATION_NOTICE}.`,
      )
    } catch (err) {
      setError(err.message || 'Translation failed')
    } finally {
      clearBusyFor(phrase.id)
    }
  }

  async function onPlay(phrase) {
    setBusyFor(phrase.id, 'audio')
    setError('')
    setMessage('')
    try {
      const resp = await apiPost(`/api/phrases/${phrase.id}/audio`, {})
      const player = new Audio(resp.audio_url)
      await player.play()
      setMessage(
        resp.cached
          ? 'Playing cached Santali audio.'
          : `Audio generated in ${formatMs(resp.latency_ms)} (offline TTS).`,
      )
    } catch (err) {
      setError(err.message || 'Audio failed')
    } finally {
      clearBusyFor(phrase.id)
    }
  }

  const hasSantali = (p) => p.validation_status === 'AI_GENERATED'

  return (
    <div>
      <h1>Classroom Phrase Pack</h1>
      <p className="hindi subtitle">कक्षा वाक्यांश संग्रह</p>
      <p className="muted">
        Everyday classroom instructions in Hindi and Santali (Ol Chiki) with
        audio. Hindi phrase → offline IndicTrans2 → Santali text → offline TTS →
        student hears it. No internet needed once the models are downloaded.
      </p>

      {data?.categories?.length > 0 && (
        <div className="chip-row" role="group" aria-label="Filter by category">
          <button
            type="button"
            className={`chip${category === '' ? ' active' : ''}`}
            onClick={() => setCategory('')}
          >
            All
          </button>
          {data.categories.map((c) => (
            <button
              key={c}
              type="button"
              className={`chip${category === c ? ' active' : ''}`}
              onClick={() => setCategory(c)}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      {loadError && (
        <div className="error-banner" role="alert">
          <strong>Could not load phrases.</strong> {loadError}
        </div>
      )}

      {!data && !loadError && <p className="muted">Loading phrase pack…</p>}

      {data && (
        <div className="content-grid">
          {visible.map((p) => (
            <article key={p.id} className="card" style={{ margin: 0 }}>
              <p className="hindi" style={{ fontSize: 18, fontWeight: 700, marginBottom: 2 }}>
                {p.hindi_text}
              </p>
              <p className="muted" style={{ fontSize: 13 }}>
                {p.english} · <span className="mini-chip">{p.category}</span>
              </p>

              {hasSantali(p) ? (
                <div className="text-block santali-block ol-chiki" style={{ margin: '8px 0' }}>
                  {p.santali_ol_chiki}
                </div>
              ) : (
                <div className="placeholder-block" style={{ margin: '8px 0' }}>
                  Santali not generated yet — tap “Generate Santali” below.
                </div>
              )}

              <div className="action-row">
                {!hasSantali(p) && (
                  <button
                    type="button"
                    className="btn-small primary"
                    disabled={busy[p.id] === 'translate'}
                    onClick={() => onTranslate(p)}
                  >
                    {busy[p.id] === 'translate' ? 'Translating…' : 'Generate Santali'}
                  </button>
                )}
                {hasSantali(p) && (
                  <button
                    type="button"
                    className="btn-audio"
                    disabled={busy[p.id] === 'audio'}
                    onClick={() => onPlay(p)}
                  >
                    ▶ {busy[p.id] === 'audio' ? 'Generating…' : 'Play Santali Audio'}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {data && (
        <p className="status-detail">
          {visible.length} phrase(s) · Santali text and audio:{' '}
          {VALIDATION_NOTICE}.
        </p>
      )}

      {message && (
        <p className="status-detail" role="status">
          {message}
        </p>
      )}
      {error && (
        <div className="error-banner" role="alert">
          <strong>Action failed.</strong> {error}
        </div>
      )}
    </div>
  )
}
