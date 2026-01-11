import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import '../../styles/main.Css'; 

const Header = () => {
  // 2. On récupère les infos du contexte
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/'); // Redirection vers l'accueil après déconnexion
  };

  // --- STYLES ---
  const headerStyle = {
    background: 'var(--white)',
    boxShadow: 'var(--shadow)',
    padding: '1rem 0',
    position: 'sticky',
    top: 0,
    zIndex: 100
  };

  const navStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const logoStyle = {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    color: 'var(--primary)',
    letterSpacing: '-1px',
    textDecoration: 'none'
  };

  const linkContainerStyle = {
    display: 'flex',
    gap: '20px',
    alignItems: 'center'
  };

  const authContainerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '15px'
  };

  return (
    <header style={headerStyle}>
      <div className="container">
        <nav style={navStyle}>
          {/* Logo */}
          <Link to="/" style={logoStyle}>
            PureSkin 🌿
          </Link>

          {/* Liens de navigation principaux */}
          <div style={linkContainerStyle}>
            <Link to="/" className="nav-link">Accueil</Link>
            <Link to="/scanner" className="nav-link">Scanner</Link>
            <Link to="/dupes" className="nav-link">Trouver un Dupe</Link>
          </div>

          {/* 3. Section Authentification Dynamique */}
          <div style={authContainerStyle}>
            {isAuthenticated ? (
              <>
                {/* SI CONNECTÉ */}
                <span style={{ fontSize: '0.9rem', fontWeight: '500' }}>
                  Bonjour, {user?.name} 👋
                </span>
                
                {/* Lien vers les favoris (qu'on a créé tout à l'heure) */}
                <Link to="/favorites" style={{ fontSize: '0.9rem' }}>
                  ❤️ Mes Favoris
                </Link>

                <button 
                  onClick={handleLogout} 
                  className="btn btn-outline"
                  style={{ fontSize: '0.8rem', padding: '5px 10px' }}
                >
                  Déconnexion
                </button>
              </>
            ) : (
              <>
                {/* SI DÉCONNECTÉ */}
                <Link to="/login" style={{ marginRight: '10px', fontWeight: '500' }}>
                  Se connecter
                </Link>
                <Link to="/register" className="btn btn-primary" style={{ padding: '8px 16px' }}>
                  S'inscrire
                </Link>
              </>
            )}
          </div>

        </nav>
      </div>
    </header>
  );
};

export default Header;