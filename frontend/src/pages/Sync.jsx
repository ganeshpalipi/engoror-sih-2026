import PagePlaceholder from '../components/PagePlaceholder.jsx'

export default function Sync() {
  return (
    <PagePlaceholder
      title="Sync (BRC)"
      hindiTitle="सिंक — ब्लॉक संसाधन केंद्र"
      phase="Phase 11"
      description="At a Block Resource Centre (or any connected spot), the device imports fresh content via a ZIP file or folder — no runtime cloud dependency."
      bullets={[
        'ZIP import / export (MVP)',
        'Folder-based sync via USB drive or SD card',
        'Bluetooth-ready architecture for later phases',
        'Imports: updated lessons, phrases, language packs, models',
      ]}
    />
  )
}
