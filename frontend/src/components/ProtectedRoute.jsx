import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  
  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // 2. Si le chargement est fini et qu'il n'y a pas d'utilisateur, on redirige
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // 3. Sinon, on affiche la page demandée
  return children;
};

export default ProtectedRoute;