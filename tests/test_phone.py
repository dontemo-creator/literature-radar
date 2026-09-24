# -*- coding: utf-8 -*-
"""Phone layout and touch interactions, driven through Chrome DevTools.

Headless Chrome will not open a window narrower than 500 px, so the phone
layout can only be exercised under device emulation over CDP -- and only real
coordinate taps catch the class of bug where an invisible overlay swallows
every touch.  Skips cleanly when Chrome is not installed.

The run walks the whole first-time path a person actually takes: create an
account, answer "which direction do you work on?", then read.
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
config.DB_PATH = TMP / "phone.db"

from app import server, store                                 # noqa: E402

fails = []
SSB = "solid-state-battery"
SHOTS = pathlib.Path(os.environ.get("SSB_SHOT_DIR", TMP))


def check(name, got, want=True):
    ok = got == want
    if not ok:
        fails.append((name, got, want))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}")
    return ok


def seed(n=60):
    store.init()
    # pretend the library was refreshed just now, so no network call is made
    store.meta_set("last_refresh_ok:" + SSB, store.now_iso())
    fams = [("sulfide", ["sulfide", "sulfide.argyrodite"], ["interface"]),
            ("halide", ["halide", "halide.chloride"], ["transport"]),
            ("polymer", ["polymer", "polymer.peo"], ["limetal"]),
            ("oxide", ["oxide", "oxide.garnet"], ["characterization"])]
    for i in range(n):
        fam, chem, themes = fams[i % len(fams)]
        store.upsert(SSB, {
            "doi": "10.1/p%03d" % i,
            "title": "Paper %02d on %s solid electrolytes for all-solid-state batteries" % (i, fam),
            "abstract": ("A study of %s solid electrolytes. " % fam) * 12,
            "abstract_source": "crossref", "journal": "Joule", "journal_tier": 1,
            "journal_jif": 38.6, "authors": "Zhang, Y.; Li, H.", "author_count": 2,
            "pub_date": "2026-09-%02d" % (1 + i % 7), "indexed_date": "2026-09-01",
            "url": "https://doi.org/10.1/p%03d" % i,
            "doc_type": "journal-article", "is_oa": 0, "cited_by": i,
        }, {"chemistry": chem, "theme": themes}, fam, 40.0)


def typed(b, selector, value):
    """Set an input the way a person does, so the app's listeners fire."""
    b.js("(function(){var e=document.querySelector(%s);e.focus();e.value=%s;"
         "e.dispatchEvent(new Event('input',{bubbles:true}));"
         "e.dispatchEvent(new Event('change',{bubbles:true}));})()"
         % (json.dumps(selector), json.dumps(value)))


def reachable(b, sel):
    """Is the element actually the thing a finger would hit at its centre?"""
    return b.js(
        "(function(){var e=document.querySelector(%s);if(!e)return 'missing';"
        "var r=e.getBoundingClientRect();"
        "if(r.width===0||r.height===0)return 'invisible';"
        "if(r.top<0||r.top>window.innerHeight)return 'offscreen';"
        "var h=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);"
        "return !!(h&&(h===e||e.contains(h)||h.contains(e)));})()" % json.dumps(sel))


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
    httpd, port = server.serve("127.0.0.1", 8910)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.2},
                     daemon=True).start()
    time.sleep(0.4)
    base = "http://127.0.0.1:%d/" % port
    b = None
    try:
        b = Browser(base, width=390, height=844, scale=2.0)

        print("\n-- 闸门一：创建账号 --")
        check("登录卡出现", b.wait_js("!document.getElementById('authView').hidden"))
        check("首次运行直接进入注册",
              b.js("document.getElementById('btnAuth').textContent.indexOf('创建') >= 0"))
        check("首次运行不显示悬空的切换问句",
              b.js("document.getElementById('authSwitchRow').hidden"))
        check("主界面此时不可见", b.js("document.getElementById('appView').hidden"))
        check("无横向溢出", b.js(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        check("输入框字号足够大（iOS 不会缩放）", b.js(
            "parseFloat(getComputedStyle(document.getElementById('authUser')).fontSize) >= 16"))
        for sel in ("#authUser", "#authPass", "#btnAuth", "#btnReveal"):
            check("可点: " + sel, reachable(b, sel) in (True, "offscreen"), True)
        check("显示密码按钮生效", b.tap("#btnReveal"))
        check("  密码变为明文", b.js("document.getElementById('authPass').type"), "text")
        b.tap("#btnReveal")

        typed(b, "#authUser", "lihengbo")
        typed(b, "#authPass", "a-good-long-secret")
        typed(b, "#authName", "李恒博")
        check("提交注册", b.tap("#btnAuth"))

        print("\n-- 全球检索先行，方向追踪可选 --")
        check("注册后可直接全球检索", b.wait_js(
            "!document.getElementById('appView').hidden && "
            "document.getElementById('appView').classList.contains('global-mode')",
            tries=40))
        check("方向问询未强制出现", b.js("document.getElementById('onboardView').hidden"))
        check("手机无横向溢出", b.js(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        b.shot(str(SHOTS / "phone-global.png"))
        check("打开方向追踪", b.tap("#btnField"))
        check("方向页出现", b.wait_js("!document.getElementById('onboardView').hidden"))
        check("方向卡加载完成", b.wait_js(
            "document.querySelectorAll('#fieldGrid .fieldcard').length >= 6"))
        check("列出六个内置方向",
              b.js("document.querySelectorAll('#fieldGrid [data-field]').length"), 6)
        check("可返回全球检索", b.js("document.getElementById('btnObBack').hidden"), False)
        check("卡片一列排布（手机）", b.js(
            "(function(){var c=document.querySelectorAll('.fieldcard');"
            "return c.length>1 && Math.abs(c[0].getBoundingClientRect().left -"
            " c[1].getBoundingClientRect().left) < 1;})()"))
        check("方向卡可点", reachable(b, '[data-field="solid-state-battery"]'), True)
        check("自定义面板可展开", b.tap("#customBox summary")); time.sleep(0.4)
        check("  自定义输入框可点", reachable(b, "#cfName") in (True, "offscreen"), True)
        b.js("document.getElementById('customBox').open=false")
        check("选择固态电池", b.tap('[data-field="solid-state-battery"]'))

        print("\n-- 主界面 --")
        check("卡片渲染", b.wait_js("document.querySelectorAll('.rec').length > 0", tries=50))
        check("两道闸门都已隐藏", b.js(
            "document.getElementById('authView').hidden && "
            "document.getElementById('onboardView').hidden"))
        check("标题随方向变化",
              b.js("document.title"), "固态电池文献雷达")
        check("方向标签显示方向名",
              b.js("document.getElementById('fieldName').textContent"), "固态电池")
        check("账号入口是文字",
              b.js("document.getElementById('avatarText').textContent"), "账号")
        check("手机媒体查询生效",
              b.js("window.matchMedia('(max-width: 860px)').matches"))
        check("视口宽度 390", b.js("document.documentElement.clientWidth"), 390)
        check("无横向溢出", b.js(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        check("底部标签栏显示",
              b.js("getComputedStyle(document.getElementById('tabbar')).display"), "flex")
        check("桌面结果栏隐藏",
              b.js("getComputedStyle(document.querySelector('.resbar')).display"), "none")
        check("侧栏变为底部抽屉",
              b.js("getComputedStyle(document.getElementById('rail')).position"), "fixed")

        # An overlay with the `hidden` attribute must not intercept taps: a
        # class-level `display` once beat [hidden] and blocked the whole app.
        for sel in ("#btnSheet", "#q", "#btnRefresh", "#btnField", "#btnAccount",
                    '[data-tab="star"]', "[data-star]", ".act-primary", ".cat",
                    ".abs-toggle"):
            check("可点: " + sel, reachable(b, sel) in (True, "offscreen"), True)

        print("\n-- 账号菜单与方向切换 --")
        check("打开账号菜单", b.tap("#btnAccount")); time.sleep(0.4)
        check("  菜单可见", b.js("!document.getElementById('accountMenu').hidden"))
        check("  菜单项可点", reachable(b, '[data-act="field"]'), True)
        check("  菜单未溢出屏幕", b.js(
            "(function(){var r=document.getElementById('accountMenu')"
            ".getBoundingClientRect();return r.left>=0 && r.right<=window.innerWidth+1;})()"))
        check("进入方向切换", b.tap('[data-act="field"]'))
        check("  方向页出现", b.wait_js("!document.getElementById('onboardView').hidden"))
        check("  当前方向被标记", b.wait_js(
            """document.querySelector('[data-field="solid-state-battery"]')"""
            """.classList.contains('current')"""))
        check("  这次有返回按钮",
              b.js("document.getElementById('btnObBack').hidden"), False)
        check("返回文献列表", b.tap("#btnObBack")); time.sleep(0.5)
        check("  回到主界面", b.js("document.getElementById('appView').hidden"), False)
        check("  方向页已隐藏", b.js("document.getElementById('onboardView').hidden"))
        check("打开账号设置", b.tap("#btnAccount") and b.tap('[data-act="devices"]'))
        check("  设备列表已读取", b.wait_js(
            "document.querySelectorAll('#devList .dev').length > 0"))
        check("  当前设备被识别为 iPhone", b.js(
            "document.querySelector('#devList .dev.now b').textContent"), "iPhone")
        check("关闭账号设置", b.tap("#btnAcctClose")); time.sleep(0.4)
        check("  已关闭", b.js("document.getElementById('acctView').hidden"))

        print("\n-- 筛选抽屉 --")
        check("打开筛选抽屉", b.tap("#btnSheet")); time.sleep(0.7)
        check("  抽屉已开", b.js("document.getElementById('rail').classList.contains('open')"))
        check("  页面滚动被锁", b.js("document.body.style.overflow"), "hidden")
        check("  应用按钮显示条数", b.js(
            """document.getElementById('btnSheetApply').textContent.indexOf('条结果') > 0"""))
        check("  轴标题来自方向配置", b.js(
            """document.querySelector('[data-facet="chemistry"] .facet-head span:last-child')"""
            """.textContent"""), "电解质体系")
        check("选一个体系", b.tap('[data-pick="chemistry"][data-id="halide"]')); time.sleep(1.3)
        check("  条件写进 URL", b.js("location.hash.indexOf('f.chemistry=halide') >= 0"))
        check("  角标显示一个条件", b.js(
            "document.getElementById('mobarBadge').textContent"), "1")
        check("展开细分", b.tap('[data-kids="halide"]')); time.sleep(0.6)
        check("  细分已列出", b.js(
            """document.querySelectorAll("[data-id^='halide.']").length > 0"""))
        check("应用并关闭", b.tap("#btnSheetApply")); time.sleep(0.7)
        check("  抽屉已关",
              b.js("document.getElementById('rail').classList.contains('open')"), False)
        check("  滚动已释放", b.js("document.body.style.overflow"), "")
        check("从条件条移除", b.tap('[data-drop="chemistry"]')); time.sleep(1.2)
        check("  条件已清除", b.js("location.hash.indexOf('f.chemistry=halide') < 0"))

        print("\n-- 标签栏与列表 --")
        for tab, frag in (("new", "new_only=1"), ("unread", "unread=1"),
                          ("star", "starred=1"), ("all", "")):
            check("标签 " + tab, b.tap('[data-tab="%s"]' % tab)); time.sleep(1.2)
            if frag:
                check("  URL 含 " + frag, b.js("location.hash.indexOf('%s') >= 0" % frag))
                check("  标签高亮", b.js(
                    """document.querySelector("[data-tab='%s']").classList.contains('on')""" % tab))

        before = b.js("document.querySelectorAll('.rec').length")
        check("加载更多", b.tap("#btnLoadMore")); time.sleep(1.8)
        after = b.js("document.querySelectorAll('.rec').length")
        check("  追加而非替换 (%d -> %d)" % (before, after), after > before)

        b.js("window.scrollTo(0,0)"); time.sleep(0.3)
        check("展开摘要", b.tap(".abs-toggle")); time.sleep(0.4)
        check("  摘要已展开",
              b.js("!document.querySelector('.abs').classList.contains('clamped')"))
        check("收藏一篇", b.tap("[data-star]")); time.sleep(0.9)
        check("  已收藏", b.js("document.querySelector('[data-star]').classList.contains('on')"))

        print("\n-- 会话保持与 PWA --")
        b.call("Page.reload", {"ignoreCache": False}); time.sleep(0.5)
        check("刷新后仍然登录", b.wait_js(
            "!document.getElementById('appView').hidden && "
            "document.getElementById('authView').hidden", tries=50))
        check("  收藏状态保留", b.wait_js(
            "document.querySelectorAll('[data-star].on').length > 0"))
        man = b.call("Page.getAppManifest")
        check("manifest 无错误", man.get("errors") or [], [])
        d = json.loads(man.get("data") or "{}")
        check("  从根路径启动", d.get("start_url"), "/")
        check("  独立窗口显示", d.get("display"), "standalone")
        check("  含 maskable 图标",
              any(i.get("purpose") == "maskable" for i in d.get("icons") or []))
        check("service worker 已接管", b.wait_js(
            "navigator.serviceWorker.getRegistrations()"
            ".then(function(r){return r.length>0 && !!r[0].active})", tries=25, delay=0.4))

        print("\n-- 退出登录 --")
        check("退出", b.tap("#btnAccount") and b.tap('[data-act="logout"]'))
        check("  回到登录卡", b.wait_js("!document.getElementById('authView').hidden"))
        check("  这次是登录模式，不是注册",
              b.js("document.getElementById('btnAuth').textContent.indexOf('登') >= 0"))
        check("  显示切换到注册的链接",
              b.js("document.getElementById('authSwitchRow').hidden"), False)
        typed(b, "#authUser", "lihengbo")
        typed(b, "#authPass", "a-good-long-secret")
        check("重新登录", b.tap("#btnAuth"))
        check("  直接回到列表（方向已记住）", b.wait_js(
            "document.querySelectorAll('.rec').length > 0 && "
            "document.getElementById('onboardView').hidden", tries=50))
    finally:
        if b:
            b.close()
        httpd.shutdown()
        httpd.server_close()

    print("\n%s" % ("ALL PHONE CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    code = 1 if run() else 0
    _tmp.cleanup()
    sys.exit(code)
