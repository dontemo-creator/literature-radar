# -*- coding: utf-8 -*-
"""Desktop layout, the two gates, and switching research directions.

The switch is the interesting part: a different field declares different axes,
so the rail, the URL state and the record chips all have to be rebuilt with
nothing left over from the previous field.  Skips when Chrome is absent.
"""
import json, os, pathlib, sys, tempfile, threading, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

_tmp = tempfile.TemporaryDirectory()
TMP = pathlib.Path(_tmp.name)
os.environ["SSB_DATA_DIR"] = str(TMP)

from app import config                                        # noqa: E402
config.DATA_DIR = TMP
config.DB_PATH = TMP / "desk.db"

from app import fields, server, store                         # noqa: E402
from app.sources import live_search                            # noqa: E402

fails = []
SSB, LIB = "solid-state-battery", "lithium-ion-battery"
SHOTS = pathlib.Path(os.environ.get("SSB_SHOT_DIR", TMP))


def check(name, got, want=True):
    ok = got == want
    if not ok:
        fails.append((name, got, want))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}")
    return ok


def seed():
    store.init()
    for field in (SSB, LIB):
        store.meta_set("last_refresh_ok:" + field, store.now_iso())
    rows = [
        (SSB, "10.2/s%d", "%02d Argyrodite sulfide solid electrolyte for solid-state cells",
         {"chemistry": ["sulfide", "sulfide.argyrodite"], "theme": ["interface"]}, "sulfide"),
        (SSB, "10.2/o%d", "%02d Garnet LLZO oxide electrolyte against lithium metal",
         {"chemistry": ["oxide", "oxide.garnet"], "theme": ["limetal"]}, "oxide"),
        (LIB, "10.3/c%d", "%02d High-nickel NCM cathode for lithium-ion batteries",
         {"cathode": ["cathode.layered"], "anode": [], "electrolyte": [],
          "theme": ["theme.degradation"]}, "cathode.layered"),
        (LIB, "10.3/a%d", "%02d Silicon anode with a designed binder for Li-ion cells",
         {"cathode": [], "anode": ["anode.silicon"], "electrolyte": [],
          "theme": ["theme.fastcharge"]}, "anode.silicon"),
    ]
    for field, doi_fmt, title_fmt, labels, primary in rows:
        for i in range(9 if field == SSB else 6):
            doi = doi_fmt % i
            store.upsert(field, {
                "doi": doi, "title": title_fmt % i,
                "abstract": "An abstract about %s. " % primary * 8,
                "abstract_source": "crossref", "journal": "Joule", "journal_tier": 1,
                "journal_jif": 38.6, "authors": "Li, H.", "author_count": 1,
                "pub_date": "2026-09-0%d" % (1 + i % 8), "indexed_date": "2026-09-01",
                "url": "https://doi.org/" + doi, "doc_type": "journal-article",
                "is_oa": 0, "cited_by": i,
            }, labels, primary, 40.0)


def typed(b, selector, value):
    b.js("(function(){var e=document.querySelector(%s);e.focus();e.value=%s;"
         "e.dispatchEvent(new Event('input',{bubbles:true}));"
         "e.dispatchEvent(new Event('change',{bubbles:true}));})()"
         % (json.dumps(selector), json.dumps(value)))


def run():
    try:
        from cdp import Browser, CHROME
    except Exception as exc:
        print("  SKIP: cannot import the CDP helper (%s)" % exc)
        return 0
    if not pathlib.Path(CHROME).exists():
        print("  SKIP: Google Chrome not installed at %s" % CHROME)
        return 0

    seed()
    def sample_global(q, page=1, page_size=25, sort="date", mode="broad"):
        if not q:
            return {"papers": [], "total": 0, "pages": 0, "page": page,
                    "page_size": page_size, "source": "none", "search_terms": ""}
        return {"papers": [{
            "doi": "10.2/global", "title": "New solid-state battery algorithm",
            "authors": "A Researcher", "journal": "Example Journal",
            "pub_date": "2026-09-22", "url": "https://doi.org/10.2/global",
            "abstract": "A new paper about solid-state batteries.",
            "journal_tier": 3, "cited_by": 0, "labels": {}, "source_engine": "openalex",
        }], "total": 1, "pages": 1, "page": page, "page_size": page_size,
                "source": "openalex", "search_terms": '"solid-state battery"'}
    live_search.query_global = sample_global
    def sample_hot(q, mode="broad", limit=12):
        return {"papers": [{
            "doi": "10.2/hot", "title": "Hot solid-state battery paper",
            "authors": "A Researcher", "journal": "Example Journal",
            "pub_date": "2026-09-22", "url": "https://doi.org/10.2/hot",
            "abstract": "A recent paper.", "cited_by": 3, "recent_citations": 2,
        }], "total": 1, "source": "openalex", "candidates_checked": 1,
            "from_date": "2026-08-25", "to_date": "2026-09-23"}
    live_search.query_hot = sample_hot
    httpd, port = server.serve("127.0.0.1", 8920)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.2},
                     daemon=True).start()
    time.sleep(0.4)
    b = None
    try:
        b = Browser("http://127.0.0.1:%d/" % port, width=1440, height=900, scale=1.0)

        print("\n-- 登录界面（桌面）--")
        check("登录卡出现", b.wait_js("!document.getElementById('authView').hidden"))
        check("卡片居中且不过宽", b.js(
            "(function(){var r=document.querySelector('.gate-card').getBoundingClientRect();"
            "return r.width<=420 && Math.abs((r.left+r.right)/2 - window.innerWidth/2)<2;})()"))
        check("桌面无横向溢出", b.js(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        b.shot(str(SHOTS / "01-login.png"))
        typed(b, "#authUser", "lihengbo")
        typed(b, "#authPass", "a-good-long-secret")
        typed(b, "#authName", "李恒博")
        check("注册", b.tap("#btnAuth"))

        print("\n-- 全球检索入口（桌面）--")
        check("注册后直接进入全球检索", b.wait_js(
            "!document.getElementById('appView').hidden && "
            "document.getElementById('appView').classList.contains('global-mode')"))
        check("没有强制选择方向", b.js("document.getElementById('onboardView').hidden"))
        check("显示搜索示例", b.wait_js(
            "!!document.querySelector('[data-example=\"固态电池\"]')"))
        check("示例词可检索", b.tap('[data-example="固态电池"]'))
        check("全球结果出现", b.wait_js(
            "document.querySelector('.rec-title') && "
            "document.querySelector('.rec-title').textContent.indexOf('solid-state battery') >= 0"))
        check("分页按全球结果工作", b.js("document.getElementById('pager').textContent.indexOf('1') >= 0"))
        b.shot(str(SHOTS / "02-global.png"))
        check("打开近30天热门", b.tap("#tabHot"))
        check("热门论文可见", b.wait_js(
            "!document.getElementById('hotPane').hidden && "
            "document.getElementById('hotList').textContent.indexOf('Hot solid-state battery paper') >= 0"))
        check("热门视图写入地址", b.js("location.hash.indexOf('view=hot') >= 0"))
        check("热门视图无横向溢出", b.js(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        b.shot(str(SHOTS / "02-hot.png"))
        check("切回最新文献", b.tap("#tabRecent"))
        check("打开定向追踪设置", b.tap("#btnField"))

        print("\n-- 方向问询（桌面）--")
        check("方向页出现", b.wait_js("!document.getElementById('onboardView').hidden"))
        check("方向卡加载完成", b.wait_js(
            "document.querySelectorAll('#fieldGrid .fieldcard').length >= 6"))
        check("多列网格", b.js(
            "(function(){var c=document.querySelectorAll('.fieldcard');"
            "return c.length>1 && c[1].getBoundingClientRect().left >"
            " c[0].getBoundingClientRect().left + 40;})()"))
        check("每张卡都有说明与统计", b.js(
            "Array.prototype.every.call(document.querySelectorAll('.fieldcard'),"
            "function(c){return c.querySelector('.fc-tag').textContent.length>4 &&"
            " c.querySelectorAll('.fc-chip').length>=3;})"))
        b.shot(str(SHOTS / "02-direction.png"))
        check("选择固态电池", b.tap('[data-field="solid-state-battery"]'))

        print("\n-- 固态电池：两条轴 --")
        check("方向已生效", b.wait_js(
            "window.FIELD && window.FIELD.id === 'solid-state-battery'", tries=50))
        check("列表渲染", b.wait_js(
            "document.querySelectorAll('.rec:not(.skel)').length > 0", tries=50))
        # quick / days / tier / journal are sections too, so 2 axes -> 6 sections
        check("分面区块数（3 固定 + 2 轴 + 期刊）",
              b.js("document.querySelectorAll('#facets .facet[data-facet]').length"), 6)
        check("有电解质体系轴", b.js(
            "!!document.querySelector('[data-facet=\"chemistry\"]')"))
        check("有研究主题轴", b.js("!!document.querySelector('[data-facet=\"theme\"]')"))
        check("没有锂离子的轴", b.js(
            "!document.querySelector('[data-facet=\"cathode\"]')"))
        check("库内 18 篇", b.wait_js(
            "document.getElementById('resCount').textContent.indexOf('18') >= 0"))
        b.shot(str(SHOTS / "03-app-ssb.png"))
        check("点体系筛选", b.tap('[data-pick="chemistry"][data-id="sulfide"]')); time.sleep(1.2)
        check("  URL 记录", b.js("location.hash.indexOf('f.chemistry=sulfide') >= 0"))
        check("  结果收窄到 9 篇", b.wait_js(
            "document.getElementById('resCount').textContent.indexOf('9') >= 0"))

        print("\n-- 切换到锂离子电池：四条轴 --")
        check("打开方向页", b.tap("#btnField"))
        check("  方向页出现", b.wait_js("!document.getElementById('onboardView').hidden"))
        check("切换", b.tap('[data-field="lithium-ion-battery"]'))
        check("新方向已生效", b.wait_js(
            "window.FIELD && window.FIELD.id === 'lithium-ion-battery'", tries=60))
        check("列表重建", b.wait_js(
            "document.querySelectorAll('.rec:not(.skel)').length > 0", tries=60))
        check("分面区块数（3 固定 + 4 轴 + 期刊）",
              b.js("document.querySelectorAll('#facets .facet[data-facet]').length"), 8)
        check("标题已改", b.js("document.title"), "锂离子电池文献雷达")
        check("旧方向的轴已消失", b.js(
            "!document.querySelector('[data-facet=\"chemistry\"]')"))
        for axis in ("cathode", "anode", "electrolyte", "theme"):
            check("有新轴 " + axis, b.js(
                "!!document.querySelector('[data-facet=\"%s\"]')" % axis))
        check("旧筛选条件未残留", b.js("location.hash.indexOf('chemistry') < 0"))
        check("条件条已清空", b.js(
            "document.getElementById('activeFilters').hidden"))
        check("只看到锂离子的 12 篇", b.js(
            "document.getElementById('resCount').textContent.indexOf('12') >= 0"))
        check("卡片首个标签来自新方向独有的轴", b.js(
            "(function(){var c=document.querySelector('.rec .cat');"
            "return c ? c.getAttribute('data-pickcat') : '';})()") in
              ("cathode", "anode", "electrolyte"), True)
        b.shot(str(SHOTS / "04-app-lib.png"))
        check("换方向后回到顶部", b.js("window.scrollY"), 0)
        check("在新方向里筛选", b.tap('[data-pick="anode"][data-id="anode.silicon"]'))
        check("  URL 用新轴名", b.wait_js(
            "location.hash.indexOf('f.anode=anode.silicon') >= 0"))
        check("  结果收窄到 6 篇", b.wait_js(
            "document.getElementById('resCount').textContent.indexOf('6') >= 0"))

        print("\n-- 账号面板 --")
        check("打开", b.tap("#btnAccount") and b.tap('[data-act="password"]'))
        check("  面板出现", b.wait_js("!document.getElementById('acctView').hidden"))
        time.sleep(0.6)                       # let the fade-in finish before the shot
        check("  面板完全不透明", b.js(
            "getComputedStyle(document.querySelector('#acctView .gate-card')).opacity"), "1")
        b.shot(str(SHOTS / "05-account.png"))
        typed(b, "#pwOld", "a-good-long-secret")
        typed(b, "#pwNew", "new-longer-secret")
        typed(b, "#pwNew2", "mismatch-secret")
        check("不一致时拒绝", b.tap("#btnPw")); time.sleep(0.4)
        check("  给出提示", b.js("!document.getElementById('pwErr').hidden"))
        typed(b, "#pwNew2", "new-longer-secret")
        check("改密码", b.tap("#btnPw")); time.sleep(1.0)
        check("  回到列表并保持登录", b.js(
            "document.getElementById('acctView').hidden && "
            "!document.getElementById('appView').hidden"))
        check("  改密后会话仍有效", b.wait_js(
            "document.querySelectorAll('.rec').length > 0"))
        print("\n  截图目录: %s" % SHOTS)
    finally:
        if b:
            b.close()
        httpd.shutdown()
        httpd.server_close()

    print("\n%s" % ("ALL DESKTOP CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    code = 1 if run() else 0
    _tmp.cleanup()
    sys.exit(code)
