import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '../services/api'
import { formatMs } from '../utils/format'

const VALIDATION_NOTICE = 'AI-generated — Requires native-speaker validation'
const NIPUN_NOTE =
  'Designed around foundational literacy and numeracy skills relevant to NIPUN Bharat goals.'

const SKILL_FILTERS = [
  { value: '', label_hindi: 'सभी', label: 'All skills' },
  { value: 'literacy', label_hindi: 'साक्षरता', label: 'Literacy' },
  { value: 'numeracy', label_hindi: 'गणित', label: 'Numeracy' },
]

export default function Lessons() {
  const [lessons, setLessons] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [skill, setSkill] = useState('')
  const [category, setCategory] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [busy, setBusy] = useState({}) // { [lessonId]: 'translate' | 'audio' }
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiGet('/api/fln/lessons')
      .then((d) => {
        if (active) setLessons(d.lessons || [])
      })
      .catch((e) => {
        if (active) setLoadError(e.message || 'Could not load lessons')
      })
    return () => {
      active = false
    }
  }, [])

  const categories = useMemo(() => {
    if (!lessons) return []
    const seen = new Map()
    for (const l of lessons) {
      if (l.category && !seen.has(l.category)) {
        seen.set(l.category, l.title_english)
      }
    }
    return [...seen.entries()].map(([value, label]) => ({ value, label }))
  }, [lessons])

  const visible = useMemo(
    () =>
      (lessons || []).filter(
        (l) =>
          (!skill || l.subject === skill) && (!category || l.category === category),
      ),
    [lessons, skill, category],
  )

  const selected = visible.find((l) => l.id === selectedId) || null

  function replaceLesson(updated) {
    setLessons((rows) => rows.map((r) => (r.id === updated.id ? updated : r)))
  }

  async function onTranslate(lesson) {
    setBusy((b) => ({ ...b, [lesson.id]: 'translate' }))
    setError('')
    setMessage('')
    try {
      const data = await apiPost(`/api/fln/lessons/${lesson.id}/translate`, {})
      replaceLesson(data.lesson)
      setMessage(
        `Santali generated in ${formatMs(data.translation_latency_ms)} (offline model). ${VALIDATION_NOTICE}.`,
      )
    } catch (err) {
      setError(err.message || 'Translation failed')
    } finally {
      setBusy((b) => {
        const next = { ...b }
        delete next[lesson.id]
        return next
      })
    }
  }

  async function onPlayAudio(lesson) {
    setBusy((b) => ({ ...b, [lesson.id]: 'audio' }))
    setError('')
    setMessage('')
    try {
      const data = await apiPost(`/api/fln/lessons/${lesson.id}/audio`, {})
      const player = new Audio(data.audio_url)
      await player.play()
      setMessage(
        data.cached
          ? 'Playing cached Santali audio.'
          : `Audio generated in ${formatMs(data.latency_ms)}.`,
      )
    } catch (err) {
      setError(err.message || 'Audio failed')
    } finally {
      setBusy((b) => {
        const next = { ...b }
        delete next[lesson.id]
        return next
      })
    }
  }

  const hasSantali = (l) => l.validation_status === 'AI_GENERATED'

  return (
    <div>
      <h1>FLN Lessons</h1>
      <p className="hindi subtitle">बुनियादी साक्षरता और गणित पाठ</p>
      <p className="muted">
        Foundational literacy &amp; numeracy lesson bank (Hindi + Santali Ol Chiki).
        Works fully offline. {NIPUN_NOTE}
      </p>

      {/* Skill filter */}
      <div className="chip-row" role="group" aria-label="Filter by skill">
        {SKILL_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={`chip${skill === f.value ? ' active' : ''}`}
            onClick={() => {
              setSkill(f.value)
              setSelectedId(null)
            }}
          >
            {f.label_hindi} · {f.label}
          </button>
        ))}
      </div>

      {/* Category filter */}
      {categories.length > 0 && (
        <div className="chip-row" role="group" aria-label="Filter by topic">
          <button
            type="button"
            className={`chip${category === '' ? ' active' : ''}`}
            onClick={() => setCategory('')}
          >
            All topics
          </button>
          {categories.map((c) => (
            <button
              key={c.value}
              type="button"
              className={`chip${category === c.value ? ' active' : ''}`}
              onClick={() => setCategory(c.value)}
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      {loadError && (
        <div className="error-banner" role="alert">
          <strong>Could not load lessons.</strong> {loadError}
        </div>
      )}

      {!lessons && !loadError && <p className="muted">Loading lessons…</p>}

      {lessons && (
        <>
          <p className="muted" style={{ fontSize: 13 }}>
            {visible.length} lesson(s)
          </p>
          <div className="content-grid">
            {visible.map((l) => (
              <button
                key={l.id}
                type="button"
                className={`content-card${selectedId === l.id ? ' selected' : ''}`}
                onClick={() => setSelectedId(selectedId === l.id ? null : l.id)}
                aria-pressed={selectedId === l.id}
              >
                <h3 className="hindi">{l.title_hindi}</h3>
                <p className="card-sub">{l.title_english}</p>
                <div className="card-meta">
                  <span className="mini-chip">Class {l.grade_level}</span>
                  <span className="mini-chip">{l.subject}</span>
                  {hasSantali(l) ? (
                    <span className="mini-chip">Santali ready</span>
                  ) : (
                    <span className="mini-chip warm">Needs translation</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {/* Detail */}
      {selected && (
        <section className="card" aria-label="Lesson detail">
          <h2 className="hindi">{selected.title_hindi}</h2>
          <p className="muted" style={{ marginTop: -6 }}>
            {selected.title_english} · Class {selected.grade_level} ·{' '}
            {selected.skill || selected.subject}
          </p>

          <h2 style={{ fontSize: 16 }}>Learning objective</h2>
          <p style={{ marginBottom: 10 }}>{selected.learning_objective}</p>

          <h2 style={{ fontSize: 16 }}>Activity (for the teacher)</h2>
          <p className="hindi" style={{ marginBottom: 10 }}>
            {selected.activity_instruction}
          </p>

          <h2 style={{ fontSize: 16 }}>Hindi text</h2>
          <div className="text-block hindi-block hindi">{selected.hindi_text}</div>

          <h2 style={{ fontSize: 16 }}>Santali — Ol Chiki</h2>
          {hasSantali(selected) ? (
            <div className="text-block santali-block ol-chiki">
              {selected.santali_ol_chiki}
            </div>
          ) : (
            <div className="placeholder-block">
              Santali translation not generated yet for this lesson. It will be
              produced on this device by the offline IndicTrans2 model — no
              internet needed.
            </div>
          )}

          <div className="action-row">
            {!hasSantali(selected) && (
              <button
                type="button"
                className="btn-small primary"
                disabled={busy[selected.id] === 'translate'}
                onClick={() => onTranslate(selected)}
              >
                {busy[selected.id] === 'translate'
                  ? 'Translating…'
                  : 'Generate Santali Translation'}
              </button>
            )}
            {hasSantali(selected) && (
              <button
                type="button"
                className="btn-audio"
                disabled={busy[selected.id] === 'audio'}
                onClick={() => onPlayAudio(selected)}
              >
                ▶ {busy[selected.id] === 'audio' ? 'Generating audio…' : 'Play Santali Audio'}
              </button>
            )}
          </div>

          {hasSantali(selected) && (
            <p>
              <span className="badge" style={{ marginBottom: 0 }}>
                {VALIDATION_NOTICE}
              </span>
            </p>
          )}
        </section>
      )}

      {message && (
        <p className="status-detail" role="status" style={{ marginTop: 10 }}>
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
