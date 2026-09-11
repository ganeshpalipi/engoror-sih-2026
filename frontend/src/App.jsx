import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import LiveTranslation from './pages/LiveTranslation.jsx'
import TextTranslation from './pages/TextTranslation.jsx'
import Lessons from './pages/Lessons.jsx'
import Phrases from './pages/Phrases.jsx'
import Worksheets from './pages/Worksheets.jsx'
import Flashcards from './pages/Flashcards.jsx'
import History from './pages/History.jsx'
import OfflineContent from './pages/OfflineContent.jsx'
import Sync from './pages/Sync.jsx'
import Settings from './pages/Settings.jsx'
import ModelStatus from './pages/ModelStatus.jsx'

// All 12 teacher-facing pages from the SIH design. Phase 1 ships the
// navigation skeleton; pages become functional phase by phase.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="/live-translation" element={<LiveTranslation />} />
        <Route path="/text-translation" element={<TextTranslation />} />
        <Route path="/lessons" element={<Lessons />} />
        <Route path="/phrases" element={<Phrases />} />
        <Route path="/worksheets" element={<Worksheets />} />
        <Route path="/flashcards" element={<Flashcards />} />
        <Route path="/history" element={<History />} />
        <Route path="/offline-content" element={<OfflineContent />} />
        <Route path="/sync" element={<Sync />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/model-status" element={<ModelStatus />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  )
}
