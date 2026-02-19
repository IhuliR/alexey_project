import { Navigate, Outlet } from 'react-router-dom';

function PrivateRoute({ children }) {
  const hasToken = Boolean(localStorage.getItem('access_token'));

  if (!hasToken) {
    return <Navigate to="/login" replace />;
  }

  return children || <Outlet />;
}

export default PrivateRoute;
