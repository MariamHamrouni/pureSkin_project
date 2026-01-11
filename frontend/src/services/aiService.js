// services/aiService.js
import axios from 'axios';

// URL de ton backend Python (FastAPI)
const PYTHON_API_URL = 'http://localhost:8000';

// Configuration Axios par défaut
const axiosConfig = {
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000 // 30 secondes avant timeout
};

// --- 1. SCAN IMAGE (OCR) ---
export const scanImage = async (imageFile) => {
    const formData = new FormData();
    formData.append('file', imageFile);

    try {
        console.log("📸 Envoi de l'image au scan...");
        const response = await axios.post(`${PYTHON_API_URL}/analyze/scan`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 30000
        });
        return response.data;
    } catch (error) {
        console.error('Error scanning image:', error);
        throw error;
    }
};

// --- 2. ANALYSE QUALITÉ ---
export const getQualityAnalysis = async (productData) => {
    console.log("🔄 Envoi des données d'analyse:", productData);
    try {
        const response = await axios.post(`${PYTHON_API_URL}/analyze/quality`, productData, axiosConfig);
        console.log("✅ Réponse reçue:", response.data);
        return response.data;
    } catch (error) {
        console.error("❌ Erreur analyse qualité:", error);
        throw error;
    }
};

// --- 3. RECHERCHE DE DUPES (VERSION BLINDÉE ANTI-ERREUR 422) ---
export const findDupes = async (ingredients, type = null, price = 0, category = "All") => {
    try {
        // --- ETAPE DE NETTOYAGE DES DONNEES (CRITIQUE) ---
        
        // 1. Ingrédients : Force en string
        const ingredientsStr = Array.isArray(ingredients) 
            ? ingredients.join(", ") 
            : String(ingredients || "");

        // 2. Gestion intelligente des arguments mélangés (Prix vs Type)
        // Le log montre que 'type' reçoit parfois le prix (ex: 195).
        
        let finalPrice = parseFloat(price);
        let finalType = type;

        // Si 'type' est un nombre (ex: 195), c'est que les arguments sont décalés !
        if (typeof type === 'number' || (typeof type === 'string' && !isNaN(parseFloat(type)) && type.length < 5)) {
            // On récupère ce nombre comme prix si le prix actuel est vide/0
            if (!finalPrice || finalPrice === 0) {
                finalPrice = parseFloat(type);
            }
            // On force le type à null car "195" n'est pas une catégorie valide
            finalType = null;
        }
        
        // Sécurité : Si le prix n'est pas valide, on met 0
        if (isNaN(finalPrice)) finalPrice = 0;

        // Sécurité : On force le type en string ou null (jamais de nombre)
        const safeSecondaryCategory = (typeof finalType === 'string' && finalType.length > 1) ? finalType : null;

        // 3. Catégorie principale
        const safePrimaryCategory = (category === "All" || !category) ? null : String(category);

        console.log(`🔍 Recherche dupes. \n   Ingredients: ${ingredientsStr.length} chars\n   Prix Cible: ${finalPrice}\n   Type (Sec): ${safeSecondaryCategory}\n   Cat (Prim): ${safePrimaryCategory}`);

        // --- CREATION DU PAYLOAD ---
        const payload = {
            ingredients: ingredientsStr,
            target_price: finalPrice, 
            primary_category: safePrimaryCategory,
            secondary_category: safeSecondaryCategory, // Ici, on est sûr que ce n'est plus un nombre
            top_n: 20
        };

        const response = await axios.post(
            `${PYTHON_API_URL}/analyze/find_dupes`, 
            payload, 
            axiosConfig
        );
        
        const count = response.data.alternatives ? response.data.alternatives.length : 0;
        console.log(`✅ ${count} résultats trouvés`);
        
        return response.data;
        
    } catch (error) {
        console.error("❌ Erreur communication IA:", error.message);
        
        if (error.response?.data?.detail) {
             console.error("Détail Précis Erreur Backend:", JSON.stringify(error.response.data.detail, null, 2));
             // On ne throw pas une erreur complexe pour ne pas casser l'UI, on renvoie un objet vide
             return { alternatives: [], best_dupe: null, note: "Erreur de format de données" };
        } else if (error.code === 'ECONNREFUSED') {
            throw new Error("Le serveur backend est éteint.");
        } else {
            throw error;
        }
    }
};

// --- 4. AUTRES FONCTIONS ---
export const analyzeReview = async (text, skinType = "All") => {
    try {
        const response = await axios.post(`${PYTHON_API_URL}/analyze/review`, { text, skin_type: skinType }, axiosConfig);
        return response.data;
    } catch  {
        return { sentiment: "Neutral", confidence: 0 };
    }
};

export const getRecommendations = async (skinType) => {
    try {
        const response = await axios.post(`${PYTHON_API_URL}/analyze/recommend`, { skin_type: skinType }, axiosConfig);
        return response.data;
    } catch {
        return { recommendations: [] };
    }
};

export const checkHealth = async () => {
    try {
        const response = await axios.get(`${PYTHON_API_URL}/health`, axiosConfig);
        return response.data;
    } catch {
        return { status: "offline" };
    }
};
export const getDynamicFilters = async () => {
    try {
        const response = await axios.get(`${PYTHON_API_URL}/analyze/filters`, axiosConfig);
        return response.data;
    } catch (error) {
        console.warn("⚠️ Impossible de charger les filtres dynamiques:", error.message);
        // On renvoie des tableaux vides pour ne pas casser l'UI
        return { categories: [], brands: [], types: [] };
    }
};
export const getFavorites = async () => {
    try {
        const response = await axios.get(`${PYTHON_API_URL}/favorites`);
        return response.data;
    } catch (error) {
        console.error("Erreur chargement favoris", error);
        return [];
    }
};

// Ajouter un favori
export const addFavorite = async (product) => {
    try {
        // On nettoie l'objet pour correspondre au modèle Python
        const payload = {
            product_name: product.product_name,
            brand_name: product.brand_name,
            price: parseFloat(product.price) || 0,
            similarity: parseFloat(product.similarity) || 0,
            primary_category: product.primary_category || "Unknown"
        };
        const response = await axios.post(`${PYTHON_API_URL}/favorites`, payload);
        return response.data;
    } catch (error) {
        console.error("Erreur ajout favori", error);
        throw error;
    }
};

// Retirer un favori
export const removeFavorite = async (productName) => {
    try {
        // Encodage de l'URL car le nom peut contenir des espaces ou caractères spéciaux
        const encodedName = encodeURIComponent(productName);
        const response = await axios.delete(`${PYTHON_API_URL}/favorites/${encodedName}`);
        return response.data;
    } catch (error) {
        console.error("Erreur suppression favori", error);
        throw error;
    }
};