(function () {
  var utils = window.DemoUtils;

  function randomToken() {
    return 'demo_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function init() {
    if (window.Auth.redirectIfAuthenticated()) {
      return;
    }

    var form = utils.qs('#login-form');
    var userInput = utils.qs('#username');
    var passInput = utils.qs('#password');
    var status = utils.qs('#login-status');
    var button = utils.qs('#login-button');

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      status.textContent = '';
      status.className = 'status-line';

      var username = userInput.value.trim();
      var password = passInput.value;

      if (!username || !password) {
        status.textContent = 'Введите имя пользователя и пароль.';
        status.classList.add('error');
        return;
      }

      button.disabled = true;
      status.textContent = 'Проверка учетных данных...';
      status.classList.add('loading');

      window.FakeAPI.login(username, password)
        .then(function (user) {
          window.Auth.writeSession(randomToken(), user);
          window.location.href = 'documents.html';
        })
        .catch(function (error) {
          status.textContent = error.message || 'Ошибка входа';
          status.className = 'status-line error';
        })
        .finally(function () {
          button.disabled = false;
        });
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
