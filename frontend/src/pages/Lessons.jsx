import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function Lessons() {
  return (
    <PagePlaceholder
      title="FLN Lessons"
      hindiTitle="बुनियादी साक्षरता पाठ"
      phase="Phase 9"
      description="Foundational literacy and numeracy lessons — numbers, alphabet, shapes, colors, basic arithmetic — bilingual in Hindi and Santhali, with audio."
      bullets={[
        'Lesson cards with class level, subject and learning objective',
        'Activity instructions in Hindi + Santhali field',
        'Audio playback per lesson',
        'Designed to align with NIPUN Bharat FLN learning goals (no official certification claimed)',
      ]}
    />
  )
}
