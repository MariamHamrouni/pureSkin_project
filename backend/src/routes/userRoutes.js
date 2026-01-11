const express = require('express');
const router = express.Router();
const { updateUserProfile, deleteUser } = require('../controllers/userController');
const { protect } = require('../middleware/authMiddleware');

// Toutes ces routes sont protégées
router.put('/profile', protect, updateUserProfile);
router.delete('/profile', protect, deleteUser);

module.exports = router;