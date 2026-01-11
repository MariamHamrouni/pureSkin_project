import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
// On importe les fonctions spécifiques du service AI au lieu d'axios direct
import { getFavorites, removeFavorite as removeFavoriteApi } from '../services/aiService';
import toast, { Toaster } from 'react-hot-toast';
import { Heart, Trash2, Filter, Search, ArrowLeft, Star, TrendingDown, ShoppingBag } from 'lucide-react';

const FavoritesPage = () => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Chargement initial
  useEffect(() => {
    loadFavorites();
  }, []);

  const loadFavorites = async () => {
    try {
      setLoading(true);
      // Appel via le service centralisé (plus propre)
      const data = await getFavorites();
      
      // Le backend Python renvoie une liste simple [ {product_name...}, ... ]
      if (Array.isArray(data)) {
          setFavorites(data);
      } else {
          setFavorites([]);
      }
    } catch (error) {
      console.error("Erreur favoris:", error);
      toast.error("Impossible de charger les favoris");
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveFavorite = async (productName) => {
    try {
      // 1. Mise à jour Optimiste (Interface immédiate)
      const previousFavorites = [...favorites];
      setFavorites(prev => prev.filter(fav => fav.product_name !== productName));

      // 2. Appel API Backend
      // Note: Notre backend Python attend le nom du produit, pas un ID numérique
      await removeFavoriteApi(productName);
      
      toast.success('Retiré des favoris');
    } catch (error) {
      console.error(error);
      toast.error('Erreur lors de la suppression');
      // Rollback si erreur serveur
      loadFavorites(); 
    }
  };

  // --- FILTRAGE & RECHERCHE ---
  const filteredFavorites = favorites.filter(fav => {
    // Normalisation des noms (le backend Python envoie product_name)
    const pName = fav.product_name || "Produit Inconnu";
    const bName = fav.brand_name || "Marque Inconnue";
    const price = fav.price || 0;
    const similarity = fav.similarity || 0;

    const matchesSearch = searchQuery === '' || 
      pName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      bName.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesFilter = filter === 'all' || 
      (filter === 'high_similarity' && similarity >= 0.8) ||
      (filter === 'low_price' && price <= 20);
    
    return matchesSearch && matchesFilter;
  });

  // --- CALCUL DES STATS ---
  const getSavingsStats = () => {
    if (!favorites.length) return { savings: 0, percentage: 0 };

    // Estimation: On suppose que le produit original coûtait 50% plus cher 
    // (ou tu peux stocker le prix original dans le backend plus tard)
    const totalOriginal = favorites.reduce((sum, fav) => sum + ((fav.price || 0) * 1.5), 0);
    const totalCurrent = favorites.reduce((sum, fav) => sum + (fav.price || 0), 0);
    const savings = totalOriginal - totalCurrent;
    const percentage = totalOriginal > 0 ? (savings / totalOriginal * 100).toFixed(1) : 0;
    
    return { savings, percentage };
  };

  const stats = getSavingsStats();

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Toaster position="top-right" />
      
      {/* En-tête */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Link to="/dupes" className="text-gray-600 hover:text-gray-800 transition-colors">
              <ArrowLeft size={24} />
            </Link>
            <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
              <Heart className="text-red-500 fill-red-500" /> Mes Produits Favoris
            </h1>
          </div>
          <div className="text-sm font-medium text-blue-600 bg-blue-50 px-4 py-2 rounded-full border border-blue-100">
            {favorites.length} produit{favorites.length > 1 ? 's' : ''}
          </div>
        </div>
        
        <p className="text-gray-600 ml-1">
          Retrouvez ici toutes vos alternatives économiques sauvegardées.
        </p>
      </div>

      {/* Statistiques d'économies */}
      {favorites.length > 0 && (
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-2xl shadow-lg text-white p-6 mb-8 transform hover:scale-[1.01] transition-transform">
            <div className="flex items-center justify-between">
            <div>
                <h2 className="text-emerald-100 font-medium mb-1 uppercase tracking-wider text-xs">Économies Estimées</h2>
                <div className="text-4xl font-bold mb-2">
                ${stats.savings.toFixed(2)}
                </div>
                <div className="inline-block bg-white/20 px-3 py-1 rounded-full text-sm font-medium backdrop-blur-sm">
                📉 -{stats.percentage}% sur votre budget
                </div>
            </div>
            <div className="bg-white/10 p-4 rounded-full">
                <TrendingDown size={40} className="text-white" />
            </div>
            </div>
        </div>
      )}

      {/* Barre d'outils (Recherche & Filtres) */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Rechercher un produit ou une marque..."
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              />
            </div>
          </div>
          
          <div className="flex gap-2">
            <div className="relative">
                <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="pl-10 pr-8 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white appearance-none cursor-pointer"
                >
                <option value="all">Tous les favoris</option>
                <option value="high_similarity">Top Match (+80%)</option>
                <option value="low_price">Petit Prix (-$20)</option>
                </select>
            </div>
          </div>
        </div>
      </div>

      {/* Liste des résultats */}
      {loading ? (
        <div className="text-center py-20">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600 mb-4"></div>
          <p className="text-gray-500 font-medium">Récupération de vos pépites...</p>
        </div>
      ) : filteredFavorites.length > 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Produit</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Similarité</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Prix</th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredFavorites.map((fav, index) => (
                  <tr key={index} className="hover:bg-gray-50 transition-colors group">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-semibold text-gray-900 text-lg">
                          {fav.product_name}
                        </div>
                        <div className="text-sm text-gray-500 font-medium">
                          {fav.brand_name}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {(fav.similarity || 0) >= 0.8 ? (
                            <span className="flex items-center gap-1 bg-green-100 text-green-700 px-2 py-1 rounded-md text-xs font-bold">
                                <Star size={12} fill="currentColor" /> {Math.round((fav.similarity || 0) * 100)}%
                            </span>
                        ) : (
                            <span className="flex items-center gap-1 bg-yellow-100 text-yellow-700 px-2 py-1 rounded-md text-xs font-bold">
                                <Star size={12} fill="currentColor" /> {Math.round((fav.similarity || 0) * 100)}%
                            </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-900">
                        ${(fav.price || 0).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        // Important: On passe product_name ici
                        onClick={() => handleRemoveFavorite(fav.product_name)}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                        title="Retirer des favoris"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
          <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <ShoppingBag className="text-gray-400" size={40} />
          </div>
          <h3 className="text-xl font-bold text-gray-800 mb-2">
            Aucun favori pour le moment
          </h3>
          <p className="text-gray-500 mb-8 max-w-md mx-auto leading-relaxed">
            Vos produits sauvegardés apparaîtront ici.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              to="/dupes"
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-semibold shadow-lg shadow-blue-200 transition-all flex items-center gap-2"
            >
              <Search size={18}/> Trouver des alternatives
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default FavoritesPage;