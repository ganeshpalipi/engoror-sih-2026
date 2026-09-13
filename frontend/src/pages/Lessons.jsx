import { useEffect, useMemo, useState } from 'react'
import {
  IS_SHOWCASE_MODE,
  apiGet,
  apiPost,
} from '../services/api'
import { formatMs } from '../utils/format'

const VALIDATION_NOTICE =
  'AI-generated — Requires native-speaker validation'

const NIPUN_NOTE =
  'Designed around foundational literacy and numeracy skills relevant to NIPUN Bharat goals.'

const SHOWCASE_LESSON_COUNT = 18

const SKILL_FILTERS = [
  {
    value: '',
    hindi: 'सभी',
    label: 'All skills',
  },
  {
    value: 'literacy',
    hindi: 'साक्षरता',
    label: 'Literacy',
  },
  {
    value: 'numeracy',
    hindi: 'गणित',
    label: 'Numeracy',
  },
]

export default function Lessons() {
  const [lessons, setLessons] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [skill, setSkill] = useState('')
  const [category, setCategory] = useState('')
  const [selectedId, setSelectedId] = useState(null)

  const [busy, setBusy] = useState({})
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    apiGet('/api/fln/lessons')
      .then((data) => {
        if (active) {
          setLessons(data.lessons || [])
        }
      })
      .catch((err) => {
        if (active) {
          setLoadError(
            err.message || 'Could not load lessons',
          )
        }
      })

    return () => {
      active = false
    }
  }, [])

  const categories = useMemo(() => {
    if (!lessons) return []

    const seen = new Map()

    for (const lesson of lessons) {
      if (
        lesson.category &&
        !seen.has(lesson.category)
      ) {
        seen.set(
          lesson.category,
          lesson.title_english,
        )
      }
    }

    return [...seen.entries()].map(
      ([value, label]) => ({
        value,
        label,
      }),
    )
  }, [lessons])

  const visible = useMemo(
    () =>
      (lessons || []).filter(
        (lesson) =>
          (!skill ||
            lesson.subject === skill) &&
          (!category ||
            lesson.category === category),
      ),
    [lessons, skill, category],
  )

  const selected =
    visible.find(
      (lesson) => lesson.id === selectedId,
    ) || null

  const hasSantali = (lesson) =>
    lesson.validation_status ===
    'AI_GENERATED'

  function replaceLesson(updated) {
    setLessons((rows) =>
      rows.map((row) =>
        row.id === updated.id
          ? updated
          : row,
      ),
    )
  }

  async function onTranslate(lesson) {
    setBusy((current) => ({
      ...current,
      [lesson.id]: 'translate',
    }))

    setError('')
    setMessage('')

    try {
      const data = await apiPost(
        `/api/fln/lessons/${lesson.id}/translate`,
        {},
      )

      replaceLesson(data.lesson)

      setMessage(
        `Santali generated locally in ${formatMs(
          data.translation_latency_ms,
        )}.`,
      )
    } catch (err) {
      setError(
        err.message || 'Translation failed',
      )
    } finally {
      setBusy((current) => {
        const next = { ...current }
        delete next[lesson.id]
        return next
      })
    }
  }

  async function onPlayAudio(lesson) {
    setBusy((current) => ({
      ...current,
      [lesson.id]: 'audio',
    }))

    setError('')
    setMessage('')

    try {
      const data = await apiPost(
        `/api/fln/lessons/${lesson.id}/audio`,
        {},
      )

      const player = new Audio(
        data.audio_url,
      )

      await player.play()

      setMessage(
        data.cached
          ? 'Playing saved Santali audio.'
          : `Santali audio generated in ${formatMs(
              data.latency_ms,
            )}.`,
      )
    } catch (err) {
      setError(
        err.message ||
          'Audio could not be played',
      )
    } finally {
      setBusy((current) => {
        const next = { ...current }
        delete next[lesson.id]
        return next
      })
    }
  }

  return (
    <div className="eng-lessons-page">
      <header className="eng-page-head">
        <p className="eyebrow">
          ENGOROR LEARNING HUB
        </p>

        <h1>Foundational Learning</h1>

        <p>
          Simple bilingual classroom lessons
          for literacy and numeracy, designed
          for Hindi-speaking teachers and
          Santali-speaking children.
        </p>
      </header>

      <section className="eng-learning-summary">
        <div>
          <strong>
            {IS_SHOWCASE_MODE
              ? SHOWCASE_LESSON_COUNT
              : lessons?.length || 0}
          </strong>

          <span>
            {IS_SHOWCASE_MODE
              ? 'Lessons in local demo'
              : 'Offline lessons'}
          </span>
        </div>

        <div>
          <strong>Hindi + Santali</strong>
          <span>Bilingual learning</span>
        </div>

        <div>
          <strong>FLN</strong>
          <span>Literacy & numeracy</span>
        </div>
      </section>

      <section className="eng-filter-panel">
        <div>
          <p className="eng-result-label">
            LEARNING SKILL
          </p>

          <div className="eng-filter-row">
            {SKILL_FILTERS.map(
              (filter) => (
                <button
                  key={filter.value}
                  type="button"
                  className={`eng-filter-chip ${
                    skill === filter.value
                      ? 'active'
                      : ''
                  }`}
                  onClick={() => {
                    setSkill(filter.value)
                    setSelectedId(null)
                  }}
                >
                  <span className="hindi">
                    {filter.hindi}
                  </span>

                  <span>
                    {filter.label}
                  </span>
                </button>
              ),
            )}
          </div>
        </div>

        {categories.length > 0 && (
          <div className="eng-topic-filter">
            <p className="eng-result-label">
              TOPIC
            </p>

            <div className="eng-filter-row">
              <button
                type="button"
                className={`eng-filter-chip ${
                  category === ''
                    ? 'active'
                    : ''
                }`}
                onClick={() => {
                  setCategory('')
                  setSelectedId(null)
                }}
              >
                All topics
              </button>

              {categories.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  className={`eng-filter-chip ${
                    category === item.value
                      ? 'active'
                      : ''
                  }`}
                  onClick={() => {
                    setCategory(
                      item.value,
                    )
                    setSelectedId(null)
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {loadError && !IS_SHOWCASE_MODE && (
        <div
          className="eng-friendly-error"
          role="alert"
        >
          <strong>
            Lessons could not be loaded.
          </strong>

          <span>{loadError}</span>
        </div>
      )}

      {!lessons &&
        !loadError &&
        !IS_SHOWCASE_MODE && (
          <div className="eng-learning-loading">
            Loading classroom lessons...
          </div>
        )}

      {(lessons || IS_SHOWCASE_MODE) && (
        <>
          <div className="eng-lessons-heading">
            <div>
              <p className="eng-result-label">
                LESSON BANK
              </p>

              <h2>Choose a lesson</h2>
            </div>

            <span>
              {IS_SHOWCASE_MODE
                ? `${SHOWCASE_LESSON_COUNT} lessons in local demo`
                : `${visible.length} lessons available`}
            </span>
          </div>

          {IS_SHOWCASE_MODE ? (
            <div className="eng-showcase-content-note">
              <strong>
                Lesson content is available
                in the local offline demo.
              </strong>

              <p>
                This public website
                demonstrates the Engoror
                interface. The classroom
                device contains the complete
                local lesson bank and runs
                translation and Santali audio
                directly on the device.
              </p>

              <p>
                During the working demo,
                Engoror provides 18
                foundational literacy and
                numeracy lessons without
                requiring a cloud AI API.
              </p>
            </div>
          ) : (
            <div className="eng-lessons-grid">
              {visible.map((lesson) => (
                <button
                  key={lesson.id}
                  type="button"
                  className={`eng-lesson-card ${
                    selectedId ===
                    lesson.id
                      ? 'selected'
                      : ''
                  }`}
                  onClick={() =>
                    setSelectedId(
                      selectedId ===
                        lesson.id
                        ? null
                        : lesson.id,
                    )
                  }
                >
                  <div className="eng-lesson-card-top">
                    <span>
                      Class{' '}
                      {
                        lesson.grade_level
                      }
                    </span>

                    <span
                      className={
                        hasSantali(
                          lesson,
                        )
                          ? 'eng-ready-small'
                          : 'eng-wait-small'
                      }
                    >
                      {hasSantali(
                        lesson,
                      )
                        ? 'Santali ready'
                        : 'Translation needed'}
                    </span>
                  </div>

                  <h3 className="hindi">
                    {
                      lesson.title_hindi
                    }
                  </h3>

                  <p>
                    {
                      lesson.title_english
                    }
                  </p>

                  <div className="eng-lesson-meta">
                    <span>
                      {lesson.subject}
                    </span>

                    <span>
                      {lesson.category}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {selected &&
        !IS_SHOWCASE_MODE && (
          <section className="eng-lesson-detail">
            <div className="eng-lesson-detail-head">
              <div>
                <p className="eng-result-label">
                  SELECTED LESSON
                </p>

                <h2 className="hindi">
                  {
                    selected.title_hindi
                  }
                </h2>

                <p>
                  {
                    selected.title_english
                  }{' '}
                  · Class{' '}
                  {
                    selected.grade_level
                  }{' '}
                  ·{' '}
                  {selected.skill ||
                    selected.subject}
                </p>
              </div>

              <span className="eng-local-badge">
                ● Works offline
              </span>
            </div>

            <div className="eng-lesson-info-grid">
              <div>
                <p className="eng-result-label">
                  LEARNING OBJECTIVE
                </p>

                <p>
                  {
                    selected.learning_objective
                  }
                </p>
              </div>

              <div>
                <p className="eng-result-label">
                  TEACHER ACTIVITY
                </p>

                <p className="hindi">
                  {
                    selected.activity_instruction
                  }
                </p>
              </div>
            </div>

            <div className="eng-lesson-language-grid">
              <div className="eng-lesson-language-card">
                <p className="eng-result-label">
                  HINDI — TEACHER
                </p>

                <div className="hindi eng-lesson-hindi">
                  {
                    selected.hindi_text
                  }
                </div>
              </div>

              <div className="eng-lesson-language-card santali">
                <p className="eng-result-label">
                  SANTALI — STUDENT
                </p>

                {hasSantali(
                  selected,
                ) ? (
                  <div className="ol-chiki eng-lesson-santali">
                    {
                      selected.santali_ol_chiki
                    }
                  </div>
                ) : (
                  <div className="eng-lesson-placeholder">
                    Santali translation
                    has not been generated
                    for this lesson yet.
                  </div>
                )}
              </div>
            </div>

            <div className="eng-lesson-actions">
              {!hasSantali(
                selected,
              ) && (
                <button
                  type="button"
                  className="eng-translate-button"
                  disabled={
                    busy[
                      selected.id
                    ] === 'translate'
                  }
                  onClick={() =>
                    onTranslate(
                      selected,
                    )
                  }
                >
                  {busy[
                    selected.id
                  ] === 'translate'
                    ? 'Translating...'
                    : 'Generate Santali'}
                </button>
              )}

              {hasSantali(
                selected,
              ) && (
                <button
                  type="button"
                  className="eng-audio-button"
                  disabled={
                    busy[
                      selected.id
                    ] === 'audio'
                  }
                  onClick={() =>
                    onPlayAudio(
                      selected,
                    )
                  }
                >
                  {busy[
                    selected.id
                  ] === 'audio'
                    ? 'Generating audio...'
                    : '▶ Play Santali Audio'}
                </button>
              )}
            </div>

            {hasSantali(
              selected,
            ) && (
              <span className="eng-validation">
                {
                  VALIDATION_NOTICE
                }
              </span>
            )}
          </section>
        )}

      {message &&
        !IS_SHOWCASE_MODE && (
          <div
            className="eng-success-message"
            role="status"
          >
            ✓ {message}
          </div>
        )}

      {error &&
        !IS_SHOWCASE_MODE && (
          <div
            className="eng-friendly-error"
            role="alert"
          >
            <strong>
              Lesson action could not
              be completed.
            </strong>

            <span>{error}</span>
          </div>
        )}

      <details className="eng-tech-details eng-learning-tech">
        <summary>
          About this learning content
        </summary>

        <p>{NIPUN_NOTE}</p>

        <p>
          Lesson content is stored locally
          and can be used without internet
          connectivity after setup.
        </p>
      </details>
    </div>
  )
}