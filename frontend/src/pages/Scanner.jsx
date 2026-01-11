import React from 'react';
import ProductScanner from '../components/product/ProductScanner';

const Scanner = () => {
  return (
    <div className="container" style={{ padding: '40px 0' }}>
      {/* On appelle notre composant ici */}
      <ProductScanner />
      
      {/* Petite section d'aide en dessous */}
      <div style={{ marginTop: '40px', textAlign: 'center', color: '#888', fontSize: '0.9rem' }}>
        <p>💡 Astuce : Assurez-vous que la liste d'ingrédients est bien éclairée et lisible.</p>
        <p>Formats supportés : JPG, PNG.</p>
      </div>
    </div>
  );
};

export default Scanner;