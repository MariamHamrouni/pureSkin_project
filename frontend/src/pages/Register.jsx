import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const result = await register(name, email, password);
    if (result.success) {
      navigate('/');
    } else {
      setError(result.message);
    }
  };

  return (
    <div className="card" style={{ maxWidth: '400px', margin: '50px auto', padding: '30px' }}>
      <h2 style={{ textAlign: 'center', color: '#2c3e50' }}>📝 Inscription</h2>
      {error && <div style={{ color: 'red', textAlign: 'center' }}>{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label>Nom complet</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required style={{ width: '100%', padding: '8px' }} />
        </div>
        <div style={{ marginBottom: '15px' }}>
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ width: '100%', padding: '8px' }} />
        </div>
        <div style={{ marginBottom: '20px' }}>
          <label>Mot de passe</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required style={{ width: '100%', padding: '8px' }} />
        </div>
        <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>S'inscrire</button>
      </form>
      <p style={{ marginTop: '15px', textAlign: 'center' }}>
        Déjà un compte ? <Link to="/login">Se connecter</Link>
      </p>
    </div>
  );
};

export default Register;