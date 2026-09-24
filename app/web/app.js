/* Solid-State Battery Literature Radar -- front end.
 *
 * Deliberate choices that keep this from breaking:
 *   - every piece of external text goes through esc() before reaching innerHTML;
 *   - searches use an AbortController so a slow response can never overwrite a
 *     newer one;
 *   - all row/facet interaction is delegated from a container, so re-rendering
 *     never leaves stale listeners behind;
 *   - state lives in one object and is mirrored to the URL hash, so a reload
 *     restores exactly what you were looking at.
 */
'use strict';

// ------------------------------------------------------------------ state
var DEFAULTS = {
  q: '', scope: 'local', mode: 'broad', view: 'recent',
  sel: {}, journal: [], tier: 3, days: 0,
  sort: 'date', page: 1, page_size: 25,
  new_only: false, starred: false, unread: false, has_abs: false
};
function freshState() {
  return Object.assign({}, DEFAULTS, { sel: {}, journal: [] });
}
var state = freshState();
var LAST_PAPERS_MAP = {};     // doi -> paper object
var ME = null;                // signed-in reader
var FIELD = null;             // the research direction being read
var FACETS = [];              // whatever axes this field's pack declares
var JOURNALS = [];
var TIER_LABELS = {};
var LAST = null;              // last search payload
var openKids = {};            // chemistry parents expanded in the rail
var showAllJournals = false;
var showAllNodes = {};        // per facet: is the long list expanded
var inflight = null;          // AbortController for the running search
var classicInflight = null;
var classicCache = {};
var hotInflight = null;
var hotCache = {};
var pollTimer = null;
var searchTimer = null;
var refreshSeen = null;       // status snapshot when a refresh started

// ------------------------------------------------------------------ utils
function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function el(id) { return document.getElementById(id); }

/* The refresh control holds an icon plus a label, so only the label is
   rewritten -- setting textContent on the button would drop the icon. */
function refreshBtn(label, busy) {
  var b = el('btnRefresh');
  if (!b) return;
  var span = b.querySelector('span');
  if (span) { span.textContent = label; } else { b.textContent = label; }
  b.disabled = !!busy;
}
function num(n) {
  n = Number(n) || 0;
  return n.toLocaleString('zh-CN');
}
function fmtDate(s) {
  if (!s) return '';
  var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s));
  return m ? (m[1] + '-' + m[2] + '-' + m[3]) : String(s).slice(0, 10);
}
function ago(iso) {
  if (!iso) return '';
  var t = Date.parse(iso);
  if (isNaN(t)) return '';
  var mins = Math.floor((Date.now() - t) / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return mins + ' 分钟前';
  var h = Math.floor(mins / 60);
  if (h < 24) return h + ' 小时前';
  return Math.floor(h / 24) + ' 天前';
}
var PHONE = window.matchMedia('(max-width: 860px)');

function isPhone() { return PHONE.matches; }

function selOf(fid) {
  return state.sel[fid] || [];
}

function toggleSel(fid, id) {
  var arr = state.sel[fid] ? state.sel[fid].slice() : [];
  var i = arr.indexOf(id);
  if (i >= 0) arr.splice(i, 1); else arr.push(id);
  if (arr.length) state.sel[fid] = arr; else delete state.sel[fid];
}

function selCount() {
  var n = 0;
  Object.keys(state.sel).forEach(function (k) { n += state.sel[k].length; });
  return n;
}

function toggleIn(arr, v) {
  var i = arr.indexOf(v);
  if (i >= 0) { arr.splice(i, 1); } else { arr.push(v); }
  return arr;
}

var EXPIRED = 'SESSION_EXPIRED';

function api(path, opts) {
  opts = opts || {};
  return fetch(path, opts).then(function (r) {
    // 401 on a data route means the session died (server restarted, cookie
    // expired, another device revoked it) -- ask again instead of showing
    // a puzzling "search failed".
    if (r.status === 401 && path.indexOf('/api/auth/') !== 0) {
      handleSignedOut();
      throw new Error(EXPIRED);
    }
    if (!r.ok && r.status >= 500) throw new Error('服务端错误 ' + r.status);
    return r.json().catch(function () { throw new Error('返回内容无法解析'); });
  });
}

function handleSignedOut() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  if (inflight) { try { inflight.abort(); } catch (e) {} inflight = null; }
  ME = null; FIELD = null; FACETS = [];
  setAuthMode('login', false);
  showView('authView');
  showErr('authErr', '登录已过期，请重新登录。');
}

// ------------------------------------------------------------ url syncing
function stateToHash() {
  var p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  Object.keys(state.sel).forEach(function (fid) {
    if (state.sel[fid].length) p.set('f.' + fid, state.sel[fid].join(','));
  });
  if (state.journal.length) p.set('journal', state.journal.join('|'));
  if (Number(state.tier) !== 3) p.set('tier', state.tier);
  if (Number(state.days) > 0) p.set('days', state.days);
  if (state.sort !== 'date') p.set('sort', state.sort);
  if (Number(state.page) > 1) p.set('page', state.page);
  if (Number(state.page_size) !== 25) p.set('ps', state.page_size);
  if (state.scope && state.scope !== 'local') p.set('scope', state.scope);
  if (state.scope === 'live' && state.mode === 'precise') p.set('mode', 'precise');
  if (state.scope === 'live' && state.q && state.view !== 'recent') p.set('view', state.view);
  ['new_only', 'starred', 'unread', 'has_abs'].forEach(function (k) {
    if (state[k]) p.set(k, '1');
  });
  var s = p.toString();
  var target = s ? '#' + s : '#';
  if (location.hash !== target) history.replaceState(null, '', target);
}

function hashToState() {
  var raw = location.hash.replace(/^#/, '');
  var p = new URLSearchParams(raw);
  state.q = p.get('q') || '';
  state.scope = p.get('scope') === 'live' ? 'live' : 'local';
  state.mode = p.get('mode') === 'precise' ? 'precise' : 'broad';
  state.view = ['hot', 'classics'].indexOf(p.get('view')) >= 0 ? p.get('view') : 'recent';
  state.sel = {};
  p.forEach(function (value, key) {
    if (key.indexOf('f.') !== 0) return;
    var picked = value.split(',').filter(Boolean);
    if (picked.length) state.sel[key.slice(2)] = picked;
  });
  state.journal = (p.get('journal') || '').split('|').filter(Boolean);
  state.tier = Math.min(3, Math.max(1, parseInt(p.get('tier'), 10) || 3));
  state.days = Math.max(0, parseInt(p.get('days'), 10) || 0);
  state.sort = p.get('sort') || 'date';
  state.page = Math.max(1, parseInt(p.get('page'), 10) || 1);
  state.page_size = [25, 50, 100].indexOf(parseInt(p.get('ps'), 10)) >= 0
    ? parseInt(p.get('ps'), 10) : 25;
  ['new_only', 'starred', 'unread', 'has_abs'].forEach(function (k) {
    state[k] = p.get(k) === '1';
  });
}

// ------------------------------------------------------------------ search
function buildQuery() {
  var p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  Object.keys(state.sel).forEach(function (fid) {
    state.sel[fid].forEach(function (v) { p.append('f.' + fid, v); });
  });
  state.journal.forEach(function (v) { p.append('journal', v); });
  p.set('tier', state.tier);
  p.set('days', state.days);
  p.set('sort', state.sort);
  p.set('page', state.page);
  p.set('page_size', state.page_size);
  if (state.new_only) p.set('new_only', '1');
  if (state.starred) p.set('starred', '1');
  if (state.unread) p.set('unread', '1');
  if (state.has_abs) p.set('has_abs', '1');
  return p.toString();
}

function buildLiveQuery() {
  var p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  p.set('page', state.page);
  p.set('page_size', Math.min(50, state.page_size));
  p.set('sort', state.sort === 'cited' ? 'cited' : (state.sort === 'date' ? 'date' : 'relevance'));
  p.set('mode', state.mode);
  return p.toString();
}

function syncResultView() {
  var available = state.scope === 'live' && !!state.q;
  var hot = available && state.view === 'hot';
  var classics = available && state.view === 'classics';
  el('resultTabs').hidden = !available;
  el('recentPane').hidden = hot || classics;
  el('hotPane').hidden = !hot;
  el('classicsPane').hidden = !classics;
  el('appView').classList.toggle('classics-view', hot || classics);
  el('tabRecent').setAttribute('aria-selected', hot || classics ? 'false' : 'true');
  el('tabHot').setAttribute('aria-selected', hot ? 'true' : 'false');
  el('tabClassics').setAttribute('aria-selected', classics ? 'true' : 'false');
}

function renderClassics(data) {
  var box = el('classicsList');
  if (data.unavailable) {
    box.innerHTML = '<div class="classics-empty">学术索引暂时无法访问，请稍后再试。</div>';
    return;
  }
  if (!data.papers || !data.papers.length) {
    box.innerHTML = '<div class="classics-empty">暂未找到符合主题和发表时间条件的文献。试试泛搜，或输入更具体的英文术语。</div>';
    return;
  }
  box.innerHTML = data.papers.map(function (p, i) {
    return '<article class="classic-rec">' +
      '<span class="classic-rank tnum">' + String(i + 1).padStart(2, '0') + '</span>' +
      '<div class="classic-main">' +
        '<h3><a href="' + esc(p.url) + '" target="_blank" rel="noopener noreferrer">' +
          esc(p.title) + '</a></h3>' +
        (p.authors ? '<p class="classic-authors">' + esc(p.authors) + '</p>' : '') +
        '<p class="classic-meta"><span>' + esc(p.journal) + '</span>' +
          '<span>' + esc(fmtDate(p.pub_date)) + '</span>' +
          '<strong>被引 ' + num(p.cited_by) + '</strong></p>' +
      '</div></article>';
  }).join('');
}

function loadClassics() {
  var q = state.q;
  var mode = state.mode;
  var key = mode + '\u0000' + q;
  el('classicsTitle').textContent = '「' + q + '」的经典文献';
  el('classicsCriteria').textContent = '标题或领域方法匹配 · 发表满 5 年 · 按被引次数排序；算法筛选的高被引候选，不代表公认必读。';
  if (classicCache[key]) {
    renderClassics(classicCache[key]);
    return;
  }
  el('classicsList').innerHTML = '<div class="classics-empty">正在查找高被引文献…</div>';
  var controller = new AbortController();
  classicInflight = controller;
  var params = new URLSearchParams({ q: q, mode: mode });
  api('/api/search/classics?' + params.toString(), { signal: controller.signal })
    .then(function (data) {
      if (controller !== classicInflight || state.q !== q || state.mode !== mode ||
          state.view !== 'classics') return;
      if (data && data.error) throw new Error(data.detail || data.error);
      if (!data.unavailable) classicCache[key] = data;
      renderClassics(data);
    })
    .catch(function (err) {
      if (err && (err.name === 'AbortError' || err.message === EXPIRED)) return;
      el('classicsList').innerHTML = '<div class="classics-empty">经典文献加载失败：' +
        esc(err.message || err) + '</div>';
    });
}

function renderHot(data) {
  var box = el('hotList');
  if (data.unavailable) {
    box.innerHTML = '<div class="classics-empty">学术索引暂时无法访问，请稍后再试。</div>';
    return;
  }
  if (!data.papers || !data.papers.length) {
    box.innerHTML = '<div class="classics-empty">已核对的候选论文中，近 30 天暂无可验证的新增引用。可试试其他关键词。</div>';
    return;
  }
  box.innerHTML = data.papers.map(function (p, i) {
    return '<article class="classic-rec hot-rec">' +
      '<span class="classic-rank tnum">' + String(i + 1).padStart(2, '0') + '</span>' +
      '<div class="classic-main">' +
        '<h3><a href="' + esc(p.url) + '" target="_blank" rel="noopener noreferrer">' +
          esc(p.title) + '</a></h3>' +
        (p.authors ? '<p class="classic-authors">' + esc(p.authors) + '</p>' : '') +
        '<p class="classic-meta"><span>' + esc(p.journal) + '</span>' +
          '<span>' + esc(fmtDate(p.pub_date)) + '</span>' +
          '<strong>近 30 天被引 ' + num(p.recent_citations) + '</strong>' +
          (p.cited_by ? '<span>累计被引 ' + num(p.cited_by) + '</span>' : '') + '</p>' +
        (p.abstract ? '<p class="hot-summary">' + esc(p.abstract) + '</p>' : '') +
      '</div></article>';
  }).join('');
}

function loadHot() {
  var q = state.q;
  var mode = state.mode;
  var key = mode + '\u0000' + q;
  el('hotTitle').textContent = '「' + q + '」近 30 天热门';
  el('hotCriteria').textContent = '按近 30 天新增引用排序，论文可以发表于更早年份。';
  var cached = hotCache[key];
  if (cached && Date.now() - cached.time < 120000) {
    el('hotCriteria').textContent = cached.criteria;
    renderHot(cached.data);
    return;
  }
  el('hotList').innerHTML = '<div class="classics-empty">正在核对主题论文的近 30 天新增引用…</div>';
  var controller = new AbortController();
  hotInflight = controller;
  var params = new URLSearchParams({ q: q, mode: mode });
  api('/api/search/hot?' + params.toString(), { signal: controller.signal })
    .then(function (data) {
      if (controller !== hotInflight || state.q !== q || state.mode !== mode ||
          state.view !== 'hot') return;
      if (data && data.error) throw new Error(data.detail || data.error);
      var criteria = data.unavailable ? 'OpenAlex 暂不可用，无法核对近 30 天新增引用。' :
        fmtDate(data.from_date) + ' 至 ' + fmtDate(data.to_date) +
        ' 期间被引用 · 从 ' + num(data.candidates_checked || 0) +
        ' 篇主题候选中核对 · OpenAlex 数据，收录可能滞后。' +
        (data.partial ? '部分候选核对失败，本榜单不完整。' : '');
      el('hotCriteria').textContent = criteria;
      if (!data.unavailable) hotCache[key] = { data: data, time: Date.now(), criteria: criteria };
      renderHot(data);
    })
    .catch(function (err) {
      if (err && (err.name === 'AbortError' || err.message === EXPIRED)) return;
      el('hotList').innerHTML = '<div class="classics-empty">热门文献加载失败：' +
        esc(err.message || err) + '</div>';
    });
}

function showSkeleton() {
  var h = '';
  for (var i = 0; i < 6; i++) {
    h += '<div class="skel">' +
         '<div class="skel-line" style="width:' + (58 + (i % 3) * 13) + '%;height:14px"></div>' +
         '<div class="skel-line" style="width:38%"></div>' +
         '<div class="skel-line" style="width:26%;height:8px"></div>' +
         '<div class="skel-line" style="width:92%"></div>' +
         '<div class="skel-line" style="width:84%"></div></div>';
  }
  el('reclist').innerHTML = h;
  el('pager').innerHTML = '';
}

function runSearch(opts) {
  opts = opts || {};
  if (!state.q || state.scope !== 'live') state.view = 'recent';
  stateToHash();
  syncScopeTabs();
  if (inflight) { try { inflight.abort(); } catch (e) {} }
  if (classicInflight) { try { classicInflight.abort(); } catch (e) {} }
  if (hotInflight) { try { hotInflight.abort(); } catch (e) {} }
  if (state.scope === 'live' && state.view === 'hot') {
    loadHot();
    return;
  }
  if (state.scope === 'live' && state.view === 'classics') {
    loadClassics();
    return;
  }
  inflight = new AbortController();
  var mine = inflight;
  if (!opts.quiet && !opts.append) showSkeleton();
  if (opts.append) {
    el('btnLoadMore').disabled = true;
    el('btnLoadMore').textContent = '正在载入…';
  }
  el('resCount').textContent = '正在检索…';

  var isLive = state.scope === 'live';
  var url = isLive ? ('/api/search/live?' + buildLiveQuery()) : ('/api/search?' + buildQuery());

  api(url, { signal: mine.signal })
    .then(function (data) {
      if (mine !== inflight) return;      // a newer search has taken over
      if (data && data.error) throw new Error(data.detail || data.error);
      LAST = data;
      LAST_PAPERS_MAP = {};
      (data.papers || []).forEach(function (p) { if (p && p.doi) LAST_PAPERS_MAP[p.doi] = p; });
      renderCount(data);
      renderActiveFilters();
      if (!isLive) renderFacets(data.facets || {});
      renderResults(data, opts.append === true);
      renderPager(data);
      renderLoadMore(data);
      syncTabs();
    })
    .catch(function (err) {
      if (err && err.name === 'AbortError') return;
      if (err && err.message === EXPIRED) return;
      el('resCount').textContent = '检索失败';
      el('btnLoadMore').hidden = true;
      el('reclist').innerHTML =
        '<div class="empty"><h3>检索失败</h3><p>' + esc(err.message || err) +
        '</p><p>软件服务可能已停止，请检查终端窗口后重试。</p></div>';
      el('pager').innerHTML = '';
    });
}

function scheduleSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(function () { state.page = 1; runSearch(); },
                           state.scope === 'live' ? 650 : 280);
}

// ------------------------------------------------------------------ render
var TAB_FOR_STATE = ['new_only', 'unread', 'starred'];

function activeFilterCount() {
  var n = selCount() + state.journal.length;
  if (Number(state.tier) !== 3) n += 1;
  if (Number(state.days) > 0) n += 1;
  if (state.has_abs) n += 1;
  if (state.q) n += 1;
  return n;
}

function syncTabs() {
  var tab = 'all';
  if (state.new_only) tab = 'new';
  else if (state.unread) tab = 'unread';
  else if (state.starred) tab = 'star';
  var btns = el('tabbar').querySelectorAll('[data-tab]');
  for (var i = 0; i < btns.length; i++) {
    btns[i].classList.toggle('on', btns[i].getAttribute('data-tab') === tab);
  }
  var n = activeFilterCount();
  var badge = el('mobarBadge');
  badge.hidden = n === 0;
  badge.textContent = n;
}

function renderCount(d) {
  if (state.scope === 'live') {
    if (d.unavailable) {
      el('resCount').textContent = '全球学术检索 · 数据源暂时不可用';
      el('mobarCount').textContent = '暂不可用';
      el('btnSheetApply').textContent = '暂时无法检索';
      return;
    }
    var srcName = (d.source === 'openalex') ? 'OpenAlex 全球索引' :
                  (d.source === 'crossref' ? 'Crossref 官方检索' : '');
    var qLabel = state.q ? ('「' + esc(state.q) + '」') : '输入主题开始';
    var shown = d.papers ? d.papers.length : 0;
    var from = d.total === 0 ? 0 : (d.page - 1) * d.page_size + 1;
    var range = shown ? '<span class="sub"> 第 ' + num(from) + '–' + num(from + shown - 1) + ' 条</span>' : '';
    var expanded = d.search_terms && d.search_terms !== state.q
      ? '<span class="sub" title="' + esc(d.search_terms) + '"> · 已扩展英文关键词</span>' : '';
    if (d.ranked) {
      el('resCount').innerHTML = '全球学术检索 ' + qLabel +
        ' · 本批 <b class="tnum">' + num(shown) + '</b> 篇标题或摘要匹配' +
        '<span class="sub"> · 索引候选约 ' + num(d.candidate_count) + ' 条' +
        (srcName ? ' · ' + srcName : '') + '</span>' + expanded;
      el('mobarCount').innerHTML = '<b>' + num(shown) + '</b> 篇';
      el('btnSheetApply').textContent = '查看本批 ' + num(shown) + ' 篇';
      return;
    }
    if (d.limited) {
      el('resCount').innerHTML = '全球学术检索 ' + qLabel +
        ' · Crossref 备用结果 <b class="tnum">' + num(shown) +
        '</b> 篇标题或摘要核对匹配<span class="sub"> · 仅核对当前候选批次</span>';
      el('mobarCount').innerHTML = '<b>' + num(shown) + '</b> 篇';
      el('btnSheetApply').textContent = '查看 ' + num(shown) + ' 篇';
      return;
    }
    el('resCount').innerHTML = '全球学术检索 ' + qLabel +
      (state.q ? ' · 约 <b class="tnum">' + num(d.total) + '</b> 条结果' : '') + range +
      (srcName ? '<span class="sub"> · ' + srcName + '</span>' : '') + expanded;
    el('mobarCount').innerHTML = '<b>' + num(d.total) + '</b> 条';
    el('btnSheetApply').innerHTML = d.total ? ('查看 ' + num(d.total) + ' 条结果') : '没有符合条件的结果';
    return;
  }
  var bits = [];
  if (state.q) bits.push('检索「' + esc(state.q) + '」');
  if (state.new_only) bits.push('仅本次新推送');
  if (Number(state.days) > 0) bits.push('近 ' + state.days + ' 天');
  var shown = d.papers.length;
  var from = d.total === 0 ? 0 : (d.page - 1) * d.page_size + 1;
  var range = shown
    ? '<span class="sub"> 第 ' + num(from) + '–' + num(from + shown - 1) + ' 条</span>' : '';
  var extra = bits.length ? '<span class="sub"> · ' + bits.join(' · ') + '</span>' : '';
  el('resCount').innerHTML = '<b class="tnum">' + num(d.total) + '</b> 条结果' + range + extra;
  el('mobarCount').innerHTML = '<b>' + num(d.total) + '</b> 条';
  el('btnSheetApply').innerHTML = d.total
    ? ('查看 ' + num(d.total) + ' 条结果') : '没有符合条件的结果';
}

function facetSection(key, title, bodyHtml, note) {
  var collapsed = localStorage.getItem('facet.' + key) === '0' ? ' collapsed' : '';
  return '<div class="facet' + collapsed + '" data-facet="' + esc(key) + '">' +
    '<button class="facet-head" type="button" data-toggle-facet="' + esc(key) + '">' +
      '<span class="caret"></span><span>' + esc(title) + '</span></button>' +
    '<div class="facet-body">' +
      (note ? '<div class="facet-note">' + esc(note) + '</div>' : '') +
      bodyHtml + '</div></div>';
}

function frow(facetId, id, zh, en, count, selected, depth, hasKids) {
  var cls = 'frow' + (depth ? ' sub' : '') + (selected ? ' on' : '') +
            (!count && !selected ? ' zero' : '');
  var kid = '';
  if (hasKids) {
    kid = '<button class="kid-toggle" type="button" data-kids="' + esc(id) + '" ' +
          'title="' + (openKids[id] ? '收起细分' : '展开细分') + '" ' +
          'aria-label="展开细分">' + (openKids[id] ? '▼' : '▶') + '</button>';
  } else if (depth) {
    kid = '';
  }
  return '<div class="' + cls + '" data-pick="' + esc(facetId) + '" data-id="' + esc(id) + '" ' +
    'title="' + esc(zh + (en ? '  ' + en : '')) + '" ' +
    'role="checkbox" tabindex="0" aria-checked="' + (selected ? 'true' : 'false') + '">' +
    '<input type="checkbox" tabindex="-1" ' + (selected ? 'checked' : '') + '>' +
    kid +
    '<span class="fname">' + esc(zh) + '<span class="en">' + esc(en) + '</span></span>' +
    '<span class="fcount">' + num(count) + '</span></div>';
}

var NODE_VISIBLE = 16;   // a long flat axis folds behind an expander

function renderFacets(facets) {
  var counts = (facets && facets.nodes) || {};
  var fj = (facets && facets.journal) || {};
  var out = '';

  // --- quick toggles ------------------------------------------------------
  var quick = [['new_only', '新推送'], ['unread', '未读'],
               ['starred', '收藏'], ['has_abs', '有摘要']];
  out += facetSection('quick', '快捷筛选',
    '<div class="chiprow">' + quick.map(function (q) {
      return '<button class="pill' + (state[q[0]] ? ' on' : '') +
        '" data-quick="' + q[0] + '" type="button">' + esc(q[1]) + '</button>';
    }).join('') + '</div>');

  // --- publication window -------------------------------------------------
  var windows = [[0, '不限'], [3, '3 天'], [7, '7 天'], [30, '30 天'],
                 [90, '90 天'], [180, '180 天']];
  out += facetSection('days', '出版时间',
    '<div class="chiprow">' + windows.map(function (w) {
      return '<button class="pill' + (Number(state.days) === w[0] ? ' on' : '') +
        '" data-days="' + w[0] + '" type="button">' + esc(w[1]) + '</button>';
    }).join('') + '</div>');

  // --- journal tier -------------------------------------------------------
  var tiers = [[1, '仅顶级'], [2, '一流及以上'], [3, '全部']];
  out += facetSection('tier', '期刊等级',
    '<div class="chiprow">' + tiers.map(function (t) {
      return '<button class="pill' + (Number(state.tier) === t[0] ? ' on' : '') +
        '" data-tier="' + t[0] + '" type="button">' + esc(t[1]) + '</button>';
    }).join('') + '</div>',
    '顶级 / 一流 / 专业三档，依收录期刊清单划分');

  // --- one section per axis the field pack declares -----------------------
  FACETS.forEach(function (f) {
    var fc = counts[f.id] || {};
    var chosen = selOf(f.id);
    var nested = (f.nodes || []).some(function (n) { return (n.children || []).length > 0; });
    var html = '';

    if (nested) {
      f.nodes.forEach(function (node) {
        var kids = node.children || [];
        if (kids.some(function (k) { return chosen.indexOf(k.id) >= 0; })) {
          openKids[node.id] = true;
        }
        html += frow(f.id, node.id, node.zh, node.en, fc[node.id] || 0,
                     chosen.indexOf(node.id) >= 0, 0, kids.length > 0);
        if (openKids[node.id]) {
          kids.forEach(function (k) {
            html += frow(f.id, k.id, k.zh, k.en, fc[k.id] || 0,
                         chosen.indexOf(k.id) >= 0, 1, false);
          });
        }
      });
    } else {
      var rows = (f.nodes || []).slice().sort(function (a, b) {
        return (fc[b.id] || 0) - (fc[a.id] || 0);
      });
      var open = showAllNodes[f.id] === true;
      var shown = open ? rows : rows.slice(0, NODE_VISIBLE);
      html = shown.map(function (n) {
        return frow(f.id, n.id, n.zh, n.en, fc[n.id] || 0,
                    chosen.indexOf(n.id) >= 0, 0, false);
      }).join('');
      // a selection scrolled out of the visible slice must stay removable
      chosen.forEach(function (id) {
        if (!shown.some(function (n) { return n.id === id; })) {
          html += frow(f.id, id, labelOf(f.id, id), '', fc[id] || 0, true, 0, false);
        }
      });
      if (rows.length > NODE_VISIBLE) {
        html += '<button class="expander" type="button" data-allnodes="' + esc(f.id) +
          '">' + (open ? '收起' : ('显示全部 ' + rows.length + ' 项')) + '</button>';
      }
    }
    out += facetSection(f.id, f.zh, html || '<div class="facet-note">暂无数据</div>',
                        f.note || '');
  });

  // --- source journals ----------------------------------------------------
  var jnames = Object.keys(fj).sort(function (a, b) {
    return (fj[b] - fj[a]) || a.localeCompare(b);
  });
  var LIMIT = 12;
  var visible = showAllJournals ? jnames : jnames.slice(0, LIMIT);
  var jHtml = visible.map(function (n) {
    var meta = JOURNALS.filter(function (j) { return j.name === n; })[0] || {};
    return frow('__journal', n, n, meta.jif ? ('IF ' + meta.jif) : '', fj[n] || 0,
                state.journal.indexOf(n) >= 0, 0, false);
  }).join('');
  state.journal.forEach(function (n) {
    if (visible.indexOf(n) < 0) {
      jHtml += frow('__journal', n, n, '', fj[n] || 0, true, 0, false);
    }
  });
  if (jnames.length > LIMIT) {
    jHtml += '<button class="expander" type="button" data-alljournals="1">' +
      (showAllJournals ? '收起' : ('显示全部 ' + jnames.length + ' 种期刊')) + '</button>';
  }
  out += facetSection('journal', '来源期刊', jHtml || '<div class="facet-note">暂无数据</div>');

  el('facets').innerHTML = out;
}

function renderActiveFilters() {
  var box = el('activeFilters');
  var tags = [];
  function tag(kind, id, text) {
    tags.push('<span class="tag">' + esc(text) +
      '<button type="button" data-drop="' + esc(kind) + '" data-id="' + esc(id) +
      '" aria-label="移除筛选">✕</button></span>');
  }
  FACETS.forEach(function (f) {
    selOf(f.id).forEach(function (id) { tag(f.id, id, labelOf(f.id, id)); });
  });
  state.journal.forEach(function (n) { tag('__journal', n, n); });
  if (Number(state.tier) !== 3) {
    var tl = (TIER_LABELS[state.tier] && TIER_LABELS[state.tier].zh) || ('第 ' + state.tier + ' 级');
    tag('tier', '', Number(state.tier) === 1 ? ('仅' + tl) : (tl + '及以上'));
  }
  if (Number(state.days) > 0) tag('days', '', '近 ' + state.days + ' 天');
  if (state.new_only) tag('quick', 'new_only', '仅本次新推送');
  if (state.unread) tag('quick', 'unread', '仅未读');
  if (state.starred) tag('quick', 'starred', '仅收藏');
  if (state.has_abs) tag('quick', 'has_abs', '仅含摘要');

  if (!tags.length) { box.hidden = true; box.innerHTML = ''; return; }
  box.hidden = false;
  box.innerHTML = '<span class="lbl">已选条件</span>' + tags.join('') +
    '<span class="tag clear"><button type="button" data-drop="all" data-id="">' +
    '全部清除</button></span>';
}

function labelOf(facetId, id) {
  var list = [];
  FACETS.forEach(function (f) {
    if (!facetId || f.id === facetId) list = list.concat(f.nodes || []);
  });
  for (var i = 0; i < list.length; i++) {
    if (list[i].id === id) return list[i].zh;
    var kids = list[i].children || [];
    for (var j = 0; j < kids.length; j++) {
      if (kids[j].id === id) return list[i].zh + ' › ' + kids[j].zh;
    }
  }
  return id;
}

function tierBadge(tier, jif) {
  var lab = (TIER_LABELS[tier] && TIER_LABELS[tier].zh) || ('T' + tier);
  var h = '<span class="badge t' + (tier || 3) + '">' + esc(lab) + '</span>';
  if (jif) h += '<span class="badge jif">IF ' + esc(jif) + '</span>';
  return h;
}

var TIER_LABEL_FALLBACK = { 1: '顶级期刊', 2: '一流期刊', 3: '专业期刊' };
var CAT_VISIBLE = 6;   // beyond this, categories fold behind a "+N"

function tierBadges(tier, jif) {
  var lab = (TIER_LABELS[tier] && TIER_LABELS[tier].zh) || TIER_LABEL_FALLBACK[tier] || '';
  var out = lab ? '<span class="badge t' + tier + '">' + esc(lab) + '</span>' : '';
  if (jif) out += '<span class="badge jif">IF ' + esc(jif) + '</span>';
  return out;
}

var TOPIC_KEYWORD_RULES = [
  // Thermoelectric & Thermal
  [/\b(thermoelectric cooling|thermoelectric cooler)\b/i, '热电制冷'],
  [/\b(thermoelectric|peltier|seebeck)\b/i, '热电材料'],
  [/\b(radiative cooling)\b/i, '辐射制冷'],
  [/\b(phase-change|phase change|pcms?)\b/i, '相变材料'],
  [/\b(thermal management|thermal conduction|thermal dissipation)\b/i, '热管理'],

  // Batteries & Solid-State
  [/\b(sulfide.*solid.*electrolyte|sulfide-based|argyrodite|li6ps5cl)\b/i, '硫化物电解质'],
  [/\b(garnet|llzo|llto|latp|lagp)\b/i, '氧化物电解质'],
  [/\b(halide.*electrolyte|li3ycl6|li3incl6)\b/i, '卤化物电解质'],
  [/\b(polymer electrolyte|solid polymer electrolyte|\bspe\b|pvdf-hfp)\b/i, '聚合物电解质'],
  [/\b(lithium metal anode|anode-free|lithium metal batteries)\b/i, '锂金属电池'],
  [/\b(silicon anode|silicon-based anode|si\/c)\b/i, '硅基负极'],
  [/\b(sodium-ion|na-ion|nasicon|sodium metal)\b/i, '钠电池'],
  [/\b(lithium-sulfur|li-s|na-s)\b/i, '硫系电池'],
  [/\b(all-solid-state|solid-state battery|solid-state lithium)\b/i, '全固态电池'],
  [/\b(solid electrolyte interphase|\bsei\b|localized high-concentration)\b/i, '界面SEI'],
  [/\b(supercapacitor|electrochemical capacitor)\b/i, '超级电容器'],

  // Perovskite & PV & Opto
  [/\bperovskite\b/i, '钙钛矿'],
  [/\b(photovoltaic|solar cell)\b/i, '光伏/太阳能'],
  [/\b(electroluminescence|\boled\b|\bqled\b|light-emitting)\b/i, '发光显示'],
  [/\b(water splitting|\bher\b|\boer\b|hydrogen evolution|oxygen evolution)\b/i, '水分解/析氢'],
  [/\b(co2 reduction|\bco2rr\b)\b/i, 'CO2催化还原'],
  [/\b(fluorescence|luminescen|bloch surface)\b/i, '荧光/发光'],

  // AI & Modeling
  [/\b(graph neural|gnn|equivariant)\b/i, '图神经网络'],
  [/\b(molecular dynamics|aimd|ab initio|\bdft\b)\b/i, '分子模拟/DFT'],
  [/\b(machine learning|deep learning|neural network)\b/i, '机器学习'],
  [/\b(large language model|\bllm\b|foundation model)\b/i, '大语言模型'],

  // 2D, Materials & Physics
  [/\bmxene\b/i, 'MXene'],
  [/\b(metal-organic framework|\bmofs?\b|\bcofs?\b)\b/i, 'MOF/COF'],
  [/\b(metamaterial|metasurface)\b/i, '超材料'],
  [/\bhall effect\b/i, '霍尔效应'],
  [/\b(superconducting|superconductivity)\b/i, '超导材料'],
  [/\bsupramolecular\b/i, '超分子'],
  [/\bdeep eutectic\b/i, '深共晶溶剂'],
  [/\b(topological insulator|weyl semimetal|berry curvature)\b/i, '拓扑物态'],
  [/\bhydrogen storage\b/i, '储氢材料'],
  [/\b(high-entropy|entropy-driven)\b/i, '高熵材料'],
  [/\b(biomaterial|biofilm|living materials?)\b/i, '生物材料'],
  [/\b(semiconductor|heterojunction|heterostructure)\b/i, '半导体/异质结'],
  [/\b(sensor|biosensor|sensing)\b/i, '传感探测'],
  [/\b(catalytic|catalysis|catalyst)\b/i, '催化反应'],
  [/\b(organic electrochemical transistors?|\boects?\b)\b/i, '有机电化学晶体管'],
  [/\bartificial spin ice\b/i, '人工自旋冰'],
  [/\bcellulose\b/i, '纤维素材料'],
  [/\b(plastics? recycling|plastics? circularity|pyrolysis)\b/i, '塑料回收/热解'],
  [/\b(quantum dots?|\bqds?\b)\b/i, '量子点'],
  [/\b(regolith|lunar)\b/i, '月壤/地外演化'],
  [/\b(spectroscopy|\bepr\b|\bnmr\b|nuclear polarization)\b/i, '波谱学/表征']
];

var MAT_RE = /\b([A-Z][a-z]?[0-9]*(?:[A-Z][a-z0-9]*){1,6}(?:-[A-Za-z0-9]+)?)\b/g;
var STOP_MATS = {
  DNA: 1, RNA: 1, USA: 1, IEEE: 1, DOI: 1, ORR: 1, HER: 1, OER: 1,
  XRD: 1, TEM: 1, SEM: 1, XPS: 1, DFT: 1, AI: 1, ML: 1, NIR: 1, UV: 1,
  NMR: 1, AFM: 1, LED: 1, OLED: 1, COF: 1, MOF: 1, PEG: 1, PVA: 1, PMMA: 1,
  PEO: 1, SPE: 1, SEI: 1, LIB: 1, SIB: 1, LAB: 1, ASSB: 1, PCM: 1, PCMS: 1,
  AM: 1, ACS: 1, WILEY: 1, NCM: 1, PDF: 1, HTML: 1, URL: 1, EPR: 1, BTEC: 1,
  AND: 1, FOR: 1, THE: 1, NEW: 1, ADV: 1, DAY: 1, TWO: 1, ONE: 1, NOT: 1,
  ARE: 1, CAN: 1, USE: 1, WITH: 1, FROM: 1, INTO: 1, OVER: 1, VIA: 1, OUT: 1
};

function extractPaperKeywords(p) {
  var tags = [];
  if (p.label_chips && p.label_chips.length) {
    for (var i = 0; i < p.label_chips.length; i++) {
      var c = p.label_chips[i];
      if (c.id && c.id !== 'other' && c.zh && c.zh.indexOf('其他') < 0 && c.zh.indexOf('未指明') < 0) {
        var cleanZh = c.zh.split(' / ')[0].trim();
        if (cleanZh && tags.indexOf(cleanZh) < 0) {
          tags.push(cleanZh);
          break;
        }
      }
    }
  }

  var title = p.title || '';
  for (var j = 0; j < TOPIC_KEYWORD_RULES.length; j++) {
    var rule = TOPIC_KEYWORD_RULES[j];
    if (rule[0].test(title)) {
      if (tags.indexOf(rule[1]) < 0) tags.push(rule[1]);
      if (tags.length >= 2) break;
    }
  }

  var matMatch = null;
  MAT_RE.lastIndex = 0;
  var m;
  while ((m = MAT_RE.exec(title)) !== null) {
    var raw = m[1];
    var w = raw.replace(/-(doped|based|coated|modified|like|assisted|driven|type|free|rich|enabled|derived|containing)$/i, '');
    if (w.length < 3 || STOP_MATS[w.toUpperCase()]) continue;
    if (/[0-9]/.test(w) || ['LLZO', 'LATP', 'LAGP', 'MXene', 'PVDF', 'PVDF-HFP'].indexOf(w) >= 0) {
      matMatch = w;
      break;
    }
  }

  if (tags.length < 2 && p.abstract) {
    for (var k = 0; k < TOPIC_KEYWORD_RULES.length; k++) {
      var r = TOPIC_KEYWORD_RULES[k];
      if (r[0].test(p.abstract)) {
        if (tags.indexOf(r[1]) < 0) tags.push(r[1]);
        if (tags.length >= 2) break;
      }
    }
  }

  var res = [];
  if (tags.length > 0) res.push(tags[0]);
  if (matMatch) {
    res.push(matMatch);
  } else if (tags.length > 1) {
    res.push(tags[1]);
  }
  return res;
}

function renderResults(d, append) {
  var box = el('reclist');
  if (!d.papers.length && !append) {
    if (state.scope === 'live') {
      box.innerHTML = d.unavailable
        ? '<div class="empty"><h3>学术索引暂时无法访问</h3>' +
          '<p>OpenAlex 和 Crossref 当前都没有返回有效结果，请稍后重试。</p></div>'
        : !state.q
        ? '<div class="empty empty-discover"><p class="empty-kicker">开始检索</p>' +
          '<h3>搜索任何学科的最新论文</h3>' +
          '<p class="empty-lead">从一个研究主题出发，浏览全球学术索引中新发表的论文。</p>' +
          '<div class="empty-queries"><span>试着检索</span>' +
          '<button type="button" class="example-query" data-example="固态电池">固态电池</button>' +
          '<button type="button" class="example-query" data-example="AI算法">AI 算法</button>' +
          '<button type="button" class="example-query" data-example="量子计算">量子计算</button></div>' +
          '<p class="empty-note">主题越具体，结果越准确。英文关键词的覆盖通常更完整。</p></div>'
        : d.ranked
        ? '<div class="empty"><h3>这批最新候选没有明确的标题或摘要匹配</h3>' +
          '<p>可浏览下一批，或换成更具体的英文关键词。</p></div>'
        : '<div class="empty"><h3>全球学术库未检索到匹配文献</h3>' +
          '<p>试试更具体的主题，或改用英文关键词。</p></div>';
    } else {
      var globalBtn = state.q
        ? '<p><button class="btn-primary" id="btnSwitchGlobal" type="button" style="margin-top:14px;padding:8px 18px;font-size:13.5px">在全球学术库中检索「' + esc(state.q) + '」</button></p>'
        : '';
      box.innerHTML = '<div class="empty"><h3>当前方向雷达库中暂无匹配文献</h3>' +
        globalBtn +
        '<p>可尝试放宽筛选：清除左侧条件、放宽出版时间，或把期刊等级调为「全部」。</p>' +
        (d.total === 0 && !state.q && !selCount()
          ? '<p>若文献库仍为空，点击右上角「立即更新」抓取最新文献。</p>' : '') +
        '</div>';
      if (state.q) {
        var sg = el('btnSwitchGlobal');
        if (sg) sg.onclick = function () { setScope('live'); };
      }
    }
    return;
  }
  var start = (d.page - 1) * d.page_size;
  var html = d.papers.map(function (p, i) {
    var badges = '';
    if (p.is_new) badges += '<span class="badge new">新推送</span>';
    if (p.is_oa) badges += '<span class="badge oa">开放获取</span>';
    badges += tierBadges(p.journal_tier, p.journal_jif);

    var kws = extractPaperKeywords(p);
    kws.forEach(function (k) {
      var isMat = /[0-9]/.test(k) || ['LLZO', 'LATP', 'LAGP', 'MXene', 'PVDF', 'PVDF-HFP'].indexOf(k) >= 0;
      badges += '<span class="badge kw' + (isMat ? ' mat' : '') + '" data-kw="' + esc(k) + '" title="点击按「' + esc(k) + '」检索">' + esc(k) + '</span>';
    });

    var vip = [];
    if (p.volume) vip.push('卷 ' + esc(p.volume));
    if (p.issue) vip.push('期 ' + esc(p.issue));
    if (p.pages) vip.push(esc(p.pages));
    var meta = ['<span class="jname">' + esc(p.journal) + '</span>'];
    if (vip.length) meta.push('<span>' + vip.join('，') + '</span>');
    if (state.scope === 'live' && p.cited_by > 0) {
      meta.push('<span>被引 ' + num(p.cited_by) + '</span>');
    }
    meta.push('<span class="date">' + esc(fmtDate(p.pub_date)) + '</span>');

    // the server tags each chip with the axis it came from, so a record shows
    // whatever axes the field declares -- primary axis first, then the rest
    var primaryAxis = FACETS.length ? FACETS[0].id : '';
    var cats = (p.label_chips || []).slice().sort(function (a, b) {
      return (a.facet === primaryAxis ? 0 : 1) - (b.facet === primaryAxis ? 0 : 1);
    });
    var catHtml = cats.map(function (c, k) {
      return '<button class="cat' + (c.facet === primaryAxis ? '' : ' theme') +
        (k >= CAT_VISIBLE ? ' extra' : '') +
        '" type="button" data-pickcat="' + esc(c.facet) + '" data-id="' + esc(c.id) +
        '" title="' + esc(c.path || c.en || '') + '">' + esc(c.zh) + '</button>';
    }).join('');
    if (cats.length > CAT_VISIBLE) {
      catHtml += '<button class="cat-more" type="button" data-catmore="1">+' +
        (cats.length - CAT_VISIBLE) + '</button>';
    }

    var absHtml;
    var absToggle = '';
    if (p.abstract) {
      absHtml = '<p class="abs clamped" data-abs="1">' + esc(p.abstract) + '</p>';
      absToggle = '<button class="abs-toggle" type="button" data-expand="1">' +
        (state.scope === 'live' ? '查看摘要' : '展开全文摘要') + '</button>';
    } else {
      absHtml = '<p class="abs-none">该期刊未向公开数据库提供摘要，软件会在后续更新中继续尝试补全；' +
        '可点击标题查看原文摘要。</p>';
    }

    return '<article class="rec' + (p.read_at ? ' isread' : '') +
        '" data-doi="' + esc(p.doi) + '">' +
      '<div class="rec-index">' +
        '<span class="rec-kind">研究论文</span>' +
        (p.is_oa ? '<span class="rec-open">开放获取</span>' : '') +
        '<time class="rec-pubdate">' + esc(fmtDate(p.pub_date)) + '</time>' +
      '</div>' +
      '<div class="rec-main">' +
        '<h3 class="rec-title"><a href="' + esc(p.url) + '" target="_blank" ' +
          'rel="noopener noreferrer">' + esc(p.title) + '</a><span class="ext">↗</span></h3>' +
        (p.authors ? '<div class="rec-authors" title="' + esc(p.authors) + '">' +
          esc(p.authors) + '</div>' : '') +
        '<div class="rec-src">' + meta.join('<span class="dot">·</span>') +
          '<span class="badges">' + badges + '</span></div>' +
        (catHtml ? '<div class="cats">' + catHtml + '</div>' : '') +
        absHtml +
        '<div class="rowacts">' +
          absToggle +
          '<a class="act-primary" href="' + esc(p.url) + '" target="_blank" ' +
            'rel="noopener noreferrer">查看原文 ↗</a>' +
          (p.is_oa && p.oa_url ? '<a class="act-oa" href="' + esc(p.oa_url) + '" target="_blank" rel="noopener noreferrer">PDF 全文 ↗</a>' : '') +
          '<button type="button" class="star' + (p.starred ? ' on' : '') + '" data-star="1">' +
            (p.starred ? '★ 已收藏' : '☆ 收藏') + '</button>' +
          '<button type="button" data-read="1">' + (p.read_at ? '标为未读' : '标为已读') + '</button>' +
          '<button type="button" data-copy="1">' +
            (p.doi.indexOf('openalex:') === 0 ? '复制链接' : '复制 DOI') + '</button>' +
          (p.first_seen ? ('<span class="seen">入库 ' + esc(ago(p.first_seen)) + '</span>') : '') +
        '</div>' +
      '</div>' +
      '<div class="rec-side">' +
        '<div class="n' + (p.cited_by > 0 ? ' tnum' : ' none') + '">' +
          (p.cited_by > 0 ? num(p.cited_by) : '—') + '</div>' +
        '<div class="k">被引</div>' +
      '</div>' +
    '</article>';
  }).join('');
  if (append) { box.insertAdjacentHTML('beforeend', html); } else { box.innerHTML = html; }
}

function renderLoadMore(d) {
  var b = el('btnLoadMore');
  b.disabled = false;
  var more = d.total - d.page * (d.ranked ? 200 : d.page_size);
  if (!isPhone() || more <= 0) { b.hidden = true; return; }
  b.hidden = false;
  b.textContent = d.ranked ? '加载下一批主题匹配' : '加载更多（还有 ' + num(more) + ' 条）';
}

function renderPager(d) {
  if (d.pages <= 1) {
    el('pager').innerHTML = d.ranked ? '<span class="info">已浏览当前候选</span>' : d.total
      ? '<span class="info">共 ' + num(d.total) + ' 条，已全部显示</span>' : '';
    return;
  }
  var cur = d.page, last = d.pages, parts = [];
  parts.push('<button type="button" data-page="' + (cur - 1) + '"' +
    (cur <= 1 ? ' disabled' : '') + '>上一页</button>');
  var pages = [];
  for (var i = 1; i <= last; i++) {
    if (i <= 2 || i > last - 2 || Math.abs(i - cur) <= 2) pages.push(i);
  }
  var prev = 0;
  pages.forEach(function (i) {
    if (prev && i - prev > 1) parts.push('<span class="gap">…</span>');
    parts.push('<button type="button" class="' + (i === cur ? 'on' : '') +
      '" data-page="' + i + '">' + i + '</button>');
    prev = i;
  });
  parts.push('<button type="button" data-page="' + (cur + 1) + '"' +
    (cur >= last ? ' disabled' : '') + '>下一页</button>');
  parts.push('<span class="info">第 ' + cur + ' / ' + last +
    (d.ranked ? ' 批' : ' 页') + '</span>');
  el('pager').innerHTML = parts.join('');
}

// ----------------------------------------------------------------- notices
function notices(list) {
  el('notices').innerHTML = list.filter(Boolean).join('');
}

/* ``dismissKey`` adds a close button and, once closed, keeps that notice from
   coming back on every open (it is remembered per browser). */
function noticeHtml(kind, html, extra, dismissKey) {
  if (dismissKey && dismissed(dismissKey)) return '';
  var x = dismissKey
    ? '<button class="notice-x" type="button" data-dismiss="' + esc(dismissKey) +
      '" aria-label="不再提示">✕</button>'
    : '';
  return '<div class="notice ' + kind + '">' + (extra || '') +
    '<span class="grow">' + html + '</span>' + x + '</div>';
}

function dismissed(key) {
  try { return localStorage.getItem('notice.' + key) === '1'; } catch (e) { return false; }
}

function renderIdentity() {
  if (!ME) return;
  var zh = (FIELD && FIELD.zh) || '';
  el('brandZh').textContent = '文献雷达';
  el('brandEn').textContent = 'Literature Radar';
  document.title = zh ? zh + '文献雷达' : '文献雷达';
  el('fieldName').textContent = zh || '设置定向追踪';
  var name = ME.display_name || ME.username || '';
  el('avatarText').textContent = '账号';
  el('btnAccount').title = name + '（点击管理账号）';
  el('menuName').textContent = name;
  el('menuSub').textContent = '@' + (ME.username || '');
  var fn = el('fnField');
  if (fn) fn.textContent = zh || '所选方向';
}

function renderHeader(boot) {
  var st = boot.stats || {};
  var last = boot.refresh && boot.refresh.last;
  var total = st.total || st.n || 0;
  var cov = (total && st.with_abs) ? Math.round(100 * st.with_abs / total) : 0;
  function pill(label, value, cls) {
    return '<span class="stat' + (cls ? ' ' + cls : '') + '">' + esc(label) +
      '<i class="tnum">' + value + '</i></span>';
  }
  var html = pill('库内', num(total) + ' 篇') +
             pill('近 7 天', num(st.week || 0)) +
             pill('摘要', cov + '%') +
             pill('期刊', num(st.journals_tracked || 0));
  if (last) html += '<span class="stat plain">更新于 <i>' + esc(ago(last.finished)) + '</i></span>';
  el('mastMeta').innerHTML = html;
  el('fnJournals').textContent = num(st.journals_tracked || 0);
}

// ---------------------------------------------------------------- refresh
function startPolling(announce) {
  if (pollTimer) return;
  refreshBtn('更新中…', true);
  pollTimer = setInterval(function () {
    api('/api/status').then(function (d) {
      var s = d.status || {};
      if (s.running) {
        notices([noticeHtml('', '<b>正在更新文献库</b> — ' + esc(s.message || '请稍候') +
          '（已检视 ' + num(s.scanned) + ' 条记录，命中 ' + num(s.matched) +
          ' 篇，新增 ' + num(s.added) + ' 篇）', '<span class="spin"></span>')]);
        return;
      }
      clearInterval(pollTimer); pollTimer = null;
      refreshBtn('立即更新', false);
      renderHeader({ stats: d.stats || {}, refresh: { last: d.last } });
      if (s.ok === false || s.error) {
        notices([noticeHtml('bad', '<b>更新未完成</b> — ' + esc(s.error || s.message ||
          '请查看终端日志') + '。已显示现有文献。')]);
      } else if (announce !== false) {
        var msg = '<b>更新完成</b> — 新增 ' + num(s.added) + ' 篇，更新 ' +
          num(s.updated) + ' 篇' +
          (s.abstracts_filled ? '，补全摘要 ' + num(s.abstracts_filled) + ' 篇' : '') + '。';
        notices([noticeHtml('good', msg)]);
        setTimeout(function () {
          var box = el('notices');
          if (box.textContent.indexOf('更新完成') >= 0) box.innerHTML = '';
        }, 12000);
      }
      state.page = 1;
      runSearch({ quiet: true });
    }).catch(function () {
      clearInterval(pollTimer); pollTimer = null;
      refreshBtn('立即更新', false);
    });
  }, 1800);
}

function triggerRefresh() {
  refreshBtn('更新中…', true);
  api('/api/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: '{}' })
    .then(function () { startPolling(true); })
    .catch(function (e) {
      refreshBtn('立即更新', false);
      notices([noticeHtml('bad', '无法启动更新：' + esc(e.message || e))]);
    });
}

// ------------------------------------------------------- phone: filter sheet
function openSheet() {
  if (!isPhone()) return;
  el('rail').classList.add('open');
  var bd = el('sheetBackdrop');
  bd.hidden = false;
  requestAnimationFrame(function () { bd.classList.add('open'); });
  document.body.style.overflow = 'hidden';
}

function closeSheet() {
  el('rail').classList.remove('open');
  var bd = el('sheetBackdrop');
  bd.classList.remove('open');
  setTimeout(function () { if (!bd.classList.contains('open')) bd.hidden = true; }, 280);
  document.body.style.overflow = '';
}

function setTab(tab) {
  state.new_only = tab === 'new';
  state.unread = tab === 'unread';
  state.starred = tab === 'star';
  state.page = 1;
  runSearch();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function registerWorker() {
  if (!('serviceWorker' in navigator)) return;
  // Browsers only allow a worker on a secure origin; a plain-HTTP LAN address
  // will refuse, which is expected and must stay silent.
  var secure = location.protocol === 'https:' ||
               location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  if (!secure) return;
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
}

function setScope(mode) {
  if (mode === 'local' && !FIELD) { openOnboarding(); return; }
  state.scope = (mode === 'live') ? 'live' : 'local';
  state.view = 'recent';
  state.page = 1;
  syncScopeTabs();
  runSearch();
}

function syncScopeTabs() {
  var isLive = state.scope === 'live';
  el('appView').classList.toggle('global-mode', isLive);
  el('searchModeRow').hidden = !isLive;
  el('modeBroad').setAttribute('aria-pressed', state.mode === 'broad' ? 'true' : 'false');
  el('modePrecise').setAttribute('aria-pressed', state.mode === 'precise' ? 'true' : 'false');
  el('modeHelp').textContent = state.mode === 'precise'
    ? '输入更具体的研究问题或多个关键条件；结果须覆盖这些要点'
    : '输入较宽的研究主题；结果仍须在标题或摘要中明确涉及该主题';
  syncResultView();
  var tLocal = el('tabScopeLocal');
  var tLive = el('tabScopeLive');
  if (tLocal) {
    tLocal.hidden = !FIELD;
    tLocal.classList.toggle('active', !isLive);
    tLocal.setAttribute('aria-selected', !isLive ? 'true' : 'false');
  }
  if (tLive) {
    tLive.classList.toggle('active', isLive);
    tLive.setAttribute('aria-selected', isLive ? 'true' : 'false');
  }
  if (isLive && ['date', 'relevance', 'cited'].indexOf(state.sort) < 0) {
    state.sort = 'date'; syncSortControls();
  }
  if (isLive && state.page_size > 50) {
    state.page_size = 50; el('pageSize').value = '50';
  }
  var dateLabel = isLive
    ? '主题匹配优先 · 较新' : '出版日期：最新优先';
  el('sort').querySelector('option[value="date"]').textContent = dateLabel;
  el('sortMobile').querySelector('option[value="date"]').textContent =
    isLive ? '主题优先' : '最新发表';
  ['new', 'journal', 'title'].forEach(function (value) {
    var option = el('sort').querySelector('option[value="' + value + '"]');
    if (option) option.disabled = isLive;
    var mobile = el('sortMobile').querySelector('option[value="' + value + '"]');
    if (mobile) mobile.disabled = isLive;
  });
  el('btnRefresh').hidden = isLive || !FIELD;
  var qInput = el('q');
  if (qInput) {
    qInput.placeholder = isLive
      ? (state.mode === 'precise'
          ? '输入详细问题，如固态电池 硫化物电解质 界面稳定性'
          : '输入研究主题，如固态电池、AI算法、量子计算')
      : '检索标题、摘要、期刊、作者';
  }
  var rail = el('rail');
  if (rail) {
    var notice = el('railLiveNotice');
    if (!notice) {
      notice = document.createElement('div');
      notice.id = 'railLiveNotice';
      notice.className = 'rail-live-notice';
      notice.innerHTML = '<div class="hint-title">全球多学科检索</div><div class="hint-text">输入任何学科的研究主题。使用更具体的英文术语，通常能得到更准确的结果。</div>';
      var body = rail.querySelector('.rail-body') || rail;
      body.insertBefore(notice, body.firstChild);
    }
    notice.hidden = !isLive;
  }
}

// ------------------------------------------------------------------ events
function wire() {
  if (el('tabScopeLocal')) {
    el('tabScopeLocal').addEventListener('click', function () { setScope('local'); });
  }
  if (el('tabScopeLive')) {
    el('tabScopeLive').addEventListener('click', function () { setScope('live'); });
  }
  el('modeBroad').addEventListener('click', function () {
    if (state.mode === 'broad') return;
    state.mode = 'broad'; state.page = 1; runSearch();
  });
  el('modePrecise').addEventListener('click', function () {
    if (state.mode === 'precise') return;
    state.mode = 'precise'; state.page = 1; runSearch();
  });
  el('tabRecent').addEventListener('click', function () {
    if (state.view === 'recent') return;
    state.view = 'recent'; state.page = 1; runSearch();
  });
  el('tabHot').addEventListener('click', function () {
    if (state.view === 'hot') return;
    state.view = 'hot'; state.page = 1; runSearch();
  });
  el('tabClassics').addEventListener('click', function () {
    if (state.view === 'classics') return;
    state.view = 'classics'; state.page = 1; runSearch();
  });
  el('q').addEventListener('input', function () {
    state.q = this.value.trim(); scheduleSearch();
  });
  el('q').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { clearTimeout(searchTimer); state.page = 1; runSearch(); }
  });
  el('btnClearQ').addEventListener('click', function () {
    el('q').value = ''; state.q = ''; state.page = 1; runSearch();
  });
  el('btnSearch').addEventListener('click', function () {
    clearTimeout(searchTimer); state.page = 1; runSearch();
  });
  el('btnReset').addEventListener('click', function () {
    var scope = state.scope;
    state = freshState(); state.scope = scope;
    el('q').value = '';
    el('pageSize').value = String(state.page_size);
    syncSortControls();
    showAllJournals = false; showAllNodes = {}; runSearch();
  });
  el('btnClearFacets').addEventListener('click', function () {
    state.sel = {}; state.journal = [];
    state.tier = 3; state.days = 0;
    state.new_only = state.starred = state.unread = state.has_abs = false;
    state.page = 1; runSearch();
  });
  el('sort').addEventListener('change', function () {
    state.sort = this.value; state.page = 1;
    syncSortControls();
    runSearch();
  });
  el('pageSize').addEventListener('change', function () {
    state.page_size = parseInt(this.value, 10) || 25; state.page = 1; runSearch();
  });
  el('btnRefresh').addEventListener('click', triggerRefresh);
  el('notices').addEventListener('click', function (e) {
    var b = e.target.closest('[data-dismiss]');
    if (!b) return;
    try { localStorage.setItem('notice.' + b.getAttribute('data-dismiss'), '1'); } catch (x) {}
    var box = b.closest('.notice');
    if (box) box.remove();
  });

  // ---- phone chrome
  el('btnSheet').addEventListener('click', openSheet);
  el('btnSheetClose').addEventListener('click', closeSheet);
  el('btnSheetApply').addEventListener('click', closeSheet);
  el('sheetBackdrop').addEventListener('click', closeSheet);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSheet();
  });
  el('tabbar').addEventListener('click', function (e) {
    var b = e.target.closest('[data-tab]');
    if (b) setTab(b.getAttribute('data-tab'));
  });
  el('sortMobile').addEventListener('change', function () {
    state.sort = this.value; state.page = 1;
    el('sort').value = this.value;
    runSearch();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  el('btnLoadMore').addEventListener('click', function () {
    state.page += 1;
    runSearch({ append: true, quiet: true });
  });
  PHONE.addEventListener('change', function () {
    if (!isPhone()) closeSheet();
    renderLoadMore(LAST || { total: 0, page: 1, page_size: 25 });
  });

  // ---- rail (delegated)
  el('rail').addEventListener('click', function (e) {
    var t = e.target;
    var kidBtn = t.closest('[data-kids]');
    if (kidBtn) {
      e.stopPropagation();
      var pid = kidBtn.getAttribute('data-kids');
      openKids[pid] = !openKids[pid];
      renderFacets((LAST && LAST.facets) || {});
      return;
    }
    var head = t.closest('[data-toggle-facet]');
    if (head) {
      var key = head.getAttribute('data-toggle-facet');
      var sec = el('facets').querySelector('[data-facet="' + key + '"]');
      if (sec) {
        sec.classList.toggle('collapsed');
        localStorage.setItem('facet.' + key, sec.classList.contains('collapsed') ? '0' : '1');
      }
      return;
    }
    var quick = t.closest('[data-quick]');
    if (quick) {
      var k = quick.getAttribute('data-quick');
      state[k] = !state[k]; state.page = 1; runSearch(); return;
    }
    var dayBtn = t.closest('[data-days]');
    if (dayBtn) {
      state.days = parseInt(dayBtn.getAttribute('data-days'), 10) || 0;
      state.page = 1; runSearch(); return;
    }
    var tierBtn = t.closest('[data-tier]');
    if (tierBtn) {
      state.tier = parseInt(tierBtn.getAttribute('data-tier'), 10) || 3;
      state.page = 1; runSearch(); return;
    }
    if (t.closest('[data-alljournals]')) {
      showAllJournals = !showAllJournals;
      renderFacets((LAST && LAST.facets) || {}); return;
    }
    var allNodes = t.closest('[data-allnodes]');
    if (allNodes) {
      var afid = allNodes.getAttribute('data-allnodes');
      showAllNodes[afid] = !showAllNodes[afid];
      renderFacets((LAST && LAST.facets) || {}); return;
    }
    var pick = t.closest('[data-pick]');
    if (pick) {
      var kind = pick.getAttribute('data-pick');
      var id = pick.getAttribute('data-id');
      if (kind === '__journal') toggleIn(state.journal, id);
      else toggleSel(kind, id);
      state.page = 1; runSearch();
    }
  });
  el('rail').addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var pick = e.target.closest('[data-pick]');
    if (pick) { e.preventDefault(); pick.click(); }
  });

  // ---- active filter chips
  el('activeFilters').addEventListener('click', function (e) {
    var b = e.target.closest('[data-drop]');
    if (!b) return;
    var kind = b.getAttribute('data-drop'), id = b.getAttribute('data-id');
    if (kind === 'all') {
      state.sel = {}; state.journal = [];
      state.tier = 3; state.days = 0;
      state.new_only = state.starred = state.unread = state.has_abs = false;
    } else if (kind === '__journal') toggleIn(state.journal, id);
    else if (kind === 'tier') state.tier = 3;
    else if (kind === 'days') state.days = 0;
    else if (kind === 'quick') state[id] = false;
    else toggleSel(kind, id);
    state.page = 1; runSearch();
  });

  // ---- results (delegated)
  el('reclist').addEventListener('click', function (e) {
    var t = e.target;
    var example = t.closest('[data-example]');
    if (example) {
      state.q = example.getAttribute('data-example') || '';
      el('q').value = state.q; state.page = 1; runSearch(); return;
    }
    var kwBtn = t.closest('[data-kw]');
    if (kwBtn) {
      var kw = kwBtn.getAttribute('data-kw');
      if (kw) {
        el('q').value = kw;
        state.q = kw;
        state.page = 1;
        runSearch();
      }
      return;
    }
    var cat = t.closest('[data-pickcat]');
    if (cat) {
      toggleSel(cat.getAttribute('data-pickcat'), cat.getAttribute('data-id'));
      state.page = 1; runSearch(); return;
    }
    var more = t.closest('[data-catmore]');
    if (more) {
      var wrap = more.closest('.cats');
      if (wrap) wrap.classList.add('expanded');
      return;
    }
    var rec = t.closest('.rec');
    if (!rec) return;
    var doi = rec.getAttribute('data-doi');

    if (t.closest('[data-expand]')) {
      var p = rec.querySelector('[data-abs]');
      var btn = t.closest('[data-expand]');
      if (p) {
        p.classList.toggle('clamped');
        btn.textContent = p.classList.contains('clamped')
          ? (state.scope === 'live' ? '查看摘要' : '展开全文摘要') : '收起摘要';
      }
      return;
    }
    if (t.closest('[data-star]')) {
      var on = !t.closest('[data-star]').classList.contains('on');
      setFlag(doi, 'starred', on, rec); return;
    }
    if (t.closest('[data-read]')) {
      setFlag(doi, 'read', !rec.classList.contains('isread'), rec); return;
    }
    if (t.closest('[data-copy]')) {
      copyText(doi.indexOf('openalex:') === 0
        ? ((LAST_PAPERS_MAP[doi] || {}).url || '') : doi, t.closest('[data-copy]')); return;
    }
  });

  el('pager').addEventListener('click', function (e) {
    var b = e.target.closest('[data-page]');
    if (!b || b.disabled) return;
    var n = parseInt(b.getAttribute('data-page'), 10);
    if (!n || n < 1) return;
    state.page = n; runSearch();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  window.addEventListener('hashchange', function () {
    hashToState();
    el('q').value = state.q;
    el('pageSize').value = String(state.page_size);
    syncSortControls();
    runSearch();
  });
}

function syncSortControls() {
  var d = el('sort'), m = el('sortMobile');
  if (d) d.value = state.sort;
  if (m) {
    var has = false;
    for (var i = 0; i < m.options.length; i++) {
      if (m.options[i].value === state.sort) { has = true; break; }
    }
    m.value = has ? state.sort : 'date';
  }
}

function setFlag(doi, field, value, recEl) {
  var pObj = LAST_PAPERS_MAP[doi];
  var external = !!(pObj && pObj.source_engine);
  var savePromise = (external && value)
    ? api('/api/paper/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper: pObj, starred: field === 'starred' })
      }).then(function (r) {
        if (!r || !r.ok || field === 'starred') return r;
        return api('/api/flag', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ doi: doi, field: field, value: value })
        });
      })
    : api('/api/flag', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doi: doi, field: field, value: value })
      });

  savePromise.then(function (r) {
    if (!r || !r.ok) return;
    if (field === 'starred') {
      var b = recEl.querySelector('[data-star]');
      if (b) { b.classList.toggle('on', value); b.textContent = value ? '★ 已收藏' : '☆ 收藏'; }
      if (pObj) pObj.starred = value;
    } else {
      recEl.classList.toggle('isread', value);
      var rb = recEl.querySelector('[data-read]');
      if (rb) rb.textContent = value ? '标为未读' : '标为已读';
      if (pObj) pObj.read_at = value ? '1' : '';
    }
    if ((field === 'read' && state.unread) || (field === 'starred' && state.starred)) {
      runSearch({ quiet: true });
    }
  }).catch(function () {});
}

function copyText(text, btn) {
  var done = function () {
    var old = btn.textContent;
    btn.textContent = '已复制 ✓';
    setTimeout(function () { btn.textContent = old; }, 1400);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(function () { fallback(); });
  } else { fallback(); }
  function fallback() {
    try {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', '');
      ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta); done();
    } catch (e) { btn.textContent = '复制失败'; }
  }
}

// -------------------------------------------------------------------- boot
/* ======================================================================
 * Gates: who is reading, and what do they work on?
 *
 * Nothing in the app shell runs until both questions are answered, so no
 * request can arrive without a session and no facet can render without a
 * field pack to describe it.
 * ====================================================================== */
var authMode = 'login';
var fieldCatalog = null;
var switchingField = false;

function showView(which) {
  ['authView', 'onboardView', 'acctView', 'appView'].forEach(function (id) {
    var node = el(id);
    if (node) node.hidden = (id !== which);
  });
  // the app shell stays mounted behind the account panel so closing it is instant
  if (which === 'acctView') el('appView').hidden = false;
}

function postJSON(path, body) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  });
}

function showErr(id, msg) {
  var box = el(id);
  if (!box) return;
  if (!msg) { box.hidden = true; box.textContent = ''; return; }
  box.hidden = false;
  box.textContent = msg;
}

// ---------------------------------------------------------------- sign in
function setAuthMode(mode, firstRun) {
  authMode = mode;
  var creating = mode === 'register';
  el('authNameRow').hidden = !creating;
  el('btnAuth').textContent = creating ? '创建账号' : '登录';
  el('authPass').setAttribute('autocomplete', creating ? 'new-password' : 'current-password');
  el('authSwitchText').textContent = creating ? '已经有账号了？' : '还没有账号？';
  el('btnAuthSwitch').textContent = creating ? '直接登录' : '创建账号';
  el('authSwitchRow').hidden = !!firstRun;
  el('authSub').textContent = firstRun
    ? '创建账号后，手机与电脑共享同一份文献库'
    : (creating ? '创建后手机与电脑用同一个账号同步'
                : '登录后手机与电脑共享同一份文献库');
  showErr('authErr', '');
}

function submitAuth(e) {
  if (e) e.preventDefault();
  var user = el('authUser').value.trim();
  var pass = el('authPass').value;
  if (!user || !pass) { showErr('authErr', '请填写用户名和密码'); return; }
  if (authMode === 'register' && pass.length < 8) {
    showErr('authErr', '密码至少 8 位'); return;
  }
  var btn = el('btnAuth');
  btn.disabled = true;
  var label = btn.textContent;
  btn.textContent = '请稍候…';
  showErr('authErr', '');

  var path = authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
  postJSON(path, {
    username: user, password: pass,
    display_name: el('authName').value.trim()
  }).then(function (d) {
    if (!d.ok) throw new Error(d.error || '登录失败');
    el('authPass').value = '';
    ME = d.user;
    startApp();
  }).catch(function (err) {
    showErr('authErr', err.message || String(err));
    btn.disabled = false;
    btn.textContent = label;
    el('authPass').focus();
    el('authPass').select();
  });
}

// ------------------------------------------------------ research direction
function fieldCardHtml(f, current, index) {
  var facets = (f.facets || []).map(function (x) {
    return '<span class="fc-chip">' + esc(x.zh) + ' ' + num(x.top) + '</span>';
  }).join('');
  return '<button class="fieldcard' + (current ? ' current' : '') +
      '" type="button" data-field="' + esc(f.id) + '">' +
    (current ? '<span class="fc-current">当前</span>' : '') +
    '<span class="fc-index">' + String(index + 1).padStart(2, '0') + ' <span>/ 研究方向</span></span>' +
    '<span class="fc-top">' +
      '<span class="fc-name">' +
        '<span class="fc-zh">' + esc(f.zh) + '</span>' +
        '<span class="fc-en">' + esc(f.en) + '</span>' +
      '</span>' +
    '</span>' +
    '<span class="fc-tag">' + esc(f.tagline || '') + '</span>' +
    '<span class="fc-meta">' + facets +
      '<span class="fc-chip n">' + num(f.categories) + ' 个分类</span>' +
      '<span class="fc-chip n">' + num(f.journals) + ' 种期刊</span>' +
    '</span></button>';
}

function renderFieldGrid() {
  var cur = (ME && ME.field) || '';
  var presets = (fieldCatalog && fieldCatalog.presets) || [];
  el('fieldGrid').innerHTML = presets.map(function (f, index) {
    return fieldCardHtml(f, f.id === cur, index);
  }).join('');
  var custom = fieldCatalog && fieldCatalog.custom;
  if (custom) {
    el('fieldGrid').insertAdjacentHTML('beforeend', fieldCardHtml(custom, true, presets.length));
  }
  var switching = !!(ME && ME.field);
  el('obKicker').textContent = switching ? '切换方向' : '可选功能';
  el('btnObBack').hidden = false;
  if (custom && custom.spec) prefillCustom(custom.spec);
}

function openOnboarding() {
  showView('onboardView');
  el('fieldGrid').innerHTML = '<div class="fc-loading">正在读取可选方向…</div>';
  api('/api/fields').then(function (d) {
    if (d.error) throw new Error(d.detail || d.error);
    fieldCatalog = d;
    if (d.custom_spec) d.custom = Object.assign({}, d.custom, { spec: d.custom_spec });
    renderFieldGrid();
  }).catch(function (err) {
    el('fieldGrid').innerHTML = '<div class="fc-loading">读取失败：' +
      esc(err.message || err) + '</div>';
  });
}

function chooseField(id, cardEl) {
  if (switchingField) return;
  switchingField = true;
  if (cardEl) { cardEl.classList.add('busy'); }
  postJSON('/api/me/field', { field: id }).then(function (d) {
    if (!d.ok) throw new Error(d.error || '设置失败');
    resetForNewField();
    startApp();
  }).catch(function (err) {
    switchingField = false;
    if (cardEl) cardEl.classList.remove('busy');
    alert('无法切换到这个方向：' + (err.message || err));
  });
}

// ---- custom direction ---------------------------------------------------
var catRows = 0;

function addCatRow(zh, kw) {
  catRows += 1;
  var i = catRows;
  var row = document.createElement('div');
  row.className = 'cf-cat';
  row.innerHTML =
    '<label class="field"><span class="field-label">分类名</span>' +
      '<input class="cf-cat-zh" type="text" maxlength="16" placeholder="例如：正极"></label>' +
    '<label class="field"><span class="field-label">该分类的关键词（逗号分隔）</span>' +
      '<input class="cf-cat-kw" type="text" placeholder="cathode, sulfur host"></label>' +
    '<button class="cf-x" type="button" data-delcat="' + i + '" aria-label="删除这个分类">✕</button>';
  el('cfCats').appendChild(row);
  if (zh) row.querySelector('.cf-cat-zh').value = zh;
  if (kw) row.querySelector('.cf-cat-kw').value = kw;
}

function prefillCustom(spec) {
  if (el('cfName').value) return;          // never clobber what is being typed
  el('cfName').value = spec.name || '';
  el('cfKw').value = (spec.keywords || []).join(', ');
  el('cfExclude').value = (spec.exclude || []).join(', ');
  el('cfCats').innerHTML = '';
  (spec.categories || []).forEach(function (c) {
    addCatRow(c.zh || c.name || '', (c.keywords || []).join(', '));
  });
}

function splitList(v) {
  return (v || '').split(/[,，;；\n]/).map(function (x) { return x.trim(); })
    .filter(Boolean);
}

function submitCustom() {
  var name = el('cfName').value.trim();
  var kw = splitList(el('cfKw').value);
  if (!name) { showErr('cfErr', '请给这个方向起个名字'); return; }
  if (kw.length < 2) { showErr('cfErr', '请至少填两个核心关键词，否则筛不准'); return; }
  var short = kw.filter(function (k) { return k.replace(/[^0-9a-z]/gi, '').length < 5 &&
                                              k.indexOf(' ') < 0; });
  if (short.length) {
    showErr('cfErr', '这些词太短，容易误匹配：' + short.join('、') + '。请换成更具体的词组。');
    return;
  }
  var cats = [];
  var rows = el('cfCats').querySelectorAll('.cf-cat');
  for (var i = 0; i < rows.length; i++) {
    var zh = rows[i].querySelector('.cf-cat-zh').value.trim();
    var kws = splitList(rows[i].querySelector('.cf-cat-kw').value);
    if (zh && kws.length) cats.push({ zh: zh, keywords: kws });
  }
  showErr('cfErr', '');
  var btn = el('btnCustom');
  btn.disabled = true;
  btn.textContent = '正在建立…';
  postJSON('/api/me/field', {
    custom: { name: name, keywords: kw, categories: cats,
              exclude: splitList(el('cfExclude').value) }
  }).then(function (d) {
    if (!d.ok) throw new Error(d.error || '建立失败');
    resetForNewField();
    startApp();
    if (d.dropped && d.dropped.length) {
      setTimeout(function () {
        notices([noticeHtml('warn', '<b>已忽略过短的关键词</b> — ' +
          esc(d.dropped.join('、')) + '，它们会匹配到无关文献。')]);
      }, 400);
    }
  }).catch(function (err) {
    showErr('cfErr', err.message || String(err));
    btn.disabled = false;
    btn.textContent = '用这个方向开始';
  });
}

function resetForNewField() {
  // a new field has different axes: keep nothing from the old one
  state = freshState();
  showAllNodes = {}; showAllJournals = false; openKids = {};
  LAST = null; switchingField = false;
  // a kept scroll offset hides the top of the new rail under the sticky header
  try { window.scrollTo(0, 0); } catch (e) {}
  try { history.replaceState(null, '', '#'); } catch (e) {}
  var b = el('btnCustom');
  if (b) { b.disabled = false; b.textContent = '用这个方向开始'; }
  var box = el('customBox');
  if (box) box.open = false;
}

// ------------------------------------------------------------ account menu
function closeMenu() {
  el('accountMenu').hidden = true;
  el('btnAccount').setAttribute('aria-expanded', 'false');
}

function toggleMenu() {
  var open = el('accountMenu').hidden;
  el('accountMenu').hidden = !open;
  el('btnAccount').setAttribute('aria-expanded', open ? 'true' : 'false');
}

function openAccount() {
  showView('acctView');
  showErr('pwErr', '');
  ['pwOld', 'pwNew', 'pwNew2'].forEach(function (id) { el(id).value = ''; });
  el('devList').textContent = '正在读取…';
  api('/api/me/sessions').then(function (d) {
    var list = d.sessions || [];
    if (!list.length) { el('devList').textContent = '没有其他设备。'; return; }
    el('devList').innerHTML = list.map(function (sn) {
      return '<div class="dev' + (sn.current ? ' now' : '') + '">' +
        '<b>' + esc(deviceName(sn.agent)) + '</b>' +
        (sn.current ? '<span>（当前设备）</span>' : '') +
        '<span class="when">' + esc(ago(sn.seen_at || sn.created_at)) + '</span></div>';
    }).join('');
  }).catch(function () { el('devList').textContent = '读取失败。'; });
}

function deviceName(agent) {
  agent = agent || '';
  if (/iPhone/i.test(agent)) return 'iPhone';
  if (/iPad/i.test(agent)) return 'iPad';
  if (/Android/i.test(agent)) return 'Android 手机';
  if (/Macintosh|Mac OS/i.test(agent)) return 'Mac';
  if (/Windows/i.test(agent)) return 'Windows 电脑';
  if (/Linux/i.test(agent)) return 'Linux 电脑';
  return '未知设备';
}

function submitPassword(e) {
  if (e) e.preventDefault();
  var oldPw = el('pwOld').value, a = el('pwNew').value, b = el('pwNew2').value;
  if (a !== b) { showErr('pwErr', '两次输入的新密码不一致'); return; }
  if (a.length < 8) { showErr('pwErr', '新密码至少 8 位'); return; }
  var btn = el('btnPw');
  btn.disabled = true; btn.textContent = '正在更新…';
  postJSON('/api/me/password', { current: oldPw, new: a }).then(function (d) {
    if (!d.ok) throw new Error(d.error || '更新失败');
    showView('appView');
    notices([noticeHtml('good', '<b>密码已更新</b> — 其他设备需要重新登录。')]);
  }).catch(function (err) {
    showErr('pwErr', err.message || String(err));
  }).then(function () {
    btn.disabled = false; btn.textContent = '更新密码';
  });
}

function logout() {
  postJSON('/api/auth/logout', {}).then(function () {
    ME = null; FIELD = null; FACETS = [];
    resetForNewField();
    setAuthMode('login', false);
    showView('authView');
    el('authUser').focus();
  });
}

function wireGates() {
  el('authForm').addEventListener('submit', submitAuth);
  el('btnAuthSwitch').addEventListener('click', function () {
    setAuthMode(authMode === 'login' ? 'register' : 'login', false);
    el('authUser').focus();
  });
  el('btnReveal').addEventListener('click', function () {
    var i = el('authPass');
    var show = i.type === 'password';
    i.type = show ? 'text' : 'password';
    this.textContent = show ? '隐藏' : '显示';
    this.setAttribute('aria-label', show ? '隐藏密码' : '显示密码');
  });

  el('fieldGrid').addEventListener('click', function (e) {
    var card = e.target.closest('[data-field]');
    if (!card) return;
    chooseField(card.getAttribute('data-field'), card);
  });
  el('btnAddCat').addEventListener('click', function () { addCatRow(); });
  el('cfCats').addEventListener('click', function (e) {
    var x = e.target.closest('[data-delcat]');
    if (x) x.closest('.cf-cat').remove();
  });
  el('btnCustom').addEventListener('click', submitCustom);
  el('btnObBack').addEventListener('click', function () {
    showView('appView');
  });

  el('btnField').addEventListener('click', function () { closeMenu(); openOnboarding(); });
  el('btnAccount').addEventListener('click', function (e) {
    e.stopPropagation(); toggleMenu();
  });
  el('accountMenu').addEventListener('click', function (e) {
    var item = e.target.closest('[data-act]');
    if (!item) return;
    closeMenu();
    var act = item.getAttribute('data-act');
    if (act === 'field') openOnboarding();
    else if (act === 'password' || act === 'devices') openAccount();
    else if (act === 'logout') logout();
  });
  document.addEventListener('click', function (e) {
    if (el('accountMenu').hidden) return;
    if (e.target.closest('#accountMenu') || e.target.closest('#btnAccount')) return;
    closeMenu();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    closeMenu();
    if (!el('acctView').hidden) showView('appView');
    else if (!el('onboardView').hidden && ME) showView('appView');
  });

  el('btnAcctClose').addEventListener('click', function () { showView('appView'); });
  el('pwForm').addEventListener('submit', submitPassword);
  el('btnRevoke').addEventListener('click', function () {
    postJSON('/api/me/sessions/revoke', {}).then(function () { openAccount(); });
  });
}

var appWired = false;

function boot() {
  wireGates();
  registerWorker();
  api('/api/auth/state').then(function (st) {
    if (st.authenticated) { ME = st.user; startApp(); return; }
    setAuthMode(st.has_users ? 'login' : 'register', !st.has_users);
    showView('authView');
    el('authUser').focus();
  }).catch(function (err) {
    setAuthMode('login', false);
    showView('authView');
    showErr('authErr', '无法连接到本地服务：' + (err.message || err) +
      '。请确认启动脚本仍在运行。');
  });
}

function startApp() {
  if (!appWired) { wire(); appWired = true; }
  hashToState();
  // a restored deep page makes no sense in the phone's append-style list
  if (isPhone() && state.page > 1) state.page = 1;
  el('q').value = state.q;
  el('pageSize').value = String(state.page_size);
  syncSortControls();
  showView('appView');
  showSkeleton();
  el('resCount').textContent = '正在载入…';

  api('/api/bootstrap').then(function (b) {
    if (b.error) throw new Error(b.detail || b.error);
    if (b.needs_field) {
      ME = b.user || ME;
      FIELD = null; FACETS = []; JOURNALS = []; TIER_LABELS = {};
      state.scope = 'live';
      renderIdentity();
      el('mastMeta').textContent = '跨学科实时检索';
      syncScopeTabs();
      notices([]);
      runSearch({ quiet: true });
      return;
    }
    ME = b.user || ME;
    FIELD = b.field || null;
    FACETS = b.facets || [];
    JOURNALS = b.journals || [];
    TIER_LABELS = b.tier_labels || {};
    renderIdentity();
    renderHeader(b);
    syncTabs();
    var dot = el('tabDot');
    if (dot) dot.hidden = !(b.stats && b.stats.new_count > 0);

    var msgs = [];
    var r = b.refresh || {};
    var st = b.stats || {};
    var axes = FACETS.map(function (f) { return f.zh; }).join('与');
    if (r.started || (r.status && r.status.running)) {
      msgs.push(noticeHtml('', '<b>正在为「' + esc(FIELD.zh) + '」抓取文献</b> — ' +
        esc(r.reason || '') + '，结果会自动刷新。', '<span class="spin"></span>'));
      startPolling(true);
    } else if (st.total) {
      msgs.push(noticeHtml('good',
        '<b>今日推送已就绪</b> — ' + esc(FIELD.zh) + '文献库共 ' + num(st.total) + ' 篇，' +
        esc(r.reason || '') + '。' + (axes ? ('可按' + esc(axes) + '精炼。') : '')));
      setTimeout(function () { el('notices').innerHTML = ''; }, 9000);
    } else {
      msgs.push(noticeHtml('warn', '<b>这个方向还没有文献</b> — ' +
        '点击右上角「立即更新」开始抓取，首次大约需要一到两分钟。'));
    }
    if (st.total && st.with_abs !== null && st.with_abs < st.total) {
      var gap = st.total - st.with_abs;
      msgs.push(noticeHtml('warn', '<b>' + num(gap) + ' 篇暂缺摘要</b> — ' +
        '部分出版商（主要是 Elsevier）不向公开数据库提供摘要，软件会持续重试。' +
        '可用「仅含摘要」筛选，或在 settings.json 填入 Elsevier 免费 API key（见 README）。',
        '', 'abstract-gap'));
    }
    notices(msgs);
    runSearch({ quiet: true });
  }).catch(function (err) {
    if (err && err.message === EXPIRED) return;
    el('resCount').textContent = '初始化失败';
    el('reclist').innerHTML = '<div class="empty"><h3>无法连接到本地服务</h3><p>' +
      esc(err.message || err) + '</p><p>请确认启动脚本仍在运行，然后刷新页面。</p></div>';
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else { boot(); }
