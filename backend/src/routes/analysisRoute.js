const express = require('express');
const router = express.Router();
const analysisController = require('../controllers/analysisController');
const multer = require('multer');

// --- CONFIGURATION MULTER ---
// Important : Le frontend envoie le fichier sous le champ "file"
const upload = multer({ 
    storage: multer.memoryStorage(),
    limits: { fileSize: 10 * 1024 * 1024 } // 10MB
});

// --- ROUTES ---

// 1. DUPES & SENTIMENT
router.post('/dupes', analysisController.getDupes);
router.post('/sentiment', analysisController.getSentiment);

// 2. SCAN IMAGE (Correction ici !)
// Frontend: api.post('/analysis/scan') + formData.append('file')
// Donc la route doit être '/scan' et upload.single('file')
router.post('/scan', upload.single('file'), analysisController.scanImage);

// 3. QUALITY / RATING (Correction ici !)
// Le contrôleur s'appelle getQualityAnalysis, pas analyzeQuality
router.post('/quality', analysisController.getQualityAnalysis);

// 4. FAVORIS (Optionnel, si vous l'utilisez)
router.post('/favorites', analysisController.addToFavorites);
router.get('/favorites', analysisController.getFavorites);
router.delete('/favorites/:productId', analysisController.removeFromFavorites);

// Route de test
router.get('/test', (req, res) => {
    res.json({ success: true, message: 'API Analysis OK 🚀' });
});

module.exports = router;