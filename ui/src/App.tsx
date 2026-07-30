import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './lib/auth'
import Home from './pages/Home'
import Results from './pages/Results'
import MapScreen from './pages/MapScreen'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
        <Route path="/map" element={<MapScreen />} />
        {/* The saved-receipts screen is now the signed-in home. */}
        <Route path="/saved" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
