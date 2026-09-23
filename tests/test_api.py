# -*- coding: utf-8 -*-
"""End-to-end HTTP checks: accounts, the direction question, and search.

Runs a real server on a throwaway database and talks to it over HTTP with a
cookie jar, so the session handling is exercised the way a browser does it.
"""
import http.cookiejar, json, os, pathlib, shutil, sys, tempfile, threading, urllib.error
import urllib.parse, urllib.request
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = pathlib.Path(tempfile.mkdtemp(prefix="ssb-api-"))
os.environ["SSB_DATA_DIR"] = str(TMP)

from app import config                                        # noqa: E402
config.DATA_DIR = TMP
config.DB_PATH = TMP / "papers.db"

from app import fields, server, store                          # noqa: E402

BASE = ""
fails = []
SSB = "solid-state-battery"


def check(name, got, want):
    ok = got == want
    if not ok:
        fails.append("%s: %r != %r" % (name, got, want))
    print("  [%s] %s: %r%s" % ("OK " if ok else "FAIL", name, got,
                               "" if ok else " (want %r)" % (want,)))
    return ok


def truthy(name, got):
    return check(name, bool(got), True)


class Client:
    """One browser: its own cookie jar, so sessions stay separate."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))

    def hit(self, path, method="GET", body=None, agent="TestClient/1.0"):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": agent})
        try:
            with self.opener.open(req, timeout=25) as r:
                raw = r.read().decode("utf-8", "replace")
                if "json" not in (r.headers.get("Content-Type") or ""):
                    return r.status, {"raw": raw[:120]}     # static files
                return r.status, json.loads(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw[:200]}

    def cookies(self):
        return {c.name: c for c in self.jar}


def seed():
    """A tiny, deterministic library -- no network involved."""
    pack = fields.get(SSB)
    rows = [
        ("10.1/a", "Argyrodite Li6PS5Cl electrolyte for all-solid-state batteries",
         "The sulfide solid electrolyte reaches 5 mS/cm ionic conductivity.",
         ["sulfide", "sulfide.argyrodite"], ["transport"], "sulfide", "2026-09-01", 1),
        ("10.1/b", "Garnet LLZO thin film against lithium metal",
         "Interfacial resistance of the oxide solid electrolyte is reduced.",
         ["oxide", "oxide.garnet"], ["interface", "limetal"], "oxide", "2026-08-28", 1),
        ("10.1/c", "PEO polymer electrolyte with plasticiser",
         "A polymer solid electrolyte for quasi-solid-state cells.",
         ["polymer", "polymer.peo"], ["transport"], "polymer", "2026-08-20", 2),
    ]
    for doi, title, abstract, chem, theme, primary, date, tier in rows:
        store.upsert(SSB, {
            "doi": doi, "title": title, "abstract": abstract,
            "abstract_source": "crossref", "journal": "Nature Energy" if tier == 1
            else "Journal of Power Sources", "journal_tier": tier, "journal_jif": 56.7,
            "publisher": "T", "authors": "A B; C D", "author_count": 2,
            "pub_date": date, "indexed_date": date, "volume": "1", "issue": "2",
            "pages": "3-4", "url": "https://doi.org/" + doi,
            "doc_type": "journal-article", "is_oa": 0, "cited_by": 5,
        }, {"chemistry": chem, "theme": theme}, primary, 30.0)
    return pack


def run():
    global BASE
    store.init()
    pack = seed()
    httpd, port = server.serve("127.0.0.1", 8900)
    BASE = "http://127.0.0.1:%d" % port
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print("server on", BASE)

    anon = Client()
    try:
        print("\n== 未登录 ==")
        check("首页可访问", anon.hit("/")[0], 200)
        check("bootstrap 需要登录", anon.hit("/api/bootstrap")[0], 401)
        check("search 需要登录", anon.hit("/api/search")[0], 401)
        check("flag 需要登录", anon.hit("/api/flag", "POST", {"doi": "10.1/a"})[0], 401)
        check("refresh 需要登录", anon.hit("/api/refresh", "POST", {})[0], 401)
        st = anon.hit("/api/auth/state")[1]
        check("首次运行没有账号", st["has_users"], False)
        check("未认证", st["authenticated"], False)

        print("\n== 注册与登录 ==")
        code, d = anon.hit("/api/auth/register", "POST",
                           {"username": "ab", "password": "a-good-secret"})
        check("拒绝过短用户名", code, 400)
        code, d = anon.hit("/api/auth/register", "POST",
                           {"username": "alice", "password": "short"})
        check("拒绝过短密码", code, 400)
        mac = Client()
        code, d = mac.hit("/api/auth/register", "POST",
                          {"username": "alice", "password": "a-good-long-secret",
                           "display_name": "爱丽丝"}, agent="Mozilla/5.0 (Macintosh)")
        check("注册成功", code, 200)
        truthy("下发了会话 cookie", "ssb_session" in mac.cookies())
        cookie = mac.cookies()["ssb_session"]
        truthy("cookie 是 HttpOnly", cookie.has_nonstandard_attr("HttpOnly"))
        check("cookie 路径为根", cookie.path, "/")
        check("重复用户名被拒",
              anon.hit("/api/auth/register", "POST",
                       {"username": "alice", "password": "another-long-one"})[0], 400)
        check("错误密码登录失败",
              anon.hit("/api/auth/login", "POST",
                       {"username": "alice", "password": "wrong-but-long"})[0], 401)

        print("\n== 研究方向 ==")
        code, b = mac.hit("/api/bootstrap")
        check("尚未选方向", b.get("needs_field"), True)
        truthy("给出了可选方向", len(b["fields"]["presets"]) >= 6)
        check("未选方向时检索被挡", mac.hit("/api/search")[1].get("needs_field"), True)
        global_paper = {"doi": "10.1/global", "title": "Global quantum computing paper",
                        "journal": "Example Journal", "pub_date": "2026-09-22",
                        "url": "https://doi.org/10.1/global", "source_engine": "openalex"}
        global_result = {"papers": [global_paper], "total": 1, "pages": 1,
                         "page": 1, "page_size": 25, "source": "openalex"}
        with patch.object(server.live_search, "query_global", return_value=global_result):
            check("未选方向也能全球检索",
                  mac.hit("/api/search/live?q=" + urllib.parse.quote("量子计算"))[1]["papers"][0]["doi"],
                  "10.1/global")
        check("全球论文可保存但不收藏",
              mac.hit("/api/paper/save", "POST", {"paper": global_paper, "starred": False})[1]["ok"], True)
        check("全球论文可标记已读",
              mac.hit("/api/flag", "POST", {"doi": "10.1/global", "field": "read", "value": True})[1]["ok"], True)
        check("拒绝未知方向",
              mac.hit("/api/me/field", "POST", {"field": "no-such-field"})[1]["ok"], False)
        code, d = mac.hit("/api/me/field", "POST", {"field": SSB})
        check("选定固态电池", d["ok"], True)

        code, b = mac.hit("/api/bootstrap")
        check("bootstrap 不再要求选方向", b.get("needs_field"), False)
        check("方向名称", b["field"]["zh"], "固态电池")
        check("分面轴数量", len(b["facets"]), len(pack.facets))
        check("第一条轴", b["facets"][0]["id"], "chemistry")
        truthy("轴带节点树", b["facets"][0]["nodes"][0].get("children") is not None)
        check("期刊清单只含本方向", len(b["journals"]), len(pack.journals))
        check("库内篇数", b["stats"]["total"], 3)

        print("\n== 检索 ==")
        code, r = mac.hit("/api/search")
        check("返回全部", r["total"], 3)
        truthy("带标签芯片", len(r["papers"][0]["label_chips"]) > 0)
        check("默认按日期倒序", r["papers"][0]["doi"], "10.1/a")
        check("按体系筛选", mac.hit("/api/search?f.chemistry=oxide")[1]["total"], 1)
        check("按细分体系筛选",
              mac.hit("/api/search?f.chemistry=sulfide.argyrodite")[1]["total"], 1)
        check("父节点包含子节点",
              mac.hit("/api/search?f.chemistry=sulfide")[1]["total"], 1)
        check("多选是或关系",
              mac.hit("/api/search?f.chemistry=oxide,polymer")[1]["total"], 2)
        check("不同轴是且关系",
              mac.hit("/api/search?f.chemistry=oxide&f.theme=transport")[1]["total"], 0)
        check("同一篇同时命中两轴",
              mac.hit("/api/search?f.chemistry=oxide&f.theme=interface")[1]["total"], 1)
        check("全文检索", mac.hit("/api/search?q=argyrodite")[1]["total"], 1)
        check("检索词无结果", mac.hit("/api/search?q=zzzznotaword")[1]["total"], 0)
        check("期刊等级筛选", mac.hit("/api/search?tier=1")[1]["total"], 2)
        check("期刊筛选",
              mac.hit("/api/search?journal=" +
                      urllib.parse.quote("Nature Energy"))[1]["total"], 2)
        check("未知轴被忽略", mac.hit("/api/search?f.nosuchaxis=x")[1]["total"], 3)
        check("未知节点被忽略",
              mac.hit("/api/search?f.chemistry=nosuchnode")[1]["total"], 3)
        check("分面计数", mac.hit("/api/search")[1]["facets"]["nodes"]["chemistry"]["oxide"], 1)
        check("超大页码被夹住", mac.hit("/api/search?page=999")[1]["page"], 1)
        check("非法页码被夹住", mac.hit("/api/search?page=abc")[1]["page"], 1)
        check("非法排序回退", mac.hit("/api/search?sort=nonsense")[1]["total"], 3)
        check("超长检索词不报错", mac.hit("/api/search?q=" + "a" * 500)[0], 200)
        check("注入式检索词不报错", mac.hit("/api/search?q=" +
                                            urllib.parse.quote('" OR 1=1 --'))[0], 200)

        print("\n== 两台设备共享阅读状态 ==")
        phone = Client()
        code, d = phone.hit("/api/auth/login", "POST",
                            {"username": "alice", "password": "a-good-long-secret"},
                            agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)")
        check("手机登录成功", d["ok"], True)
        check("手机看到同一个方向", phone.hit("/api/bootstrap")[1]["field"]["id"], SSB)
        check("在电脑上收藏",
              mac.hit("/api/flag", "POST",
                      {"doi": "10.1/a", "field": "starred", "value": True})[1]["ok"], True)
        check("手机立即看到这条收藏",
              phone.hit("/api/search?starred=1")[1]["total"], 1)
        check("在手机上标记已读",
              phone.hit("/api/flag", "POST",
                        {"doi": "10.1/b", "field": "read", "value": True})[1]["ok"], True)
        check("电脑上未读数随之变化",
              mac.hit("/api/search?unread=1")[1]["total"], 2)
        check("设备列表有两台", len(mac.hit("/api/me/sessions")[1]["sessions"]), 2)
        names = sorted(s["agent"][:24] for s in mac.hit("/api/me/sessions")[1]["sessions"])
        truthy("能区分手机与电脑", any("iPhone" in n for n in names))

        print("\n== 别的账号看不到我的东西 ==")
        bob = Client()
        bob.hit("/api/auth/register", "POST",
                {"username": "bob", "password": "bobs-long-secret"})
        bob.hit("/api/me/field", "POST", {"field": SSB})
        check("bob 看到同样的文献", bob.hit("/api/search")[1]["total"], 3)
        check("bob 看不到 alice 的收藏", bob.hit("/api/search?starred=1")[1]["total"], 0)
        check("bob 的未读是全部", bob.hit("/api/search?unread=1")[1]["total"], 3)
        check("bob 的设备列表只有自己",
              len(bob.hit("/api/me/sessions")[1]["sessions"]), 1)

        print("\n== 自定义方向 ==")
        carol = Client()
        carol.hit("/api/auth/register", "POST",
                  {"username": "carol", "password": "carols-long-secret"})
        code, d = carol.hit("/api/me/field", "POST", {"custom": {
            "name": "锂硫电池",
            "keywords": ["lithium-sulfur battery", "polysulfide shuttle"],
            "categories": [{"zh": "正极", "keywords": ["sulfur cathode", "sulfur host"]},
                           {"zh": "电解液", "keywords": ["ether electrolyte"]}],
            "exclude": ["fuel cell"]}})
        check("自定义方向建立成功", d.get("ok"), True)
        code, b = carol.hit("/api/bootstrap")
        check("自定义方向名称", b["field"]["zh"], "锂硫电池")
        check("自定义方向标记为非内置", b["field"]["builtin"], False)
        check("自定义方向有一条轴", len(b["facets"]), 1)
        check("自定义分类进入轴",
              sorted(n["zh"] for n in b["facets"][0]["nodes"]),
              sorted(["正极", "电解液", "其他"]))
        check("自定义方向自己的库是空的", b["stats"]["total"], 0)
        check("过短关键词被拒",
              carol.hit("/api/me/field", "POST",
                        {"custom": {"name": "x", "keywords": ["na", "li"]}})[1]["ok"], False)

        print("\n== 登出 ==")
        check("登出成功", mac.hit("/api/auth/logout", "POST", {})[1]["ok"], True)
        check("登出后被挡", mac.hit("/api/search")[0], 401)
        check("手机仍然在线", phone.hit("/api/search")[0], 200)
        check("手机上撤销其他设备",
              phone.hit("/api/me/sessions/revoke", "POST", {})[1]["ok"], True)
        check("撤销后手机自己仍在线", phone.hit("/api/search")[0], 200)

        print("\n== 杂项 ==")
        check("健康检查", anon.hit("/healthz")[1]["ok"], True)
        check("未知 API 返回 404", phone.hit("/api/nope")[0], 404)
        check("目录穿越被拒", anon.hit("/static/../../etc/passwd")[0] in (403, 404), True)
        truthy("service worker 可取", anon.hit("/sw.js")[0] == 200)
        truthy("manifest 可取", anon.hit("/manifest.webmanifest")[0] == 200)
    finally:
        httpd.shutdown()

    print("\n%s" % ("ALL API CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    code = run()
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if code else 0)
