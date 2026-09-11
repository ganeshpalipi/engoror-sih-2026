// Shared placeholder for pages whose functionality arrives in later phases.
// Keeps Phase 1 honest: navigation works, features are clearly marked.

export default function PagePlaceholder({ title, hindiTitle, phase, description, bullets = [] }) {
  return (
    <section className="page-placeholder" aria-label={title}>
      <p className="badge">Coming in {phase}</p>
      <h1>{title}</h1>
      {hindiTitle && <p className="hindi subtitle">{hindiTitle}</p>}
      <p className="muted">{description}</p>

      {bullets.length > 0 && (
        <ul className="feature-list">
          {bullets.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}

      <div className="card notice" style={{ marginTop: 16 }}>
        <strong>Phase 1 note:</strong> this page is part of the navigation skeleton.
        Its functionality is delivered in {phase} of the build plan — see
        docs/PROJECT_PLAN.md.
      </div>
    </section>
  )
}
