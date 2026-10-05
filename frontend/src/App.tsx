import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';
import { ScansPage } from './pages/ScansPage';
import { ScanDetailPage } from './pages/ScanDetailPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Header />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/scans" element={<ScansPage />} />
            <Route path="/scans/:scanId" element={<ScanDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
