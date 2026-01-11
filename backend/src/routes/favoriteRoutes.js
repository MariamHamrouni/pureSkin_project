const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');
const { 
  addFavorite, 
  getMyFavorites, 
  deleteFavorite 
} = require('../controllers/favoriteController');

router.route('/')
  .post(protect, addFavorite)
  .get(protect, getMyFavorites);

router.route('/:id')
  .delete(protect, deleteFavorite);

module.exports = router;