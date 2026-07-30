import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Results from './pages/Results'
import MapScreen from './pages/MapScreen'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/results" element={<Results />} />
      <Route path="/map" element={<MapScreen />} />
    </Routes>
  )
}

export default App
