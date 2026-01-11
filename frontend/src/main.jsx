import React, { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles/main.css';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
    <AuthProvider>
      <App />
    </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
