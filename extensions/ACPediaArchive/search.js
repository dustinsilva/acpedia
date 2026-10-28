/* Extend MediaWiki's native accessible suggestions; retain its keyboard and link behavior. */
(function () {
    'use strict';
    var original = mw.searchSuggest.request;
    mw.searchSuggest.request = function (api, query, response, limit, namespace) {
        var clean = query.replace(/\*/g, '').trim().slice(0, 120);
        var maximum = Math.min(Number(limit) || 10, 20);
        var deferred = $.Deferred(), pending, cancelled = false;
        function finish(titles, meta) {
            if (!cancelled) {
                response(titles.slice(0, maximum), Object.assign({}, meta, {query: query}));
                deferred.resolve(titles);
            }
        }
        if (!clean) {
            finish([], {});
        } else {
            pending = original(api, clean, function (prefix, meta) {
                if (cancelled) { return; }
                if (prefix.length >= maximum || clean.length < 3) {
                    finish(prefix, meta);
                    return;
                }
                // SQL full-text title search supports word-prefix matching, so
                // 'ralir' can find 'Aun Ralirea' without a new search service.
                pending = api.get({
                    action: 'query', formatversion: 2, list: 'search',
                    srwhat: 'title', srsearch: clean + '*',
                    srnamespace: namespace || 0, srlimit: maximum,
                    srprop: ''
                }).done(function (data) {
                    var titles = prefix.slice();
                    (data.query && data.query.search || []).forEach(function (row) {
                        if (titles.indexOf(row.title) === -1) { titles.push(row.title); }
                    });
                    finish(titles, meta);
                }).fail(function () { finish(prefix, meta); });
            }, maximum, namespace).fail(function () { finish([], {}); });
        }
        return deferred.promise({abort: function () {
            cancelled = true;
            if (pending && pending.abort) { pending.abort(); }
            deferred.reject('abort');
        }});
    };
    $(function () {
        $('#searchInput, .mw-searchInput').attr('placeholder', 'Search titles — partial words work');
    });
}());
