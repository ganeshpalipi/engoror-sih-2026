import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function Settings() {
  return (
    <PagePlaceholder
      title="Settings"
      hindiTitle="सेटिंग्स"
      phase="Phase 8"
      description="Teacher-facing options, stored in the local database."
      bullets={[
        'Offline mode toggle (default: ON)',
        'TTS speaking speed and voice selection',
        'Model cache and generated-files locations',
        'Backend server address for the frontend',
      ]}
    />
  )
}
