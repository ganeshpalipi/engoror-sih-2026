// Single HTTP layer for Engoror.
//
// Localhost:
//   Uses the local FastAPI backend.
//
// Public Vercel deployment without VITE_API_BASE_URL:
//   Runs in showcase mode. No AI result is faked.

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const HOSTNAME =
  typeof window !== 'undefined' ? window.location.hostname : ''

const IS_LOCAL_HOST =
  HOSTNAME === 'localhost' || HOSTNAME === '127.0.0.1'

export const IS_SHOWCASE_MODE =
  !BASE_URL && !IS_LOCAL_HOST

class ShowcaseModeError extends Error {
  constructor() {
    super(
      'This is the Engoror online showcase. AI inference runs locally on the classroom device. Start the local offline system to use this feature.',
    )
    this.name = 'ShowcaseModeError'
    this.code = 'SHOWCASE_MODE'
  }
}

function showcaseGetResponse(path) {
  switch (path) {
    case '/api/fln/lessons':
      return { lessons: [] }

    case '/api/phrases':
      return {
        phrases: [],
        categories: [],
      }

    case '/api/worksheets/meta':
      return {
        topics: [],
        type_legend: {},
      }

    case '/api/flashcards':
      return {
        flashcards: [],
        topics: [],
      }

    case '/api/models/status':
      return {
        offline: true,
        translation: {
          status: 'showcase',
          device: 'local classroom device',
          detail: 'Local inference demo required',
        },
        asr: {
          status: 'showcase',
        },
        tts: {
          status: 'showcase',
        },
      }

    default:
      return undefined
  }
}

async function handleResponse(res) {
  const contentType =
    res.headers.get('content-type') || ''

  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`

    if (contentType.includes('application/json')) {
      try {
        const data = await res.json()

        if (data?.detail) {
          detail =
            typeof data.detail === 'string'
              ? data.detail
              : JSON.stringify(data.detail)
        }
      } catch {
        // Keep the generic error.
      }
    }

    throw new Error(detail)
  }

  if (!contentType.includes('application/json')) {
    throw new Error(
      'The Engoror backend returned a non-JSON response. Check that the FastAPI backend is running.',
    )
  }

  return res.json()
}

function friendlyNetworkError(err) {
  if (err?.code === 'SHOWCASE_MODE') {
    return err
  }

  if (err instanceof TypeError) {
    return new Error(
      'Cannot reach the Engoror backend. Start it with: python -m uvicorn app.main:app --reload',
    )
  }

  return err
}

export async function getHealth() {
  if (IS_SHOWCASE_MODE) {
    return {
      status: 'showcase',
      app: 'Engoror',
      version: 'online-showcase',
      offline_mode: true,
      components: {},
    }
  }

  try {
    const res = await fetch(`${BASE_URL}/health`)
    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}

export async function apiGet(path) {
  if (IS_SHOWCASE_MODE) {
    const fallback = showcaseGetResponse(path)

    if (fallback !== undefined) {
      return fallback
    }

    throw new ShowcaseModeError()
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`)
    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}

export async function apiPost(path, body) {
  if (IS_SHOWCASE_MODE) {
    throw new ShowcaseModeError()
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}

export async function getTranslationModelStatus() {
  return apiGet('/api/models/status')
}

export async function apiPostAudio(
  path,
  blob,
  filename,
  language = 'hi',
) {
  if (IS_SHOWCASE_MODE) {
    throw new ShowcaseModeError()
  }

  try {
    const form = new FormData()

    form.append('file', blob, filename)
    form.append('language', language)

    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      body: form,
    })

    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}