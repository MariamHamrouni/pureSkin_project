import axios from 'axios';

// Instance pour Python (Port 8000)
const axiosAI = axios.create({
    baseURL: 'http://localhost:8000', 
    // ⚠️ IMPORTANT : Ne pas mettre de 'Content-Type' ici par défaut.
    // Axios le détectera automatiquement :
    // - JSON pour les objets classiques
    // - Multipart/form-data pour les images (FormData)
});

// Intercepteur : Ajoute le Token automatiquement s'il existe
axiosAI.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default axiosAI;