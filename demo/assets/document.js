(function () {
  var utils = window.DemoUtils;

  function renderNotFound(message) {
    var view = utils.qs('#document-view');
    var missing = utils.qs('#document-missing');
    var messageNode = utils.qs('#missing-message');

    view.hidden = true;
    missing.hidden = false;
    messageNode.textContent = message || 'Документ не найден';
  }

  function validRange(content, start, end) {
    if (typeof content !== 'string') {
      return false;
    }
    var s = Number(start);
    var e = Number(end);
    if (!Number.isInteger(s) || !Number.isInteger(e)) {
      return false;
    }
    if (s < 0 || e <= s) {
      return false;
    }
    return e <= content.length;
  }

  function renderContent(container, content, activeAnnotation) {
    utils.clearNode(container);

    if (!activeAnnotation || !validRange(content, activeAnnotation.start, activeAnnotation.end)) {
      container.appendChild(document.createTextNode(content));
      return;
    }

    var start = Number(activeAnnotation.start);
    var end = Number(activeAnnotation.end);

    container.appendChild(document.createTextNode(content.slice(0, start)));

    var mark = utils.el('mark', 'active-highlight');
    mark.appendChild(document.createTextNode(content.slice(start, end)));
    container.appendChild(mark);

    container.appendChild(document.createTextNode(content.slice(end)));
  }

  function init() {
    if (!window.Auth.requireAuth()) {
      return;
    }

    utils.renderProtectedHeader('documents');

    var id = utils.getQueryParam('id');
    var documentId = Number(id);
    var status = utils.qs('#document-status');

    if (!id || !Number.isInteger(documentId) || documentId <= 0) {
      renderNotFound('Документ не найден');
      return;
    }

    status.textContent = 'Загрузка...';
    status.className = 'status-line loading';

    Promise.all([
      window.FakeAPI.getDocumentById(documentId),
      window.FakeAPI.getLabels(),
      window.FakeAPI.getAnnotationsByDocumentId(documentId),
    ])
      .then(function (results) {
        var doc = results[0];
        var labels = results[1];
        var annotations = results[2];

        if (!doc) {
          renderNotFound('Документ не найден');
          status.textContent = '';
          status.className = 'status-line';
          return;
        }

        var labelsById = labels.reduce(function (acc, label) {
          acc[label.id] = label;
          return acc;
        }, {});

        var view = utils.qs('#document-view');
        var missing = utils.qs('#document-missing');
        var title = utils.qs('#document-title');
        var created = utils.qs('#document-created');
        var tags = utils.qs('#document-tags');
        var contentNode = utils.qs('#document-content');
        var list = utils.qs('#annotation-list');
        var listEmpty = utils.qs('#annotation-empty');

        view.hidden = false;
        missing.hidden = true;

        title.textContent = doc.title || ('Документ #' + doc.id);
        created.textContent = utils.formatDate(doc.created_at);

        utils.clearNode(tags);
        (doc.label_ids || []).forEach(function (labelId) {
          var label = labelsById[labelId];
          if (!label) {
            return;
          }
          var chip = utils.el('span', 'chip', label.name);
          chip.style.backgroundColor = label.color;
          tags.appendChild(chip);
        });

        var activeId = null;

        function activeAnnotation() {
          if (activeId === null) {
            return null;
          }
          return annotations.find(function (annotation) {
            return Number(annotation.id) === Number(activeId);
          }) || null;
        }

        function renderList() {
          utils.clearNode(list);

          if (!annotations.length) {
            listEmpty.hidden = false;
            return;
          }

          listEmpty.hidden = true;

          annotations.forEach(function (annotation) {
            var li = utils.el('li', 'annotation-row');

            var button = utils.el('button', 'annotation-link', annotation.text || 'Аннотация');
            button.type = 'button';
            button.addEventListener('click', function () {
              if (activeId === annotation.id) {
                activeId = null;
              } else {
                activeId = annotation.id;
              }
              renderContent(contentNode, doc.content, activeAnnotation());
              renderList();
            });

            if (activeId === annotation.id) {
              button.classList.add('is-active');
            }

            var label = labelsById[annotation.label_id];
            var chip = utils.el('span', 'chip', label ? label.name : 'Неизвестно');
            if (label && label.color) {
              chip.style.backgroundColor = label.color;
            }

            var noteText = annotation.note ? annotation.note : 'Без заметки';
            var note = utils.el('span', 'annotation-note', noteText);

            li.appendChild(button);
            li.appendChild(chip);
            li.appendChild(note);
            list.appendChild(li);
          });
        }

        renderContent(contentNode, doc.content, null);
        renderList();

        status.textContent = '';
        status.className = 'status-line';
      })
      .catch(function (error) {
        status.textContent = error.message || 'Не удалось загрузить документ.';
        status.className = 'status-line error';
      });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
