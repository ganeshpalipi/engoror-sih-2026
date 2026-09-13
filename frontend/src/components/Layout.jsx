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

      <aside
        className={`sidebar engoror-sidebar${
          menuOpen ? ' open' : ''
        }`}
      >
        <div className="sidebar-brand">
          <span className="brand-mark engoror-mark">
            E
          </span>

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
        </nav>

        <div className="sidebar-foot engoror-sidebar-foot">
          <strong>● Offline-first</strong>
          <span>Hindi → Santali</span>
          <span>SIH 2026 Prototype</span>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar engoror-topbar">
          <button
            type="button"
            className="hamburger"
            onClick={() =>
              setMenuOpen((value) => !value)
            }
            aria-expanded={menuOpen}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>

          <div className="topbar-mobile-brand">
            <span className="brand-mark small">
              E
            </span>

            <span className="topbar-title">
              Engoror
            </span>
          </div>

          <span className="offline-pill">
            ● Offline-first
          </span>
        </header>

        <main className="page engoror-page">
          <Outlet />
        </main>

        <footer className="footer engoror-footer">
          <span>
            <strong>Engoror</strong> — Language should
            never be a barrier to learning.
          </span>

          <span>
            Hindi → Santali · SIH 2026 Prototype
          </span>
        </footer>
      </div>
    </div>
  )
}