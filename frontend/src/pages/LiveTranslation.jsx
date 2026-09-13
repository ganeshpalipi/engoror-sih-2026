import { useEffect, useRef, useState } from 'react'
import { apiPostAudio, getHealth } from '../services/api'
import { useApiStatus } from '../hooks/useApiStatus'
import { useRecorder } from '../hooks/useRecorder'

const VALIDATION_NOTICE = 'AI-generated — Requires native-speaker validation'

function filenameForMime(mimeType) {
  if (!mimeType) return 'recording.webm'
  if (mimeType.includes('webm')) return 'recording.webm'
  if (mimeType.includes('mp4')) return 'recording.m4a'
  if (mimeType.includes('ogg')) return 'recording.ogg'
  if (mimeType.includes('wav')) return 'recording.wav'
  return 'recording.audio'
}

function StepCard({ number, label, active, done }) {
  return (
    <div className={`eng-live-step${done ? ' done' : ''}${active ? ' active' : ''}`}>
      <span>STEP {number}</span>
      <strong>{label}</strong>
    </div>
  )
}

export default function LiveTranslation() {
  const { data: health } = useApiStatus(getHealth)
  const recorder = useRecorder()

  const [mode, setMode] = useState('full')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [speech, setSpeech] = useState(null)
  const [asrOnly, setAsrOnly] = useState(null)
  const [replayUrl, setReplayUrl] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [playing, setPlaying] = useState(false)

  const replayRef = useRef('')
  const fileInputRef = useRef(null)
  const studentAudioRef = useRef(null)

  useEffect(() => {
    const previous = replayRef.current
    replayRef.current = replayUrl
    if (previous && previous !== replayUrl) URL.revokeObjectURL(previous)
  }, [replayUrl])

  useEffect(
    () => () => {
      if (replayRef.current) URL.revokeObjectURL(replayRef.current)
    },
    [],
  )

  const recording = recorder.state === 'recording'
  const busy = processing

  const asrComp = health?.components?.asr
  const mtComp = health?.components?.translation
  const dbComp = health?.components?.database
  const ttsComp = health?.components?.tts

  function resetResults() {
    setSpeech(null)
    setAsrOnly(null)
    setError('')
    setPlaying(false)
  }

  async function processBlob(blob, filename) {
    setProcessing(true)
    setError('')
    setSpeech(null)
    setAsrOnly(null)

    try {
      if (mode === 'asr') {
        const data = await apiPostAudio('/api/asr/transcribe', blob, filename, 'hi')
        setAsrOnly(data)

        if (data.message) {
          setError(data.message)
        }
      } else {
        const data = await apiPostAudio(
          '/api/classroom/speech-translate',
          blob,
          filename,
          'hi',
        )

        setSpeech(data)

        if (data.message) {
          setError(data.message)
        }
      }
    } catch (err) {
      setError(err.message || 'Processing failed. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  async function onStartRecording() {
    resetResults()

    try {
      await recorder.start()
    } catch {
      // recorder.error already contains a teacher-friendly message
    }
  }

  async function onStopAndProcess() {
    try {
      setProcessing(true)

      const { blob, seconds, mimeType } = await recorder.stop()
      setReplayUrl(URL.createObjectURL(blob))

      if (seconds < 1) {
        setError(
          'The recording was too short. Hold the button and speak a full Hindi sentence.',
        )
        return
      }

      await processBlob(blob, filenameForMime(mimeType))
    } catch (err) {
      setError(err.message || 'Could not process the recording.')
    } finally {
      setProcessing(false)
    }
  }

  function onCancelRecording() {
    recorder.reset()
    setError('')
  }

  function onUploadSelected(e) {
    const file = e.target.files?.[0]

    setUploadFile(file || null)
    resetResults()
  }

  async function onProcessUpload() {
    if (!uploadFile) return

    setReplayUrl(URL.createObjectURL(uploadFile))
    await processBlob(uploadFile, uploadFile.name || 'recording.webm')
  }

  const hindiText = asrOnly?.text || speech?.recognized_hindi || ''
  const santaliText = speech?.success ? speech.santali_ol_chiki : ''

  return (
    <div className="eng-live">
      <header className="eng-page-head">
        <p className="eyebrow">ENGOROR CLASSROOM AI</p>
        <h1>Live Classroom Translation</h1>
        <p>
          Speak naturally in Hindi. Engoror helps your students understand in
          Santali.
        </p>
      </header>

      <div className="eng-live-steps">
        <StepCard
          number="1"
          label="Teacher speaks Hindi"
          active={recording}
          done={Boolean(replayUrl)}
        />
        <StepCard
          number="2"
          label="Hindi recognized"
          active={busy && !hindiText}
          done={Boolean(hindiText)}
        />
        <StepCard
          number="3"
          label="Santali translation"
          active={busy && Boolean(hindiText) && !santaliText}
          done={Boolean(santaliText)}
        />
        <StepCard
          number="4"
          label="Student listens"
          active={playing}
          done={Boolean(speech?.audio_available)}
        />
      </div>

      <section className="eng-live-control-card">
        <div className="eng-live-control-top">
          <div>
            <p className="eyebrow">TEACHER INPUT</p>
            <h2>Speak or use a saved classroom recording</h2>
            <p className="muted">
              Short classroom sentences work best.
            </p>
          </div>

          <div className="eng-live-mode">
            <label htmlFor="pipeline-mode">Mode</label>

            <select
              id="pipeline-mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              disabled={busy || recording}
            >
              <option value="full">Hindi speech → Santali</option>
              <option value="asr">Hindi recognition only</option>
            </select>
          </div>
        </div>

        <div className="eng-live-actions">
          {!recording && (
            <button
              type="button"
              className="eng-main-record"
              onClick={onStartRecording}
              disabled={busy}
            >
              Start Recording
            </button>
          )}

          {recording && (
            <>
              <button
                type="button"
                className="eng-stop-record"
                onClick={onStopAndProcess}
                disabled={busy}
              >
                Stop & Process
              </button>

              <button
                type="button"
                className="eng-secondary-button"
                onClick={onCancelRecording}
              >
                Cancel
              </button>

              <span className="eng-listening">
                ● Listening — {recorder.elapsedSec}s
              </span>
            </>
          )}
        </div>

        <div className="eng-upload-row">
          <div>
            <strong>Saved audio demo</strong>
            <p className="muted">
              You can also upload WAV, MP3, M4A, WebM or OGG.
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.wav,.webm,.mp3,.m4a,.ogg"
            onChange={onUploadSelected}
          />

          <button
            type="button"
            className="eng-secondary-button"
            onClick={onProcessUpload}
            disabled={!uploadFile || busy}
          >
            Process Audio
          </button>
        </div>

        {busy && (
          <div className="eng-processing">
            <span className="eng-spinner" />
            <div>
              <strong>Engoror is translating locally...</strong>
              <p>
                Speech recognition, translation and student audio are running on
                this computer.
              </p>
            </div>
          </div>
        )}
      </section>

      {(error || recorder.error) && (
        <div className="eng-friendly-error">
          <strong>We could not complete that classroom request.</strong>
          <span>{recorder.error || error}</span>
        </div>
      )}

      {replayUrl && (
        <section className="eng-result-card">
          <p className="eng-result-label">TEACHER SPEECH</p>
          <audio
            controls
            src={replayUrl}
            className="eng-audio-player"
            aria-label="Teacher speech playback"
          />
        </section>
      )}

      {(hindiText || santaliText) && (
        <div className="eng-language-grid">
          <section className="eng-result-card">
            <p className="eng-result-label">HINDI — WHAT THE TEACHER SAID</p>

            <div className="eng-hindi-output hindi">
              {hindiText || 'Hindi text will appear here.'}
            </div>
          </section>

          {mode === 'full' && (
            <section className="eng-result-card eng-santali-card">
              <p className="eng-result-label">SANTALI — FOR THE STUDENTS</p>

              <div className="eng-santali-output ol-chiki">
                {santaliText || 'Santali translation will appear here.'}
              </div>

              {santaliText && (
                <span className="eng-validation">
                  {VALIDATION_NOTICE}
                </span>
              )}
            </section>
          )}
        </div>
      )}

      {speech?.success &&
        speech.audio_available &&
        speech.audio_url && (
          <section className="eng-student-audio">
            <div>
              <p className="eyebrow">STUDENT AUDIO</p>
              <h2>Let the student hear the lesson</h2>
              <p>
                Santali speech generated locally from the translated Ol Chiki
                text.
              </p>
            </div>

            <button
              type="button"
              className="eng-play-audio"
              onClick={() => {
                const el = studentAudioRef.current
                if (!el) return

                if (el.paused) {
                  el.play().catch(() =>
                    setError('Could not play the Santali audio. Try again.'),
                  )
                } else {
                  el.pause()
                }
              }}
            >
              {playing ? 'Pause Santali Audio' : 'Play Santali Audio'}
            </button>

            <audio
              ref={studentAudioRef}
              controls
              preload="none"
              src={speech.audio_url}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
              onError={() =>
                setError(
                  'The Santali audio file could not be loaded. Please record again.',
                )
              }
              className="eng-audio-player"
            />

            <span className="eng-validation">
              {VALIDATION_NOTICE}
            </span>
          </section>
        )}

      {speech?.success &&
        !speech.audio_available &&
        speech.tts_message && (
          <section className="eng-result-card">
            <h2>Student Audio</h2>
            <p>{speech.tts_message}</p>
          </section>
        )}

      <details className="eng-tech-details">
        <summary>Technical details</summary>

        <div className="eng-tech-grid">
          <div>
            <strong>Hindi speech recognition</strong>
            <span>
              {asrComp?.status === 'ok'
                ? 'Local model ready'
                : asrComp?.detail || 'Checking'}
            </span>
          </div>

          <div>
            <strong>Hindi → Santali translation</strong>
            <span>
              {mtComp?.status === 'ok'
                ? 'Local model ready'
                : mtComp?.detail || 'Checking'}
            </span>
          </div>

          <div>
            <strong>Santali voice</strong>
            <span>
              {ttsComp?.status === 'ok'
                ? 'Local model ready'
                : ttsComp?.detail || 'Checking'}
            </span>
          </div>

          <div>
            <strong>Local database</strong>
            <span>
              {dbComp?.status === 'ok'
                ? 'SQLite connected'
                : dbComp?.detail || 'Checking'}
            </span>
          </div>
        </div>

        {asrOnly && (
          <p>
            ASR latency: {asrOnly.latency_ms} ms · Model: {asrOnly.model}
          </p>
        )}

        {speech && (
          <p>
            ASR: {speech.asr_latency_ms} ms · Translation:{' '}
            {speech.translation_latency_ms} ms · TTS:{' '}
            {speech.tts_latency_ms || '—'} ms · Total:{' '}
            {speech.total_latency_ms} ms
          </p>
        )}
      </details>
    </div>
  )
}