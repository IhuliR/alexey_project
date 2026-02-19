(function () {
  var utils = window.DemoUtils;

  function getAnnotations() {
    return fetch('data/annotations.json', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) {
        throw new Error('Не удалось загрузить аннотации');
      }
      return response.json();
    });
  }

  function init() {
    if (!window.Auth.requireAuth()) {
      return;
    }

    utils.renderProtectedHeader('tags');

    var list = utils.qs('#tags-list');
    var status = utils.qs('#tags-status');

    status.textContent = 'Загрузка...';
    status.className = 'status-line loading';

    Promise.all([
      window.FakeAPI.getLabels(),
      window.FakeAPI.getDocuments(),
      getAnnotations(),
    ])
      .then(function (results) {
        var labels = results[0];
        var documents = results[1];
        var annotations = results[2];

        utils.clearNode(list);

        labels.forEach(function (label) {
          var documentCount = documents.filter(function (doc) {
            return (doc.label_ids || []).indexOf(label.id) !== -1;
          }).length;

          var annotationCount = annotations.filter(function (annotation) {
            return Number(annotation.label_id) === Number(label.id);
          }).length;

          var row = utils.el('article', 'tag-card');

          var heading = utils.el('a', 'tag-title', label.name);
          heading.href = 'documents.html?tag=' + encodeURIComponent(label.slug);

          var colorChip = utils.el('span', 'chip', label.color);
          colorChip.style.backgroundColor = label.color;

          var stats = utils.el(
            'p',
            'tag-stats',
            'Документы: ' + documentCount + ' | Аннотации: ' + annotationCount
          );

          row.appendChild(heading);
          row.appendChild(colorChip);
          row.appendChild(stats);
          list.appendChild(row);
        });

        status.textContent = '';
        status.className = 'status-line';
      })
      .catch(function (error) {
        status.textContent = error.message || 'Не удалось загрузить теги.';
        status.className = 'status-line error';
      });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
