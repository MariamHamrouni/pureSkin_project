import { createContext, useContext, useState, useEffect } from "react";
import api from "../services/axiosClient";

const AuthContext = createContext();

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (token) {
            api.get("/auth/me")
                .then((response) => {
                    setUser(response.data);
                })
                .catch(() => {
                    setUser(null);
                    localStorage.removeItem("token");
                })
                .finally(() =>
                    setLoading(false));
        }
        else {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setLoading(false);
        }
    }, []);

    // --- FONCTION REGISTER CORRIGÉE ---
    const register = async (name, email, password) => {
        try {
            const response = await api.post("/auth/register", { name, email, password });
            
            // On stocke le token et l'user
            localStorage.setItem("token", response.data.token);
            setUser(response.data.user || response.data); 
            
            // ✅ IMPORTANT : On retourne un objet avec success: true
            return { success: true };
        } catch (error) {
            console.error("Erreur Inscription:", error);
            // ❌ On gère l'erreur proprement
            return { 
                success: false, 
                message: error.response?.data?.msg || error.response?.data?.message || "Erreur lors de l'inscription"
            };
        }
    };

    // --- FONCTION LOGIN CORRIGÉE ---
    const login = async (email, password) => {
        try {
            const response = await api.post("/auth/login", { email, password });
            
            // On stocke le token et l'user
            setUser(response.data.user || response.data);
            localStorage.setItem("token", response.data.token);
            
            // ✅ IMPORTANT : On retourne un objet avec success: true
            return { success: true };
        } catch (error) {
            console.error("Erreur Login:", error);
            // ❌ On retourne l'erreur pour l'afficher dans le Login.jsx
            return { 
                success: false, 
                message: error.response?.data?.msg || error.response?.data?.message || "Email ou mot de passe incorrect"
            };
        }
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem("token");
    };

    const value = {
        user,
        loading,
        register,
        login,
        logout,
        isAuthenticated: !!user,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}