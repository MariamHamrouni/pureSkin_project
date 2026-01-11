const Favorite = require('../models/Favorite');
const mongoose = require('mongoose');

// @desc    Ajouter un favori
// @route   POST /api/favorites
const addFavorite = async (req, res) => {
  try {
    const { 
      product_name, brand_name, price, ingredients, category, similarity, product_id 
    } = req.body;

    // 1. 👇 VÉRIFICATION ANTI-DOUBLON
    // On cherche si ce produit existe déjà pour cet utilisateur
    const existingFavorite = await Favorite.findOne({ 
      userId: req.user.id, 
      productName: product_name // On vérifie par le nom
    });

    if (existingFavorite) {
      // Si trouvé, on arrête tout et on renvoie une erreur 400
      return res.status(400).json({ msg: "Ce produit est déjà dans vos favoris !" });
    }

    // 2. Si pas de doublon, on crée le favori
    const newFavorite = new Favorite({
      userId: req.user.id,
      productId: product_id || new mongoose.Types.ObjectId().toString(),
      productName: product_name || "Nom inconnu",
      brandName: brand_name || "Marque inconnue",
      price: price || 0,
      ingredients: ingredients || "",
      category: category || "Skincare",
      similarity: similarity || 0,
      source: 'dupe_finder'
    });

    const savedFavorite = await newFavorite.save();
    res.status(201).json(savedFavorite);

  } catch (err) {
    console.error("❌ Erreur Add Favorite:", err.message);
    
    // Sécurité supplémentaire : Erreur MongoDB (Index unique)
    if (err.code === 11000) {
      return res.status(400).json({ msg: "Produit déjà en favoris" });
    }
    
    res.status(500).json({ msg: "Erreur serveur" });
  }
};

// @desc    Récupérer les favoris de l'utilisateur connecté
// @route   GET /api/favorites
const getMyFavorites = async (req, res) => {
  try {
    // ⚠️ LA CORRECTION EST ICI : 
    // Votre schéma utilise 'userId', donc on doit chercher { userId: ... }
    // Si on met { user: ... }, ça renvoie vide !
    const favorites = await Favorite.find({ userId: req.user.id })
                                    .sort({ createdAt: -1 }); // Plus récents en premier

    // On renvoie directement le tableau
    res.json(favorites);

  } catch (err) {
    console.error("❌ Erreur Get Favorites:", err.message);
    res.status(500).json({ msg: "Erreur serveur lors du chargement des favoris" });
  }
};

// @desc    Supprimer un favori
// @route   DELETE /api/favorites/:id
const deleteFavorite = async (req, res) => {
  try {
    // On cherche le favori par son _id (MongoDB)
    const favorite = await Favorite.findById(req.params.id);

    if (!favorite) {
      return res.status(404).json({ msg: "Favori non trouvé" });
    }

    // Vérifier que c'est bien l'utilisateur propriétaire
    if (favorite.userId.toString() !== req.user.id) {
      return res.status(401).json({ msg: "Non autorisé" });
    }

    await favorite.deleteOne();
    res.json({ msg: "Favori supprimé" });

  } catch (err) {
    console.error("❌ Erreur Delete Favorite:", err.message);
    res.status(500).json({ msg: "Erreur serveur" });
  }
};

module.exports = {
  addFavorite,
  getMyFavorites,
  deleteFavorite
};