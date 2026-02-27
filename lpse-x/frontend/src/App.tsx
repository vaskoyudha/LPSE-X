import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { TenderDetail } from './pages/TenderDetail'
import { CartelGraph } from './pages/CartelGraph'
import { RiskMap } from './pages/RiskMap'
import { Reports } from './pages/Reports'
import { ConfigPanel } from './pages/ConfigPanel'

function App(): React.ReactElement {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="tender/:id" element={<TenderDetail />} />
          <Route path="cartel" element={<CartelGraph />} />
          <Route path="map" element={<RiskMap />} />
          <Route path="reports" element={<Reports />} />
          <Route path="config" element={<ConfigPanel />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
