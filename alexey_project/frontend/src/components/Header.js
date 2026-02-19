import { NavLink, useNavigate } from 'react-router-dom';

function Header() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login', { replace: true });
  };

  return (
    <header className="app-header">
      <nav className="app-nav">
        <NavLink
          to="/documents"
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          Documents
        </NavLink>
        <NavLink
          to="/labels"
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          Labels
        </NavLink>
      </nav>
      <button type="button" className="btn secondary" onClick={handleLogout}>
        Logout
      </button>
    </header>
  );
}

export default Header;
