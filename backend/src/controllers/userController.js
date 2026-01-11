const User = require('../models/User');
const bcrypt = require('bcryptjs');

// @desc    Mettre à jour mon profil (Nom ou Email)
// @route   PUT /api/users/profile
exports.updateUserProfile = async (req, res) => {
  try {
    const user = await User.findById(req.user.id);

    if (user) {
      user.name = req.body.name || user.name;
      user.email = req.body.email || user.email;

      // Si l'utilisateur veut changer son mot de passe
      if (req.body.password) {
        const salt = await bcrypt.genSalt(10);
        user.password = await bcrypt.hash(req.body.password, salt);
      }

      const updatedUser = await user.save();

      res.json({
        _id: updatedUser._id,
        name: updatedUser.name,
        email: updatedUser.email,
        token: req.headers.authorization.split(' ')[1], // On renvoie le même token
      });
    } else {
      res.status(404).json({ message: 'Utilisateur non trouvé' });
    }
  } catch (error) {
    res.status(500).json({ message: 'Erreur serveur' });
  }
};

// @desc    Supprimer mon compte
// @route   DELETE /api/users/profile
exports.deleteUser = async (req, res) => {
    try {
        const user = await User.findById(req.user.id);
        
        if(user) {
            await user.deleteOne();
            // Optionnel : Ici, on pourrait aussi supprimer tous les favoris liés à cet user
            res.json({ message: "Utilisateur supprimé avec succès" });
        } else {
            res.status(404).json({ message: 'Utilisateur non trouvé' });
        }
    } catch (error) {
        res.status(500).json({ message: 'Erreur serveur' });
    }
};