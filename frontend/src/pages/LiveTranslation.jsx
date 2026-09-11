import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function LiveTranslation() {
  return (
    <PagePlaceholder
      title="Live Translation"
      hindiTitle="लाइव अनुवाद"
      phase="Phases 5–8"
      description="Teacher speaks Hindi → offline ASR → Hindi-to-Santhali translation → Ol Chiki text on screen → Santhali audio for students."
      bullets={[
        'Microphone / Record / Stop controls (large, teacher-friendly buttons)',
        'Recognized Hindi text and Santhali text in Ol Chiki script',
        'Play Santhali audio button',
        'Latency panel: ASR / MT / TTS / total — target ≤ 3 s, shown only after real measurement',
      ]}
    />
  )
}
