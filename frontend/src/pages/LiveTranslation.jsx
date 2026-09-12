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
function ModelCard({ label, state, detail }) {
  const dot = state === 'ok' ? 'ok' : state === 'error' ? 'err' : 'wait'
  return (
    <div className="card">
      <div className="status-row">
        <span className={`status-dot ${dot}`} />
        <span className="status-label">{label}</span>
      </div>
      <p className="status-detail" style={{ marginBottom: 0 }}>
        {detail}
      </p>
    </div>
  )
}

export default function LiveTranslation() {
  const { data: health } = useApiStatus(getHealth)
  const recorder = useRecorder()

  const [mode, setMode] = useState('full') // 'full' | 'asr'
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [speech, setSpeech] = useState(null) // /api/classroom/speech-translate result
  const [asrOnly, setAsrOnly] = useState(null) // /api/asr/transcribe result
  const [replayUrl, setReplayUrl] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [playing, setPlaying] = useState(false)
  const replayRef = useRef('')
  const fileInputRef = useRef(null)
  const studentAudioRef = useRef(null)

  // Revoke the previous object URL whenever a new one is set.
  useEffect(() => {
    const previous = replayRef.current
    replayRef.current = replayUrl
    if (previous && previous !== replayUrl) URL.revokeObjectURL(previous)
  }, [replayUrl])
  useEffect(() => () => {
    if (replayRef.current) URL.revokeObjectURL(replayRef.current)
  }, [])

  const asrComp = health?.components?.asr
  const mtComp = health?.components?.translation
  const dbComp = health?.components?.database
  const ttsComp = health?.components?.tts

  const recording = recorder.state === 'recording'
  const busy = processing

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
        if (data.message) setError(data.message) // e.g. no speech detected
      } else {
        const data = await apiPostAudio('/api/classroom/speech-translate', blob, filename, 'hi')
        setSpeech(data)
        if (data.message) setError(data.message)
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
      // recorder.error already carries a teacher-friendly message
    }
  }

  async function onStopAndProcess() {
    try {
      setProcessing(true)
      const { blob, seconds, mimeType } = await recorder.stop()
      setReplayUrl(URL.createObjectURL(blob))
      if (seconds < 1) {
        setError('The recording was too short. Hold the button and speak a full Hindi sentence.')
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

  return (
    <div>
      <h1>Live Translation</h1>
      <p className="hindi subtitle">बोलिए हिंदी में → संथाली (ओल चिकी)</p>
      <p className="muted">
        Teacher speaks Hindi → offline speech recognition → Hindi text → the Phase 2
        IndicTrans2 translator → Santali in Ol Chiki → the Phase 4 offline Santali
        voice speaks it aloud for the student. Everything runs on this device.
      </p>

      {/* Status strip: ASR / Translation / Database */}
      <div className="grid-cards" style={{ marginTop: 14 }}>
        <ModelCard
          label="ASR (speech → Hindi)"
          state={asrComp ? (asrComp.status === 'not_ready' ? 'wait' : asrComp.status) : 'wait'}
          detail={
            asrComp
              ? asrComp.status === 'ok'
                ? `Offline · ${asrComp.detail}`
                : asrComp.detail
              : 'Checking…'
          }
        />
        <ModelCard
          label="Translation (Hindi → Santali)"
          state={mtComp ? (mtComp.status === 'not_ready' ? 'wait' : mtComp.status) : 'wait'}
          detail={
            mtComp
              ? mtComp.status === 'ok'
                ? 'Offline · IndicTrans2 ready'
                : mtComp.detail
              : 'Checking…'
          }
        />
        <ModelCard
          label="TTS (Santali speech)"
          state={ttsComp ? (ttsComp.status === 'not_ready' ? 'wait' : ttsComp.status) : 'wait'}
          detail={
            ttsComp
              ? ttsComp.status === 'ok'
                ? 'Offline · model cached'
                : ttsComp.detail
              : 'Checking…'
          }
        />
        <ModelCard
          label="Database (SQLite)"
          state={dbComp ? dbComp.status : 'wait'}
          detail={dbComp ? (dbComp.status === 'ok' ? 'Connected' : dbComp.detail) : 'Checking…'}
        />
      </div>

      {/* Pipeline */}
      <ul className="pipeline" aria-label="Processing pipeline">
        <li className="pipeline-step"><span className="step-num">1</span> 🎤 Teacher speaks Hindi</li>
        <li className="pipeline-arrow">→</li>
        <li className="pipeline-step"><span className="step-num">2</span> Offline ASR</li>
        <li className="pipeline-arrow">→</li>
        <li className="pipeline-step"><span className="step-num">3</span> Hindi text</li>
        <li className="pipeline-arrow">→</li>
        <li className="pipeline-step"><span className="step-num">4</span> IndicTrans2</li>
        <li className="pipeline-arrow">→</li>
        <li className="pipeline-step"><span className="step-num">5</span> Santali (Ol Chiki)</li>
        <li className="pipeline-arrow">→</li>
        <li className="pipeline-step"><span className="step-num">6</span> Offline TTS</li>
        <li className="pipeline-arrow">→</li>
        <li className="pipeline-step"><span className="step-num">7</span> 🔊 Student hears Santali</li>
      </ul>

      {/* Recorder */}
      <div className="card" style={{ marginTop: 6 }}>
        <h2>Classroom Microphone</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {!recording && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onStartRecording}
              disabled={busy}
            >
              🎤 Start Recording
            </button>
          )}
          {recording && (
            <button
              type="button"
              className="btn btn-accent"
              onClick={onStopAndProcess}
              disabled={busy}
            >
              ⏹ Stop &amp; Process
            </button>
          )}
          {recording && (
            <button type="button" className="btn btn-outline" onClick={onCancelRecording}>
              Cancel
            </button>
          )}
          {recording && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span
                className="status-dot err"
                style={{ animation: 'pulse 1.2s infinite' }}
                aria-hidden="true"
              />
              <strong style={{ color: 'var(--danger)' }}>
                Listening… speak Hindi ({recorder.elapsedSec}s)
              </strong>
            </span>
          )}
          {busy && <span className="muted">Working on this device — this can take a few seconds…</span>}
        </div>

        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <label className="muted" htmlFor="pipeline-mode">Mode:</label>
          <select
            id="pipeline-mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border)' }}
          >
            <option value="full">Speech → Hindi → Santali</option>
            <option value="asr">ASR test only (Hindi text)</option>
          </select>
          <span className="muted" style={{ fontSize: 13 }}>
            Short classroom sentences work best (up to 2 minutes).
          </span>
        </div>
      </div>

      {/* Audio-file fallback (also handy to re-test a saved recording) */}
      <div className="card" style={{ marginTop: 14 }}>
        <h2>Or use an audio file</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.wav,.webm,.mp3,.m4a,.ogg"
            onChange={onUploadSelected}
            aria-label="Choose an audio file"
          />
          <button
            type="button"
            className="btn btn-outline"
            onClick={onProcessUpload}
            disabled={!uploadFile || busy}
          >
            Process file
          </button>
        </div>
      </div>

      {/* Error / info banner */}
      {(error || recorder.error) && (
        <div className="error-banner" role="alert">
          <strong>Something needs your attention.</strong> {recorder.error || error}
        </div>
      )}

      {/* Results */}
      {replayUrl && (
        <section className="card" style={{ marginTop: 14 }} aria-label="Teacher speech">
          <h2>Teacher Speech</h2>
          <audio controls src={replayUrl} style={{ width: '100%' }} aria-label="Recording playback" />
        </section>
      )}

      {asrOnly && (
        <section className="card" style={{ marginTop: 14 }} aria-label="Hindi recognition result">
          <h2>Hindi Recognition</h2>
          <p
            className="hindi"
            style={{
              fontSize: 22, lineHeight: 1.8, whiteSpace: 'pre-wrap',
              background: 'var(--bg)', borderRadius: 8, padding: 14,
              border: '1px solid var(--border)',
            }}
          >
            {asrOnly.text || '— no speech detected —'}
          </p>
          <p className="status-detail" style={{ marginBottom: 0 }}>
            {asrOnly.latency_ms} ms for {asrOnly.duration_sec}s audio · {asrOnly.model} ·{' '}
            {asrOnly.offline ? 'local inference (offline)' : ''} · translation skipped (ASR test mode)
          </p>
        </section>
      )}

      {speech && (
        <>
          <section className="card" style={{ marginTop: 14 }} aria-label="Hindi recognition">
            <h2>Hindi Recognition</h2>
            <p
              className="hindi"
              style={{
                fontSize: 22, lineHeight: 1.8, whiteSpace: 'pre-wrap',
                background: 'var(--bg)', borderRadius: 8, padding: 14,
                border: '1px solid var(--border)', marginBottom: 8,
              }}
            >
              {speech.recognized_hindi || '— no speech detected —'}
            </p>
            <p className="status-detail" style={{ marginBottom: 0 }}>
              ASR {speech.asr_latency_ms} ms · {speech.asr_model}
            </p>
          </section>

          {speech.success && (
            <section className="card" style={{ marginTop: 14 }} aria-label="Santali translation">
              <h2>Santali Translation</h2>
              <p
                className="ol-chiki"
                style={{
                  fontSize: 20, lineHeight: 1.8, whiteSpace: 'pre-wrap',
                  background: 'var(--green-soft)', borderRadius: 8, padding: 14,
                  border: '1px solid var(--border)', marginBottom: 10,
                }}
              >
                {speech.santali_ol_chiki}
              </p>
              <p>
                <span className="badge" style={{ marginBottom: 0 }}>{VALIDATION_NOTICE}</span>
              </p>
              <p className="status-detail" style={{ marginBottom: 0 }}>
                Translation {speech.translation_latency_ms} ms · {speech.translation_model} ·
                {' '}total {speech.total_latency_ms} ms · {speech.offline ? 'local inference (offline)' : ''}
              </p>
            </section>
          )}

          {speech.success && speech.audio_available && speech.audio_url && (
            <section className="card" style={{ marginTop: 14 }} aria-label="Student audio">
              <h2>Student Audio</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    const el = studentAudioRef.current
                    if (!el) return
                    if (el.paused) {
                      el.play().catch(() => setError('Could not play the Santali audio. Try again.'))
                    } else {
                      el.pause()
                    }
                  }}
                >
                  {playing ? '⏸ Pause Santali Audio' : '▶ Play Santali Audio'}
                </button>
                <audio
                  ref={studentAudioRef}
                  controls
                  preload="none"
                  src={speech.audio_url}
                  onPlay={() => setPlaying(true)}
                  onPause={() => setPlaying(false)}
                  onEnded={() => setPlaying(false)}
                  onError={() => setError('The Santali audio file could not be loaded. Please record again.')}
                  style={{ width: '100%', maxWidth: 420 }}
                  aria-label="Generated Santali speech playback"
                />
              </div>
              <p className="status-detail" style={{ marginTop: 10, marginBottom: 0 }}>
                Generated locally by the offline Santali voice ({speech.tts_model}) in{' '}
                {speech.tts_latency_ms} ms · 16 kHz WAV
              </p>
              <p style={{ marginBottom: 0 }}>
                <span className="badge" style={{ marginBottom: 0 }}>{VALIDATION_NOTICE}</span>
              </p>
            </section>
          )}

          {speech.success && !speech.audio_available && speech.tts_message && (
            <section className="card" style={{ marginTop: 14 }} aria-label="Student audio unavailable">
              <h2>Student Audio</h2>
              <p style={{ marginBottom: 6 }}>
                Santali audio was not generated for this sentence:
              </p>
              <p className="status-detail" style={{ marginBottom: 0 }}>
                {speech.tts_message}
              </p>
            </section>
          )}
        </>
      )}
    </div>
  )
}
