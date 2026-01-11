import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  findDupes, 
  getDynamicFilters, 
  getFavorites, 
  addFavorite, 
  removeFavorite 
} from '../../services/aiService'; 
// import api from '../../services/axiosClient'; // Décommente si tu as une API user
import styled from 'styled-components';
import toast, { Toaster } from 'react-hot-toast';
import { 
  Heart, Filter, Search, Clock, RefreshCw, ChevronRight, Trophy 
} from 'lucide-react';

// --- STYLED COMPONENTS ---
const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
  background-color: #f9fafb;
  min-height: 100vh;
`;

const Header = styled.div`
  text-align: center;
  margin-bottom: 3rem;
`;

const Title = styled.h1`
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #4f46e5 0%, #818cf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.5rem;
`;

const FormSection = styled.div`
  background: white;
  border-radius: 1.25rem;
  padding: 2rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 1.25rem;
  border: 2px solid #e5e7eb;
  border-radius: 1rem;
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
  min-height: 160px;
  transition: all 0.2s;
  &:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
  }
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  @media (min-width: 1024px) {
    grid-template-columns: 380px 1fr;
  }
`;

const ProductCard = styled.div`
  background: white;
  border-radius: 1rem;
  padding: 1.5rem;
  border: ${props => props.isBestMatch ? '2px solid #10b981' : '1px solid #e5e7eb'};
  position: relative;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.1);
  }
`;

const Badge = styled.span`
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 2rem;
  font-weight: 600;
  background: ${props => props.color || '#f3f4f6'};
  color: ${props => props.textColor || '#374151'};
`;

const BestMatchBadge = styled.div`
  position: absolute;
  top: -12px;
  right: 20px;
  background: #10b981;
  color: white;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.4);
`;

// --- COMPOSANT PRINCIPAL ---
const DupeFinder = () => {
  const location = useLocation();

  // State du formulaire
  const [formData, setFormData] = useState({
    ingredients: '',
    brand: '',
    primary_category: 'All',
    secondary_category: '', // Correspond à 'type' (ex: Serum)
    maxPrice: ''
  });

  // State pour les filtres dynamiques
  const [filterOptions, setFilterOptions] = useState({
    categories: [], 
    types: [],      
    brands: []      
  });

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [favorites, setFavorites] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [history, setHistory] = useState([]);

  // 1. Initialisation (Chargement Historique, Filtres ET Favoris)
  useEffect(() => {
    const initData = async () => {
        // A. Historique Local
        const savedHistory = localStorage.getItem('pureSkin_history');
        if (savedHistory) setHistory(JSON.parse(savedHistory));

        // B. Filtres Dynamiques
        try {
            const filterData = await getDynamicFilters();
            setFilterOptions({
                categories: filterData.categories || [],
                types: filterData.types || [],
                brands: filterData.brands || []
            });
        } catch (e) { 
            console.warn("Erreur chargement filtres", e); 
        }

        // C. Chargement des Favoris (IMPORTANT pour voir les cœurs rouges au chargement)
        try {
            const userFavorites = await getFavorites();
            setFavorites(userFavorites || []);
        } catch (e) {
            console.warn("Erreur chargement favoris", e);
        }
    };

    initData();

    // D. Si on vient de la page Scan
    if (location.state?.scannedIngredients) {
      const data = {
        ingredients: location.state.scannedIngredients,
        brand: location.state.scannedBrand || '',
        primary_category: location.state.scannedCategory || 'Skincare',
        secondary_category: '',
        maxPrice: ''
      };
      setFormData(data);
      performSearch(data);
    }
  }, [location]);

  // 2. Logique de Recherche
  const performSearch = async (data = formData) => {
    if (!data.ingredients) {
        toast.error("Veuillez entrer des ingrédients");
        return;
    }
    
    setLoading(true);
    const toastId = toast.loading("Analyse de la formulation...");

    try {
      const priceToSearch = data.maxPrice ? parseFloat(data.maxPrice) : 0;

      const response = await findDupes(
        data.ingredients,
        data.secondary_category || null, 
        priceToSearch,                   
        data.primary_category            
      );

      let items = [];
      
      const normalizeProduct = (p) => ({
        ...p,
        price: p.price_usd || p.price || 0,
        similarity: p.similarity_score || p.similarity || 0,
        brand_name: p.brand_name || p.brand || "Unknown Brand",
        product_name: p.product_name || "Unknown Product"
      });

      if (response.best_dupe) {
        items.push({ 
            ...normalizeProduct(response.best_dupe), 
            is_best_match: true 
        });
      }

      if (response.alternatives && Array.isArray(response.alternatives)) {
        const alts = response.alternatives.map(p => normalizeProduct(p));
        items = [...items, ...alts];
      }

      if (items.length === 0 && Array.isArray(response)) {
         items = response.map(p => normalizeProduct(p));
      }

      // Mapping avec les favoris actuels
      const mappedResults = items.map(p => ({
        ...p,
        isFavorite: favorites.some(f => f.product_name === p.product_name)
      }));

      setResults(mappedResults);

      if (items.length === 0) {
        toast.error("Aucun dupe trouvé.", { id: toastId });
      } else {
        toast.success(`${items.length} produits trouvés !`, { id: toastId });
        saveToHistory(data);
      }

    } catch (error) {
      console.error(error);
      toast.error(error.message || "Erreur lors de la recherche", { id: toastId });
    } finally {
      setLoading(false);
    }
  };

  const saveToHistory = (data) => {
    const newEntry = { ...data, id: Date.now() };
    const filteredHistory = history.filter(h => h.ingredients !== data.ingredients);
    const updated = [newEntry, ...filteredHistory].slice(0, 5);
    setHistory(updated);
    localStorage.setItem('pureSkin_history', JSON.stringify(updated));
  };

  // 3. Gestion Réelle des Favoris
  const handleToggleFavorite = async (product) => {
      // Vérifie si déjà favori
      const isAlreadyFav = favorites.some(f => f.product_name === product.product_name);
      
      // Sauvegarde état précédent pour rollback en cas d'erreur
      const previousFavorites = [...favorites];
      
      // MISE À JOUR OPTIMISTE (Interface instantanée)
      if (isAlreadyFav) {
          setFavorites(prev => prev.filter(f => f.product_name !== product.product_name));
      } else {
          setFavorites(prev => [...prev, product]);
      }

      // Mise à jour visuelle des cartes produits
      setResults(prevResults => prevResults.map(p => 
          p.product_name === product.product_name 
            ? { ...p, isFavorite: !isAlreadyFav } 
            : p
      ));

      try {
          // APPEL API
          if (isAlreadyFav) {
              await removeFavorite(product.product_name);
              toast.success("Retiré des favoris");
          } else {
              await addFavorite(product);
              toast.success("Ajouté aux favoris");
          }
      } catch (error) {
          console.error("Erreur favoris API:", error);
          // ROLLBACK EN CAS D'ERREUR
          setFavorites(previousFavorites);
          setResults(prevResults => prevResults.map(p => 
              p.product_name === product.product_name 
                ? { ...p, isFavorite: isAlreadyFav } // Remet l'état d'origine
                : p
          ));
          toast.error("Impossible de mettre à jour les favoris");
      }
  };

  return (
    <Container>
      <Toaster position="top-center" />
      <Header>
        <Title>Dupe Finder AI</Title>
        <p style={{ color: '#6b7280' }}>Trouvez des alternatives clean & budget basées sur la science des ingrédients.</p>
      </Header>

      <Grid>
        {/* COLONNE GAUCHE : FORMULAIRE */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <FormSection>
            <form onSubmit={(e) => { e.preventDefault(); performSearch(); }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <label style={{ fontWeight: 700, fontSize: '0.9rem' }}>Liste INCI</label>
                <button type="button" onClick={() => setShowFilters(!showFilters)} style={{ background: 'none', border: 'none', color: '#4f46e5', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, display:'flex', alignItems:'center', gap:'4px' }}>
                  <Filter size={14} /> {showFilters ? 'Moins de filtres' : 'Plus de filtres'}
                </button>
              </div>

              <TextArea 
                placeholder="Collez les ingrédients ici..."
                value={formData.ingredients}
                onChange={(e) => setFormData({ ...formData, ingredients: e.target.value })}
              />

              {showFilters && (
                <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  
                  {/* SELECT CATÉGORIE DYNAMIQUE */}
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '-0.5rem' }}>Catégorie</label>
                  <select 
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #d1d5db' }}
                    value={formData.primary_category}
                    onChange={(e) => setFormData({ ...formData, primary_category: e.target.value })}
                  >
                    <option value="All">Toutes Catégories</option>
                    {filterOptions.categories.map((cat, i) => (
                        <option key={i} value={cat}>{cat}</option>
                    ))}
                  </select>

                  <div style={{ display:'flex', gap:'1rem' }}>
                    {/* SELECT TYPE DYNAMIQUE */}
                    <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Type</label>
                        <select 
                            style={{ width:'100%', padding: '0.75rem', marginTop: '0.25rem', borderRadius: '0.5rem', border: '1px solid #d1d5db' }}
                            value={formData.secondary_category}
                            onChange={(e) => setFormData({ ...formData, secondary_category: e.target.value })}
                        >
                            <option value="">Tous Types</option>
                            {filterOptions.types.map((t, i) => (
                                <option key={i} value={t}>{t}</option>
                            ))}
                        </select>
                    </div>
                    
                    <div style={{ width: '80px' }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Max $</label>
                        <input 
                            type="number"
                            placeholder="$"
                            style={{ width:'100%', padding: '0.75rem', marginTop: '0.25rem', borderRadius: '0.5rem', border: '1px solid #d1d5db' }}
                            value={formData.maxPrice}
                            onChange={(e) => setFormData({ ...formData, maxPrice: e.target.value })}
                        />
                    </div>
                  </div>

                  {/* SELECT MARQUE DYNAMIQUE */}
                  <div>
                     <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Marque (Optionnel)</label>
                     <select 
                        style={{ width: '100%', padding: '0.75rem', marginTop: '0.25rem', borderRadius: '0.5rem', border: '1px solid #d1d5db' }}
                        value={formData.brand}
                        onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                      >
                         <option value="">Toutes Marques</option>
                         {filterOptions.brands.map((b, i) => (
                            <option key={i} value={b}>{b}</option>
                         ))}
                      </select>
                  </div>
                </div>
              )}

              <button 
                type="submit" 
                disabled={loading}
                style={{ width: '100%', marginTop: '1.5rem', padding: '1rem', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '0.75rem', fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', opacity: loading ? 0.7 : 1 }}
              >
                {loading ? <RefreshCw className="animate-spin" size={18} /> : <Search size={18} />}
                {loading ? 'Analyse...' : 'Trouver les alternatives'}
              </button>
            </form>
          </FormSection>

          {history.length > 0 && (
            <div style={{ padding: '0 0.5rem' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Clock size={16} /> Historique récent</h3>
              {history.map(item => (
                <div key={item.id} onClick={() => { setFormData(item); performSearch(item); }} style={{ padding: '0.75rem', background: 'white', borderRadius: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer', border: '1px solid #e5e7eb', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.2s' }}>
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '200px', color: '#4b5563' }}>
                    {item.ingredients.substring(0, 35)}...
                  </span>
                  <ChevronRight size={14} color="#9ca3af" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* COLONNE DROITE : RÉSULTATS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem', alignContent: 'start' }}>
          {results.length > 0 ? results.map((product, idx) => (
            <ProductCard key={idx} isBestMatch={product.is_best_match}>
              {product.is_best_match && (
                <BestMatchBadge>
                  <Trophy size={12} /> MEILLEUR DUPE
                </BestMatchBadge>
              )}
              
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <Badge color={product.is_best_match ? '#ecfdf5' : '#eef2ff'} textColor={product.is_best_match ? '#059669' : '#4f46e5'}>
                    {product.primary_category || 'Skincare'}
                  </Badge>
                  <span style={{ fontWeight: 800, color: '#10b981', fontSize: '1.1rem' }}>
                    {product.price > 0 ? `$${product.price}` : 'N/A'}
                  </span>
                </div>
                
                <h3 style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.25rem', lineHeight: '1.4' }}>
                  {product.product_name}
                </h3>
                <p style={{ color: '#6b7280', fontSize: '0.9rem', marginBottom: '1rem', fontStyle: 'italic' }}>
                  {product.brand_name}
                </p>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  <div style={{ flex: 1, height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${product.similarity * 100}%`, height: '100%', background: product.is_best_match ? '#10b981' : '#4f46e5', borderRadius: '4px' }} />
                  </div>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: product.is_best_match ? '#10b981' : '#4f46e5' }}>
                    {Math.round(product.similarity * 100)}% Match
                  </span>
                </div>
                
                {product.is_economic_dupe && product.savings_amount > 0 && (
                    <div style={{fontSize: '0.8rem', color: '#059669', background: '#ecfdf5', padding: '0.5rem', borderRadius: '0.5rem', marginBottom: '1rem'}}>
                        💰 Économie: ${product.savings_amount}
                    </div>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f3f4f6', paddingTop: '1rem' }}>
                <span style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'capitalize' }}>
                    {product.rating ? `⭐ ${product.rating}/5` : 'Pas d\'avis'}
                </span>
                <button 
                  onClick={() => handleToggleFavorite(product)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: product.isFavorite ? '#ef4444' : '#d1d5db', transition: 'transform 0.2s', padding: '4px' }}
                >
                  <Heart fill={product.isFavorite ? '#ef4444' : 'none'} size={22} />
                </button>
              </div>
            </ProductCard>
          )) : (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '4rem', color: '#9ca3af', background: 'white', borderRadius: '1rem', border: '2px dashed #e5e7eb' }}>
              <Search size={48} style={{ marginBottom: '1rem', opacity: 0.2 }} />
              <p style={{ fontSize: '1.1rem', fontWeight: 500 }}>Prêt à scanner</p>
              <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>Collez une liste d'ingrédients ou scannez un produit pour voir les dupes apparaître ici.</p>
            </div>
          )}
        </div>
      </Grid>
    </Container>
  );
};

export default DupeFinder;