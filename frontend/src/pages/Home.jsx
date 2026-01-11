import React from 'react';
import { Link } from 'react-router-dom';

const Home = () => {
  return (
    <div className="container" style={{ padding: '4rem 0', textAlign: 'center' }}>
      
      {/* Hero Section */}
      <section style={{ marginBottom: '4rem' }}>
        <h1 style={{ fontSize: '3.5rem', marginBottom: '1rem', color: 'var(--secondary)' }}>
          Décryptez vos cosmétiques.
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#666', marginBottom: '2rem', maxWidth: '600px', margin: '0 auto 2rem auto' }}>
          Utilisez l'intelligence artificielle pour analyser les ingrédients, trouver des dupes moins chers et construire votre routine idéale.
        </p>
        
        <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
          <Link to="/dupes" className="btn btn-primary">
            🔍 Trouver un Dupe
          </Link>
          <Link to="/scanner" className="btn" style={{ background: 'var(--secondary)', color: 'white' }}>
            📸 Scanner un produit
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <div className="card">
          <h3>🔬 Analyse Scientifique</h3>
          <p>Notre IA analyse chaque ingrédient pour détecter les allergènes et les bénéfices réels.</p>
        </div>
        <div className="card">
          <h3>💰 Économisez</h3>
          <p>Trouvez des produits avec la même composition mais 50% moins chers.</p>
        </div>
        <div className="card">
          <h3>✨ Routine Personnalisée</h3>
          <p>Obtenez une routine matin et soir adaptée à votre type de peau spécifique.</p>
        </div>
      </div>

    </div>
  );
};

export default Home;