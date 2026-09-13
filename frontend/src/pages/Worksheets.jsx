import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '../services/api'

export default function Worksheets() {
  const [meta, setMeta] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [grade, setGrade] = useState(1)
  const [skill, setSkill] = useState('literacy')
  const [topic, setTopic] = useState('')
  const [count, setCount] = useState(5)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiGet('/api/worksheets/meta')
      .then((d) => {
        if (active) setMeta(d)
      })
      .catch((e) => {
        if (active) setLoadError(e.message || 'Could not load worksheet options')
      })
    return () => {
      active = false
    }
  }, [])

  const topicsForSkill = useMemo(
    () => (meta?.topics || []).filter((t) => t.skill === skill),
    [meta, skill],
  )

  // keep the selected topic valid whenever the skill changes
  useEffect(() => {
    if (topicsForSkill.length && !topicsForSkill.some((t) => t.topic === topic)) {
      setTopic(topicsForSkill[0].topic)
    }
  }, [topicsForSkill, topic])

  const topicLabel = useMemo(() => {
    const t = topicsForSkill.find((x) => x.topic === topic)
    return t ? `${t.label_hindi} · ${t.label_english}` : topic
  }, [topicsForSkill, topic])

  async function onGenerate(e) {
    e.preventDefault()
    setGenerating(true)
    setError('')
    setResult(null)
    try {
      const data = await apiPost('/api/worksheets/generate', {
        grade,
        skill,
        topic,
        count,
      })
      setResult(data)
    } catch (err) {
      setError(err.message || 'Worksheet generation failed')
    } finally {
      setGenerating(false)
    }
  }

  function printWorksheet() {
    if (!result) return
    const frame = document.getElementById('ws-print-frame')
    if (frame && frame.contentWindow) {
      frame.contentWindow.focus()
      frame.contentWindow.print()
    }
  }

  const typeLegend = meta?.type_legend || {}

  return (
    <div>
      <h1>Worksheet Generator</h1>
      <p className="hindi subtitle">द्विभाषी वर्कशीट जनरेटर</p>
      <p className="muted">
        Printable bilingual worksheets built from the lesson bank and flashcards
        — fully offline, deterministic (same options give the same sheet). A
        teacher answer key is included on the second page.
      </p>

      {loadError && (
        <div className="error-banner" role="alert">
          <strong>Could not load worksheet options.</strong> {loadError}
        </div>
      )}

      <form className="card worksheet-form" onSubmit={onGenerate}>
        <h2>Choose the worksheet</h2>

        <h2 style={{ fontSize: 15 }}>Class / कक्षा</h2>
        <div className="radio-row" role="group" aria-label="Class level">
          {[1, 2, 3].map((g) => (
            <button
              key={g}
              type="button"
              className={`chip${grade === g ? ' active' : ''}`}
              onClick={() => setGrade(g)}
              aria-pressed={grade === g}
            >
              Class {g}
            </button>
          ))}
        </div>

        <h2 style={{ fontSize: 15 }}>Skill / कौशल</h2>
        <div className="radio-row" role="group" aria-label="Skill">
          <button
            type="button"
            className={`chip${skill === 'literacy' ? ' active' : ''}`}
            onClick={() => setSkill('literacy')}
            aria-pressed={skill === 'literacy'}
          >
            साक्षरता · Literacy
          </button>
          <button
            type="button"
            className={`chip${skill === 'numeracy' ? ' active' : ''}`}
            onClick={() => setSkill('numeracy')}
            aria-pressed={skill === 'numeracy'}
          >
            गणित · Numeracy
          </button>
        </div>

        <h2 style={{ fontSize: 15 }}>Topic / विषय</h2>
        <select
          className="worksheet-select"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          aria-label="Worksheet topic"
        >
          {topicsForSkill.map((t) => (
            <option key={t.topic} value={t.topic}>
              {t.label_hindi} · {t.label_english}
            </option>
          ))}
        </select>

        <h2 style={{ fontSize: 15 }}>Questions / प्रश्न</h2>
        <div className="radio-row" role="group" aria-label="Number of questions">
          {[5, 10].map((n) => (
            <button
              key={n}
              type="button"
              className={`chip${count === n ? ' active' : ''}`}
              onClick={() => setCount(n)}
              aria-pressed={count === n}
            >
              {n} questions
            </button>
          ))}
        </div>

        <div style={{ marginTop: 8 }}>
          <button type="submit" className="btn btn-primary" disabled={generating || !topic}>
            {generating ? 'Generating…' : 'Generate Worksheet'}
          </button>
        </div>
      </form>

      {error && (
        <div className="error-banner" role="alert">
          <strong>Generation failed.</strong> {error}
        </div>
      )}

      {result && (
        <section className="ws-result" aria-label="Worksheet ready">
          <h3>
            Worksheet ready — Class {result.grade} · {result.topic_label}
          </h3>
          <p className="status-detail" style={{ marginBottom: 6 }}>
            {result.question_count} questions · types:{' '}
            {result.types_included.map((t) => typeLegend[t] || t).join(', ')} ·{' '}
            {result.offline ? 'generated offline' : ''}
          </p>
          {!result.santali_available && (
            <p className="placeholder-block" style={{ margin: '6px 0 10px' }}>
              This sheet is Hindi-only right now: the Santali translation model
              is not ready on this device. Generate translations first (see FLN
              Lessons / Model Status), then regenerate the worksheet to get the
              bilingual version.
            </p>
          )}
          {result.validation_notice && (
            <p>
              <span className="badge" style={{ marginBottom: 6 }}>
                {result.validation_notice}
              </span>
            </p>
          )}
          <div className="action-row">
            <a
              className="btn-small primary"
              href={result.html_url}
              target="_blank"
              rel="noreferrer"
            >
              Preview (new tab)
            </a>
            <button type="button" className="btn-small" onClick={printWorksheet}>
              🖨️ Print
            </button>
            <a className="btn-small" href={result.download_url}>
              ⬇ Download HTML
            </a>
          </div>
          <p className="muted" style={{ fontSize: 12.5 }}>
            Tip: Print → “Save as PDF” gives a PDF with correct Devanagari and
            Ol Chiki text (no extra software needed).
          </p>
          <iframe
            id="ws-print-frame"
            title="Worksheet preview"
            className="ws-frame"
            src={result.html_url}
          />
          <p className="muted" style={{ fontSize: 12 }}>
            {result.nipun_note}
          </p>
        </section>
      )}
    </div>
  )
}
