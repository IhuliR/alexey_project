(function () {
  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function clearNode(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (typeof text === 'string') {
      node.textContent = text;
    }
    return node;
  }

  function formatDate(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return 'Дата неизвестна';
    }
    return date.toLocaleString();
  }

  function snippet(text, max) {
    var input = typeof text === 'string' ? text : '';
    var limit = typeof max === 'number' ? max : 140;
    if (input.length <= limit) {
      return input;
    }
    return input.slice(0, limit - 1) + '…';
  }

  function getQueryParam(name) {
    var url = new URL(window.location.href);
    return url.searchParams.get(name);
  }

  function setQueryParam(name, value) {
    var url = new URL(window.location.href);
    if (value === null || value === '') {
      url.searchParams.delete(name);
    } else {
      url.searchParams.set(name, value);
    }
    window.history.replaceState({}, '', url.toString());
  }

  function renderProtectedHeader(activePage) {
    var host = qs('#app-header');
    if (!host) {
      return;
    }

    clearNode(host);
    host.className = 'top-nav';

    var nav = el('nav', 'top-nav-links');
    var docs = el('a', activePage === 'documents' ? 'active' : '', 'Документы');
    docs.href = 'documents.html';

    var tags = el('a', activePage === 'tags' ? 'active' : '', 'Теги');
    tags.href = 'tags.html';

    var logout = el('button', 'logout-btn', 'Выход');
    logout.type = 'button';
    logout.addEventListener('click', function () {
      if (window.Auth) {
        window.Auth.logout();
      }
    });

    nav.appendChild(docs);
    nav.appendChild(tags);

    host.appendChild(nav);
    host.appendChild(logout);
  }

  window.DemoUtils = {
    qs: qs,
    qsa: qsa,
    el: el,
    clearNode: clearNode,
    formatDate: formatDate,
    snippet: snippet,
    getQueryParam: getQueryParam,
    setQueryParam: setQueryParam,
    renderProtectedHeader: renderProtectedHeader,
  };
})();
