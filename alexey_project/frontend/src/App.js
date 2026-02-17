import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import PrivateRoute from './components/PrivateRoute';
import DocumentPage from './pages/DocumentPage';
import DocumentsPage from './pages/DocumentsPage';
import LabelsPage from './pages/LabelsPage';
import LoginPage from './pages/LoginPage';
import './styles/App.css';

function App() {
  const hasToken = Boolean(localStorage.getItem('access_token'));

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<PrivateRoute />}>
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/labels" element={<LabelsPage />} />
        </Route>
        <Route
          path="/"
          element={<Navigate to={hasToken ? '/documents' : '/login'} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
