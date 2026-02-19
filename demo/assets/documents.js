(function () {
  var utils = window.DemoUtils;
  var FILTERS_KEY = 'demo.documents.filters';

  function loadSavedFilters() {
    var fallback = { sort: 'newest', tag: '' };
    try {
      var raw = localStorage.getItem(FILTERS_KEY);
      if (!raw) {
        return fallback;
      }
      var parsed = JSON.parse(raw);
      return {
        sort: parsed.sort === 'oldest' ? 'oldest' : 'newest',
        tag: typeof parsed.tag === 'string' ? parsed.tag : '',
      };
    } catch (error) {
      return fallback;
    }
  }

  function saveFilters(sort, tag) {
    localStorage.setItem(FILTERS_KEY, JSON.stringify({ sort: sort, tag: tag }));
  }

  function buildLabelMap(labels) {
    return labels.reduce(function (acc, label) {
      acc[label.id] = label;
      return acc;
    }, {});
  }

  function countAnnotationsByDocument(documents, labels) {
    var map = {};
    documents.forEach(function (doc) {
      map[doc.id] = 0;
    });
    return window.FakeAPI.getDocuments().then(function () {
      return fetch('data/annotations.json', { cache: 'no-store' });
    }).then(function (response) {
      if (!response.ok) {
        throw new Error('Не удалось загрузить аннотации');
      }
      return response.json();
    }).then(function (annotations) {
      annotations.forEach(function (item) {
        if (typeof map[item.document_id] === 'number') {
          map[item.document_id] += 1;
        }
      });
      return map;
    }).catch(function () {
      return map;
    });
  }

  function renderTagFilter(labels, activeTag) {
    var select = utils.qs('#tag-filter');
    utils.clearNode(select);

    var allOption = utils.el('option', '', 'Все теги');
    allOption.value = '';
    select.appendChild(allOption);

    labels.forEach(function (label) {
      var option = utils.el('option', '', label.name);
      option.value = label.slug;
      select.appendChild(option);
    });

    select.value = activeTag || '';
  }

  function renderDocuments(documents, labelsById, annotationCountMap) {
    var list = utils.qs('#documents-list');
    var empty = utils.qs('#documents-empty');
    utils.clearNode(list);

    if (!documents.length) {
      empty.hidden = false;
      return;
    }

    empty.hidden = true;

    documents.forEach(function (doc) {
      var item = utils.el('article', 'doc-card');

      var top = utils.el('div', 'doc-card-top');
      var titleLink = utils.el('a', 'doc-title', doc.title || ('Документ #' + doc.id));
      titleLink.href = 'document.html?id=' + encodeURIComponent(String(doc.id));
      var created = utils.el('span', 'doc-date', utils.formatDate(doc.created_at));
      top.appendChild(titleLink);
      top.appendChild(created);

      var meta = utils.el('div', 'doc-meta');
      meta.appendChild(utils.el('span', 'meta-pill', 'Аннотации: ' + (annotationCountMap[doc.id] || 0)));

      var chips = utils.el('div', 'chip-row');
      (doc.label_ids || []).forEach(function (labelId) {
        var label = labelsById[labelId];
        if (!label) {
          return;
        }
        var chip = utils.el('span', 'chip', label.name);
        chip.style.backgroundColor = label.color;
        chips.appendChild(chip);
      });

      var snippet = utils.el('p', 'doc-snippet', utils.snippet(doc.content, 180));

      item.appendChild(top);
      item.appendChild(meta);
      item.appendChild(chips);
      item.appendChild(snippet);
      list.appendChild(item);
    });
  }

  function applyFilters(documents, labelsBySlug, searchText, tagSlug, sortValue) {
    var query = searchText.trim().toLowerCase();

    var filtered = documents.filter(function (doc) {
      var title = (doc.title || '').toLowerCase();
      var text = utils.snippet(doc.content || '', 200).toLowerCase();

      var matchesSearch = !query || title.indexOf(query) !== -1 || text.indexOf(query) !== -1;
      var matchesTag = true;

      if (tagSlug) {
        var label = labelsBySlug[tagSlug];
        matchesTag = Boolean(label && (doc.label_ids || []).indexOf(label.id) !== -1);
      }

      return matchesSearch && matchesTag;
    });

    filtered.sort(function (a, b) {
      var ad = new Date(a.created_at).getTime();
      var bd = new Date(b.created_at).getTime();
      if (sortValue === 'oldest') {
        return ad - bd;
      }
      return bd - ad;
    });

    return filtered;
  }

  function init() {
    if (!window.Auth.requireAuth()) {
      return;
    }

    utils.renderProtectedHeader('documents');

    var searchInput = utils.qs('#search-input');
    var sortSelect = utils.qs('#sort-select');
    var tagSelect = utils.qs('#tag-filter');
    var status = utils.qs('#documents-status');

    var state = {
      documents: [],
      labels: [],
      labelsById: {},
      labelsBySlug: {},
      annotationCount: {},
      search: '',
      sort: 'newest',
      tag: '',
    };

    var saved = loadSavedFilters();
    state.sort = saved.sort;
    state.tag = saved.tag;

    var queryTag = utils.getQueryParam('tag');
    if (queryTag) {
      state.tag = queryTag;
    }

    sortSelect.value = state.sort;

    function rerender() {
      saveFilters(state.sort, state.tag);
      utils.setQueryParam('tag', state.tag || null);

      var docs = applyFilters(
        state.documents,
        state.labelsBySlug,
        state.search,
        state.tag,
        state.sort
      );
      renderDocuments(docs, state.labelsById, state.annotationCount);
    }

    status.textContent = 'Загрузка...';
    status.className = 'status-line loading';

    Promise.all([
      window.FakeAPI.getDocuments(),
      window.FakeAPI.getLabels(),
    ])
      .then(function (results) {
        var documents = results[0];
        var labels = results[1];

        state.documents = documents;
        state.labels = labels;
        state.labelsById = buildLabelMap(labels);
        state.labelsBySlug = labels.reduce(function (acc, label) {
          acc[label.slug] = label;
          return acc;
        }, {});

        renderTagFilter(labels, state.tag);

        return countAnnotationsByDocument(documents, labels).then(function (counts) {
          state.annotationCount = counts;
          status.textContent = '';
          status.className = 'status-line';
          rerender();
        });
      })
      .catch(function (error) {
        status.textContent = error.message || 'Не удалось загрузить документы.';
        status.className = 'status-line error';
      });

    searchInput.addEventListener('input', function () {
      state.search = searchInput.value;
      rerender();
    });

    sortSelect.addEventListener('change', function () {
      state.sort = sortSelect.value === 'oldest' ? 'oldest' : 'newest';
      rerender();
    });

    tagSelect.addEventListener('change', function () {
      state.tag = tagSelect.value;
      rerender();
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
