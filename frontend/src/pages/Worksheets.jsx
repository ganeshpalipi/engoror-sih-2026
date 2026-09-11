import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function Worksheets() {
  return (
    <PagePlaceholder
      title="Worksheet Generator"
      hindiTitle="वर्कशीट जनरेटर"
      phase="Phase 10"
      description="Generate printable bilingual worksheets (PDF) from lessons — Hindi question, Santhali field, images where relevant, and answer space."
      bullets={[
        'Choose class, topic and question count',
        'PDF output saved to backend/generated_files/',
        'Works fully offline (Windows-compatible PDF library)',
      ]}
    />
  )
}
