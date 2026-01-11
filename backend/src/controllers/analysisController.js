const nlpService = require('../services/nlpService');
const Favorite = require('../models/Favorite');
const User = require('../models/User');

// --- 1. SCANNER INTELLIGENT (IMAGE) ---
exports.scanImage = async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ 
                success: false, 
                message: "Aucune image fournie." 
            });
        }

        if (req.file.size > 10 * 1024 * 1024) {
            return res.status(400).json({
                success: false,
                message: "L'image est trop volumineuse (max 10MB)"
            });
        }

        console.log(`📸 Scan image: ${req.file.originalname}`);

        // Appel au service Python via nlpService
        const result = await nlpService.scanImage(
            req.file.buffer, 
            req.file.filename, 
            req.file.originalname
        );

        res.json({ success: true, data: result });

    } catch (error) {
        console.error("❌ Erreur scanImage:", error.message);
        res.status(500).json({ 
            success: false, 
            message: error.message,
            suggestion: "Essayez une image plus nette"
        });
    }
};

// --- 2. ANALYSE QUALITÉ / RATING (✅ AJOUTÉ) ---
exports.getQualityAnalysis = async (req, res) => {
    try {
        // Récupération des données du frontend
        const { product_name, brand_name, ingredients } = req.body;

        if (!product_name) {
             return res.status(400).json({ 
                success: false, 
                message: "Le nom du produit est requis pour trouver sa note." 
            });
        }

        // Appel au service qui contacte Python
        const result = await nlpService.analyzeQuality({ 
            product_name, 
            brand_name, 
            ingredients 
        });

        res.status(200).json({
            success: true,
            data: result
        });

    } catch (error) {
         console.error("❌ Erreur getQualityAnalysis:", error.message);
         res.status(500).json({ 
            success: false, 
            message: "Erreur lors de la récupération de la note." 
        });
    }
};

// --- 3. RECHERCHE DE DUPES ---
exports.getDupes = async (req, res) => {
    try {
        const { ingredients, brand, type, price, category } = req.body;

        if (!ingredients || ingredients.trim().length < 5) {
            return res.status(400).json({ 
                success: false, 
                message: "Ingrédients requis pour trouver des dupes." 
            });
        }

        console.log(`🔍 Dupes pour ~${ingredients.length} chars`);

        const results = await nlpService.findDupes(ingredients, brand, type, price, category);

        // Gestion des favoris si connecté
        if (req.userId && results.results) {
            try {
                const userFavorites = await Favorite.find({ userId: req.userId });
                const favIds = userFavorites.map(fav => fav.productId);
                results.results = results.results.map(p => ({
                    ...p,
                    isFavorite: favIds.includes(p.product_id)
                }));
            } catch (e) { console.warn("Info: Favoris non sync"); }
        }

        res.status(200).json({
            success: true,
            count: results.count || 0,
            data: results.results || []
        });

    } catch (error) {
        console.error("❌ Erreur getDupes:", error.message);
        res.status(500).json({ success: false, message: error.message });
    }
};

// --- 4. ANALYSE DE SENTIMENT ---
exports.getSentiment = async (req, res) => {
    try {
        const { text, skinType } = req.body;
        if (!text) return res.status(400).json({ message: "Texte requis" });

        const analysis = await nlpService.analyzeReview(text, skinType);
        res.status(200).json({ success: true, data: analysis });

    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};

// --- 5. GESTION DES FAVORIS ---
exports.addToFavorites = async (req, res) => {
    try {
        const { productId, productName, brandName, price, ingredients, similarity } = req.body;
        
        if (!req.userId) return res.status(401).json({ message: "Connectez-vous" });

        const existing = await Favorite.findOne({ userId: req.userId, productId });
        if (existing) return res.status(200).json({ message: "Déjà favori", alreadyExists: true });

        const favorite = new Favorite({
            userId: req.userId,
            productId, productName, brandName, 
            price: parseFloat(price) || 0,
            ingredients, similarity,
            addedAt: new Date(), source: 'dupe_finder'
        });

        await favorite.save();
        res.status(201).json({ success: true, message: "Ajouté aux favoris", data: favorite });

    } catch (error) {
        res.status(500).json({ success: false, message: "Erreur favoris" });
    }
};

exports.removeFromFavorites = async (req, res) => {
    try {
        if (!req.userId) return res.status(401).json({ message: "Non autorisé" });
        await Favorite.findOneAndDelete({ userId: req.userId, productId: req.params.productId });
        res.status(200).json({ success: true, message: "Retiré des favoris" });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};

exports.getFavorites = async (req, res) => {
    try {
        if (!req.userId) return res.status(401).json({ message: "Connectez-vous" });
        const favorites = await Favorite.find({ userId: req.userId }).sort({ addedAt: -1 });
        res.status(200).json({ success: true, data: favorites });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};

// --- 6. SANTÉ SERVICE ---
exports.checkServiceHealth = async (req, res) => {
    try {
        const health = await nlpService.checkHealth();
        res.status(200).json({ success: true, status: health.status, details: health });
    } catch (error) {
        res.status(200).json({ success: false, status: "offline" });
    }
};