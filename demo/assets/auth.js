(function () {
  var SESSION_KEY = 'session';

  function readSession() {
    var raw = localStorage.getItem(SESSION_KEY);
    if (!raw) {
      return null;
    }
    try {
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed.token !== 'string' || typeof parsed.currentUser !== 'string') {
        return null;
      }
      var user = JSON.parse(parsed.currentUser);
      return {
        token: parsed.token,
        currentUser: user,
      };
    } catch (error) {
      return null;
    }
  }

  function writeSession(token, user) {
    var payload = {
      token: token,
      currentUser: JSON.stringify(user),
    };
    localStorage.setItem(SESSION_KEY, JSON.stringify(payload));
  }

  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
  }

  function isAuthenticated() {
    return Boolean(readSession());
  }

  function requireAuth() {
    if (!isAuthenticated()) {
      window.location.href = 'index.html';
      return false;
    }
    return true;
  }

  function redirectIfAuthenticated() {
    if (isAuthenticated()) {
      window.location.href = 'documents.html';
      return true;
    }
    return false;
  }

  function logout() {
    clearSession();
    window.location.href = 'index.html';
  }

  window.Auth = {
    readSession: readSession,
    writeSession: writeSession,
    clearSession: clearSession,
    isAuthenticated: isAuthenticated,
    requireAuth: requireAuth,
    redirectIfAuthenticated: redirectIfAuthenticated,
    logout: logout,
  };
})();
