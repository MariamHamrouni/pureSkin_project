import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  
  const { login } = useAuth(); // On récupère la fonction login du contexte
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const result = await login(email, password);
    
    if (result.success) {
      navigate('/'); // Redirection vers l'accueil après connexion
    } else {
      setError(result.message);
    }
  };

  return (
    <div className="card" style={{ maxWidth: '400px', margin: '50px auto', padding: '30px' }}>
      <h2 style={{ textAlign: 'center', color: '#2c3e50' }}>🔐 Connexion</h2>
      
      {error && <div style={{ color: 'red', marginBottom: '10px', textAlign: 'center' }}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label>Email</label>
          <input 
            type="email" 
            className="form-control" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)}
            required 
            style={{ width: '100%', padding: '8px' }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label>Mot de passe</label>
          <input 
            type="password" 
            className="form-control" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)}
            required 
            style={{ width: '100%', padding: '8px' }}
          />
        </div>

        <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
          Se connecter
        </button>
      </form>
      
      <p style={{ marginTop: '15px', textAlign: 'center' }}>
        Pas encore de compte ? <Link to="/register">S'inscrire</Link>
      </p>
    </div>
  );
};

export default Login;