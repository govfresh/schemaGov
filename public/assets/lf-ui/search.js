// Site search — fetches /search.json (built at generation time from the
// same _data every page is generated from, see _data/searchIndex.js) and
// builds a Lunr index client-side. The index is small (one entry per
// profile, code list, standard, and static page — a few hundred, not one
// per term-value page), so search-as-you-type is instant and there's no
// need for a submit step; the URL's `?q=` still works for a direct link
// straight to a result set.
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('search-form');
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if (!form || !input || !results) return;

  let idx;
  let documents = [];

  function categoryFor(url) {
    if (url.startsWith('/profiles/')) return 'Profile';
    if (url.startsWith('/v1/')) return 'Vocabulary';
    if (url.startsWith('/standards/')) return 'Standard';
    return 'Page';
  }

  function excerpt(body, term) {
    const clean = body.trim();
    if (!clean) return '';
    const i = clean.toLowerCase().indexOf(term.toLowerCase());
    const start = i > 40 ? i - 40 : 0;
    const snippet = clean.slice(start, start + 160);
    return (start > 0 ? '…' : '') + snippet + (start + 160 < clean.length ? '…' : '');
  }

  function render(term) {
    if (!term) {
      results.innerHTML = '';
      return;
    }
    if (!idx) return;
    const words = term
      .replace(/[*:^~+-]/g, ' ')
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .map(function (w) { return w + '*'; });
    if (!words.length) {
      results.innerHTML = '';
      return;
    }
    let hits;
    try {
      hits = idx.search(words.join(' '));
    } catch (e) {
      hits = [];
    }
    if (!hits.length) {
      results.innerHTML = '<p class="text-body-secondary">No results for "' + term + '".</p>';
      return;
    }
    results.innerHTML =
      '<p class="text-body-secondary mb-3">' + hits.length + ' result' + (hits.length === 1 ? '' : 's') + '</p>' +
      '<div class="list-group">' +
      hits
        .map(function (hit) {
          const doc = documents[Number(hit.ref)];
          return (
            '<a href="' + doc.url + '" class="list-group-item list-group-item-action">' +
            '<div class="d-flex justify-content-between align-items-start gap-3">' +
            '<span class="h6 mb-1">' + doc.title + '</span>' +
            '<span class="badge text-bg-secondary">' + categoryFor(doc.url) + '</span>' +
            '</div>' +
            '<p class="mb-1 small text-body-secondary">' + excerpt(doc.body, term) + '</p>' +
            '<p class="mb-0 small font-secondary">' + doc.url + '</p>' +
            '</a>'
          );
        })
        .join('') +
      '</div>';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
  });
  input.addEventListener('input', function () {
    render(input.value);
  });

  fetch('/search.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      documents = data;
      idx = lunr(function () {
        this.ref('id');
        this.field('title', { boost: 10 });
        this.field('body');
        // Search-as-you-type means every query is a wildcard prefix
        // ("ocds*"), and Lunr's wildcard matching skips the stemmer at
        // query time even though stemming still ran at index time - so a
        // word the stemmer shortens (it turns "ocds" into "ocd") stops
        // matching its own prefix. Most of what's searched here is
        // identifiers and acronyms (electoralSystem, OCDS, fptp) anyway,
        // where English stemming was never buying anything.
        this.pipeline.remove(lunr.stemmer);
        this.searchPipeline.remove(lunr.stemmer);
        data.forEach(function (doc) { this.add(doc); }, this);
      });
      const params = new URLSearchParams(location.search);
      if (params.has('q')) {
        const q = params.get('q');
        input.value = q;
        render(q);
      }
    });
});
