import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function OfflineContent() {
  return (
    <PagePlaceholder
      title="Offline Content"
      hindiTitle="ऑफ़लाइन सामग्री"
      phase="Phase 11"
      description="Shows what is available on the device without internet: downloaded models, lessons, phrase audio and storage usage."
      bullets={[
        'Model download status and size on disk',
        'Content packs installed (lessons, phrases, flashcards)',
        'Everything works after one-time download — no cloud dependency',
      ]}
    />
  )
}
