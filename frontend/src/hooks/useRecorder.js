// Microphone recorder for the classroom page (Phase 3).
import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * useRecorder — minimal MediaRecorder wrapper for Phase 3.
 *
 * start() begins recording from the default microphone.
 * stop()  returns { blob, seconds } and releases the microphone.
 *
 * Errors are converted into teacher-friendly messages (SIH rule #17):
 * permission denied, no microphone, mic busy, insecure context, etc.
 */

const MIME_CANDIDATES = [
  'audio/webm;codecs=opus', // Chrome / Edge on Windows (best quality/size)
  'audio/webm',
  'audio/mp4', // Safari / some mobile browsers
  '', // let the browser choose
]

function friendlyMicError(err) {
  const name = err?.name || ''
  if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') {
    return new Error(
      'Microphone access was denied. Click the lock icon in the browser address bar, allow the microphone for this site, then try again.',
    )
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return new Error('No microphone was found. Please connect a microphone and try again.')
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return new Error(
      'The microphone is busy (another app may be using it). Close other apps and try again.',
    )
  }
  if (name === 'OverconstrainedError') {
    return new Error('The microphone does not support the requested audio settings.')
  }
  return new Error(err?.message || 'Could not start recording. Please try again.')
}

export function useRecorder() {
  const [state, setState] = useState('idle') // idle | recording | error
  const [error, setError] = useState('')
  const [elapsedSec, setElapsedSec] = useState(0)

  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const timerRef = useRef(null)
  const startedAtRef = useRef(0)

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    recorderRef.current = null
    chunksRef.current = []
  }, [])

  useEffect(() => cleanup, [cleanup])

  const start = useCallback(async () => {
    setError('')
    if (typeof window === 'undefined' || !window.isSecureContext) {
      // Microphone needs a secure context: http://localhost counts, LAN http does not.
      const msg =
        'Microphone access requires a secure page. Open the app via http://localhost:5173 (or HTTPS).'
      setError(msg)
      setState('error')
      throw new Error(msg)
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      const msg = 'This browser does not support audio recording. Please use Chrome or Edge.'
      setError(msg)
      setState('error')
      throw new Error(msg)
    }

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      })
    } catch (err) {
      const friendly = friendlyMicError(err)
      setError(friendly.message)
      setState('error')
      throw friendly
    }

    streamRef.current = stream
    const mimeType = MIME_CANDIDATES.find((m) => !m || MediaRecorder.isTypeSupported(m)) || ''
    let recorder
    try {
      recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)
    } catch (err) {
      cleanup()
      const friendly = friendlyMicError(err)
      setError(friendly.message)
      setState('error')
      throw friendly
    }

    chunksRef.current = []
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.start(250) // gather chunks every 250 ms
    recorderRef.current = recorder
    startedAtRef.current = Date.now()
    setElapsedSec(0)
    timerRef.current = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAtRef.current) / 1000))
    }, 500)
    setState('recording')
    return mimeType
  }, [cleanup])

  /** Stops recording. Resolves { blob, seconds, mimeType } — rejects if never started. */
  const stop = useCallback(() => {
    return new Promise((resolve, reject) => {
      const recorder = recorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        cleanup()
        setState('idle')
        reject(new Error('Recording was not started.'))
        return
      }
      const seconds = Math.max(0.5, (Date.now() - startedAtRef.current) / 1000)
      recorder.onstop = () => {
        const type = recorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type })
        cleanup()
        setState('idle')
        resolve({ blob, seconds, mimeType: type })
      }
      recorder.stop()
    })
  }, [cleanup])

  const reset = useCallback(() => {
    cleanup()
    setError('')
    setElapsedSec(0)
    setState('idle')
  }, [cleanup])

  return { state, elapsedSec, error, start, stop, reset }
}
