import React from 'react';
import { Routes, Route } from 'react-router-dom';

// Import des composants
import Header from './components/common/Header';
import Home from './pages/Home';
import Scanner from './pages/Scanner';
import DupeFinder from './components/analysis/DupeFinder';
import Login from './pages/Login';
import Register from './pages/Register';
import ProtectedRoute from './components/ProtectedRoute';
import Favorites from './pages/FavoritesPage';
// Placeholder
const Routine = () => (
  <div className="container">
    <h2>Page Routine (À venir)</h2>
  </div>
);

function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header />

      <main style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dupes" element={<DupeFinder />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/routine" element={<Routine />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route 
  path="/favorites" 
  element={
    <ProtectedRoute>
      <Favorites />
    </ProtectedRoute>
  } 
/>        </Routes>
      </main>

      <footer style={{ textAlign: 'center', padding: '20px', background: '#eee' }}>
        <p>© 2024 PureSkin AI - MERN Stack Project</p>
      </footer>
    </div>
  );
}

export default App;
