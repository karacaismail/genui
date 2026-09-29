(function () {
  'use strict';
  var d = document, root = d.documentElement;
  var DATA = JSON.parse(d.getElementById('kitap-veri').textContent);
  var Q = DATA.sorular, CH = DATA.bolumler, META = DATA.meta, ICON = DATA.ikonlar;
  var KEY = 'genui-karar-kitabi-v1';
  var byId = {};
  Q.forEach(function (q) { byId[q.id] = q; });
  var chTitle = {};
  CH.forEach(function (c) { chTitle[c.id] = c.baslik; });

  /* ---------- state ---------- */
  var state = { answers: {} };
  try {
    var raw = localStorage.getItem(KEY);
    if (raw) { var parsed = JSON.parse(raw); if (parsed && parsed.answers) state = parsed; }
  } catch (e) { /* storage unavailable: the page still works without it */ }
  function ans(id) {
    if (!state.answers[id]) state.answers[id] = { sel: [], custom: '', note: '', deferred: false, src: null, at: null };
    return state.answers[id];
  }
  var saveTimer = null;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var ok = true;
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { ok = false; }
      var el = d.getElementById('saved');
      if (el) {
        var t = new Date();
        el.textContent = ok ? 'Bu tarayıcıda kaydedildi · ' + String(t.getHours()).padStart(2, '0') + ':' + String(t.getMinutes()).padStart(2, '0')
                            : 'Tarayıcı kaydı kapalı; bitirince JSON indir';
      }
    }, 250);
  }

  function visible(q) {
    if (!q.goster) return true;
    var dep = state.answers[q.goster.soru];
    var sel = dep ? dep.sel : [];
    var want = [].concat(q.goster.iceren);
    return want.some(function (v) { return sel.indexOf(v) !== -1; });
  }
  function status(q) {
    if (!visible(q)) return 'na';
    var a = state.answers[q.id];
    if (a && a.sel.length) return 'answered';
    if (a && a.deferred) return 'deferred';
    return 'empty';
  }
  function matchesRec(q) {
    var a = state.answers[q.id];
    if (!q.oneri.length || !a || !a.sel.length) return null;
    var s = a.sel.slice().sort().join('|'), r = q.oneri.slice().sort().join('|');
    return s === r;
  }

  /* ---------- helpers ---------- */
  function el(tag, attrs, kids) {
    var n = d.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else if (k === 'cls') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === 'string' ? d.createTextNode(c) : c); });
    return n;
  }
  function icon(name) { var s = el('span', { html: ICON[name] || '' }); return s.firstChild; }
  function labelsOf(q, ids) {
    return ids.map(function (id) { var o = q.secenekler.filter(function (x) { return x.id === id; })[0]; return o ? o.etiket : id; });
  }

  /* ---------- render ---------- */
  var main = d.getElementById('main');
  var chNav = d.getElementById('chapters');
  var cards = {};

  CH.forEach(function (c, ci) {
    var qs = Q.filter(function (q) { return q.bolum === c.id; });
    var sec = el('section', { cls: 'chapter', id: 'b-' + c.id, 'aria-labelledby': 'b-' + c.id + '-h' });
    sec.appendChild(el('header', null, [
      el('span', { cls: 'num', text: 'Bölüm ' + String(ci + 1).padStart(2, '0') + ' · ' + qs.length + ' soru' }),
      el('h2', { id: 'b-' + c.id + '-h', text: c.baslik }),
      el('p', { text: c.aciklama })
    ]));
    qs.forEach(function (q) { var card = renderQ(q); cards[q.id] = card; sec.appendChild(card); });
    sec.appendChild(el('p', { cls: 'empty-filter', hidden: 'hidden', text: 'Bu filtrede bu bölümde gösterilecek soru yok.' }));
    main.insertBefore(sec, d.getElementById('bitir'));

    var a = el('a', { href: '#b-' + c.id, 'data-ch': c.id }, [el('span', { text: c.baslik }), el('span', { cls: 'c' })]);
    chNav.appendChild(el('li', null, [a]));
  });

  function renderQ(q) {
    var art = el('article', { cls: 'q', id: q.id, 'data-id': q.id });
    var stateEl = el('span', { cls: 'q-state' });
    art.appendChild(el('div', { cls: 'q-head' }, [
      el('span', { cls: 'qid', text: q.id }),
      el('span', { cls: 'chip ' + q.oncelik.toLowerCase(), text: q.oncelik === 'P1' ? 'P1 · önce karar' : 'P2 · plan kesinleşirken' }),
      el('span', { cls: 'chip' + (q.kime === 'sen' ? '' : ' tek'), text: q.kime === 'sen' ? 'Ürün kararı · sen' : 'Teknik varsayılan · onay yeterli' }),
      el('span', { cls: 'chip', text: q.tip === 'cok' ? 'Birden fazla seçilebilir' : 'Tek seçim' }),
      stateEl
    ]));
    art.appendChild(el('h3', { id: q.id + '-t', text: q.soru }));
    art.appendChild(el('p', { cls: 'why' }, [el('b', { text: 'Neden soruluyor? ' }), q.neden]));
    var refs = el('div', { cls: 'refs' }, [el('span', { cls: 'k', text: 'Kaynak:' })]);
    q.kaynak.forEach(function (k) { refs.appendChild(el('code', { text: k })); });
    if (q.etkiler.length) {
      refs.appendChild(el('span', { cls: 'k', text: ' Etkilediği:' }));
      q.etkiler.forEach(function (k) { refs.appendChild(el('code', { text: k })); });
    }
    art.appendChild(refs);

    var fs = el('fieldset', { cls: 'opts' + (q.tip === 'cok' && q.secenekler.length > 4 ? ' many' : ''), 'aria-labelledby': q.id + '-t' });
    var type = q.tip === 'cok' ? 'checkbox' : 'radio';
    q.secenekler.forEach(function (o) {
      var inp = el('input', { type: type, name: 'q-' + q.id, value: o.id, 'aria-describedby': q.id + '-' + o.id + '-d' });
      var top = el('div', { cls: 'opt-top' }, [el('span', { cls: 'opt-label', text: o.etiket })]);
      if (q.oneri.indexOf(o.id) !== -1) top.appendChild(el('span', { cls: 'badge-rec' }, [icon('star'), 'Önerilen']));
      var body = el('div', { cls: 'opt-body' }, [
        top,
        el('p', { cls: 'desc', id: q.id + '-' + o.id + '-d', text: o.aciklama }),
        el('div', { cls: 'ex' }, [icon('lightbulb'), el('span', null, [el('b', { text: 'Gerçek dünyada: ' }), o.ornek])]),
        el('p', { cls: 'eff' }, [el('b', { text: 'Seçersen: ' }), o.sonuc])
      ]);
      var lab = el('label', { cls: 'opt' }, [inp, body]);
      inp.addEventListener('change', function () {
        var a = ans(q.id);
        if (type === 'radio') a.sel = [o.id];
        else {
          var i = a.sel.indexOf(o.id);
          if (inp.checked && i === -1) a.sel.push(o.id);
          if (!inp.checked && i !== -1) a.sel.splice(i, 1);
        }
        a.deferred = false; a.src = 'user'; a.at = new Date().toISOString();
        save(); update();
      });
      fs.appendChild(lab);
    });
    art.appendChild(fs);

    if (q.oneri.length) {
      art.appendChild(el('div', { cls: 'rec-why' }, [icon('star'), el('span', null, [el('b', { text: 'Neden öneriyoruz: ' }), q.oneri_neden])]));
    } else if (q.oneri_neden) {
      art.appendChild(el('div', { cls: 'rec-why' }, [icon('info'), el('span', null, [el('b', { text: 'Önerimiz yok: ' }), q.oneri_neden])]));
    }

    if (q.serbest) {
      var ci = el('input', { type: 'text', id: q.id + '-custom', autocomplete: 'off' });
      ci.addEventListener('input', function () { var a = ans(q.id); a.custom = ci.value; a.at = new Date().toISOString(); save(); });
      art.appendChild(el('label', { cls: 'custom', for: q.id + '-custom' }, ['Diğer veya ek açıklama (isteğe bağlı)', ci]));
    }

    var actions = el('div', { cls: 'q-actions' });
    if (q.oneri.length) {
      var br = el('button', { type: 'button', cls: 'btn' }, [icon('star'), 'Önerileni seç']);
      br.addEventListener('click', function () {
        var a = ans(q.id); a.sel = q.oneri.slice(); a.deferred = false; a.src = 'user'; a.at = new Date().toISOString();
        save(); update();
      });
      actions.appendChild(br);
    }
    var bd = el('button', { type: 'button', cls: 'btn', 'aria-pressed': 'false', 'data-role': 'defer' }, [icon('hourglass-medium'), 'Sonra karar vereceğim']);
    bd.addEventListener('click', function () {
      var a = ans(q.id); var on = !a.deferred;
      a.deferred = on; if (on) { a.sel = []; a.src = null; }
      a.at = new Date().toISOString(); save(); update();
    });
    actions.appendChild(bd);
    var note = el('textarea', { cls: 'note', id: q.id + '-note', hidden: 'hidden', 'aria-label': q.id + ' için not' });
    note.addEventListener('input', function () { var a = ans(q.id); a.note = note.value; a.at = new Date().toISOString(); save(); });
    var bn = el('button', { type: 'button', cls: 'btn ghost', 'aria-expanded': 'false', 'aria-controls': q.id + '-note' }, [icon('note-pencil'), 'Not ekle']);
    bn.addEventListener('click', function () {
      var open = note.hidden; note.hidden = !open; bn.setAttribute('aria-expanded', String(open));
      if (open) note.focus();
    });
    actions.appendChild(bn);
    art.appendChild(actions);
    art.appendChild(note);
    art._state = stateEl; art._defer = bd; art._note = note; art._noteBtn = bn;
    return art;
  }

  /* ---------- view update ---------- */
  var filter = 'all';
  function update() {
    var counts = { total: 0, answered: 0, deferred: 0, empty: 0, na: 0, p1left: 0 };
    var chCounts = {};
    Q.forEach(function (q) {
      var card = cards[q.id], st = status(q), a = state.answers[q.id];
      card.dataset.state = st;
      card.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(function (inp) {
        inp.checked = !!(a && a.sel.indexOf(inp.value) !== -1);
      });
      var ci = card.querySelector('.custom input'); if (ci && d.activeElement !== ci) ci.value = a ? a.custom || '' : '';
      if (d.activeElement !== card._note) card._note.value = a ? a.note || '' : '';
      if (a && a.note && card._note.hidden) { card._note.hidden = false; card._noteBtn.setAttribute('aria-expanded', 'true'); }
      card._defer.setAttribute('aria-pressed', String(!!(a && a.deferred)));
      card._state.innerHTML = '';
      if (st === 'answered') { card._state.appendChild(icon('check-circle')); card._state.appendChild(d.createTextNode(a.src === 'bulk' ? 'Önerilenle dolduruldu' : 'Cevaplandı')); }
      else if (st === 'deferred') { card._state.appendChild(icon('hourglass-medium')); card._state.appendChild(d.createTextNode('Ertelendi')); }
      else { card._state.appendChild(icon('circle-dashed')); card._state.appendChild(d.createTextNode('Cevap bekliyor')); }

      var c = chCounts[q.bolum] || (chCounts[q.bolum] = { vis: 0, done: 0 });
      if (st === 'na') { counts.na++; }
      else {
        counts.total++; c.vis++;
        counts[st]++;
        if (st !== 'empty') c.done++;
        if (st === 'empty' && q.oncelik === 'P1') counts.p1left++;
      }
      var show = st !== 'na';
      if (show && filter === 'p1') show = q.oncelik === 'P1';
      if (show && filter === 'empty') show = st === 'empty';
      if (show && filter === 'deferred') show = st === 'deferred';
      if (show && filter === 'differs') show = matchesRec(q) === false;
      card.hidden = !show;
    });
    d.querySelectorAll('.chapter').forEach(function (sec) {
      var any = [].some.call(sec.querySelectorAll('.q'), function (c) { return !c.hidden; });
      sec.querySelector('.empty-filter').hidden = any;
    });
    CH.forEach(function (c) {
      var a = chNav.querySelector('a[data-ch="' + c.id + '"]'); var cc = chCounts[c.id] || { vis: 0, done: 0 };
      a.querySelector('.c').textContent = cc.done + '/' + cc.vis;
      a.classList.toggle('done', cc.vis > 0 && cc.done === cc.vis);
    });
    var pct = function (n) { return counts.total ? (100 * n / counts.total).toFixed(2) + '%' : '0%'; };
    d.getElementById('p-answered').textContent = counts.answered;
    d.getElementById('p-total').textContent = counts.total;
    d.getElementById('p-deferred').textContent = counts.deferred;
    d.getElementById('p-p1').textContent = counts.p1left;
    d.getElementById('t-a').style.width = pct(counts.answered);
    d.getElementById('t-d').style.width = pct(counts.deferred);
    d.getElementById('progress').setAttribute('aria-valuenow', String(counts.answered + counts.deferred));
    d.getElementById('progress').setAttribute('aria-valuemax', String(counts.total));
    renderFinish(counts);
  }

  function renderFinish(counts) {
    var bulk = 0, differs = 0;
    Q.forEach(function (q) {
      var a = state.answers[q.id];
      if (status(q) === 'answered' && a.src === 'bulk') bulk++;
      if (matchesRec(q) === false) differs++;
    });
    d.getElementById('s-answered').textContent = counts.answered;
    d.getElementById('s-deferred').textContent = counts.deferred;
    d.getElementById('s-empty').textContent = counts.empty;
    d.getElementById('s-p1').textContent = counts.p1left;
    d.getElementById('s-bulk').textContent = bulk;
    d.getElementById('s-differs').textContent = differs;
    var todo = d.getElementById('todo'); todo.innerHTML = '';
    Q.forEach(function (q) {
      if (status(q) === 'empty' && q.oncelik === 'P1') todo.appendChild(el('a', { href: '#' + q.id, text: q.id }));
    });
    d.getElementById('todo-wrap').hidden = !todo.children.length;
  }

  /* ---------- filters ---------- */
  var segBtns = [].slice.call(d.querySelectorAll('#filtre button'));
  segBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      filter = b.getAttribute('data-f');
      segBtns.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      update();
    });
  });

  /* ---------- export / import ---------- */
  function buildExport() {
    var list = Q.map(function (q) {
      var a = state.answers[q.id] || { sel: [], custom: '', note: '', deferred: false, src: null, at: null };
      var st = status(q);
      return {
        id: q.id, chapter: q.bolum, chapterTitle: chTitle[q.bolum], priority: q.oncelik,
        decisionOwner: q.kime === 'sen' ? 'product-owner' : 'technical-default',
        question: q.soru,
        status: { answered: 'answered', deferred: 'deferred', empty: 'unanswered', na: 'not_applicable' }[st],
        selected: st === 'answered' ? a.sel.slice() : [],
        selectedLabels: st === 'answered' ? labelsOf(q, a.sel) : [],
        recommended: q.oneri.slice(), recommendedLabels: labelsOf(q, q.oneri),
        matchesRecommendation: st === 'answered' ? matchesRec(q) : null,
        source: st === 'answered' ? (a.src || 'user') : null,
        customText: a.custom || '', note: a.note || '',
        affects: q.etkiler.slice(), sources: q.kaynak.slice(),
        answeredAt: a.at || null
      };
    });
    var s = { total: 0, answered: 0, deferred: 0, unanswered: 0, notApplicable: 0, bulkRecommended: 0, differsFromRecommendation: 0, p1Unanswered: [] };
    list.forEach(function (x) {
      if (x.status === 'not_applicable') { s.notApplicable++; return; }
      s.total++;
      if (x.status === 'answered') s.answered++;
      if (x.status === 'deferred') s.deferred++;
      if (x.status === 'unanswered') { s.unanswered++; if (x.priority === 'P1') s.p1Unanswered.push(x.id); }
      if (x.source === 'bulk') s.bulkRecommended++;
      if (x.matchesRecommendation === false) s.differsFromRecommendation++;
    });
    return { kind: 'genui-karar-kitabi-yanitlari', schemaVersion: 1, book: META, exportedAt: new Date().toISOString(), summary: s, answers: list };
  }
  function fileName() {
    var t = new Date(), p = function (n) { return String(n).padStart(2, '0'); };
    return 'genui-karar-kitabi-' + t.getFullYear() + p(t.getMonth() + 1) + p(t.getDate()) + '-' + p(t.getHours()) + p(t.getMinutes()) + '.json';
  }
  function download() {
    var txt = JSON.stringify(buildExport(), null, 2);
    var out = d.getElementById('json-out'); out.value = txt;
    try {
      var blob = new Blob([txt], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = el('a', { href: url, download: fileName() });
      d.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      announce('JSON dosyası indirildi: ' + a.download);
    } catch (e) {
      announce('İndirme bu ortamda engellendi; aşağıdaki metni kopyala.');
    }
  }
  function announce(msg) { var s = d.getElementById('duyuru'); s.textContent = ''; setTimeout(function () { s.textContent = msg; }, 30); }
  [].forEach.call(d.querySelectorAll('[data-act="export"]'), function (b) { b.addEventListener('click', download); });
  d.getElementById('copy').addEventListener('click', function () {
    var out = d.getElementById('json-out'); out.value = JSON.stringify(buildExport(), null, 2);
    var done = function () { announce('JSON panoya kopyalandı.'); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(out.value).then(done, function () { out.select(); announce('Metin seçildi; kopyalayabilirsin.'); });
    else { out.select(); announce('Metin seçildi; kopyalayabilirsin.'); }
  });
  var fileInp = d.getElementById('import-file');
  [].forEach.call(d.querySelectorAll('[data-act="import"]'), function (b) { b.addEventListener('click', function () { fileInp.click(); }); });
  fileInp.addEventListener('change', function () {
    var f = fileInp.files && fileInp.files[0]; if (!f) return;
    var r = new FileReader();
    r.onload = function () {
      try {
        var data = JSON.parse(r.result);
        if (data.kind !== 'genui-karar-kitabi-yanitlari' || !Array.isArray(data.answers)) throw new Error('kind');
        var n = 0;
        data.answers.forEach(function (x) {
          var q = byId[x.id]; if (!q) return;
          var valid = (x.selected || []).filter(function (id) { return q.secenekler.some(function (o) { return o.id === id; }); });
          state.answers[x.id] = { sel: valid, custom: x.customText || '', note: x.note || '', deferred: x.status === 'deferred', src: x.source || (valid.length ? 'user' : null), at: x.answeredAt || null };
          n++;
        });
        save(); update(); announce(n + ' cevap yüklendi.');
      } catch (e) { announce('Bu dosya karar kitabı cevap dosyası değil.'); }
      fileInp.value = '';
    };
    r.readAsText(f);
  });

  /* ---------- bulk fill and reset (two-step confirmation) ---------- */
  function armed(btn, label, run) {
    var orig = btn.innerHTML, timer = null;
    btn.addEventListener('click', function () {
      if (btn.getAttribute('data-armed') === 'true') {
        clearTimeout(timer); btn.setAttribute('data-armed', 'false'); btn.innerHTML = orig; run(); return;
      }
      btn.setAttribute('data-armed', 'true'); btn.textContent = label(); announce(btn.textContent);
      timer = setTimeout(function () { btn.setAttribute('data-armed', 'false'); btn.innerHTML = orig; }, 5000);
    });
  }
  function emptyWithRec() { return Q.filter(function (q) { return status(q) === 'empty' && q.oneri.length; }); }
  armed(d.getElementById('bulk'), function () { return 'Onayla: ' + emptyWithRec().length + ' boş soruya öneri uygulanacak'; }, function () {
    var n = 0;
    // conditional questions may appear after their parent is filled, so repeat until nothing changes
    for (var pass = 0; pass < 3; pass++) {
      emptyWithRec().forEach(function (q) { var a = ans(q.id); a.sel = q.oneri.slice(); a.src = 'bulk'; a.deferred = false; a.at = new Date().toISOString(); n++; });
    }
    save(); update(); announce(n + ' soruya önerilen seçenek uygulandı. İstediğini değiştirebilirsin.');
  });
  armed(d.getElementById('reset'), function () { return 'Onayla: bütün cevaplar silinecek'; }, function () {
    state = { answers: {} }; save(); update(); announce('Bütün cevaplar silindi.');
  });

  /* ---------- glossary ---------- */
  var dlg = d.getElementById('sozluk');
  [].forEach.call(d.querySelectorAll('[data-act="gloss"]'), function (b) {
    b.addEventListener('click', function () { if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', ''); });
  });
  d.getElementById('sozluk-kapat').addEventListener('click', function () { if (dlg.close) dlg.close(); else dlg.removeAttribute('open'); });

  /* ---------- theme ---------- */
  var TK = 'genui-karar-kitabi-tema', tb = d.getElementById('tema');
  var NAMES = { system: 'sistem', light: 'aydınlık', dark: 'koyu' };
  function applyTheme(m) {
    if (m === 'light' || m === 'dark') root.setAttribute('data-theme', m); else root.removeAttribute('data-theme');
    tb.setAttribute('data-mode', m); tb.querySelector('.tt').textContent = 'Tema: ' + NAMES[m];
  }
  var savedTheme = null; try { savedTheme = localStorage.getItem(TK); } catch (e) {}
  applyTheme(savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'system');
  tb.addEventListener('click', function () {
    var cur = tb.getAttribute('data-mode'), next = cur === 'system' ? 'light' : cur === 'light' ? 'dark' : 'system';
    applyTheme(next);
    try { if (next === 'system') localStorage.removeItem(TK); else localStorage.setItem(TK, next); } catch (e) {}
  });

  /* ---------- active chapter in the rail ---------- */
  if ('IntersectionObserver' in window) {
    var links = [].slice.call(chNav.querySelectorAll('a'));
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) links.forEach(function (l) { l.classList.toggle('active', l.getAttribute('href') === '#' + e.target.id); });
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    d.querySelectorAll('.chapter').forEach(function (s) { io.observe(s); });
  }

  update();
  var s = d.getElementById('saved');
  if (s && Object.keys(state.answers).length) s.textContent = 'Önceki cevapların bu tarayıcıdan yüklendi';
})();
