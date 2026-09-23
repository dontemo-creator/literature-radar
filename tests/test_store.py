# -*- coding: utf-8 -*-
"""Schema-v2 store checks: per-field papers, per-user reading state, accounts.

The point of accounts is that a phone and a laptop hitting the same server show
the same starred papers -- and that another account sees none of them.  Both
halves of that are asserted here.
"""
import os, pathlib, shutil, sqlite3, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = pathlib.Path(tempfile.mkdtemp(prefix="ssb-store-"))
os.environ["SSB_DATA_DIR"] = str(TMP)

from app import config                                       # noqa: E402
config.DATA_DIR = TMP
config.DB_PATH = TMP / "papers.db"

from app import fields, store                                # noqa: E402

fails = []
SSB = "solid-state-battery"
LIB = "lithium-ion-battery"


def check(name, got, want):
    ok = got == want
    if not ok:
        fails.append(f"{name}: {got!r} != {want!r}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}" + ("" if ok else f" (want {want!r})"))
    return ok


def truthy(name, got):
    return check(name, bool(got), True)


def paper(doi, **kw):
    rec = {"doi": doi, "title": "T " + doi, "abstract": "A " + doi,
           "abstract_source": "crossref", "journal": "Nature Energy",
           "journal_tier": 1, "journal_jif": 56.7, "publisher": "NPG",
           "authors": ["X Y", "Z W"],          # a list must be coerced, not crash
           "author_count": 2, "pub_date": "2026-09-01", "indexed_date": "2026-09-02",
           "volume": "9", "issue": "3", "pages": "1-9",
           "url": "https://doi.org/" + doi, "doc_type": "journal-article",
           "is_oa": 0, "cited_by": 0}
    rec.update(kw)
    return rec


def add(field, doi, labels=None, primary="oxide", relevance=20.0, **kw):
    return store.upsert(field, paper(doi, **kw),
                        labels or {"chemistry": ["oxide"], "theme": ["transport"]},
                        primary, relevance)


def run():
    print("== 建库 ==")
    store.init()
    check("schema 版本", store.schema_version(), store.SCHEMA_VERSION)
    check("初始无用户", store.user_count(), 0)

    print("\n== 账号 ==")
    alice = store.create_user("alice", "correct horse battery", "爱丽丝")
    bob = store.create_user("bob", "another good secret", "鲍勃")
    check("用户数", store.user_count(), 2)
    truthy("密码不以明文存储",
           b"correct horse" not in pathlib.Path(config.DB_PATH).read_bytes())
    truthy("正确密码可登录", store.verify_login("alice", "correct horse battery"))
    check("错误密码被拒", store.verify_login("alice", "wrong"), None)
    check("未知用户被拒", store.verify_login("nobody", "x"), None)
    truthy("用户名大小写不敏感", store.verify_login("ALICE", "correct horse battery"))
    for bad, why in [("ab", "太短"), ("a" * 40, "太长"), ("bad name", "含空格"),
                     ("alice", "重复")]:
        try:
            store.create_user(bad, "a good long secret", "")
            check(f"拒绝用户名（{why}）", "accepted", "rejected")
        except ValueError:
            check(f"拒绝用户名（{why}）", "rejected", "rejected")
    try:
        store.create_user("carol", "short", "")
        check("拒绝短密码", "accepted", "rejected")
    except ValueError:
        check("拒绝短密码", "rejected", "rejected")

    print("\n== 会话 ==")
    tok_phone = store.create_session(alice["id"], "iPhone Safari")
    tok_mac = store.create_session(alice["id"], "Mac Chrome")
    truthy("token 足够长", len(tok_phone) >= 32)
    check("两台设备各自的 token 不同", tok_phone == tok_mac, False)
    check("手机 token 解析到 alice", (store.session_user(tok_phone) or {}).get("id"),
          alice["id"])
    check("电脑 token 解析到同一账号", (store.session_user(tok_mac) or {}).get("id"),
          alice["id"])
    check("伪造 token 无效", store.session_user("x" * 43), None)
    check("空 token 无效", store.session_user(""), None)
    check("会话列表", len(store.sessions_for(alice["id"])), 2)
    store.drop_session(tok_mac)
    check("登出电脑后手机仍在线", (store.session_user(tok_phone) or {}).get("id"),
          alice["id"])
    check("登出的电脑 token 失效", store.session_user(tok_mac), None)

    print("\n== 研究方向 ==")
    store.set_user_field(alice["id"], SSB, {})
    check("alice 的方向", store.get_user(alice["id"])["field"], SSB)
    store.set_user_field(bob["id"], LIB, {})
    check("bob 的方向", store.get_user(bob["id"])["field"], LIB)
    check("在用方向", sorted(store.active_fields()), sorted([SSB, LIB]))
    spec = {"name": "钙钛矿界面", "keywords": ["perovskite interface"], "categories": []}
    store.set_user_field(bob["id"], "custom:{}".format(bob["id"]), spec)
    check("自定义方向的 spec 可取回",
          store.get_user(bob["id"])["field_spec"]["name"], "钙钛矿界面")
    store.set_user_field(bob["id"], LIB, {})

    print("\n== 文献入库 ==")
    check("首次入库", add(SSB, "10.1/a"), "added")
    check("重复入库不变", add(SSB, "10.1/a"), "unchanged")
    check("标题变化算更新", add(SSB, "10.1/a", title="新标题"), "updated")
    check("同一 DOI 可属于两个方向", add(LIB, "10.1/a", primary="cathode"), "added")
    for i in range(2, 8):
        add(SSB, f"10.1/{i}", pub_date=f"2026-08-{i:02d}")
    add(SSB, "10.1/nolabel", labels={"chemistry": ["other"], "theme": []},
        primary="other", relevance=7.0)
    check("papers 表按 DOI 去重",
          store.conn().execute("SELECT COUNT(*) c FROM papers").fetchone()["c"], 8)
    check("paper_fields 记录两个方向",
          store.conn().execute("SELECT COUNT(*) c FROM paper_fields").fetchone()["c"], 9)
    check("固态电池计数", store.stats(SSB)["total"], 8)
    check("锂离子计数", store.stats(LIB)["total"], 1)

    print("\n== 摘要回填 ==")
    truthy("回填成功", store.update_paper("10.1/2", abstract="回填的摘要",
                                          abstract_source="europepmc"))
    check("回填后内容", store.paper_row("10.1/2")["abstract"], "回填的摘要")
    check("回填对两个方向同时生效",
          store.get(LIB, "10.1/a", alice["id"])["abstract"] is not None, True)

    print("\n== 每人独立的阅读状态 ==")
    truthy("alice 收藏", store.set_flag(alice["id"], "10.1/a", "starred", 1))
    truthy("alice 标记已读", store.set_flag(alice["id"], "10.1/3", "read_at",
                                            store.now_iso()))
    res_a = store.search(user_id=alice["id"], field=SSB, only_starred=True,
                         facet_ids=["chemistry", "theme"])
    check("alice 看到 1 篇收藏", res_a["total"], 1)
    res_b = store.search(user_id=bob["id"], field=SSB, only_starred=True,
                         facet_ids=["chemistry", "theme"])
    check("其他用户看不到我的收藏", res_b["total"], 0)
    both = store.search(user_id=bob["id"], field=SSB, facet_ids=["chemistry", "theme"])
    check("但同一篇文献两人都能看到", both["total"], 8)
    truthy("取消收藏", store.set_flag(alice["id"], "10.1/a", "starred", 0))
    check("取消后为空", store.search(user_id=alice["id"], field=SSB, only_starred=True,
                                     facet_ids=["chemistry"])["total"], 0)

    print("\n== 检索与分面 ==")
    pack = fields.get(SSB)
    kw = dict(facet_ids=[f.id for f in pack.facets], descendants=pack.descendants)
    r = store.search(user_id=alice["id"], field=SSB, **kw)
    check("默认返回全部", r["total"], 8)
    check("分面计数含 oxide", r["facets"]["nodes"]["chemistry"].get("oxide"), 7)
    check("未指明体系单独成桶", r["facets"]["nodes"]["chemistry"].get("other"), 1)
    r = store.search(user_id=alice["id"], field=SSB,
                     selections={"chemistry": ["oxide"]}, **kw)
    check("按体系筛选", r["total"], 7)
    r = store.search(user_id=alice["id"], field=SSB,
                     selections={"chemistry": ["other"]}, **kw)
    check("筛选未指明体系不会漏掉文献", r["total"], 1)
    r = store.search(user_id=alice["id"], field=SSB, q="回填的摘要", **kw)
    check("全文检索命中回填内容", r["total"], 1)
    r = store.search(user_id=alice["id"], field=SSB, q="不存在的词", **kw)
    check("检索无结果时为空", r["total"], 0)
    r = store.search(user_id=alice["id"], field=SSB, only_unread=True, **kw)
    check("未读筛选排除已读的一篇", r["total"], 7)
    r = store.search(user_id=alice["id"], field=SSB, page=2, page_size=3, **kw)
    check("翻页", len(r["papers"]), 3)
    check("翻页总数不变", r["total"], 8)
    r = store.search(user_id=alice["id"], field=SSB, sort="relevance", **kw)
    truthy("按相关度排序单调不增",
           all(r["papers"][i]["relevance"] >= r["papers"][i + 1]["relevance"]
               for i in range(len(r["papers"]) - 1)))
    r = store.search(user_id=alice["id"], field=LIB, **kw)
    check("换方向后只看到该方向的文献", r["total"], 1)

    print("\n== 删除与清理 ==")
    check("从固态电池移除一篇", store.delete_field_papers(SSB, ["10.1/7"]), 1)
    check("移除后计数", store.stats(SSB)["total"], 7)
    check("从锂离子移除共有的 DOI", store.delete_field_papers(LIB, ["10.1/a"]), 1)
    truthy("共有 DOI 仍留在固态电池", store.paper_row("10.1/a"))
    check("孤立 DOI 会被清理", store.delete_field_papers(SSB, ["10.1/a"]), 1)
    check("papers 表随之收缩", store.paper_row("10.1/a"), None)

    print("\n== 登录限流 ==")
    ip = "203.0.113.9"
    for _ in range(10):
        store.note_login_attempt(ip, False)
    truthy("连续失败后限流", store.login_blocked(ip))
    check("其他 IP 不受影响", store.login_blocked("203.0.113.10"), 0)

    print("\n== v1 → v2 迁移 ==")
    old = TMP / "v1.db"
    con = sqlite3.connect(old)
    con.executescript("""
      CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
      INSERT INTO meta VALUES('schema_version','1');
      CREATE TABLE papers(
        doi TEXT PRIMARY KEY, title TEXT, abstract TEXT, abstract_source TEXT,
        journal TEXT, journal_tier INT, journal_jif REAL, publisher TEXT,
        authors TEXT, author_count INT, pub_date TEXT, indexed_date TEXT,
        volume TEXT, issue TEXT, pages TEXT, url TEXT, doc_type TEXT,
        is_oa INT, cited_by INT, relevance REAL, chemistry TEXT, themes TEXT,
        primary_chem TEXT, first_seen TEXT, updated_at TEXT,
        abstract_tries INT DEFAULT 0, read_at TEXT DEFAULT '',
        starred INT DEFAULT 0);
      CREATE TABLE refresh_log(id INTEGER PRIMARY KEY, started TEXT, finished TEXT,
        scanned INT, added INT, updated INT, note TEXT);
      INSERT INTO papers(doi,title,abstract,journal,journal_tier,pub_date,relevance,
        chemistry,themes,primary_chem,first_seen,starred,read_at)
        VALUES('10.9/old','旧文献','旧摘要','Nature Energy',1,'2026-01-01',30.0,
               '["sulfide", "sulfide.argyrodite"]','["interface", "limetal"]',
               'sulfide','2026-01-02',1,'2026-01-03');
    """)
    con.commit(); con.close()
    dest = TMP / "papers.db"
    store.close()
    shutil.copy(old, dest)
    store.init()
    check("迁移后版本", store.schema_version(), store.SCHEMA_VERSION)
    row = store.paper_row("10.9/old")
    truthy("旧文献保留", row)
    check("旧标题保留", row["title"], "旧文献")
    migrated = store.field_dois(SSB)
    check("旧文献归入默认方向", "10.9/old" in migrated, True)
    rec = store.get(SSB, "10.9/old", 0)
    check("旧标签转为分面结构", sorted(rec["labels"]["chemistry"]),
          ["sulfide", "sulfide.argyrodite"])
    check("旧主题转为分面结构", sorted(rec["labels"]["theme"]), ["interface", "limetal"])
    check("旧的收藏被暂存",
          "legacy_flag:10.9/old" in
          {r["key"] for r in store.conn().execute("SELECT key FROM meta")}, True)
    revived = store.create_user("dave", "yet another secret", "戴夫")
    rec2 = store.get(SSB, "10.9/old", revived["id"])
    check("首个新账号继承旧的收藏", rec2["starred"], True)
    check("首个新账号继承旧的已读", bool(rec2["read_at"]), True)
    store.init()
    check("迁移可重复执行", store.schema_version(), store.SCHEMA_VERSION)
    check("重复迁移不复制文献",
          store.conn().execute("SELECT COUNT(*) c FROM papers").fetchone()["c"], 1)

    print("\n%s" % ("ALL STORE CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    code = run()
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if code else 0)
