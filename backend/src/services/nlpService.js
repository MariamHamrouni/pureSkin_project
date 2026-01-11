const axios = require('axios');
const FormData = require('form-data');

// Configuration améliorée
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

// Timeout configurable
const axiosConfig = {
    timeout: 30000, // 30 secondes
    headers: {
        'Accept': 'application/json',
    }
};

// Service amélioré pour la recherche de dupes
const findDupes = async (ingredients, brand = null, type = null, price = 0, category = "All") => {
    try {
        console.log(`🔍 Recherche dupes pour ${ingredients.length} caractères`);
        
        const payload = {
            ingredients: ingredients,
            brand_name: brand,
            target_product_type: type,
            price: parseFloat(price) || 100,
            category: category
        };

        const response = await axios.post(
            `${PYTHON_API_URL}/analyze/find_dupes`, 
            payload, 
            axiosConfig
        );
        
        console.log(`✅ ${response.data.count || 0} résultats trouvés`);
        return response.data;
        
    } catch (error) {
        console.error("❌ Erreur communication IA:", error.message);
        
        // Messages d'erreur plus explicites
        if (error.code === 'ECONNREFUSED') {
            throw new Error("Le service d'analyse IA n'est pas disponible. Vérifiez que le serveur Python est en cours d'exécution.");
        } else if (error.response?.status === 503) {
            throw new Error("Le service d'analyse est en cours de chargement, veuillez réessayer dans quelques instants.");
        } else {
            throw new Error(`Erreur d'analyse: ${error.response?.data?.detail || error.message}`);
        }
    }
};

// Service d'analyse de sentiment
const analyzeReview = async (text, skinType = "All") => {
    try {
        const response = await axios.post(
            `${PYTHON_API_URL}/analyze/review`, 
            { text, skin_type: skinType },
            axiosConfig
        );
        return response.data;
    } catch (error) {
        console.warn("⚠️ Analyse de sentiment indisponible:", error.message);
        return { 
            sentiment: "Indisponible", 
            confidence: 0,
            error: error.message 
        };
    }
};

// Service de scan d'image amélioré
const scanImage = async (fileBuffer, fileName, originalname) => {
    try {
        console.log(`📸 Traitement image: ${originalname || fileName}`);
        
        const form = new FormData();
        form.append('file', fileBuffer, {
            filename: fileName || originalname || 'image.jpg',
            contentType: 'image/jpeg' 
        });

        // On récupère les headers spécifiques au formulaire (Content-Type + Boundary)
        const formHeaders = form.getHeaders();

        const response = await axios.post(
            `${PYTHON_API_URL}/analyze/scan-image`, 
            form, 
            {
                // On garde seulement le timeout de la config globale
                timeout: axiosConfig.timeout, 
                headers: {
                    ...formHeaders, // C'est le plus important !
                    // On peut ajouter d'autres headers si nécessaire, mais PAS Content-Type
                    // 'Authorization': 'Bearer ...' (si besoin)
                },
                // Important pour axios avec stream (Node.js)
                maxContentLength: Infinity,
                maxBodyLength: Infinity
            }
        );
        
        console.log(`✅ Scan réussi: ${response.data.scan_summary?.brand_detected || 'Inconnu'}`);
        return response.data;
    } catch (error) {
        console.error("❌ Erreur scan image:", error.message);
        
        if (error.response?.data?.detail) {
            throw new Error(error.response.data.detail);
        } else if (error.code === 'ECONNREFUSED') {
            throw new Error("Service OCR non disponible");
        } else {
            throw new Error(`Erreur de traitement d'image: ${error.message}`);
        }
    }
};

// Nouveau: Récupérer les recommandations
const getRecommendations = async (skinType) => {
    try {
        const response = await axios.post(
            `${PYTHON_API_URL}/analyze/recommend`, 
            { skin_type: skinType },
            axiosConfig
        );
        return response.data;
    } catch (error) {
        console.error("❌ Erreur recommandations:", error.message);
        return { recommendations: [] };
    }
};

// Nouveau: Vérifier la santé du service
const checkHealth = async () => {
    try {
        const response = await axios.get(`${PYTHON_API_URL}/health`, axiosConfig);
        return response.data;
    } catch (error) {
        return { 
            status: "offline", 
            message: "Service IA indisponible",
            error: error.message 
        };
    }
};
const analyzeQuality = async (data) => {
    // Appel vers Python /analyze/quality
    const response = await axios.post(`${PYTHON_API_URL}/analyze/quality`, data, axiosConfig);
    return response.data;
};

module.exports = { 
    findDupes, 
    analyzeReview, 
    scanImage, 
    getRecommendations,
    checkHealth,
    analyzeQuality
};