// Daily Briefing — テーマ切替 / Mermaid 描画 / 一覧の絞り込み / 目次の追従

/* ------------------------------------------------------------ theme ----- */

const root = document.documentElement;

function currentPalette() {
  const cs = getComputedStyle(root);
  const v = (n, f) => (cs.getPropertyValue(n).trim() || f);
  return {
    paper: v('--paper', '#f5f5f5'),
    paper2: v('--paper-2', '#ffffff'),
    paper3: v('--paper-3', '#ecebe8'),
    ink: v('--ink', '#2d3142'),
    muted: v('--muted', '#6b6f80'),
    rule: v('--rule-solid', '#c4c3bf'),
    accent: v('--accent', '#bf4520'),
    accentTint: v('--accent-tint', '#f6e3dc'),
  };
}

function setTheme(mode) {
  root.setAttribute('data-theme', mode);
  try { localStorage.setItem('db-theme', mode); } catch (e) { /* private mode */ }
  renderMermaid();
}

document.querySelector('.theme-toggle')?.addEventListener('click', () => {
  const now = root.getAttribute('data-theme') || 'auto';
  const isDark = now === 'dark'
    || (now === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  setTheme(isDark ? 'light' : 'dark');
});

/* ---------------------------------------------------------- mermaid ----- */

let mermaidLib = null;
let mermaidSeq = 0;

function collectMermaidBlocks() {
  // 4 バッククォートのコードブロック内に書かれた ```mermaid は <code> にならないため、
  // ここでは実際の mermaid ブロックだけが拾われる。
  const blocks = [];
  document.querySelectorAll('pre > code.language-mermaid').forEach((code) => {
    const pre = code.parentElement;
    const host = document.createElement('div');
    host.className = 'mermaid-card';
    host.dataset.src = code.textContent;
    pre.replaceWith(host);
    blocks.push(host);
  });
  document.querySelectorAll('.mermaid-card').forEach((el) => {
    if (!blocks.includes(el)) blocks.push(el);
  });
  return blocks;
}

async function renderMermaid() {
  const hosts = collectMermaidBlocks();
  if (!hosts.length) return;

  if (!mermaidLib) {
    const url = document.querySelector('script[data-mermaid]')?.dataset.mermaid;
    if (!url) return;
    try {
      mermaidLib = (await import(url)).default;
    } catch (e) {
      hosts.forEach((h) => { h.textContent = h.dataset.src; });
      return;
    }
  }

  const p = currentPalette();
  mermaidLib.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    fontFamily: '"Geist", "Noto Sans JP", sans-serif',
    fontSize: 14,
    htmlLabels: false,
    flowchart: { curve: 'basis', htmlLabels: false, padding: 12, nodeSpacing: 44, rankSpacing: 52 },
    sequence: { actorMargin: 48, mirrorActors: false },
    theme: 'base',
    themeVariables: {
      background: p.paper2,
      primaryColor: p.paper3,
      primaryTextColor: p.ink,
      primaryBorderColor: p.rule,
      secondaryColor: p.paper2,
      tertiaryColor: p.paper,
      lineColor: p.muted,
      textColor: p.ink,
      mainBkg: p.paper3,
      nodeBorder: p.rule,
      clusterBkg: p.paper,
      clusterBorder: p.rule,
      edgeLabelBackground: p.paper2,
      noteBkgColor: p.accentTint,
      noteBorderColor: p.accent,
    },
  });

  for (const host of hosts) {
    const src = host.dataset.src || '';
    if (!src.trim()) continue;
    const id = `mmd-${mermaidSeq++}`;
    try {
      const { svg } = await mermaidLib.render(id, src);
      host.innerHTML = svg;
    } catch (e) {
      host.innerHTML = '';
      const msg = document.createElement('p');
      msg.className = 'mermaid-error';
      msg.textContent = '図を描画できませんでした（Mermaid 構文エラー）。以下は元のソースです。';
      const pre = document.createElement('pre');
      pre.textContent = src;
      host.append(msg, pre);
      document.getElementById(`d${id}`)?.remove();
    }
  }
}

/* ----------------------------------------------------------- filters ---- */

function normalize(s) {
  return s.toLowerCase().normalize('NFKC');
}

function wireFilter(inputId, countId, rowSelector, groupSelector) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const count = document.getElementById(countId);
  const rows = Array.from(document.querySelectorAll(rowSelector));
  const groups = groupSelector ? Array.from(document.querySelectorAll(groupSelector)) : [];
  const total = rows.length;

  const apply = () => {
    const terms = normalize(input.value).split(/\s+/).filter(Boolean);
    let shown = 0;
    rows.forEach((row) => {
      const hay = normalize(row.dataset.search || row.textContent);
      const ok = terms.every((t) => hay.includes(t));
      row.hidden = !ok;
      if (ok) shown += 1;
    });
    groups.forEach((g) => {
      g.hidden = !g.querySelector(`${rowSelector}:not([hidden])`);
    });
    if (count) {
      count.textContent = terms.length ? `${shown} / ${total} 件が一致` : `${total} 件`;
    }
    const url = new URL(window.location.href);
    if (input.value) url.searchParams.set('q', input.value);
    else url.searchParams.delete('q');
    history.replaceState(null, '', url);
  };

  const initial = new URL(window.location.href).searchParams.get('q');
  if (initial) input.value = initial;
  input.addEventListener('input', apply);
  apply();

  document.querySelectorAll('.chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const q = chip.dataset.q || '';
      const on = chip.getAttribute('aria-pressed') === 'true';
      document.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-pressed', 'false'));
      chip.setAttribute('aria-pressed', on ? 'false' : 'true');
      input.value = on ? '' : q;
      apply();
    });
  });
}

/* ---------------------------------------------------------- scrollspy --- */

function wireScrollSpy() {
  const links = Array.from(document.querySelectorAll('.toc-sub a, .toc-article'));
  if (!links.length) return;
  const byId = new Map();
  links.forEach((a) => {
    const id = decodeURIComponent(a.getAttribute('href') || '').slice(1);
    const el = id && document.getElementById(id);
    if (el) byId.set(el, a);
  });
  if (!byId.size) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const link = byId.get(entry.target);
      if (!link) return;
      if (entry.isIntersecting) {
        links.forEach((l) => l.classList.remove('current'));
        link.classList.add('current');
      }
    });
  }, { rootMargin: '-80px 0px -70% 0px', threshold: 0 });

  byId.forEach((_, el) => observer.observe(el));
}

/* -------------------------------------------------------------- boot ---- */

renderMermaid();
wireFilter('arch-filter', 'arch-count', '.arch-row', '.month');
wireFilter('art-filter', 'art-count', '.arttable tbody tr', null);
wireScrollSpy();

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if ((root.getAttribute('data-theme') || 'auto') === 'auto') renderMermaid();
});
