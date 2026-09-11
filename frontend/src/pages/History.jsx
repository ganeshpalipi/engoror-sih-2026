import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function History() {
  return (
    <PagePlaceholder
      title="Translation History"
      hindiTitle="अनुवाद इतिहास"
      phase="Phase 8"
      description="Every translation is stored locally: Hindi input, Santhali output, timestamp, latency, mode and success/failure — useful for the SIH demo and for debugging."
      bullets={[
        'Filter by date and success/failure',
        'Per-request latency columns (ASR / MT / TTS / total)',
        'All data stays in the local SQLite database',
      ]}
    />
  )
}
