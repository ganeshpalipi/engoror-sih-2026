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
      .then((data) => {
        if (active) setMeta(data)
      })
      .catch((err) => {
        if (active) {
          setLoadError(
            err.message || 'Could not load worksheet options',
          )
        }
      })

    return () => {
      active = false
    }
  }, [])

  const topicsForSkill = useMemo(
    () =>
      (meta?.topics || []).filter(
        (item) => item.skill === skill,
      ),
    [meta, skill],
  )

  useEffect(() => {
    if (
      topicsForSkill.length &&
      !topicsForSkill.some(
        (item) => item.topic === topic,
      )
    ) {
      setTopic(topicsForSkill[0].topic)
    }
  }, [topicsForSkill, topic])

  async function onGenerate(e) {
    e.preventDefault()

    setGenerating(true)
    setError('')
    setResult(null)

    try {
      const data = await apiPost(
        '/api/worksheets/generate',
        {
          grade,
          skill,
          topic,
          count,
        },
      )

      setResult(data)
    } catch (err) {
      setError(
        err.message || 'Worksheet generation failed',
      )
    } finally {
      setGenerating(false)
    }
  }

  function printWorksheet() {
    if (!result) return

    const frame =
      document.getElementById('ws-print-frame')

    if (frame?.contentWindow) {
      frame.contentWindow.focus()
      frame.contentWindow.print()
    }
  }

  const typeLegend = meta?.type_legend || {}

  return (
    <div className="eng-worksheets-page">
      <header className="eng-page-head">
        <p className="eyebrow">
          ENGOROR TEACHER TOOL
        </p>

        <h1>Worksheet Generator</h1>

        <p>
          Create printable bilingual classroom worksheets
          for foundational literacy and numeracy.
        </p>
      </header>

      <section className="eng-ws-summary">
        <div>
          <strong>Class 1–3</strong>
          <span>Primary learning</span>
        </div>

        <div>
          <strong>Literacy + Numeracy</strong>
          <span>FLN focused</span>
        </div>

        <div>
          <strong>Printable</strong>
          <span>Worksheet + answer key</span>
        </div>
      </section>

      {loadError && (
        <div
          className="eng-friendly-error"
          role="alert"
        >
          <strong>
            Worksheet options could not be loaded.
          </strong>
          <span>{loadError}</span>
        </div>
      )}

      <form
        className="eng-ws-builder"
        onSubmit={onGenerate}
      >
        <div className="eng-ws-builder-head">
          <div>
            <p className="eng-result-label">
              WORKSHEET SETUP
            </p>

            <h2>Build a worksheet</h2>
          </div>

          <span className="eng-local-badge">
            ● Generated locally
          </span>
        </div>

        <div className="eng-ws-section">
          <div className="eng-ws-step">
            <span>1</span>

            <div>
              <strong>Choose class</strong>
              <p>Select the student grade level.</p>
            </div>
          </div>

          <div className="eng-filter-row">
            {[1, 2, 3].map((item) => (
              <button
                key={item}
                type="button"
                className={`eng-filter-chip ${
                  grade === item ? 'active' : ''
                }`}
                onClick={() => setGrade(item)}
                aria-pressed={grade === item}
              >
                Class {item}
              </button>
            ))}
          </div>
        </div>

        <div className="eng-ws-section">
          <div className="eng-ws-step">
            <span>2</span>

            <div>
              <strong>Choose skill</strong>
              <p>
                Select literacy or numeracy.
              </p>
            </div>
          </div>

          <div className="eng-filter-row">
            <button
              type="button"
              className={`eng-filter-chip ${
                skill === 'literacy'
                  ? 'active'
                  : ''
              }`}
              onClick={() => {
                setSkill('literacy')
                setResult(null)
              }}
            >
              साक्षरता · Literacy
            </button>

            <button
              type="button"
              className={`eng-filter-chip ${
                skill === 'numeracy'
                  ? 'active'
                  : ''
              }`}
              onClick={() => {
                setSkill('numeracy')
                setResult(null)
              }}
            >
              गणित · Numeracy
            </button>
          </div>
        </div>

        <div className="eng-ws-section">
          <div className="eng-ws-step">
            <span>3</span>

            <div>
              <strong>Choose topic</strong>
              <p>
                Pick the lesson topic for this sheet.
              </p>
            </div>
          </div>

          <select
            className="eng-ws-select"
            value={topic}
            onChange={(e) =>
              setTopic(e.target.value)
            }
            aria-label="Worksheet topic"
          >
            {topicsForSkill.map((item) => (
              <option
                key={item.topic}
                value={item.topic}
              >
                {item.label_hindi} ·{' '}
                {item.label_english}
              </option>
            ))}
          </select>
        </div>

        <div className="eng-ws-section">
          <div className="eng-ws-step">
            <span>4</span>

            <div>
              <strong>
                Number of questions
              </strong>
              <p>
                Choose the worksheet length.
              </p>
            </div>
          </div>

          <div className="eng-filter-row">
            {[5, 10].map((item) => (
              <button
                key={item}
                type="button"
                className={`eng-filter-chip ${
                  count === item ? 'active' : ''
                }`}
                onClick={() => setCount(item)}
              >
                {item} questions
              </button>
            ))}
          </div>
        </div>

        <div className="eng-ws-generate-area">
          <button
            type="submit"
            className="eng-ws-generate-button"
            disabled={generating || !topic}
          >
            {generating
              ? 'Generating worksheet...'
              : 'Generate Worksheet'}
          </button>

          <span>
            Bilingual output depends on available
            Santali translations.
          </span>
        </div>

        {generating && (
          <div className="eng-processing">
            <span className="eng-spinner" />

            <div>
              <strong>
                Preparing your worksheet...
              </strong>

              <p>
                Engoror is creating the printable
                classroom material locally.
              </p>
            </div>
          </div>
        )}
      </form>

      {error && (
        <div
          className="eng-friendly-error"
          role="alert"
        >
          <strong>
            Worksheet could not be generated.
          </strong>
          <span>{error}</span>
        </div>
      )}

      {result && (
        <section
          className="eng-ws-result"
          aria-label="Worksheet ready"
        >
          <div className="eng-ws-result-head">
            <div>
              <p className="eng-result-label">
                WORKSHEET READY
              </p>

              <h2>
                Class {result.grade} ·{' '}
                {result.topic_label}
              </h2>

              <p>
                {result.question_count} questions
                {result.types_included?.length
                  ? ` · ${result.types_included
                      .map(
                        (item) =>
                          typeLegend[item] || item,
                      )
                      .join(', ')}`
                  : ''}
              </p>
            </div>

            <span className="eng-success-pill">
              ✓ Ready to print
            </span>
          </div>

          <div className="eng-ws-result-info">
            <div>
              <strong>
                {result.question_count}
              </strong>
              <span>Questions</span>
            </div>

            <div>
              <strong>
                {result.santali_available
                  ? 'Bilingual'
                  : 'Hindi'}
              </strong>
              <span>Worksheet language</span>
            </div>

            <div>
              <strong>
                {result.offline
                  ? 'Local'
                  : 'Generated'}
              </strong>
              <span>Generation mode</span>
            </div>
          </div>

          {!result.santali_available && (
            <div className="eng-ws-warning">
              Santali text is not available for all
              items in this worksheet. The Hindi
              worksheet can still be used.
            </div>
          )}

          {result.validation_notice && (
            <span className="eng-validation">
              {result.validation_notice}
            </span>
          )}

          <div className="eng-ws-actions">
            <a
              className="eng-ws-primary-action"
              href={result.html_url}
              target="_blank"
              rel="noreferrer"
            >
              Preview Worksheet
            </a>

            <button
              type="button"
              className="eng-ws-secondary-action"
              onClick={printWorksheet}
            >
              Print Worksheet
            </button>

            <a
              className="eng-ws-secondary-action"
              href={result.download_url}
            >
              Download HTML
            </a>
          </div>

          <p className="eng-ws-tip">
            Tip: In the print window choose
            “Save as PDF” to create a PDF copy.
          </p>

          <iframe
            id="ws-print-frame"
            src={result.html_url}
            title="Worksheet print frame"
            className="eng-ws-print-frame"
          />
        </section>
      )}
    </div>
  )
}