import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:5000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// 👇 1. INTERCEPTEUR DE REQUÊTE (C'est lui qui manquait !)
// Il injecte le token dans chaque appel vers le backend
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// 2. INTERCEPTEUR DE RÉPONSE (Gestion des erreurs)
api.interceptors.response.use(
    (response) => {
        return response; // Tout va bien
    },
    (error) => {
        // Si l'erreur est 401 (Token invalide ou expiré)
        if (error.response && error.response.status === 401) {
            console.warn("Session expirée (401 détecté)");
            
            // Une fois que tout marche, vous pourrez décommenter ces lignes :
            localStorage.removeItem('token');
            window.location.href = '/login'; 
        }
        return Promise.reject(error);
    }
);

export default api;