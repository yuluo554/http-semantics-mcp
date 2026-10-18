# 10-19-http-semantics-mcp 总览（plan/00）

- **项目**：HTTP 语义判定 MCP Server（CORS 放行判定 + 缓存新鲜度 + 条件请求 + Vary 命中）
- **性质**：不参赛项目题（模拟项目），发布 GitHub **公开仓库**，署名 `yuluo554`
- **版本**：v1（2026-10-17 定稿；检索基准日 2026-10-17，实测窗口 2026-10-18 10:33–11:05 UTC）
- **当前里程碑**：M0 出题定稿 ✅（骨架四件套 + 首提交）；M1–M6 待开工
- **交付形态**：**MCP Server（stdio 传输）**，唯一形态，不设备选
- **一句话定位**：把 Fetch Standard 的 CORS 协议算法与 RFC 9111 缓存新鲜度算法编译成可调用的 oracle——给一组请求/响应头，返回 `allow|block`、违反的规则编号 + 规范条款、以及该改哪个 header。**不联网、不抓包、不做安全打分。**

## 一、文档索引

| 文档 | 内容 | 状态 |
| --- | --- | --- |
| `plan/00-README总览.md` | 本文档：索引、决策记录、承诺-证据台账、里程碑 | ✅ 已建立 |
| `plan/01-题目文档.md` | 十段式题目定稿（**定稿不改写**；后续勘误走新版本号 + 版本史行） | ✅ 已建立 |
| `plan/02-架构与技术选型.md` | 交付形态、分层架构、目录结构、stdio 协议与错误契约 | ⬜ M1 前定稿 |
| `plan/03-模块详设.md` | T1–T5 判定算法、规则编号表、`spec_ref` 生成方式 | ⬜ M1 前定稿 |
| `plan/04-数据计划.md` | golden case 组织、WPT 映射台账、假时钟用例 | ⬜ M1 前定稿 |
| `plan/05-里程碑.md` | M1–M6 DoD 与状态 | ⬜ M1 前定稿 |
| `plan/06-交付对标与决策记录.md` | 评分对标、决策细化、待定决策表 | ⬜ M1 前定稿 |
| `data/README.md` | 依据查证记录（三态）、数据源可获取性、合成数据纪律、**数值口径（唯一出处）** | ✅ 已建立 |

## 二、决策记录

> **D1–D3 是本题的定位生死线，必须显著保留。**

| 编号 | 决策 | 弃选项 / 结论 | 弃因 |
| --- | --- | --- | --- |
| **D1** | 形态定为 **MCP Server（stdio）**，判定逻辑做成纯函数供 tool 调用 | 做成 CLI 或 Web 服务 | 本系列首次做 MCP 形态；MCP 是 agent 直接调用外部能力的标准接口，判定器进入 agent 工作流必须走这一形态。CLI 只能人跑，Web 服务引入端口与部署成本且违背零网络纪律 |
| **D2** | **只做语义判定，不做安全扫描** | 叠加 header 安全评级 / CVE / HSTS 评分 | `mcp security` 方向供给充足且红海；叠加后定位漂移，且"安全"是主观评分而本题要的是确定性判定 |
| **D3** | **零网络、零抓包**：输入是 header 字面量，`url` 只用于解析 scheme/host/port | 读取真实响应 / 接管代理 / 解析 HAR | 相邻形态已被 `mitmproxy-mcp`（129★）与 `powhttp-mcp`（83★）占据；抓包引入环境依赖，破坏纯函数与字节级复现 |
| D4 | 首期 5 个 tool 收敛为 T1–T5 | 首期塞入 CSP / COOP / COEP / HSTS / Permissions-Policy | 首期范围必须可完成、可验收；安全头属 D2 切割范围 |
| D5 | 每个判定输出带 `code` + `spec_ref` + 固定模板 `detail` | 输出一段自然语言解释 | 自然语言由模型生成 → 不可回归、不可字节级断言；固定模板可被 golden case 锁定 |
| D6 | **不依赖** `http-cache-semantics` 等第三方语义库，自行实现判定 | 直接 import 成熟库 | 成熟库是优秀参照（262★），但其内部条款映射不对外暴露为 `spec_ref`；本题的核心交付物正是条款级可追溯，依赖库会让判定成为黑盒 |
| D7 | 时间一律入参（T3 的 `now`），禁止读系统时钟 | 读 `time.time()` | 时钟使同输入输出不同，golden case 无法冻结 |
| D8 | 复用 WPT `cors/` 作为外部 oracle，转写为 golden case | 自造全部期望值 | 自造期望值等于用实现自证；WPT 提供浏览器行为级的第三方依据 |
| D9 | 错误输入返回结构化错误，不抛栈、不退出进程 | 让异常冒泡到 stdio | MCP 客户端需要可解析的错误；server 崩溃会中断整个会话 |
| D10 | 纯本地、零遥测、不落盘用户输入 | 收集调用样本改进规则 | 隐私红线；header 可能含 token / cookie |
| D11 | 品牌隔离：文档、仓库名、tool 名不引用本系列其他项目 | 与本系列其他仓库交叉引用 | 领域完全独立（HTTP 协议语义 vs 日志/合规类），交叉引用会污染定位与检索 |
| D12 | **弃**"OpenAPI 契约 diff"方向 | 作为本题主题 | `oasdiff` 1422★ 已占心智，且一个 50 行壳即可复制核心动作，差异化不成立 |
| D13 | **弃**"CIDR / 子网计算"方向 | 作为本题主题 | 市场窄：`mcp subnet calculator` total=4，头部仅 12★ |
| D14 | **弃**"cron / RRULE 解析"方向 | 作为本题主题 | 占位明显：`scheduler-mcp` 59★ 已在场 |
| D15 | **弃**"WCAG 对比度检查"方向 | 作为本题主题 | 天花板极低：单条公式即可完成，做不出可交付深度 |
| D16 | **弃**"SQL 方言转译"方向 | 作为本题主题 | agent 自己 `pip install sqlglot` 即可，增益低（`mcp sqlglot` total=47） |
| D17 | **弃**"Excel 公式语义"方向 | 作为本题主题 | `excel-mcp-server` 4247★ 已占心智 |
| D18 | M6 口径采用"Release 附产物" | 用源码 zipball 冒充产物 | 源码压缩包不是交付物 |

## 三、承诺-证据台账（全项目唯一一份）

> 状态列随里程碑同步翻转；其他文档只可引用本表，不得复制第二份。
> `⬜` 表示尚未兑现的承诺，**不得在任何文档里写成已完成**。

| 承诺项 | 素材来源 | 交付物内可达性 | 核验方式 | 状态 |
| --- | --- | --- | --- | --- |
| 痛点锚点：CORS 931 分原话 | HN id 20404578（重发 48614844） | `plan/01` §1.1、README 引用 | 链接可直连复核 | ✅ 已登记 |
| 痛点锚点：ETag 152 分评论 | HN id 39996521 | `plan/01` §1.1 | 同上 | ✅ 已登记 |
| 痛点锚点：Cache-Control 197 分 / Caching Refresher 180 分 | HN id 11679211 / 46368616 | `plan/01` §1.1 | 同上 | ✅ 已登记 |
| 开源空白：六条检索式 0 命中 | `gh api`，基准日 2026-10-17 | `data/README.md` §1 | 按检索式复跑；**软论据** | ⬜ 软论据（不可硬化为结论） |
| 相邻形态区分（129★ / 83★ / 0★） | `gh api` + 仓库自述 | `plan/01` §1.3 | 仓库可访问复核 | ✅ 已登记 |
| 底层引擎参照（262★ / 6194★） | `gh api` | `plan/01` §1.4 | 同上 | ✅ 已登记 |
| npm 生态体量 | npm registry 周下载 2026-10-10 ~ 10-16 | `data/README.md` §1.3 | 按周复跑 | ✅ 已登记 |
| WPT `cors/` 语料可得 | `web-platform-tests/wpt` 仓库 | `data/README.md` §2、`data/wpt-mapping.json` | 目录可访问 + 映射台账逐条对照 | ⬜ 待 M1 建立映射 |
| T1 `cors_evaluate` | 本题设计 | MCP tool + `schemas/tools/cors_evaluate.json` | golden case 正反例 | ⬜ 待 M2 |
| T2 `cors_simulate_fetch` | 本题设计 | MCP tool + schema | 重定向事件 golden case | ⬜ 待 M2 |
| T3 `cache_evaluate` | 本题设计 | MCP tool + schema | 假时钟 golden case | ⬜ 待 M3 |
| T4 `conditional_evaluate` | 本题设计 | MCP tool + schema | RFC 9110 §13 优先级 golden case | ⬜ 待 M4 |
| T5 `vary_match` | 本题设计 | MCP tool + schema | 归一化 + `Vary: *` golden case | ⬜ 待 M4 |
| 字节级确定性 | 本题设计 | 全部 tool | 同输入双跑序列化 sha256 相等 | ⬜ 待 M5 |
| stdio server 可被真实客户端调用 | MCP 协议 | `README.md` 安装说明 | 客户端启动 + `tools/list` 五个 tool 全列 | ⬜ 待 M5 |
| WPT `cors/` 全量映射 | 本题设计 | `data/wpt-mapping.json` | 可转写用例全绿 + 不可转写逐条登记原因 | ⬜ 待 M5 |
| 发布三件套 | M6 DoD | tag / Release 附产物 / `plan/RELEASE-M6.md` | `scripts/check_release.py` | ⬜ 待 M6 |

## 四、里程碑

| 里程碑 | 内容 | DoD |
| --- | --- | --- |
| **M1 数据先行** | 规范条款核对（RFC 9111 / 9110 / Fetch 算法锚点）+ golden case 组织方式 + WPT `cors/` 用例 JSON 化 + `data/wpt-mapping.json` 初版 | 每个 `code` 至少 1 条 golden case；WPT 可转写用例全部映射；不可转写用例逐条登记原因；`data/README.md` §4 口径定稿 |
| **M2 CORS** | T1 `cors_evaluate` + T2 `cors_simulate_fetch` 判定实现与 schema | golden case 全绿；重定向事件（`origin_set_to_null` / `credentials_dropped`）显式输出；`no-cors` / `same-origin` 模式可见性正确 |
| **M3 缓存** | T3 `cache_evaluate` | 假时钟注入可用；RFC 9111 新鲜度 / 年龄 / 动作判定 golden case 全绿；`reasons[]` 带条款号 |
| **M4 条件请求与 Vary** | T4 `conditional_evaluate` + T5 `vary_match` | §13.2.2 求值顺序与短路正确；强弱比较分离；`Vary: *` 与归一化用例全绿 |
| **M5 schema 与自检** | 五个 tool schema 定稿、server 组装、确定性守门、WPT 全量映射跑通 | schema 与实现字段集合相等；同输入双跑字节一致；stdio 客户端可启动并列出五个 tool；WPT 映射全量通过 |
| **M6 发布** | 发布 GitHub **公开仓库** | **M6 DoD = 三件套：①git tag ②GitHub Release（附产物：至少一个手工上传附件，本地留副本 + sha256）③发布留档文件 `plan/RELEASE-M6.md`（tag 之前写好并进 tag 树）**；发布后跑 `scripts/check_release.py` |

> 发布留档文件必须在 tag **之前**入库；tag 之后只允许追加类提交（回写实测值 / 对账 / 补记），并在留档里分栏写"tag 时点事实 / tag 后追加事实"。

## 五、当前状态

- 阶段 4（出题骨架）已完成（2026-10-18）：`plan/00`、`plan/01`、`data/README.md`、`.gitignore` 四件套落盘；`git init -b main` + 中文首提交完成。
- 尚未建立任何可运行代码：`src/`、`schemas/`、`tests/` 由 M1–M5 产出。
- 未推送远端：CI 类结论一律不写"CI 绿"，M6 首推后据实补记 run id。
