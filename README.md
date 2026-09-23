# 文献雷达 · Literature Radar

> **全学科多维学术搜索工作台与定向文献追踪雷达**  
> 纯 Python 标准库打造 · **零第三方依赖 (无需 `pip install`)** · 本地 SQLite 隐私存储 · 电脑与手机 PWA 跨端同步 · MIT 开源

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0%20(Standard%20Library)-orange.svg)](requirements.txt)

---

### 🌟 核心特色：双模协同

1. **🌐 全球学术检索（搜什么出什么）**：
   * 注册后直接进入**「全球学术检索」**，无需先选择研究方向；基于 [OpenAlex](https://help.openalex.org/api/) 与 [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) 的公开元数据。
   * 输入 `固态电池`、`AI算法`、`量子计算`，或任意学科的英文术语，按实际发表日期查看新论文。部分中文主题会自动转为英文检索词；更具体的英文术语通常更准确。
   * 遇到心仪文献，**点击「☆ 收藏」一键沉淀入本地 SQLite 数据库**。
2. **🎯 定向方向雷达（早晨顶刊必刷）**：
   * 自动追踪高质量期刊中**你专属研究方向**的最新文献，按多维正交分类轴（如材料体系、研究主题）立体分好类，界面按 Web of Science 风格设计。
   * 支持手机端与电脑端在局域网内无缝同步阅读进度与收藏夹。

---

## 快速开始

```bash
cd "路径/paper search"
python3 run.py
```

浏览器会自动打开 `http://127.0.0.1:8756/`。macOS 本地开发目录可双击
**`start.command`**；从 GitHub 获取的版本如未保留可执行权限，可运行
`bash start.command`。

**第一次打开**先创建本地账号，然后就能直接搜索：

1. **创建账号** —— 用户名 + 密码（至少 8 位）。这个账号只写进本机数据库，
   手机以后用它登录就能同步。
2. **全球搜索** —— 在搜索框输入主题即可。要持续追踪一个方向时，点击左上角
   「设置定向追踪」，选预设方向或创建自定义方向。

选定定向追踪方向后开始抓取近 90 天的文献（约 4–7 分钟，扫描相关期刊记录），
之后每天打开只增量抓取（约 40 秒）。抓取在后台进行，页面上有进度提示，
完成后结果自动刷新。换方向后同样会为新方向抓一次。

右上角的方向标签可以随时切换方向，头像里可以改密码、看已登录设备、退出登录。

按 `Ctrl+C` 停止。

**在手机上用**：`python3 run.py --lan`，然后手机浏览器打开终端里列出的
`192.168.x.x` 地址，「添加到主屏幕」即可当 App 用（详见
[在手机上当 App 用](#在手机上当-app-用)）。

### 命令行

```bash
python3 run.py                  # 启动界面
python3 run.py --no-browser     # 只启动服务，不开浏览器
python3 run.py --refresh        # 在终端跑一次更新后退出（可放进 cron）
python3 run.py --refresh --window 30   # 指定回溯天数
python3 run.py --reclassify     # 改过分类规则后，重新标注已存文献
python3 run.py --list-fields    # 列出可选研究方向
python3 run.py --field lithium-ion-battery --refresh   # 只更新某一个方向
python3 run.py --stats          # 打印各方向的统计
python3 run.py --lan            # 同时监听局域网，供手机访问
python3 run.py --diagnose       # 手机连不上时排查原因
python3 run.py --qr             # 只打印手机访问地址的二维码
python3 run.py --port 9000      # 换端口
```

---

## 界面怎么用

| 区域 | 说明 |
|---|---|
| **顶栏** | 左边是当前方向（点一下切换），右边是库内篇数、近 7 天篇数、摘要覆盖率、收录期刊数、上次更新时间；「立即更新」手动抓取；最右是账号头像 |
| **检索框** | 支持 **「本方向雷达」** 与 **「全球学术检索 🌐」** 双模自由切换：在雷达模式下检索标题/摘要/期刊/作者（多词为与，支持词组与前缀）；在全球检索模式下可查询任意学科的已收录论文，一键收藏沉淀入库 |
| **左侧「精炼结果」** | 快捷筛选、出版时间、期刊等级、**当前方向的各条分类轴**（有细分的可展开）、来源期刊。每项后面是当前结果集中的篇数。换方向时这些轴会整体换掉 |
| **结果列表** | 编号、标题（点击跳原文）、作者、期刊 / 卷期页 / 日期、徽标（新推送 / 开放获取 / 期刊等级 / 影响因子）、分类标签（超过 6 个折叠为 `+N`）、摘要（默认 3 行，可展开）、查看原文 / 收藏 / 已读 / 复制 DOI、右侧被引数 |
| **排序** | 出版日期、入库时间、相关度、期刊等级+影响因子、被引次数、标题 |

全球模式默认按发表日期倒序，并排除未来日期；可以改为相关度或被引次数。
它检索的是数据源已经收录的元数据，收录速度取决于出版商与索引更新，不能保证
覆盖今天刚上线的每一篇论文。中文概念若能在 Wikidata 找到精确英文名称，会用它
检索英文文献；无法确认时仍按原词搜索。检索词会发送给相应的公开 API，账号密码与
本地阅读记录不会发送。
如果 OpenAlex 和 Crossref 都暂时不可用，页面会明确提示数据源故障，不会把故障
显示成「没有匹配文献」。

- **同一条轴内多选是「或」**，不同轴之间是「与」。例（固态电池方向）：勾选「硫化物」
  +「卤化物」，再勾选主题「界面与界面相」→ 得到「(硫化物 或 卤化物) 且 界面」的文献。
- 点结果里的分类标签，可直接把它加为筛选条件。
- 「**新推送**」徽标 = 上次打开之后新入库的。这个标记**按自然日推进**，
  当天刷新浏览器不会把它清掉。
- 筛选状态写在地址栏 `#` 后面（形如 `#f.chemistry=sulfide&sort=date`），刷新页面
  能恢复，也可以存成书签。
- 收藏和已读**记在账号上**，不是记在浏览器里：在电脑上收藏，手机刷新就能看到。

---

## 分类体系

每个研究方向自带一套分类轴。下面以**固态电池**为例；换到别的方向，左栏会整体
换成那个方向的轴（`python3 run.py --list-fields` 可以看全部）。

### 固态电池 · 电解质体系（7 大类 + 32 细分）

| 大类 | 细分 |
|---|---|
| 聚合物电解质 | PEO 与聚醚、聚碳酸酯与聚酯、含氟聚合物、腈类与丙烯酸酯、单离子导体、凝胶与准固态、复合聚合物、MOF/COF 与超分子、生物基与纤维素 |
| 氧化物电解质 | 石榴石 (LLZO)、钙钛矿 (LLTO)、NASICON (LATP/LAGP)、LISICON 与硅酸盐、反钙钛矿、薄膜与 LiPON、硼酸盐/玻璃与其他 |
| 硫化物电解质 | 硫银锗矿 (Li6PS5Cl)、LGPS 与 thio-LISICON、玻璃与玻璃陶瓷、Li3PS4 与二元 Li–P–S、氧硫化物、其他硫化物 (Sb/Sn/Si/Na) |
| 卤化物电解质 | 氯化物、溴化物与碘化物、氟化物、氧卤化物 (LiMOCl4)、混合/双卤 |
| 氢化物与硼氢化物 | LiBH4 基、笼型硼酸盐与碳硼烷 |
| 复合与混合电解质 | 有机-无机复合、多层与梯度设计、跨体系堆叠 |
| 综合 / 未指明体系 | 在范围内但未点明具体体系的文献（制造工艺、电芯工程、正极、综述等）——放在这里而不是丢掉，避免筛选时凭空消失 |

### 固态电池 · 研究主题（16 类，与体系正交）

界面与界面相 · 锂金属负极与枝晶 · 无负极/贫锂体系 · 硅/合金与转换型负极 ·
复合正极与正极电解质 · 固态锂硫与转换反应 · 钠/钾/镁/锌等非锂体系 · 离子输运机理 ·
化学-力学与堆叠压力 · 制造与规模化 · 电芯与系统工程 · 先进表征 ·
计算、机器学习与筛选 · 安全、热与失效 · 可持续性与回收 · 综述与展望

一篇文献可同时属于多个体系与多个主题（例如「石榴石 + NASICON + 多层设计」）。

### 自定义方向

在方向问询页展开「都不是？自定义一个方向」，填三样东西：

- **方向名称** —— 显示在标题和方向标签上；
- **核心关键词** —— 决定「哪些文献算这个方向」。请用**词组**，不要用单词缩写：
  `lithium-sulfur battery` 可以，`Li-S` 不行。软件会拒绝过短的词，因为
  像 `na` 这样的片段会命中 `nanocomposite`、`analysis`，把无关文献全放进来；
- **分类**（可选）—— 每个分类一个名字加几个关键词，成为左栏那条轴上的一项。
  留空就只做相关性筛选，不分类。

自定义方向的判定门槛比内置方向宽（一个词组命中即可入选），所以关键词写得越具体
越准。方向配置随账号保存，可以随时回去改。

---

## 收录范围

**86 种期刊**（122 个 ISSN），ISSN 全部经 Crossref 权威记录核对，分三档：

- **顶级期刊**（25 种）Nature / Science / Nature Energy / Nature Materials /
  Joule / JACS / Angew / Adv. Mater. / Adv. Energy Mater. / EES / ACS Energy Lett. …
- **一流期刊**（32 种）Adv. Funct. Mater. / Energy Storage Mater. / Nano Energy /
  ACS Nano / Chem. Mater. / J. Mater. Chem. A / eScience / InfoMat …
- **专业期刊**（29 种）J. Power Sources / Electrochim. Acta / JES /
  ACS Appl. Energy Mater. / Batteries & Supercaps / Solid State Ionics …

期刊清单在 `app/journals.py`（由 `tools/gen_journals.py` 从 Crossref 生成）。
要增删期刊，改那份清单里的 `JOURNALS` 即可，`issn` 必须准确。

### 主题筛选是怎么做的

每天从这些期刊抓到的记录约 700–800 条，其中真正的固态电池文献约 20–25 条。
筛选用加权关键词规则（标题命中权重 ×2）跑在归一化文本上：下标、希腊字母、
各种连字符都会先归一，所以 `Li₆PS₅Cl`、`Li6PS5Cl`、`Li2S–P2S5`、`β-Li3PS4`
都能正确命中。

规则里专门排除了几类容易混进来的邻近领域，这些坑都是实测数据里发现的：

- **液态电解液论文**：几乎每篇锂离子电池文章都会写 "solid electrolyte
  interphase (SEI)"，含有 "solid electrolyte" 字样。若不处理，会有约 **20%** 的
  库内文献其实是液态体系。
- **质子交换膜燃料电池**：命中 "polymer electrolyte"（PEM = polymer electrolyte
  membrane）。
- **固体氧化物燃料电池 / 氧离子导体**、水系锌电池、氧化还原介体体系、
  类脑器件、热电池、渗透膜等。

规则在 `app/taxonomy.py`，可自行增删；改完跑 `python3 run.py --reclassify`
重新标注（不符合规则的旧记录会被移除）。

### 测试

改动规则或代码后跑一遍全部测试（不联网、不动正式数据库）：

```bash
python3 tests/run_all.py
```

11 个套件、约 400 项断言：
GitHub Actions 也会在 macOS 上运行这套测试（含 Chrome 与 Apple Vision 检查）。

| 套件 | 覆盖内容 |
|---|---|
| `test_textnorm.py` | 下标 / 希腊字母 / 连字符 / JATS 标记，含化学式排版的真实坑 |
| `test_classify.py` | 固态电池 23 条带标准答案的分类用例，含 8 条必须被排除的邻近领域论文 |
| `test_field_isolation.py` | 30 篇已知归属的论文 × 6 个方向：每个方向必须收下自己的、拒掉邻居的。防的是「钠电热失控论文混进锂电列表」这类串味 |
| `test_sources.py` | Crossref 解析、出版日期推断（含未来期次日期）、作者格式、非正文剔除 |
| `test_store.py` | 增删改查、分面计数、全文检索、SQL 注入、翻页边界；账号与会话；**别的账号看不到我的收藏**；v1→v2 迁移（用与正式库完全一致的表结构） |
| `test_api.py` | 全部接口；未登录必须被挡；两台设备共享阅读状态；方向切换与自定义方向；恶意入参、路径穿越 |
| `test_live_search.py` | 全学科检索、中文主题扩展、未来日期过滤、无 DOI 预印本与 Crossref 回退 |
| `test_desktop.py` | 桌面注册后直接全球搜索、可选方向追踪、**换方向后分类轴整体换掉且无残留**、账号面板与改密码。需装 Chrome |
| `test_phone.py` | 手机上走完「注册 → 全球搜索 → 选方向 → 阅读 → 退出 → 重新登录」全流程，真实坐标触摸（抽屉 / 标签栏 / 加载更多 / 收藏）、PWA 清单与 Service Worker。需装 Chrome |
| `test_netinfo.py` | 局域网地址识别：VPN 隧道口必须排除、本机热点必须保留 |
| `test_qrcode.py` | 二维码编码：格式位/容量对照标准表，并用 Apple Vision 实际解码 21 张图（含终端渲染反解）。需 Swift，否则只跑结构检查 |

想检查当前公开索引在不同学科是否正常返回近期论文，可运行：

```bash
python3 tools/check_global_search.py
python3 tools/check_global_search.py "固态电池" "graph neural network" "medieval history"
```

命令会报告实际使用的数据源、本页篇数、最新发表日期和距今天数。它需要联网，
不属于离线测试；这个抽样检查不能证明收录了某个领域的全部论文。

新增内置方向时，`test_field_isolation.py` 是必须过的那一关：**一条 `core`
标记必须是「这篇属于本方向」的证据，而不是本方向与邻居共有的研究主题。**
`thermal runaway`、`power conversion efficiency`、`oxygen reduction reaction`
这类词属于 `context`，放进 `core` 就会把邻居的论文一起收进来。

---

## 摘要覆盖：一个必须说清楚的限制

摘要按以下顺序获取：**Crossref → Europe PMC →（可选）Elsevier 官方接口 → OpenAlex**。

实际覆盖率约 **50–60%**。缺口几乎全部来自 **Elsevier**——它不向 Crossref 提交摘要，
Europe PMC 和 OpenAlex 对其新文章也基本没有。实测 40 篇 Elsevier 固态电池论文，
免费数据源合计只补到 1 篇。受影响的期刊包括 Joule、Energy Storage Materials、
Nano Energy、J. Power Sources、Chem. Eng. J.、J. Energy Chem. 等。

软件的处理方式：

1. 缺摘要的记录**照常显示**（标题 + 期刊 + 链接），并明确标注「该期刊未向公开数据库
   提供摘要」，不留空白、不假装有；
2. 每次更新会**继续重试**（最多 4 次）——有些摘要几周后会出现在 OpenAlex / Europe PMC；
3. 左侧「**仅含摘要**」可以只看有摘要的；
4. 想要完整覆盖，填一个 Elsevier 免费 key（下节）。

抓取网页不在方案内——ScienceDirect 的服务条款禁止自动化访问，官方接口才是正规途径。

### 可选：补全 Elsevier 摘要

1. 到 <https://dev.elsevier.com> 免费注册一个 API key（几分钟）。
2. 在项目根目录建 `settings.json`：

```json
{
  "elsevier_api_key": "你的key",
  "contact_email": "你的邮箱@example.com"
}
```

3. 重启软件，下次更新就会尝试补全。

能补多少取决于该 key 的权限（机构网络内通常更全）。key 无效或超额时会自动跳过，
不影响其他功能。

> `contact_email` 建议填真实邮箱：Crossref / OpenAlex 会把带邮箱的请求放进
> 更快的「polite pool」。

---

## 在手机上当 App 用

软件本身就是一个可安装的 Web App（PWA）：手机浏览器打开后「添加到主屏幕」，
就有独立图标、全屏窗口、无浏览器地址栏，用起来和原生 App 一样。

### 1. 让手机能连上电脑

```bash
python3 run.py --lan
```

启动后终端会打印手机地址**和一个二维码**，用手机相机扫一下即可打开——
不用手输地址（地址会随连接的网络变化，手输很容易出错）：

```
本机地址： http://127.0.0.1:8756/
手机访问： 手机连同一 Wi-Fi，用相机扫码，或手动输入
           ->  http://192.168.1.23:8756/

           ▄▄▄▄▄▄▄  ▄▄ ▄▄  ▄▄▄▄▄▄▄
           █ ▄▄▄ █ ▀▄ ▄▀▄  █ ▄▄▄ █
           ...
```

只想看二维码：

```bash
python3 run.py --qr
```

> 二维码是纯 Python 生成的（无第三方库），并用 Apple Vision 框架逐版本实解码
> 验证过，终端里直接扫即可。终端不支持颜色时会自动退化为方块字符版本。

> **安全提示**：`--lan` 会让同一网络内的所有设备都能打开这个页面（也能点收藏、
> 触发更新）。家里或办公室网络下没问题；公共 Wi-Fi 下不建议开启。不加 `--lan`
> 时只有本机可访问。

### 连不上怎么办

```bash
python3 run.py --diagnose
```

它会直接告诉你：服务实际在哪个端口、哪个地址是手机该用的、哪个是不能用的
VPN 隧道地址、防火墙与代理状态，以及逐条排查步骤。

最常见的四个原因：

1. **用错了地址。** 电脑上常有多个 IP，只有 Wi-Fi / 有线 / 本机热点那个能用。
   `utun` 开头的接口（如 `198.18.x.x`）是 VPN/代理的隧道口，手机永远连不上；
   `--diagnose` 会标出哪个是哪个。**地址会随网络变化**——换了 Wi-Fi、
   改用热点之后地址就变了，要重新看一次启动输出（或扫新的二维码）。
2. **手机上开着代理/VPN**（Shadowrocket、Clash、Surge 等）。它会把
   `http://192.168.x.x` 的请求送去远端服务器，表现就是 Safari「无法连接」。
   把手机代理临时关掉，或在规则里把局域网地址设为直连。
3. **端口不是 8756。** 端口被占用时程序会自动顺延到 8757、8758……
   以启动时打印的那一行为准，别照抄文档里的示例端口。
4. **路由器开了 AP 隔离 / 客户端隔离。** 常见于访客网络和部分运营商路由器，
   开了之后同一 Wi-Fi 下的设备无法互访，需要在路由器后台关闭。

其他：确认手机与电脑连的是同一个 Wi-Fi（2.4G 与 5G 有时是两个不同网络）；
macOS「系统设置 → 网络 → 防火墙」若开着，要允许 Python 接受传入连接；
Safari 地址栏要写全 `http://`，否则会被当成搜索词。

### 2. 添加到主屏幕

- **iPhone / iPad（Safari）**：分享按钮 → 「添加到主屏幕」
- **Android（Chrome）**：右上角菜单 → 「安装应用」或「添加到主屏幕」

之后从主屏图标启动，就是独立窗口的 App。iOS 上长按图标还能直接进
「今日新推送」和「我的收藏」。

### 手机端界面

针对触屏重做了交互模型，不是把桌面版缩小：

| | |
|---|---|
| **顶栏** | 压缩为标识 + 名称 + 方向标签 + 更新按钮（图标）+ 头像 |
| **检索** | 常驻吸顶，输入即搜 |
| **筛选** | 「筛选」按钮唤出**底部抽屉**，按钮上的数字是当前生效的条件数；抽屉内即时显示「查看 N 条结果」 |
| **条件条** | 已选条件横向滑动展示，点 ✕ 直接移除 |
| **结果** | 每篇一张独立卡片，摘要默认 4 行可展开 |
| **底部标签栏** | 全部 / 新推送 / 未读 / 收藏 四个视图一键切换；有新文献时「新推送」上有红点 |
| **翻页** | 改为「加载更多」，追加到列表末尾而不是跳页 |
| **触摸目标** | 全部 ≥ 38px；输入框字号 ≥ 16px（避免 iOS 自动缩放） |
| **安全区** | 适配刘海与底部横条（`env(safe-area-inset-*)`） |

### 手机与电脑同步

手机上打开同一个地址，用**同一个账号**登录即可：

- 看到的是同一份文献库（服务在电脑上，手机只是客户端）；
- 收藏和已读**双向同步**——在电脑上收藏，手机下拉刷新就有；
- 研究方向也跟着账号，在手机上换方向，电脑刷新后同步生效；
- 登录状态保存 60 天，不用每次重输密码；
- 头像 →「已登录设备」能看到哪些设备在线，「退出其他所有设备」可一键踢掉。

前提是电脑上的服务在跑（`python3 run.py --lan`）。电脑休眠或关掉终端，
手机就连不上——这是本地软件的固有限制，不是 bug。

### 离线可读

安装后 Service Worker 会缓存界面与最近一次的检索结果，断网时打开仍能读到
上次的文献列表。

> Service Worker 只在安全来源下工作：`localhost` 可以，
> 纯 HTTP 的局域网地址（`http://192.168.x.x`）**不行**——浏览器会拒绝注册。
> 也就是说手机通过局域网访问时，「添加到主屏幕」和独立窗口正常，
> 但没有离线缓存。这是浏览器的安全策略，非软件问题。

---

## 全部可配置项

在根目录 `settings.json` 里覆盖（缺省值见 `app/config.py`）：

| 键 | 缺省 | 说明 |
|---|---|---|
| `contact_email` | `ssb-radar@localhost` | 发给 API 的联系邮箱 |
| `server_port` | `8756` | 端口被占用时自动往后找 |
| `refresh_window_days` | `21` | 日常更新回溯上限（实际窗口按距上次更新的天数自适应，最少 7 天） |
| `backfill_days` | `90` | 首次运行回溯天数 |
| `auto_refresh_after_hours` | `8` | 打开时若超过这个时长就自动更新 |
| `min_relevance` | `3` | 相关度下限（规则本身还有更严的门槛） |
| `max_journal_tier` | `3` | 只抓 1/2 档期刊可设为 1 或 2 |
| `open_browser` | `true` | 启动时是否自动开浏览器 |
| `elsevier_api_key` | 空 | 见上节 |

也支持环境变量，如 `SSB_SERVER_PORT=9000 python3 run.py`。

---

## 每天自动更新（可选）

软件在你打开时会自动更新，所以通常不用配。若希望打开即有结果，
可以让系统每天早上先跑一次：

```bash
crontab -e
# 每天 07:12 更新一次（避开整点）
12 7 * * * cd "/Users/你的用户名/AI Projects/paper search" && /usr/bin/env python3 run.py --refresh >> logs/cron.log 2>&1
```

---

## 目录结构

```
run.py                  入口 / CLI
start.command           macOS 双击启动
settings.json           可选配置（自建）
app/
  config.py             配置与路径
  http_client.py        HTTP：按域限速、指数退避重试、遵守 Retry-After、磁盘缓存
  logging_util.py       日志（logs/app.log 滚动）
  textnorm.py           文本归一化（下标 / 希腊字母 / 连字符 / JATS 标记）
  fields/               研究方向（每个方向一套分类轴与关键词规则）
    base.py             Pack / Facet / Node 数据结构 + 规则审计（拦下过短的词）
    __init__.py         方向注册表；自定义方向的构建
    solid_state_battery.py    固态电池（55 分类 / 86 期刊）
    lithium_ion_battery.py    锂离子电池（29 / 64）
    sodium_ion_battery.py     钠离子电池（23 / 55）
    perovskite_solar.py       钙钛矿太阳能电池（23 / 60）
    electrocatalysis.py       电催化与制氢（26 / 72）
    fuel_cell.py              燃料电池（17 / 58）
  classify.py           相关性判定 + 多标签分类引擎（由方向驱动）
  journals.py           期刊总表（119 种，含 ISSN / 分档 / 参考影响因子）
  store.py              SQLite + FTS5 全文索引 + 分面计数 + 账号与会话
  ingest.py             抓取流水线（按方向并行状态 / 摘要回补 / 失效清理）
  server.py             本地 HTTP：会话认证 + JSON API + 静态资源
  netinfo.py            局域网地址识别、代理/防火墙检测
  qrcode.py             二维码编码与终端渲染（零依赖）
  sources/
    crossref.py         主源
    europepmc.py        摘要回补
    elsevier.py         摘要回补（可选，需 key）
    openalex.py         摘要与被引回补（配额有限，带熔断）
  web/                  前端
    index.html          页面骨架（登录 / 方向问询 / 主界面 / 账号面板 + PWA 元信息）
    styles.css          桌面 + 手机两套布局
    app.js              全部交互逻辑
    manifest.webmanifest  PWA 清单（可安装、独立窗口、快捷方式）
    sw.js               Service Worker（外壳 network-first，离线回退缓存）
    icons/              各尺寸图标（由 tools/gen_icons.py 生成）
data/papers.db          文献库（SQLite）
logs/app.log            运行日志
tools/
  resolve_journals.py   从 Crossref 解析期刊 ISSN
  gen_journals.py       生成 app/journals.py
  gen_icons.py          生成 PWA 图标（构建期需要 Pillow，运行时不需要）
  validate_packs.py     拿真实 Crossref 数据量测各方向的命中率与精度
  retune_pack.py        把方向包里的规则在 core / context / negative 之间迁移
  qr_verify.swift       用 Apple Jvision 解码二维码，供测试验证编码器
  cdp.py                测试用的 Chrome DevTools 客户端（界面测试依赖）
tests/                  11 个测试套件，见上文「测试」
data/backups/           迁移前后的数据库副本（自建）
```

数据库可以直接用 SQL 查：

```bash
# 某个方向下、主分类为卤化物的最新 10 篇
sqlite3 data/papers.db \
  "SELECT p.pub_date, p.journal, p.title
     FROM paper_fields f JOIN papers p ON p.doi = f.doi
    WHERE f.field = 'solid-state-battery' AND f.primary_node = 'halide'
    ORDER BY p.pub_date DESC LIMIT 10;"
```

表结构：`papers` 按 DOI 存一份文献本体；`paper_fields`（`field` + `doi`）存
「这篇在这个方向下的分类标签与相关度」，所以同一篇可以同时属于多个方向而不重复
存储；`user_papers` 存每个账号自己的收藏与已读。旧的单方向数据库（v1）会在
首次启动时自动迁移，原有文献与标签全部保留。

---

## 已知限制

- **摘要覆盖约 50–60%**，原因见上文；缺失者标注清楚并持续重试。
- **账号只在这台电脑上**。没有云端，没有找回密码的邮件——忘了密码就只能删掉
  `data/papers.db` 里的 `users` 表重建账号（文献本身不会丢，收藏和已读会丢）。
- **分类是关键词规则判定**，不是语义模型。会有偏差，尤其是只有标题、
  没有摘要时（这类文献约占三分之一）。请以原文为准。
- **影响因子是近期 JCR 参考值**，硬编码在 `app/journals.py`，不是实时数据，
  仅用于排序与展示。
- **被引次数**来自 Crossref，新文章基本为 0（右侧显示为 `—`）；OpenAlex 现已改为
  计量付费，免费额度用尽后不再补充。
- **出版日期**取「实际上线日」：不少出版商（尤其 Elsevier）会把 6 月上线的文章
  标成 12 月甚至次年的期次日期。软件优先用 `published-online`，其次用未来日期
  以外的 `published`，再退到 DOI 注册日，并保证不晚于今天——否则几个月前的旧文
  会一直压在今天的新文上面。
- **定向方向雷达只覆盖清单内的期刊**（每个方向 55–86 种，取自总表的 119 种）。
  全球学术检索另查 OpenAlex，可检索已收录的会议论文与预印本。
- **自定义方向的准确率不如内置方向**。内置方向的规则是拿几万条真实记录反复调过的
  （含几十条排除邻近领域的负向规则）；自定义方向只有你填的那些词，门槛也更宽。
- 服务默认只绑定 `127.0.0.1`；加 `--lan` 才对局域网开放。**加了 `--lan` 之后，
  同一网络内的任何人都能访问到登录页**——密码用 PBKDF2-SHA256（24 万轮加盐）
  存储、登录失败按 IP 限流、会话 cookie 是 HttpOnly 且不可预测；浏览器的跨站
  POST 会被拒绝，修改请求要求 JSON，内部异常不会直接返回给浏览器。但整条链路仍是
  **纯 HTTP**，同网络内可被抓包。不要在公共 Wi-Fi 上开 `--lan`，也不要用你
  在别处用过的密码。当前版本仍需额外的 HTTPS、部署与安全工作才能作为公网服务。
- **手机端离线缓存**在纯 HTTP 的局域网地址下不可用（浏览器只允许安全来源注册
  Service Worker）；「添加到主屏幕」与独立窗口不受影响。
