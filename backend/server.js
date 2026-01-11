require('dotenv').config();
const express = require('express');
const cors = require('cors');
const connectDB = require('./src/config/database');
const favoriteRoutes = require('./src/routes/favoriteRoutes');
// Import des routes
const analysisRoutes = require('./src/routes/analysisRoute');
const authRoutes = require('./src/routes/authRoutes');
const userRoutes = require('./src/routes/userRoutes');
// Initialisation de l'App
const app = express();

// Connexion BDD
connectDB();

// Middleware
app.use(cors());
app.use(express.json()); 

// Routes
app.use('/api/analysis', analysisRoutes);
app.use('/api/favorites', favoriteRoutes);
app.get('/', (req, res) => {
    res.send('PureSkin Backend API is running...');
});
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);

// Lancement du serveur
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`\n Serveur Node.js démarré sur le port ${PORT}`);
    console.log(`API Locale: http://localhost:${PORT}`);
});