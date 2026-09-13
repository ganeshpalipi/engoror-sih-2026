import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '../services/api'

const VALIDATION_NOTICE =
  'AI-generated - Requires native-speaker validation'

export default function Flashcards() {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [topic, setTopic] = useState('')
  const [busy, setBusy] = useState({})
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    apiGet('/api/flashcards')
      .then((response) => {
        if (active) setData(response)
      })
      .catch((err) => {
        if (active) {
          setLoadError(
            err.message || 'Could not load flashcards',
          )
        }
      })

    return () => {
      active = false
    }
  }, [])

  const visible = useMemo(() => {
    const rows = data?.flashcards || []

    return rows.filter(
      (card) => !topic || card.topic === topic,
    )
  }, [data, topic])

  const hasSantali = (card) =>
    card.validation_status === 'AI_GENERATED'

  function replaceCard(updated) {
    setData((current) => ({
      ...current,
      flashcards: current.flashcards.map((card) =>
        card.id === updated.id ? updated : card,
      ),
    }))
  }

  async function onTranslate(card) {
    setBusy((current) => ({
      ...current,
      [card.id]: 'translate',
    }))

    setError('')
    setMessage('')

    try {
      const response = await apiPost(
        `/api/flashcards/${card.id}/translate`,
        {},
      )

      replaceCard(response.flashcard)

      setMessage(
        `Santali word generated for "${card.english_word}".`,
      )
    } catch (err) {
      setError(err.message || 'Translation failed')
    } finally {
      setBusy((current) => {
        const next = { ...current }
        delete next[card.id]
        return next
      })
    }
  }

  async function onPlay(card) {
    setBusy((current) => ({
      ...current,
      [card.id]: 'audio',
    }))

    setError('')
    setMessage('')

    try {
      const response = await apiPost(
        `/api/flashcards/${card.id}/audio`,
        {},
      )

      const player = new Audio(response.audio_url)
      await player.play()

      setMessage(
        response.cached
          ? 'Playing saved Santali audio.'
          : 'Santali audio generated locally.',
      )
    } catch (err) {
      setError(err.message || 'Audio could not be played')
    } finally {
      setBusy((current) => {
        const next = { ...current }
        delete next[card.id]
        return next
      })
    }
  }

  return (
    <div className="eng-flashcards-page">
      <header className="eng-page-head">
        <p className="eyebrow">
          ENGOROR VISUAL LEARNING
        </p>

        <h1>Vocabulary Flashcards</h1>

        <p>
          Visual bilingual learning cards with Hindi words,
          Santali in Ol Chiki, and locally generated Santali audio.
        </p>
      </header>

      <section className="eng-fc-summary">
        <div>
          <strong>{data?.flashcards?.length || 0}</strong>
          <span>Visual flashcards</span>
        </div>

        <div>
          <strong>Hindi + Santali</strong>
          <span>Bilingual vocabulary</span>
        </div>

        <div>
          <strong>Local Audio</strong>
          <span>Student listening support</span>
        </div>
      </section>

      {data?.topics?.length > 0 && (
        <section className="eng-fc-filter">
          <p className="eng-result-label">
            FILTER BY TOPIC
          </p>

          <div className="eng-filter-row">
            <button
              type="button"
              className={`eng-filter-chip ${
                topic === '' ? 'active' : ''
              }`}
              onClick={() => setTopic('')}
            >
              All topics
            </button>

            {data.topics.map((item) => (
              <button
                key={item.topic}
                type="button"
                className={`eng-filter-chip ${
                  topic === item.topic ? 'active' : ''
                }`}
                onClick={() => setTopic(item.topic)}
              >
                {item.label_hindi} {item.label_english}
                <span className="eng-fc-count">
                  {item.count}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {loadError && (
        <div
          className="eng-friendly-error"
          role="alert"
        >
          <strong>
            Flashcards could not be loaded.
          </strong>
          <span>{loadError}</span>
        </div>
      )}

      {!data && !loadError && (
        <div className="eng-learning-loading">
          Loading visual flashcards...
        </div>
      )}

      {data && (
        <>
          <div className="eng-fc-heading">
            <div>
              <p className="eng-result-label">
                VISUAL VOCABULARY
              </p>

              <h2>Choose a card</h2>
            </div>

            <span>{visible.length} cards available</span>
          </div>

          <div className="eng-fc-grid">
            {visible.map((card) => (
              <article
                key={card.id}
                className="eng-fc-card"
              >
                <div className="eng-fc-card-top">
                  <span>{card.topic}</span>

                  {hasSantali(card) && (
                    <span className="eng-ready-small">
                      Santali ready
                    </span>
                  )}
                </div>

                <div
                  className="eng-fc-visual"
                  aria-hidden="true"
                >
                  {card.image_key ? (
                    <img
                      src={`/flashcards/${card.image_key}.svg`}
                      alt=""
                      loading="lazy"
                    />
                  ) : (
                    <span>{card.visual_emoji}</span>
                  )}
                </div>

                <div className="eng-fc-language">
                  <p className="eng-result-label">
                    HINDI
                  </p>

                  <h3 className="hindi">
                    {card.hindi_word}
                  </h3>

                  <p className="eng-fc-english">
                    {card.english_word}
                  </p>
                </div>

                <div className="eng-fc-santali">
                  <p className="eng-result-label">
                    SANTALI - OL CHIKI
                  </p>

                  {hasSantali(card) ? (
                    <div className="ol-chiki">
                      {card.santali_ol_chiki}
                    </div>
                  ) : (
                    <p>
                      Santali word has not been generated yet.
                    </p>
                  )}
                </div>

                <div className="eng-fc-actions">
                  {!hasSantali(card) && (
                    <button
                      type="button"
                      className="eng-translate-button"
                      disabled={
                        busy[card.id] === 'translate'
                      }
                      onClick={() =>
                        onTranslate(card)
                      }
                    >
                      {busy[card.id] === 'translate'
                        ? 'Translating...'
                        : 'Generate Santali'}
                    </button>
                  )}

                  {hasSantali(card) && (
                    <button
                      type="button"
                      className="eng-audio-button"
                      disabled={
                        busy[card.id] === 'audio'
                      }
                      onClick={() => onPlay(card)}
                    >
                      {busy[card.id] === 'audio'
                        ? 'Generating audio...'
                        : 'Play Santali Audio'}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {data && (
        <p className="eng-fc-validation-note">
          {VALIDATION_NOTICE}
        </p>
      )}

      {message && (
        <div
          className="eng-success-message"
          role="status"
        >
          {message}
        </div>
      )}

      {error && (
        <div
          className="eng-friendly-error"
          role="alert"
        >
          <strong>
            Flashcard action could not be completed.
          </strong>
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}