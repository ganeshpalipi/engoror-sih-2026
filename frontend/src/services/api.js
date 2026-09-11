// Single HTTP layer for the whole frontend.
// Every request goes through here so error handling stays consistent and
// human-friendly (SIH rule #17).

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`
    try {
      const data = await res.json()
      if (data && data.detail) {
        detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      }
    } catch {
      // response had no JSON body - keep the generic message
    }
    throw new Error(detail)
  }
  return res.json()
}

function friendlyNetworkError(err) {
  if (err instanceof TypeError) {
    return new Error(
      'Cannot reach the RootVerse backend. Start it with: uvicorn app.main:app --reload',
    )
  }
  return err
}

// GET /health -> { status, app, version, offline_mode, components }
export async function getHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`)
    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}

// Generic GET for future API endpoints: apiGet('/api/phrases')
export async function apiGet(path) {
  try {
    const res = await fetch(`${BASE_URL}${path}`)
    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}

// Generic POST with a JSON body: apiPost('/api/translate/text', {...})
export async function apiPost(path, body) {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return await handleResponse(res)
  } catch (err) {
    throw friendlyNetworkError(err)
  }
}

// GET /api/models/status -> { offline, translation: { model, direction, status, device, detail } }
export async function getTranslationModelStatus() {
  return apiGet('/api/models/status')
}
