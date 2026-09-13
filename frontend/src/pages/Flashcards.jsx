import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '../services/api'

const VALIDATION_NOTICE = 'AI-generated — Requires native-speaker validation'

export default function Flashcards() {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [topic, setTopic] = useState('')
  const [busy, setBusy] = useState({}) // { [cardId]: 'translate' | 'audio' }
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiGet('/api/flashcards')
      .then((d) => {
        if (active) setData(d)
      })
      .catch((e) => {
        if (active) setLoadError(e.message || 'Could not load flashcards')
      })
    return () => {
      active = false
    }
  }, [])

  const visible = useMemo(() => {
    const rows = data?.flashcards || []
    return rows.filter((c) => !topic || c.topic === topic)
  }, [data, topic])

  const topicInfo = useMemo(() => {
    const map = new Map()
    for (const t of data?.topics || []) map.set(t.topic, t)
    return map
  }, [data])

  function replaceCard(updated) {
    setData((d) => ({
      ...d,
      flashcards: d.flashcards.map((c) => (c.id === updated.id ? updated : c)),
    }))
  }

  async function onTranslate(card) {
    setBusy((b) => ({ ...b, [card.id]: 'translate' }))
    setError('')
    setMessage('')
    try {
      // Reuse the flashcard translate endpoint shape (phrase route is generic;
      // flashcards expose the same behaviour through their own route).
      const resp = await apiPost(`/api/flashcards/${card.id}/translate`, {})
      replaceCard(resp.flashcard)
      setMessage('Santali word generated (offline model).')
    } catch (err) {
      setError(err.message || 'Translation failed')
    } finally {
      setBusy((b) => {
        const next = { ...b }
        delete next[card.id]
        return next
      })
    }
  }

  async function onPlay(card) {
    setBusy((b) => ({ ...b, [card.id]: 'audio' }))
    setError('')
    setMessage('')
    try {
      const resp = await apiPost(`/api/flashcards/${card.id}/audio`, {})
      const player = new Audio(resp.audio_url)
      await player.play()
      setMessage(resp.cached ? 'Playing cached audio.' : 'Audio generated (offline TTS).')
    } catch (err) {
      setError(err.message || 'Audio failed')
    } finally {
      setBusy((b) => {
        const next = { ...b }
        delete next[card.id]
        return next
      })
    }
  }

  const hasSantali = (c) => c.validation_status === 'AI_GENERATED'

  return (
    <div>
      <h1>Flashcards</h1>
      <p className="hindi subtitle">चित्र फ्लैशकार्ड</p>
      <p className="muted">
        Visual vocabulary cards — local SVG/emoji artwork only (nothing is
        downloaded at runtime), Hindi word, Santali (Ol Chiki) word and audio.
      </p>

      {data?.topics?.length > 0 && (
        <div className="chip-row" role="group" aria-label="Filter by topic">
          <button
            type="button"
            className={`chip${topic === '' ? ' active' : ''}`}
            onClick={() => setTopic('')}
          >
            All topics
          </button>
          {data.topics.map((t) => (
            <button
              key={t.topic}
              type="button"
              className={`chip${topic === t.topic ? ' active' : ''}`}
              onClick={() => setTopic(t.topic)}
            >
              {t.label_hindi} · {t.label_english}
              <span className="chip-count">({t.count})</span>
            </button>
          ))}
        </div>
      )}

      {loadError && (
        <div className="error-banner" role="alert">
          <strong>Could not load flashcards.</strong> {loadError}
        </div>
      )}

      {!data && !loadError && <p className="muted">Loading flashcards…</p>}

      {data && (
        <div className="flashcard-grid">
          {visible.map((c) => (
            <article key={c.id} className="flashcard">
              <div className="fc-visual" aria-hidden="true">
                {c.image_key ? (
                  <img src={`/flashcards/${c.image_key}.svg`} alt="" loading="lazy" />
                ) : (
                  c.visual_emoji
                )}
              </div>
              <div className="fc-hindi hindi">{c.hindi_word}</div>
              <div className="fc-english">{c.english_word}</div>
              {hasSantali(c) ? (
                <div className="fc-santali ol-chiki">{c.santali_ol_chiki}</div>
              ) : (
                <button
                  type="button"
                  className="btn-small primary"
                  disabled={busy[c.id] === 'translate'}
                  onClick={() => onTranslate(c)}
                >
                  {busy[c.id] === 'translate' ? '…' : 'Generate Santali'}
                </button>
              )}
              {hasSantali(c) && (
                <button
                  type="button"
                  className="btn-audio"
                  style={{ minHeight: 38, padding: '6px 12px', fontSize: 14 }}
                  disabled={busy[c.id] === 'audio'}
                  onClick={() => onPlay(c)}
                  aria-label={`Play Santali audio for ${c.english_word}`}
                >
                  🔊 {busy[c.id] === 'audio' ? '…' : 'Audio'}
                </button>
              )}
            </article>
          ))}
        </div>
      )}

      {data && (
        <p className="status-detail">
          {visible.length} card(s)
          {topic && topicInfo.get(topic)
            ? ` · topic: ${topicInfo.get(topic).label_english}`
            : ''}{' '}
          · Santali words and audio: {VALIDATION_NOTICE}.
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
