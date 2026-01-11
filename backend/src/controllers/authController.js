const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const User = require('../models/User');

// Fonction utilitaire pour générer le token
const generateToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET, {
    expiresIn: '30d',
  });
};

// @desc    Inscrire un nouvel utilisateur
// @route   POST /api/auth/register
exports.register = async (req, res) => {
  const { name, email, password } = req.body;

  try {
    if (!name || !email || !password) {
      return res.status(400).json({ message: 'Veuillez remplir tous les champs' });
    }

    // Vérifier si l'utilisateur existe déjà
    const userExists = await User.findOne({ email });
    if (userExists) {
      return res.status(400).json({ message: 'Cet email est déjà utilisé' });
    }

    // Hasher le mot de passe
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    // Créer l'utilisateur
    const user = await User.create({
      name,
      email,
      password: hashedPassword,
    });

    if (user) {
      res.status(201).json({
        _id: user.id,
        name: user.name,
        email: user.email,
        token: generateToken(user._id),
      });
    } else {
      res.status(400).json({ message: 'Données invalides' });
    }
  } catch (error) {
    res.status(500).json({ message: 'Erreur Serveur' });
  }
};

// @desc    Connecter un utilisateur (Login)
// @route   POST /api/auth/login
exports.login = async (req, res) => {
  const { email, password } = req.body;

  try {
    // Vérifier l'email
    const user = await User.findOne({ email });

    // Vérifier le mot de passe
    if (user && (await bcrypt.compare(password, user.password))) {
      res.json({
        _id: user.id,
        name: user.name,
        email: user.email,
        token: generateToken(user._id),
      });
    } else {
      res.status(400).json({ message: 'Email ou mot de passe incorrect' });
    }
  } catch (error) {
    res.status(500).json({ message: 'Erreur Serveur' });
  }
};

// @desc    Récupérer mes infos (Persistance de connexion)
// @route   GET /api/auth/me
exports.getMe = async (req, res) => {
  // req.user est déjà rempli par le middleware protect
  res.status(200).json(req.user);
};