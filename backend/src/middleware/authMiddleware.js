const jwt = require('jsonwebtoken');
const User = require('../models/User');

const protect = async (req, res, next) => {
  let token;

 
  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith('Bearer')
  ) {
    try {
      // 2. Récupérer le token (enlever "Bearer ")
      token = req.headers.authorization.split(' ')[1];

      // 3. Décoder le token
      const decoded = jwt.verify(token, process.env.JWT_SECRET);

      // 4. Retrouver l'utilisateur (sans le mot de passe)
      req.user = await User.findById(decoded.id).select('-password');

      next(); // C'est validé, on passe à la suite
    } catch (error) {
      console.error(error);
      res.status(401).json({ message: 'Non autorisé, token invalide' });
    }
  }

  if (!token) {
    res.status(401).json({ message: 'Non autorisé, aucun token' });
  }
};

module.exports = {protect};