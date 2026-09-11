import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function ModelStatus() {
  return (
    <PagePlaceholder
      title="Model Status"
      hindiTitle="मॉडल स्थिति"
      phase="Phase 4+"
      description="Honest, real-time view of the AI layer: which models are loaded, cached, or missing, plus device info."
      bullets={[
        'ASR / MT / TTS model load status (never fake "ready" states)',
        'Device info: CPU / CUDA, RAM usage where measurable',
        'Lazy-loading state and cache location (backend/model_cache/)',
      ]}
    />
  )
}
