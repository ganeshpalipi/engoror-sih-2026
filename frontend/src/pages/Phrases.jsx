import { useEffect, useMemo, useState } from 'react'
import {
  IS_SHOWCASE_MODE,
  apiGet,
  apiPost,
} from '../services/api'
import { formatMs } from '../utils/format'

const VALIDATION_NOTICE =
  'AI-generated — Requires native-speaker validation'

const SHOWCASE_PHRASE_COUNT = 13

export default function Phrases() {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [category, setCategory] = useState('')
  const [busy, setBusy] = useState({})
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    apiGet('/api/phrases')
      .then((response) => {
        if (active) {
          setData(response)
        }
      })
      .catch((err) => {
        if (active) {
          setLoadError(
            err.message || 'Could not load phrases',
          )
        }
      })

    return () => {
      active = false
    }
  }, [])

  const visible = useMemo(() => {
    const rows = data?.phrases || []

    return rows.filter(
      (phrase) =>
        !category ||
        phrase.category === category,
    )
  }, [data, category])

  const hasSantali = (phrase) =>
    phrase.validation_status === 'AI_GENERATED'

  function replacePhrase(updated) {
    setData((current) => ({
      ...current,
      phrases: current.phrases.map((phrase) =>
        phrase.id === updated.id
          ? updated
          : phrase,
      ),
    }))
  }

  function setBusyFor(id, kind) {
    setBusy((current) => ({
      ...current,
      [id]: kind,
    }))
  }

  function clearBusyFor(id) {
    setBusy((current) => {
      const next = { ...current }
      delete next[id]
      return next
    })
  }

  async function onTranslate(phrase) {
    setBusyFor(phrase.id, 'translate')
    setError('')
    setMessage('')

    try {
      const response = await apiPost(
        `/api/phrases/${phrase.id}/translate`,
        {},
      )

      replacePhrase(response.phrase)

      setMessage(
        `Santali generated locally in ${formatMs(
          response.translation_latency_ms,
        )}.`,
      )
    } catch (err) {
      setError(
        err.message || 'Translation failed',
      )
    } finally {
      clearBusyFor(phrase.id)
    }
  }

  async function onPlay(phrase) {
    setBusyFor(phrase.id, 'audio')
    setError('')
    setMessage('')

    try {
      const response = await apiPost(
        `/api/phrases/${phrase.id}/audio`,
        {},
      )

      const player = new Audio(
        response.audio_url,
      )

      await player.play()

      setMessage(
        response.cached
          ? 'Playing saved Santali audio.'
          : `Santali audio generated in ${formatMs(
              response.latency_ms,
            )}.`,
      )
    } catch (err) {
      setError(
        err.message ||
          'Audio could not be played',
      )
    } finally {
      clearBusyFor(phrase.id)
    }
  }

  return (
    <div className="eng-phrases-page">
      <header className="eng-page-head">
        <p className="eyebrow">
          ENGOROR CLASSROOM TOOL
        </p>

        <h1>Classroom Phrase Pack</h1>

        <p>
          Everyday Hindi classroom instructions
          translated into Santali in Ol Chiki,
          with locally generated student audio.
        </p>
      </header>

      <section className="eng-phrase-summary">
        <div>
          <strong>
            {IS_SHOWCASE_MODE
              ? SHOWCASE_PHRASE_COUNT
              : data?.phrases?.length || 0}
          </strong>

          <span>
            {IS_SHOWCASE_MODE
              ? 'Phrases in local demo'
              : 'Classroom phrases'}
          </span>
        </div>

        <div>
          <strong>Hindi → Santali</strong>
          <span>Local translation</span>
        </div>

        <div>
          <strong>Audio</strong>
          <span>Offline Santali speech</span>
        </div>
      </section>

      {!IS_SHOWCASE_MODE &&
        data?.categories?.length > 0 && (
          <section className="eng-phrase-filter">
            <p className="eng-result-label">
              FILTER BY CATEGORY
            </p>

            <div className="eng-filter-row">
              <button
                type="button"
                className={`eng-filter-chip ${
                  category === ''
                    ? 'active'
                    : ''
                }`}
                onClick={() =>
                  setCategory('')
                }
              >
                All phrases
              </button>

              {data.categories.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`eng-filter-chip ${
                    category === item
                      ? 'active'
                      : ''
                  }`}
                  onClick={() =>
                    setCategory(item)
                  }
                >
                  {item}
                </button>
              ))}
            </div>
          </section>
        )}

      {loadError &&
        !IS_SHOWCASE_MODE && (
          <div
            className="eng-friendly-error"
            role="alert"
          >
            <strong>
              Phrase pack could not be loaded.
            </strong>

            <span>{loadError}</span>
          </div>
        )}

      {!data &&
        !loadError &&
        !IS_SHOWCASE_MODE && (
          <div className="eng-learning-loading">
            Loading classroom phrases...
          </div>
        )}

      {(data || IS_SHOWCASE_MODE) && (
        <>
          <div className="eng-phrases-heading">
            <div>
              <p className="eng-result-label">
                CLASSROOM PHRASES
              </p>

              <h2>
                Ready for the teacher
              </h2>
            </div>

            <span>
              {IS_SHOWCASE_MODE
                ? `${SHOWCASE_PHRASE_COUNT} phrases in local demo`
                : `${visible.length} phrases`}
            </span>
          </div>

          {IS_SHOWCASE_MODE ? (
            <div className="eng-showcase-content-note">
              <strong>
                Classroom phrases are available
                in the local offline demo.
              </strong>

              <p>
                Engoror includes 13 commonly
                used classroom phrases for
                teacher instructions, activities
                and praise.
              </p>

              <p>
                In the local demo, each Hindi
                phrase can be shown in Santali
                Ol Chiki and played as Santali
                audio without using a cloud AI
                service.
              </p>
            </div>
          ) : (
            <div className="eng-phrase-grid">
              {visible.map((phrase) => (
                <article
                  key={phrase.id}
                  className="eng-phrase-card"
                >
                  <div className="eng-phrase-card-head">
                    <span>
                      {phrase.category ||
                        'Classroom'}
                    </span>

                    {hasSantali(
                      phrase,
                    ) && (
                      <span className="eng-ready-small">
                        Santali ready
                      </span>
                    )}
                  </div>

                  <div className="eng-phrase-hindi">
                    <p className="eng-result-label">
                      HINDI — TEACHER
                    </p>

                    <h3 className="hindi">
                      {phrase.hindi_text}
                    </h3>

                    {phrase.english && (
                      <p className="eng-phrase-english">
                        {phrase.english}
                      </p>
                    )}
                  </div>

                  <div className="eng-phrase-santali">
                    <p className="eng-result-label">
                      SANTALI — STUDENT
                    </p>

                    {hasSantali(
                      phrase,
                    ) ? (
                      <div className="ol-chiki">
                        {
                          phrase.santali_ol_chiki
                        }
                      </div>
                    ) : (
                      <p className="eng-phrase-placeholder">
                        Generate the Santali
                        translation for this
                        classroom phrase.
                      </p>
                    )}
                  </div>

                  <div className="eng-phrase-actions">
                    {!hasSantali(
                      phrase,
                    ) && (
                      <button
                        type="button"
                        className="eng-translate-button"
                        disabled={
                          busy[
                            phrase.id
                          ] ===
                          'translate'
                        }
                        onClick={() =>
                          onTranslate(
                            phrase,
                          )
                        }
                      >
                        {busy[
                          phrase.id
                        ] ===
                        'translate'
                          ? 'Translating...'
                          : 'Generate Santali'}
                      </button>
                    )}

                    {hasSantali(
                      phrase,
                    ) && (
                      <button
                        type="button"
                        className="eng-audio-button"
                        disabled={
                          busy[
                            phrase.id
                          ] === 'audio'
                        }
                        onClick={() =>
                          onPlay(phrase)
                        }
                      >
                        {busy[
                          phrase.id
                        ] === 'audio'
                          ? 'Generating audio...'
                          : '▶ Play Santali Audio'}
                      </button>
                    )}
                  </div>

                  {hasSantali(
                    phrase,
                  ) && (
                    <span className="eng-validation">
                      {
                        VALIDATION_NOTICE
                      }
                    </span>
                  )}
                </article>
              ))}
            </div>
          )}
        </>
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
              Phrase action could not
              be completed.
            </strong>

            <span>{error}</span>
          </div>
        )}

      <details className="eng-tech-details eng-phrase-tech">
        <summary>
          How Phrase Pack works
        </summary>

        <p>
          Hindi classroom phrase → local
          translation → Santali Ol Chiki
          text → local Santali speech.
        </p>

        <p>
          Core inference works without a
          cloud API once the required
          models are available on the
          classroom device.
        </p>
      </details>
    </div>
  )
}