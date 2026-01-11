import React, { useState } from 'react';
import { scanImage, getQualityAnalysis } from '../../services/aiService'; 
import toast, { Toaster } from 'react-hot-toast';
import styled from 'styled-components';
import { Camera, Search, RefreshCw, Star, AlertCircle, Database, CheckCircle, DollarSign } from 'lucide-react';

// --- STYLES ---
const Container = styled.div`
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
  background-color: #f8fafc;
  min-height: 100vh;
`;

const ScanCard = styled.div`
  background: white;
  border-radius: 1.5rem;
  padding: 2rem;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
`;

const ImagePreview = styled.div`
  width: 100%;
  height: 250px;
  background-color: #f1f5f9;
  border-radius: 1rem;
  border: 2px dashed #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  
  img { 
    width: 100%; 
    height: 100%; 
    object-fit: contain;
    background: white;
  }
  
  &:hover { 
    border-color: #3b82f6; 
    background-color: #eff6ff; 
  }
`;

const ActionButton = styled.button`
  width: 100%;
  padding: 1rem;
  background: ${props => props.$primary ? 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)' : '#f1f5f9'};
  color: ${props => props.$primary ? 'white' : '#475569'};
  border: none;
  border-radius: 1rem;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s;

  &:hover { 
    transform: translateY(-2px); 
    box-shadow: ${props => props.$primary ? '0 5px 15px rgba(37, 99, 235, 0.3)' : 'none'};
    background: ${props => props.$primary ? '' : '#e2e8f0'};
  }
  
  &:disabled { 
    opacity: 0.6; 
    cursor: not-allowed; 
    transform: none; 
  }
`;

const ResultCard = styled.div`
  background: white;
  border-radius: 1.5rem;
  padding: 2rem;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  margin-top: 2rem;
  animation: fadeIn 0.5s ease-out;
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const ScoreBadge = styled.div`
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: ${props => props.bg};
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  box-shadow: 0 10px 30px ${props => props.shadow};
  border: 6px solid white;
  position: relative;
`;

const InfoBox = styled.div`
  background: ${props => props.type === 'error' ? '#fee2e2' : 
    props.type === 'warning' ? '#fef3c7' : 
    props.type === 'success' ? '#d1fae5' : '#e0f2fe'};
  
  border: 1px solid ${props => props.type === 'error' ? '#ef4444' : 
    props.type === 'warning' ? '#f59e0b' :
    props.type === 'success' ? '#10b981' : '#60a5fa'};
  
  color: ${props => props.type === 'error' ? '#b91c1c' : 
    props.type === 'warning' ? '#92400e' :
    props.type === 'success' ? '#065f46' : '#1e40af'};
  
  border-radius: 0.75rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
  text-align: left;
  font-size: 0.9rem;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
`;

const ProductScanner = () => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loadingScan, setLoadingScan] = useState(false);
  const [loadingRating, setLoadingRating] = useState(false);
  
  const [productData, setProductData] = useState({ 
    brand: '', 
    productName: '', 
    ingredients: '' 
  });
  
  const [scanResult, setScanResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // --- HANDLERS ---
  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
      setPreview(URL.createObjectURL(file));
      setScanResult(null);
      setErrorMsg(null);
      setProductData({ brand: '', productName: '', ingredients: '' });
    }
  };

  const handleScan = async () => {
    if (!selectedImage) return toast.error("Veuillez choisir une image");
    
    setLoadingScan(true);
    setErrorMsg(null);
    setScanResult(null);

    try {
      const data = await scanImage(selectedImage);
      console.log("📡 Réponse backend:", data);

      if (data.success === false) {
        setErrorMsg(data.error || "Erreur de scan");
        toast.error("Échec du scan");
        return;
      }

      // Stocker toute la réponse
      setScanResult(data);

      // Mettre à jour les champs avec les meilleures données
      const bestMatch = data.database_matches?.matches?.[0];
      
      setProductData({
        brand: data.ocr_data?.brand || bestMatch?.brand || '',
        productName: data.ocr_data?.product_name || bestMatch?.product_name || '',
        ingredients: bestMatch?.ingredients || ''
      });

      toast.success(`✅ Scan réussi ! ${data.database_matches?.count || 0} produit(s) trouvé(s)`);

    } catch (error) {
      console.error("Erreur scan:", error);
      toast.error("Erreur de connexion au serveur");
    } finally {
      setLoadingScan(false);
    }
  };

  const handleGetRating = async () => {
    // Si on a déjà un résultat de scan, on peut analyser manuellement
    if (!productData.productName) {
      return toast.error("Veuillez d'abord scanner ou saisir un produit");
    }

    if (!productData.ingredients || productData.ingredients.length < 20) {
      return toast.error("Les ingrédients sont nécessaires pour l'analyse");
    }

    setLoadingRating(true);

    try {
      const response = await getQualityAnalysis({
        product_name: productData.productName,
        brand_name: productData.brand,
        ingredients: productData.ingredients
      });

      const finalData = response.data || response;
      
      // Mettre à jour scanResult avec la nouvelle analyse
      setScanResult(prev => ({
        ...prev,
        analysis: finalData
      }));

      toast.success("✅ Analyse manuelle terminée !");

    } catch (error) {
      console.error("Erreur analyse:", error);
      toast.error("Erreur lors de l'analyse");
    } finally {
      setLoadingRating(false);
    }
  };

  const handleInputChange = (e) => {
    setProductData({ ...productData, [e.target.name]: e.target.value });
  };

  // --- UTILITY FUNCTIONS ---
  const getScoreStyle = (safetyScore) => {
    if (!safetyScore) return { 
      bg: 'linear-gradient(135deg, #94a3b8, #64748b)', 
      shadow: 'rgba(100, 116, 139, 0.4)', 
      label: 'Inconnu', 
      score: 0 
    };
    
    switch(safetyScore) {
      case "Excellent":
        return { 
          bg: 'linear-gradient(135deg, #10b981, #059669)', 
          shadow: 'rgba(16, 185, 129, 0.4)', 
          label: 'Excellent', 
          score: 85 
        };
      case "Good":
        return { 
          bg: 'linear-gradient(135deg, #3b82f6, #2563eb)', 
          shadow: 'rgba(37, 99, 235, 0.4)', 
          label: 'Bon', 
          score: 70 
        };
      case "Average":
        return { 
          bg: 'linear-gradient(135deg, #f59e0b, #d97706)', 
          shadow: 'rgba(245, 158, 11, 0.4)', 
          label: 'Moyen', 
          score: 55 
        };
      default:
        return { 
          bg: 'linear-gradient(135deg, #ef4444, #dc2626)', 
          shadow: 'rgba(239, 68, 68, 0.4)', 
          label: 'Problématique', 
          score: 40 
        };
    }
  };

  // --- RENDER FUNCTIONS ---
  const renderScanDetails = () => {
    if (!scanResult) return null;

    const { ocr_data, database_matches } = scanResult;
    
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
        <h4 className="font-bold text-gray-700 mb-2 flex items-center gap-2">
          <Search size={18} /> Détails du scan
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <span className="font-semibold">Marque détectée:</span> {ocr_data?.brand || 'Non détectée'}
          </div>
          <div>
            <span className="font-semibold">Produit détecté:</span> {ocr_data?.product_name || 'Non détecté'}
          </div>
          <div>
            <span className="font-semibold">Confiance OCR:</span> 
            <span className={`ml-2 px-2 py-1 rounded-full text-xs ${
              ocr_data?.confidence === 'high' ? 'bg-green-100 text-green-800' :
              ocr_data?.confidence === 'medium' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {ocr_data?.confidence || 'inconnue'}
            </span>
          </div>
          <div>
            <span className="font-semibold">Correspondances DB:</span> 
            <span className="ml-2 px-2 py-1 rounded-full bg-blue-100 text-blue-800 text-xs">
              {database_matches?.count || 0}
            </span>
          </div>
        </div>
      </div>
    );
  };

  const renderAnalysis = () => {
    if (!scanResult?.analysis) return null;

    const analysis = scanResult.analysis;
    const ingredientsAnalysis = analysis.ingredients_analysis || {};
    const safetyScore = ingredientsAnalysis.safety_score;
    const scoreStyle = getScoreStyle(safetyScore);

    return (
      <ResultCard>
        {/* SCORE */}
        <div className="text-center mb-6">
          <ScoreBadge bg={scoreStyle.bg} shadow={scoreStyle.shadow}>
            <span className="text-4xl font-bold">{scoreStyle.score}</span>
            <span className="text-sm opacity-90">/ 100</span>
            <div className="absolute -bottom-3 bg-white text-gray-800 px-3 py-1 rounded-full text-xs font-bold shadow-sm border">
              {scoreStyle.label}
            </div>
          </ScoreBadge>
          
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            {safetyScore === "Excellent" ? "✅ Composition excellente" :
             safetyScore === "Good" ? "⚠️ Composition bonne" :
             safetyScore === "Average" ? "⚠️ Composition moyenne" :
             "❌ Composition problématique"}
          </h2>
          
          {scanResult.database_matches?.count > 0 && (
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-full text-sm font-bold border border-green-100 mb-4">
              <Database size={16} /> Produit vérifié en base de données
            </div>
          )}
        </div>

        {/* PRODUIT IDENTIFIÉ */}
        {analysis.identification && (
          <div className="mb-6 p-4 bg-blue-50 rounded-xl">
            <h3 className="font-bold text-blue-700 mb-3 flex items-center gap-2">
              <CheckCircle size={18} /> Produit identifié
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <p className="text-sm text-gray-500">Nom</p>
                <p className="font-medium">{analysis.identification.product_name || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Marque</p>
                <p className="font-medium">{analysis.identification.brand || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Catégorie</p>
                <p className="font-medium">{analysis.identification.primary_category || 'N/A'}</p>
              </div>
            </div>
          </div>
        )}

        {/* ANALYSE SÉCURITÉ */}
        <div className="mb-6">
          <h3 className="font-bold text-gray-700 mb-3">🔬 Analyse de sécurité</h3>
          
          {/* Irritants */}
          {ingredientsAnalysis.irritants?.length > 0 && (
            <div className="mb-4">
              <h4 className="font-bold text-red-600 mb-2 flex items-center gap-2">
                <AlertCircle size={16} /> Ingrédients irritants détectés
              </h4>
              <div className="flex flex-wrap gap-2">
                {ingredientsAnalysis.irritants.map((item, i) => (
                  <span key={i} className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Comédogènes */}
          {ingredientsAnalysis.comedogenic?.length > 0 && (
            <div className="mb-4">
              <h4 className="font-bold text-orange-600 mb-2">⚠️ Ingrédients comédogènes</h4>
              <div className="flex flex-wrap gap-2">
                {ingredientsAnalysis.comedogenic.map((item, i) => (
                  <span key={i} className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Aucun problème */}
          {(!ingredientsAnalysis.irritants?.length && !ingredientsAnalysis.comedogenic?.length) && (
            <div className="p-4 bg-green-50 rounded-xl border border-green-200">
              <h4 className="font-bold text-green-700 mb-1 flex items-center gap-2">
                <CheckCircle size={16} /> Aucun ingrédient problématique détecté
              </h4>
              <p className="text-green-600 text-sm">
                La composition semble sûre pour la plupart des types de peau.
              </p>
            </div>
          )}
        </div>

        {/* ANALYSE MARCHÉ */}
        {analysis.market_analysis && (
          <div className="mb-6 p-4 bg-purple-50 rounded-xl">
            <h3 className="font-bold text-purple-700 mb-3 flex items-center gap-2">
              <DollarSign size={18} /> Analyse marché
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Prix moyen des similaires</p>
                <p className="text-2xl font-bold text-purple-700">
                  ${analysis.market_analysis.average_similar_price?.toFixed(2) || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Nombre de produits similaires</p>
                <p className="text-2xl font-bold text-purple-700">
                  {analysis.market_analysis.similar_count || 0}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* PRODUITS SIMILAIRES */}
        {analysis.top_similar_products?.length > 0 && (
          <div>
            <h3 className="font-bold text-gray-700 mb-3">🔄 Produits similaires recommandés</h3>
            <div className="space-y-3">
              {analysis.top_similar_products.slice(0, 3).map((product, idx) => (
                <div key={idx} className="p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-800">{product.product_name}</h4>
                      <p className="text-sm text-gray-600">{product.brand_name}</p>
                      <div className="flex items-center gap-4 mt-2">
                        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                          ${product.price}
                        </span>
                        <span className="text-sm text-gray-500">
                          ⭐ {product.rating?.toFixed(1) || 'N/A'} ({product.reviews || 0} avis)
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="inline-block px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-bold">
                        {Math.round(product.similarity * 100)}% similaire
                      </span>
                    </div>
                  </div>
                  {product.ingredients_preview && (
                    <p className="text-xs text-gray-500 mt-2 truncate">
                      {product.ingredients_preview}...
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </ResultCard>
    );
  };

  return (
    <Container>
      <Toaster 
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
          },
        }}
      />
      
      {/* HEADER */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">📸 PureSkin Scanner</h1>
        <p className="text-gray-500">Scannez l'emballage d'un produit cosmétique pour analyser sa composition</p>
      </div>

      {/* SCAN CARD */}
      <ScanCard>
        {/* IMAGE UPLOAD */}
        <ImagePreview onClick={() => document.getElementById('fileInput').click()}>
          {preview ? (
            <img src={preview} alt="Scan Preview" />
          ) : (
            <div className="text-center text-gray-400">
              <Camera size={48} className="mx-auto mb-3" />
              <p className="font-medium">Cliquez pour prendre une photo</p>
              <p className="text-xs mt-2">ou glissez-déposez une image</p>
              <p className="text-xs text-gray-400 mt-1">
                (Photo de l'emballage frontal de préférence)
              </p>
            </div>
          )}
        </ImagePreview>
        
        <input 
          id="fileInput" 
          type="file" 
          accept="image/*" 
          onChange={handleImageChange} 
          style={{display: 'none'}} 
        />

        {/* ERROR MESSAGE */}
        {errorMsg && (
          <InfoBox type="error">
            <AlertCircle size={20} />
            <div>
              <strong>Erreur de lecture :</strong> {errorMsg}
              <br />
              <span className="text-xs">
                • Assurez-vous que le texte est net et bien éclairé
                <br />
                • Évitez les reflets sur l'emballage
              </span>
            </div>
          </InfoBox>
        )}

        {/* SCAN BUTTONS */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <ActionButton onClick={() => document.getElementById('fileInput').click()}>
            <Camera size={20} />
            Changer Photo
          </ActionButton>
          
          <ActionButton 
            onClick={handleScan} 
            disabled={loadingScan || !selectedImage} 
            style={{background: '#e0e7ff', color: '#4338ca'}}
          >
            {loadingScan ? <RefreshCw className="animate-spin" /> : <Search size={20} />}
            {loadingScan ? "Analyse en cours..." : "Scanner le produit"}
          </ActionButton>
        </div>

        {/* SCAN DETAILS */}
        {renderScanDetails()}

        {/* PRODUCT FORM */}
        <div className="space-y-4 mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col text-left">
              <label className="text-xs font-bold text-gray-500 mb-1 ml-1">
                MARQUE <span className="text-red-500">*</span>
              </label>
              <input 
                name="brand" 
                value={productData.brand} 
                onChange={handleInputChange} 
                className="w-full p-3 border border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ex: CAVIAR"
                required
              />
            </div>
            
            <div className="flex flex-col text-left">
              <label className="text-xs font-bold text-gray-500 mb-1 ml-1">
                PRODUIT <span className="text-red-500">*</span>
              </label>
              <input 
                name="productName" 
                value={productData.productName} 
                onChange={handleInputChange} 
                className="w-full p-3 border border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ex: ANTI-AGING CONDITIONER"
                required
              />
            </div>
          </div>

          <div className="flex flex-col text-left">
            <label className="text-xs font-bold text-gray-500 mb-1 ml-1">
              INGRÉDIENTS <span className="text-red-500">*</span>
            </label>
            <textarea
              name="ingredients"
              value={productData.ingredients}
              onChange={handleInputChange}
              className="w-full p-3 border border-gray-300 rounded-xl text-sm h-32 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              placeholder="Saisissez ou collez la liste complète des ingrédients séparés par des virgules..."
              required
            />
            <div className="text-xs text-gray-500 mt-1 flex justify-between">
              <span>
                {productData.ingredients.length} caractères
                {productData.ingredients.length < 20 && ' (minimum 20 requis)'}
              </span>
              {scanResult?.database_matches?.count > 0 && (
                <span className="text-green-600 font-medium">
                  ✓ Ingrédients extraits de la base
                </span>
              )}
            </div>
          </div>

          {/* ACTION BUTTONS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <ActionButton 
              onClick={handleGetRating} 
              disabled={loadingRating || !productData.productName || !productData.ingredients || productData.ingredients.length < 20}
              $primary={true}
            >
              {loadingRating ? <RefreshCw className="animate-spin" /> : <Star fill="currentColor" />}
              {loadingRating ? "Analyse en cours..." : "Analyser la composition"}
            </ActionButton>
            
            <ActionButton 
              onClick={() => {
                setScanResult(null);
                setProductData({ brand: '', productName: '', ingredients: '' });
                setSelectedImage(null);
                setPreview(null);
                toast("Formulaire réinitialisé", { icon: '🔄' });
              }}
              style={{background: '#f1f5f9', color: '#64748b'}}
            >
              Effacer tout
            </ActionButton>
          </div>

          {/* INFO */}
          {!scanResult && (
            <InfoBox type="info">
              <div className="text-center w-full">
                <p className="font-medium mb-1">Comment utiliser :</p>
                <ol className="text-xs text-gray-600 list-decimal list-inside text-left space-y-1">
                  <li>Téléchargez une photo claire de l'emballage frontal</li>
                  <li>Cliquez sur "Scanner le produit" pour détecter automatiquement</li>
                  <li>Les ingrédients seront extraits de notre base de données</li>
                  <li>Cliquez sur "Analyser la composition" pour obtenir le rapport complet</li>
                </ol>
              </div>
            </InfoBox>
          )}
        </div>
      </ScanCard>

      {/* ANALYSIS RESULT */}
      {renderAnalysis()}

      {/* FOOTER */}
      <div className="text-center mt-8 text-sm text-gray-500">
        <p>
          ℹ️ L'analyse est basée sur notre base de données de plus de 10 000 produits cosmétiques.
          <br />
          Les résultats sont indicatifs et ne remplacent pas l'avis d'un professionnel de santé.
        </p>
      </div>
    </Container>
  );
};

export default ProductScanner;