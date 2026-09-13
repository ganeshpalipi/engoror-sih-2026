import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const MAIN_NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/live-translation', label: 'Live Classroom' },
  { to: '/text-translation', label: 'Text Translation' },
  { to: '/lessons', label: 'Learning Hub' },
  { to: '/phrases', label: 'Phrase Pack' },
  { to: '/worksheets', label: 'Worksheets' },
  { to: '/flashcards', label: 'Flashcards' },
]

const RESOURCE_NAV = [
  { to: '/history', label: 'History' },
  { to: '/offline-content', label: 'Offline Library' },
  { to: '/model-status', label: 'Model Status' },
]

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-shell engoror-shell">
      {menuOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar engoror-sidebar${menuOpen ? ' open' : ''}`}>
        <div className="sidebar-brand">
          <span className="brand-mark engoror-mark">E</span>
          <div>
            <p className="brand-name">Engoror</p>
            <p className="brand-tag">Classroom AI</p>
          </div>
        </div>

        <nav className="engoror-nav">
          {MAIN_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `nav-link${isActive ? ' active' : ''}`
              }
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}

          <p className="nav-section-label">RESOURCES</p>

          {RESOURCE_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link${isActive ? ' active' : ''}`
              }
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot engoror-sidebar-foot">
          <strong>● Offline Ready</strong>
          <span>Hindi → Santali</span>
          <span>SIH 2026 Prototype</span>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar engoror-topbar">
          <button
            type="button"
            className="hamburger"
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>

          <div className="topbar-mobile-brand">
            <span className="brand-mark small">E</span>
            <span className="topbar-title">Engoror</span>
          </div>

          <span className="offline-pill">● Offline AI Ready</span>
        </header>

        <main className="page engoror-page">
          <Outlet />
        </main>

        <footer className="footer engoror-footer">
          <span>
            <strong>Engoror</strong> — Language should never be a barrier to learning.
          </span>
          <span>Hindi → Santali · SIH 2026 Prototype</span>
        </footer>
      </div>
    </div>
  )
}