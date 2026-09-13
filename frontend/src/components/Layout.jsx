import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Home', end: true },
  { to: '/live-translation', label: 'Live Translation' },
  { to: '/text-translation', label: 'Text Translation' },
  { to: '/lessons', label: 'FLN Lessons' },
  { to: '/phrases', label: 'Phrase Pack' },
  { to: '/worksheets', label: 'Worksheets' },
  { to: '/flashcards', label: 'Flashcards' },
  { to: '/history', label: 'History' },
  { to: '/offline-content', label: 'Offline Content' },
  { to: '/sync', label: 'Sync' },
  { to: '/settings', label: 'Settings' },
  { to: '/model-status', label: 'Model Status' },
]

// App shell: dark navy sidebar (drawer on mobile) + main column with a
// sticky footer. Large text and targets, calm classroom palette.
export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-shell">
      {menuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar${menuOpen ? ' open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-brand">
          <span className="brand-mark" aria-hidden="true">R</span>
          <div>
            <p className="brand-name">RootVerse</p>
            <p className="brand-tag">Hindi ⇄ Santhali bridge</p>
          </div>
        </div>

        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <p className="sidebar-foot">
          Offline-first · SIH 2026
          <br />
          Phase 5: FLN classroom content live
        </p>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <button
            type="button"
            className="hamburger"
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
          <span className="topbar-title">RootVerse</span>
          <span className="topbar-badge">SIH 2026</span>
        </header>

        <main className="page">
          <Outlet />
        </main>

        <footer className="footer">
          <span>RootVerse — AI-powered vernacular pedagogy for primary education</span>
          <span>Hindi → Santhali (Ol Chiki) · Offline-first</span>
        </footer>
      </div>
    </div>
  )
}
