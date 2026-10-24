/* Zeigt die neuesten Beiträge aus mysteriendramen.ch und karmaforschung.ch
   (nur Beiträge, deren Datum erreicht ist).
   Liest die RSS-Feeds beider Blogs; ohne JavaScript bleiben die Links darunter stehen. */
(function () {
  var box = document.getElementById('neue-beitraege-liste');
  if (!box || !window.fetch || !window.DOMParser) return;
  var feeds = [
    { url: 'https://mysteriendramen.ch/feed.xml', blog: 'mysteriendramen.ch' },
    { url: 'https://karmaforschung.ch/feed.xml', blog: 'karmaforschung.ch' }
  ];
  var fmt = new Intl.DateTimeFormat('de-CH', { day: 'numeric', month: 'long', year: 'numeric' });
  Promise.all(feeds.map(function (f) {
    return fetch(f.url).then(function (r) { return r.ok ? r.text() : ''; }).then(function (t) {
      if (!t) return [];
      var doc = new DOMParser().parseFromString(t, 'application/xml');
      return Array.prototype.map.call(doc.querySelectorAll('item'), function (it) {
        var get = function (n) { var e = it.querySelector(n); return e ? e.textContent.trim() : ''; };
        return { title: get('title'), link: get('link'), date: new Date(get('pubDate')), text: get('description'), blog: f.blog };
      });
    }).catch(function () { return []; });
  })).then(function (lists) {
    var now = new Date();
    var items = [].concat.apply([], lists).filter(function (i) { return i.title && i.link && !isNaN(i.date) && i.date <= now; });
    if (!items.length) return;
    items.sort(function (a, b) { return b.date - a.date; });
    var ul = document.createElement('ul');
    ul.className = 'post-teaser';
    items.slice(0, 3).forEach(function (i) {
      var li = document.createElement('li');
      var meta = document.createElement('div'); meta.className = 'meta';
      meta.textContent = fmt.format(i.date) + ' · ' + i.blog;
      var h = document.createElement('h3'); var a = document.createElement('a');
      a.href = i.link; a.textContent = i.title; h.appendChild(a);
      var p = document.createElement('p'); p.textContent = i.text;
      li.appendChild(meta); li.appendChild(h); li.appendChild(p); ul.appendChild(li);
    });
    box.innerHTML = '';
    box.appendChild(ul);
  });
})();
