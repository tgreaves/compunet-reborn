/* Directory tree: fill panels in place instead of navigating (#121).
 *
 * ⚠ THE SITE'S ONLY SCRIPT, and deliberately an enhancement rather than a
 * dependency. Every control it touches is a real link that works without it:
 * VIEW goes to the page's own screen, CHANGE reloads the tree with that entry's
 * controls rendered inline by the server. Turn scripting off and the site behaves
 * as it did before this file existed.
 *
 * Why it exists at all, on a site that had no JavaScript: the alternative was
 * rendering every entry's frame panel and edit controls up front. Measured on a
 * 30-entry fixture that was 61% of a 183 KB page, and the move <select> made it
 * O(n^2) — every entry listing every eligible destination. Production carries 386
 * entries. Fetching one fragment on click is the difference between a page that
 * grows with the tree and one that does not.
 *
 * The fragments are server-rendered HTML, not JSON: no templating here, and no
 * second description of a form to keep in step with the first.
 */
(function () {
    'use strict';

    var pane = document.querySelector('.frame-pane');
    var tree = document.querySelector('.tree');
    if (!pane || !tree) { return; }

    var idle = pane.querySelector('.frame-pane-idle');

    function fail(where, message) {
        /* Say so rather than leaving an empty box. The link still works, so
         * pointing at it is a real way out. */
        where.innerHTML = '<p class="hint">' + message + '</p>';
    }

    function load(url, into, done) {
        into.innerHTML = '<p class="hint">Loading…</p>';
        fetch(url, { credentials: 'same-origin' })
            .then(function (r) {
                if (!r.ok) { throw new Error(r.status); }
                return r.text();
            })
            .then(function (html) {
                into.innerHTML = html;
                if (done) { done(); }
            })
            .catch(function () {
                fail(into, 'Could not load that. Use the link to open it on its own page.');
            });
    }

    tree.addEventListener('click', function (ev) {
        var link = ev.target.closest('a[data-view], a[data-edit], a[data-header]');
        if (!link) { return; }
        /* Let modified clicks do what the user asked — open in a new tab, etc. */
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button !== 0) { return; }
        ev.preventDefault();

        /* VIEW and HEADER both fill the side pane — one shows what a page holds,
         * the other what a directory draws above its listing. Only ever one at a
         * time, which is why they share it. */
        var num = link.getAttribute('data-view');
        if (num) {
            if (idle) { idle.hidden = true; }
            load('/pages/' + num + '/panel', pane);
            return;
        }

        num = link.getAttribute('data-header');
        if (num) {
            if (idle) { idle.hidden = true; }
            load('/directories/' + num + '/panel', pane);
            return;
        }

        num = link.getAttribute('data-edit');
        var row = link.closest('.tree-row');
        var existing = row.parentNode.querySelector('.tree-edit-body[data-for="' + num + '"]');
        if (existing) {                       /* second click closes it */
            existing.remove();
            return;
        }
        var box = document.createElement('div');
        box.className = 'tree-edit-body';
        box.setAttribute('data-for', num);
        row.parentNode.insertBefore(box, row.nextSibling);
        load('/pages/' + num + '/controls', box);
    });

    pane.addEventListener('click', function (ev) {
        if (!ev.target.closest('[data-close]')) { return; }
        ev.preventDefault();
        pane.innerHTML = '';
        pane.appendChild(idle || document.createTextNode(''));
        if (idle) { idle.hidden = false; }
    });
}());
