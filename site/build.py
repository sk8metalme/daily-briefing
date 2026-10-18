#!/usr/bin/env python3
"""daily-briefing の Markdown ログを GitHub Pages 用の静的サイトへ変換する。

入力:
  briefings/YYYY/MM/DD.md   日次ブリーフィング（追記のみ、front matter なし）
  briefings/YYYY/MM/figures/*.svg   図版（任意）
  selected-articles.md      選定済み記事インデックス

出力:
  _site/   そのまま GitHub Pages へデプロイできるディレクトリ

依存は markdown パッケージのみ。ブリーフィング本体には一切手を入れない
（front matter を要求しない）ため、cron routine の書き込み規約は変わらない。
"""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

ROOT = Path(__file__).resolve().parent.parent
BRIEFINGS = ROOT / "briefings"
INDEX_MD = ROOT / "selected-articles.md"
ASSETS = Path(__file__).resolve().parent / "assets"
OUT = ROOT / "_site"

SITE_TITLE = "Daily Briefing"
SITE_DESC = "AI 開発ワークフロー・組織の AI ネイティブ化に関する技術記事の日次ブリーフィング"
MERMAID_VERSION = "11.4.1"

# ---------------------------------------------------------------- parsing ---

FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})")
ARTICLE_RE = re.compile(r"^##\s+(\d+)\.\s*(.+?)\s*$")
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$")
H1_RE = re.compile(r"^#\s+Daily Briefing\s+(\d{4}-\d{2}-\d{2})")
META_RE = re.compile(r"^\s*[-*]\s+\*\*(?P<key>[^*]+)\*\*\s*[:：]\s*(?P<val>.+?)\s*$")
TITLE_SPLIT_RE = re.compile(r"^(?P<ja>.*?)\s*[（(]\s*原題\s*[:：]\s*(?P<orig>.+?)\s*[）)]\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")


def iter_logical_lines(lines: list[str]):
    """コードフェンスの内側かどうかを添えて行を返す。

    4 バッククォートの外側フェンス内に 3 バッククォートが入れ子になっている
    ブリーフィングがあるため、開いたフェンスと同じ記号列でしか閉じないものとして扱う。
    """
    open_fence: str | None = None
    for line in lines:
        m = FENCE_RE.match(line)
        if open_fence is None:
            if m:
                open_fence = m.group("fence")
            yield line, False
        else:
            # 開いたフェンス以上の長さの同種記号のみが閉じ記号
            if m and m.group("fence")[0] == open_fence[0] and len(m.group("fence")) >= len(open_fence):
                open_fence = None
            yield line, True


@dataclass
class Article:
    number: int
    title_ja: str
    title_orig: str
    url: str = ""
    published: str = ""
    source: str = ""
    sections: list[tuple[str, str]] = field(default_factory=list)  # (見出し, anchor)
    key_points: list[str] = field(default_factory=list)
    body_md: str = ""
    anchor: str = ""

    @property
    def display_title(self) -> str:
        return self.title_ja or self.title_orig or f"記事 {self.number}"

    @property
    def domain(self) -> str:
        m = re.match(r"https?://([^/]+)", self.url)
        return m.group(1).removeprefix("www.") if m else ""


@dataclass
class Briefing:
    day: date
    path: Path
    articles: list[Article]
    preamble_md: str = ""
    trailer_md: str = ""

    @property
    def slug(self) -> str:
        return f"briefings/{self.day:%Y/%m/%d}.html"

    @property
    def iso(self) -> str:
        return self.day.isoformat()


def slugify(text: str, fallback: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"[^\w\-]+", "-", text, flags=re.UNICODE).strip("-")
    return text or fallback


def parse_briefing(path: Path) -> Briefing | None:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    day: date | None = None
    for line in lines[:10]:
        m = H1_RE.match(line)
        if m:
            day = date.fromisoformat(m.group(1))
            break
    if day is None:
        # 見出しが欠けていてもパスから日付を復元する
        try:
            day = date(int(path.parent.parent.name), int(path.parent.name), int(path.stem))
        except ValueError:
            return None

    articles: list[Article] = []
    current: Article | None = None
    buf: list[str] = []
    preamble: list[str] = []
    in_key_points = False

    for line, inside_fence in iter_logical_lines(lines):
        if not inside_fence:
            m = ARTICLE_RE.match(line)
            if m:
                if current is not None:
                    current.body_md = "\n".join(buf).strip()
                    articles.append(current)
                buf = []
                in_key_points = False
                number = int(m.group(1))
                rawtitle = m.group(2)
                ts = TITLE_SPLIT_RE.match(rawtitle)
                current = Article(
                    number=number,
                    title_ja=(ts.group("ja") if ts else rawtitle).strip(),
                    title_orig=(ts.group("orig") if ts else "").strip(),
                    anchor=f"a{number}",
                )
                continue

        if current is None:
            if H1_RE.match(line):
                continue
            preamble.append(line)
            continue

        if not inside_fence:
            ms = SECTION_RE.match(line)
            if ms:
                heading = ms.group(1)
                anchor = f"{current.anchor}-{slugify(heading, str(len(current.sections) + 1))}"
                current.sections.append((heading, anchor))
                in_key_points = heading.startswith("重要ポイント")
                # attr_list 用に明示 ID を付与し、目次から安定してリンクできるようにする
                buf.append(f"### {heading} " + "{: #" + anchor + " }")
                continue

            mm = META_RE.match(line)
            if mm and not current.url:
                key, val = mm.group("key").strip(), mm.group("val").strip()
                if key == "URL":
                    current.url = re.sub(r"^<|>$", "", val)
                elif key.startswith("公開日"):
                    current.published = val
                elif key.startswith("著者"):
                    current.source = val
            elif mm:
                key, val = mm.group("key").strip(), mm.group("val").strip()
                if key.startswith("公開日") and not current.published:
                    current.published = val
                elif key.startswith("著者") and not current.source:
                    current.source = val

            if in_key_points:
                mb = BULLET_RE.match(line)
                if mb and len(current.key_points) < 6:
                    current.key_points.append(re.sub(r"\*\*|`", "", mb.group(1)))

        buf.append(line)

    if current is not None:
        current.body_md = "\n".join(buf).strip()
        articles.append(current)

    return Briefing(day=day, path=path, articles=articles, preamble_md="\n".join(preamble).strip())


def load_briefings() -> list[Briefing]:
    out: list[Briefing] = []
    for path in sorted(BRIEFINGS.rglob("*.md")):
        b = parse_briefing(path)
        if b is not None:
            out.append(b)
    out.sort(key=lambda b: b.day)
    return out


def parse_article_index() -> list[dict[str, str]]:
    if not INDEX_MD.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in INDEX_MD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        # タイトルに素の "|" が混ざっている行があるため、
        # 先頭を日付・末尾を URL とし、間をすべてタイトルとして復元する
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.match(r"^\d{4}-\d{2}-\d{2}$", cells[0]):
            continue
        title = "|".join(cells[1:-1]).replace("\\|", "|").strip()
        rows.append({"date": cells[0], "title": title, "url": cells[-1]})
    return rows


# -------------------------------------------------------------- rendering ---

class CJKEmphasis(Extension):
    """日本語本文中の ``**強調**`` を確実に <strong> にする。

    CommonMark の flanking 規則では、閉じ ``**`` の直前が約物
    （``）``『」』など）で直後が文字のとき閉じ記号と見なされないため、
    ``**制約（拡張）**は`` のような日本語で頻出する並びが素通しされる。
    インラインコードを処理する backtick（優先度 190）より後、
    既定の em_strong（60）より前に差し込むことで、
    コードブロック・インラインコードには触れずに強調だけを拾う。
    """

    STRONG = r"(\*{2})(?![\s*])(.+?)(?<![\s*])\*{2}(?!\*)"

    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(self.STRONG, "strong"), "cjk_strong", 65
        )


MD_EXTENSIONS = [
    "fenced_code",
    "tables",
    "attr_list",
    "sane_lists",
    "footnotes",
    "md_in_html",
    CJKEmphasis(),
]

IMG_SVG_RE = re.compile(r'<img\s+alt="(?P<alt>[^"]*)"\s+src="(?P<src>[^"]+\.svg)"\s*/?>')


def md_to_html(text: str, base_dir: Path) -> str:
    md = markdown.Markdown(extensions=MD_EXTENSIONS, output_format="html5")
    out = md.convert(text)
    return inline_local_svg(out, base_dir)


def inline_local_svg(html_text: str, base_dir: Path) -> str:
    """ローカル SVG を本文に展開し、ページ側の配色変数を継承させる。

    SVG が読めない場合は <img> のまま残す（Pages 側で図版ファイルも配信するため壊れない）。
    """

    def repl(m: re.Match[str]) -> str:
        src = m.group("src")
        if src.startswith(("http://", "https://", "//", "/")):
            return m.group(0)
        target = (base_dir / src).resolve()
        try:
            target.relative_to(ROOT)
            svg = target.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return m.group(0)
        svg = re.sub(r"<\?xml.*?\?>", "", svg, flags=re.DOTALL).strip()
        svg = re.sub(r"<!DOCTYPE.*?>", "", svg, flags=re.DOTALL).strip()
        label = html.escape(m.group("alt"))
        return (
            f'<figure class="fig" role="img" aria-label="{label}">{svg}'
            + (f"<figcaption>{label}</figcaption>" if label else "")
            + "</figure>"
        )

    return IMG_SVG_RE.sub(repl, html_text)


def page(title: str, body: str, depth: int, *, active: str = "", description: str = "") -> str:
    up = "../" * depth
    desc = html.escape(description or SITE_DESC)

    def nav(href: str, label: str, key: str) -> str:
        cls = ' class="active"' if key == active else ""
        return f'<a href="{up}{href}"{cls}>{label}</a>'

    return f"""<!doctype html>
<html lang="ja" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Noto+Sans+JP:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{up}assets/style.css">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<script>
  // テーマは描画前に確定させ、初回表示のちらつきを防ぐ
  try {{
    var t = localStorage.getItem('db-theme');
    if (t) document.documentElement.setAttribute('data-theme', t);
  }} catch (e) {{}}
</script>
</head>
<body>
<a class="skip" href="#main">本文へスキップ</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{up}index.html">
      <span class="brand-mark" aria-hidden="true"></span>
      <span class="brand-text">Daily<span class="brand-accent">Briefing</span></span>
    </a>
    <nav class="site-nav">
      {nav("index.html", "ホーム", "home")}
      {nav("archive.html", "アーカイブ", "archive")}
      {nav("articles.html", "記事インデックス", "articles")}
      {nav("about.html", "このサイトについて", "about")}
    </nav>
    <button class="theme-toggle" type="button" aria-label="配色を切り替える" title="配色を切り替える">
      <span class="theme-icon" aria-hidden="true"></span>
    </button>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>{html.escape(SITE_DESC)}</p>
    <p class="muted">Claude Code のクラウド routine が毎朝 06:30 JST に自動生成しています。
      <a href="https://github.com/sk8metalme/daily-briefing">GitHub リポジトリ</a></p>
  </div>
</footer>
<script type="module" src="{up}assets/app.js" data-mermaid="https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.esm.min.mjs"></script>
</body>
</html>
"""


def article_card(a: Article, href: str) -> str:
    meta = []
    if a.published:
        meta.append(html.escape(a.published))
    if a.domain:
        meta.append(html.escape(a.domain))
    metaline = f'<p class="card-meta">{" · ".join(meta)}</p>' if meta else ""
    points = "".join(f"<li>{html.escape(p)}</li>" for p in a.key_points[:3])
    orig = f'<p class="card-orig">{html.escape(a.title_orig)}</p>' if a.title_orig else ""
    return f"""<article class="card">
  <p class="card-num">{a.number}</p>
  <h3><a href="{href}#{a.anchor}">{html.escape(a.display_title)}</a></h3>
  {orig}
  {metaline}
  <ul class="card-points">{points}</ul>
</article>"""


# ------------------------------------------------------------ page builds ---

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def fmt_day(d: date) -> str:
    return f"{d:%Y年%-m月%-d日}（{WEEKDAYS[d.weekday()]}）"


def build_briefing_page(b: Briefing, prev: Briefing | None, nxt: Briefing | None) -> str:
    toc_items = []
    for a in b.articles:
        subs = "".join(
            f'<li><a href="#{anchor}">{html.escape(h)}</a></li>' for h, anchor in a.sections
        )
        toc_items.append(
            f'<li><a class="toc-article" href="#{a.anchor}">'
            f'<span class="toc-num">{a.number}</span>'
            f"<span>{html.escape(a.display_title)}</span></a>"
            f'<ul class="toc-sub">{subs}</ul></li>'
        )
    toc = f'<ol class="toc-list">{"".join(toc_items)}</ol>' if toc_items else ""

    sections_html = []
    for a in b.articles:
        meta_rows = []
        if a.url:
            safe = html.escape(a.url, quote=True)
            meta_rows.append(
                f'<div class="meta-row"><dt>URL</dt><dd>'
                f'<a href="{safe}" rel="noopener nofollow" target="_blank">{html.escape(a.url)}</a></dd></div>'
            )
        if a.published:
            meta_rows.append(f'<div class="meta-row"><dt>公開日</dt><dd>{html.escape(a.published)}</dd></div>')
        if a.source:
            meta_rows.append(f'<div class="meta-row"><dt>著者・媒体</dt><dd>{html.escape(a.source)}</dd></div>')
        metablock = f'<dl class="article-meta">{"".join(meta_rows)}</dl>' if meta_rows else ""

        # メタ情報は専用ブロックで描画するため、本文側の重複した箇条書きは落とす
        body_html = md_to_html(a.body_md, b.path.parent)
        body_html = re.sub(
            r"<ul>\s*(?:<li><strong>(?:URL|公開日|著者・媒体)</strong>.*?</li>\s*)+</ul>",
            "",
            body_html,
            flags=re.DOTALL,
        )
        orig = f'<p class="article-orig">{html.escape(a.title_orig)}</p>' if a.title_orig else ""
        sections_html.append(
            f"""<section class="article" id="{a.anchor}">
  <header class="article-head">
    <p class="article-num">記事 {a.number}</p>
    <h2>{html.escape(a.display_title)}</h2>
    {orig}
  </header>
  {metablock}
  <div class="prose">{body_html}</div>
</section>"""
        )

    pager = []
    if prev:
        pager.append(
            f'<a class="pager prev" href="../../../{prev.slug}"><span>前日</span>'
            f"<strong>{prev.iso}</strong></a>"
        )
    else:
        pager.append('<span class="pager disabled"></span>')
    if nxt:
        pager.append(
            f'<a class="pager next" href="../../../{nxt.slug}"><span>翌日</span>'
            f"<strong>{nxt.iso}</strong></a>"
        )
    else:
        pager.append('<span class="pager disabled"></span>')

    preamble = f'<div class="prose note">{md_to_html(b.preamble_md, b.path.parent)}</div>' if b.preamble_md else ""

    body = f"""<div class="wrap briefing-layout">
  <aside class="sidebar">
    <div class="sidebar-inner">
      <p class="sidebar-label">この日の記事</p>
      {toc}
      <p class="sidebar-label">ソース</p>
      <a class="sidebar-link" href="https://github.com/sk8metalme/daily-briefing/blob/main/briefings/{b.day:%Y/%m/%d}.md">Markdown 原文</a>
    </div>
  </aside>
  <div class="briefing-main">
    <header class="page-head">
      <p class="eyebrow">Daily Briefing</p>
      <h1><time datetime="{b.iso}">{fmt_day(b.day)}</time></h1>
      <p class="muted">{len(b.articles)} 件の記事</p>
    </header>
    {preamble}
    {"".join(sections_html)}
    <nav class="pager-nav">{"".join(pager)}</nav>
  </div>
</div>"""
    return page(f"{b.iso} — {SITE_TITLE}", body, depth=3, active="archive",
                description=f"{b.iso} の日次ブリーフィング: " + "／".join(a.display_title for a in b.articles[:3]))


def build_index(briefings: list[Briefing], rows: list[dict[str, str]]) -> str:
    latest = briefings[-1]
    recent = list(reversed(briefings[-13:-1]))
    total_articles = sum(len(b.articles) for b in briefings)
    span_days = (briefings[-1].day - briefings[0].day).days + 1

    cards = "".join(article_card(a, f"briefings/{latest.day:%Y/%m/%d}.html") for a in latest.articles)
    recent_rows = "".join(
        f'<li><a href="briefings/{b.day:%Y/%m/%d}.html">'
        f'<time datetime="{b.iso}">{b.iso}</time>'
        f'<span class="recent-titles">{html.escape("／".join(a.display_title for a in b.articles))}</span>'
        f"</a></li>"
        for b in recent
    )

    body = f"""<div class="hero">
  <div class="wrap">
    <p class="eyebrow">毎朝 06:30 JST 自動更新</p>
    <h1>AI 開発ワークフローの<br><span class="hero-accent">実践知</span>を毎日3件</h1>
    <p class="hero-lead">AI-Ready / SDD・AI-DLC / 組織の AI ネイティブ化 / 開発ワークフローへの AI 活用を対象に、
      世界中の新着記事から「自分の業務で再現できる」ものだけを選び、全文日本語で要約・図解・戦略分析しています。</p>
    <div class="stats">
      <div class="stat"><strong>{len(briefings)}</strong><span>ブリーフィング</span></div>
      <div class="stat"><strong>{total_articles}</strong><span>記事</span></div>
      <div class="stat"><strong>{span_days}</strong><span>日間の蓄積</span></div>
    </div>
    <div class="hero-actions">
      <a class="btn primary" href="briefings/{latest.day:%Y/%m/%d}.html">最新を読む</a>
      <a class="btn" href="archive.html">アーカイブ</a>
    </div>
  </div>
</div>

<div class="wrap">
  <section class="block">
    <div class="block-head">
      <h2>最新: <time datetime="{latest.iso}">{fmt_day(latest.day)}</time></h2>
      <a class="more" href="briefings/{latest.day:%Y/%m/%d}.html">全文を読む →</a>
    </div>
    <div class="card-grid">{cards}</div>
  </section>

  <section class="block">
    <div class="block-head">
      <h2>これまでのブリーフィング</h2>
      <a class="more" href="archive.html">すべて見る →</a>
    </div>
    <ul class="recent-list">{recent_rows}</ul>
  </section>
</div>"""
    return page(f"{SITE_TITLE} — AI 開発ワークフローの実践知", body, depth=0, active="home")


def build_archive(briefings: list[Briefing]) -> str:
    groups: dict[tuple[int, int], list[Briefing]] = {}
    for b in briefings:
        groups.setdefault((b.day.year, b.day.month), []).append(b)

    blocks = []
    for (year, month), items in sorted(groups.items(), reverse=True):
        cells = "".join(
            f'<li><a href="briefings/{b.day:%Y/%m/%d}.html" data-date="{b.iso}">'
            f'<strong>{b.day.day}</strong><span>{len(b.articles)}</span></a></li>'
            for b in items
        )
        titles = "".join(
            f'<li class="arch-row" data-search="{html.escape(" ".join([b.iso] + [a.display_title for a in b.articles] + [a.title_orig for a in b.articles]), quote=True)}">'
            f'<a href="briefings/{b.day:%Y/%m/%d}.html"><time datetime="{b.iso}">{b.iso}</time>'
            f'<span>{html.escape("／".join(a.display_title for a in b.articles))}</span></a></li>'
            for b in reversed(items)
        )
        blocks.append(
            f"""<section class="month" id="m{year}-{month:02d}">
  <h2>{year}年{month}月 <span class="muted">{len(items)} 日分</span></h2>
  <ul class="daygrid">{cells}</ul>
  <ul class="arch-list">{titles}</ul>
</section>"""
        )

    body = f"""<div class="wrap">
  <header class="page-head">
    <p class="eyebrow">Archive</p>
    <h1>アーカイブ</h1>
    <p class="muted">{len(briefings)} 日分 / {sum(len(b.articles) for b in briefings)} 記事。タイトル・日付で絞り込めます。</p>
  </header>
  <div class="filter">
    <input type="search" id="arch-filter" placeholder="キーワードで絞り込む（例: AI-DLC、Wardley、DORA）" autocomplete="off">
    <p class="filter-count muted" id="arch-count"></p>
  </div>
  {"".join(blocks)}
</div>"""
    return page(f"アーカイブ — {SITE_TITLE}", body, depth=0, active="archive")


def build_articles(rows: list[dict[str, str]]) -> str:
    domains: dict[str, int] = {}
    for r in rows:
        m = re.match(r"https?://([^/]+)", r["url"])
        d = m.group(1).removeprefix("www.") if m else "—"
        domains[d] = domains.get(d, 0) + 1
    top = sorted(domains.items(), key=lambda kv: (-kv[1], kv[0]))[:12]

    trs = "".join(
        f'<tr data-search="{html.escape(r["date"] + " " + r["title"] + " " + r["url"], quote=True)}">'
        f'<td class="c-date"><a href="briefings/{r["date"][:4]}/{r["date"][5:7]}/{r["date"][8:10]}.html">{r["date"]}</a></td>'
        f'<td class="c-title"><a href="{html.escape(r["url"], quote=True)}" rel="noopener nofollow" target="_blank">{html.escape(r["title"])}</a></td>'
        f'<td class="c-dom">{html.escape((re.match(r"https?://([^/]+)", r["url"]).group(1).removeprefix("www.") if re.match(r"https?://([^/]+)", r["url"]) else "—"))}</td>'
        f"</tr>"
        for r in reversed(rows)
    )
    chips = "".join(f'<button class="chip" type="button" data-q="{html.escape(d, quote=True)}">{html.escape(d)} <span>{n}</span></button>' for d, n in top)

    body = f"""<div class="wrap">
  <header class="page-head">
    <p class="eyebrow">Index</p>
    <h1>記事インデックス</h1>
    <p class="muted">これまでに選定した {len(rows)} 件。重複選定を防ぐためのインデックスを兼ねています。</p>
  </header>
  <div class="filter">
    <input type="search" id="art-filter" placeholder="タイトル・URL・日付で検索" autocomplete="off">
    <p class="filter-count muted" id="art-count"></p>
  </div>
  <div class="chips">{chips}</div>
  <div class="table-scroll">
    <table class="arttable">
      <thead><tr><th>選定日</th><th>タイトル</th><th>媒体</th></tr></thead>
      <tbody id="art-body">{trs}</tbody>
    </table>
  </div>
</div>"""
    return page(f"記事インデックス — {SITE_TITLE}", body, depth=0, active="articles")


def build_about(briefings: list[Briefing], rows: list[dict[str, str]]) -> str:
    about_md = (ROOT / "site" / "about.md")
    content = md_to_html(about_md.read_text(encoding="utf-8"), ROOT) if about_md.exists() else ""
    body = f"""<div class="wrap narrow">
  <header class="page-head">
    <p class="eyebrow">About</p>
    <h1>このサイトについて</h1>
  </header>
  <div class="prose">{content}</div>
</div>"""
    return page(f"このサイトについて — {SITE_TITLE}", body, depth=0, active="about")


# ------------------------------------------------------------------ main ---


def build_search_index(briefings: list[Briefing]) -> list[dict]:
    out = []
    for b in briefings:
        for a in b.articles:
            out.append(
                {
                    "d": b.iso,
                    "n": a.number,
                    "t": a.display_title,
                    "o": a.title_orig,
                    "s": a.domain,
                    "k": a.key_points[:4],
                    "h": f"briefings/{b.day:%Y/%m/%d}.html#{a.anchor}",
                }
            )
    return out


def copy_figures() -> int:
    """briefings/ 配下の .md 以外（図版等）を出力へそのままコピーする。"""
    count = 0
    for src in BRIEFINGS.rglob("*"):
        if src.is_dir() or src.suffix == ".md" or src.name == ".gitkeep":
            continue
        rel = src.relative_to(ROOT)
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    return count


def main() -> None:
    briefings = load_briefings()
    if not briefings:
        raise SystemExit("briefings/ に対象ファイルがありません")
    rows = parse_article_index()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for i, b in enumerate(briefings):
        prev = briefings[i - 1] if i > 0 else None
        nxt = briefings[i + 1] if i + 1 < len(briefings) else None
        dst = OUT / b.slug
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(build_briefing_page(b, prev, nxt), encoding="utf-8")

    (OUT / "index.html").write_text(build_index(briefings, rows), encoding="utf-8")
    (OUT / "archive.html").write_text(build_archive(briefings), encoding="utf-8")
    (OUT / "articles.html").write_text(build_articles(rows), encoding="utf-8")
    (OUT / "about.html").write_text(build_about(briefings, rows), encoding="utf-8")
    (OUT / "search-index.json").write_text(
        json.dumps(build_search_index(briefings), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    shutil.copytree(ASSETS, OUT / "assets", dirs_exist_ok=True)
    figures = copy_figures()

    latest = briefings[-1]
    print(
        f"built {len(briefings)} briefings / {sum(len(b.articles) for b in briefings)} articles "
        f"/ {len(rows)} index rows / {figures} figure files -> {OUT}"
    )
    empty = [b.iso for b in briefings if not b.articles]
    if empty:
        print("WARNING: 記事を抽出できなかった日: " + ", ".join(empty))
    malformed = [r["date"] for r in rows if not r["url"].startswith("http")]
    if malformed:
        print("WARNING: selected-articles.md の URL 列が壊れている行: " + ", ".join(malformed))
    indexed = {r["url"].rstrip("/") for r in rows}
    unindexed = [
        f"{b.iso}#{a.number}"
        for b in briefings
        for a in b.articles
        if a.url.rstrip("/") not in indexed
    ]
    if unindexed:
        print(
            "WARNING: selected-articles.md に載っていない記事（重複選定の恐れ）: "
            + ", ".join(unindexed)
        )
    print(f"latest: {latest.iso}")


if __name__ == "__main__":
    main()
