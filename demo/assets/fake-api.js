(function () {
  var DATA_PATH = 'data/';

  function delay() {
    var ms = 300 + Math.floor(Math.random() * 301);
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  function fetchJson(fileName) {
    return fetch(DATA_PATH + fileName, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) {
        throw new Error('Не удалось загрузить ' + fileName);
      }
      return response.json();
    });
  }

  function withDelay(promiseFactory) {
    return delay().then(function () {
      return promiseFactory();
    });
  }

  function getUsers() {
    return withDelay(function () {
      return fetchJson('users.json');
    });
  }

  function getDocuments() {
    return withDelay(function () {
      return fetchJson('documents.json');
    });
  }

  function getLabels() {
    return withDelay(function () {
      return fetchJson('labels.json');
    });
  }

  function getAnnotations() {
    return withDelay(function () {
      return fetchJson('annotations.json');
    });
  }

  function getDocumentById(id) {
    return getDocuments().then(function (documents) {
      var numericId = Number(id);
      return documents.find(function (doc) {
        return Number(doc.id) === numericId;
      }) || null;
    });
  }

  function getAnnotationsByDocumentId(documentId) {
    return getAnnotations().then(function (annotations) {
      var numericId = Number(documentId);
      return annotations.filter(function (item) {
        return Number(item.document_id) === numericId;
      });
    });
  }

  function login(username, password) {
    return getUsers().then(function (users) {
      var user = users.find(function (item) {
        return item.username === username && item.password === password;
      });
      if (!user) {
        throw new Error('Неверное имя пользователя или пароль');
      }
      return user;
    });
  }

  window.FakeAPI = {
    login: login,
    getUsers: getUsers,
    getDocuments: getDocuments,
    getDocumentById: getDocumentById,
    getLabels: getLabels,
    getAnnotationsByDocumentId: getAnnotationsByDocumentId,
  };
})();
