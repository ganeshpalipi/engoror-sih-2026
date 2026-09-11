import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function Flashcards() {
  return (
    <PagePlaceholder
      title="Flashcards"
      hindiTitle="फ्लैशकार्ड"
      phase="Phase 10"
      description="Picture cards for vocabulary practice — image, Hindi word, Santhali word and audio, grouped by topic."
      bullets={[
        'Topics: fruits, animals, numbers, shapes, village objects, farming, forest, school objects',
        'Tap card to hear the Santhali word',
        'Ol Chiki script display with self-hosted fonts',
      ]}
    />
  )
}
