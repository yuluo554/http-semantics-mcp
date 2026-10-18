# 10-19-http-semantics-mcp 总览（plan/00）

- **项目**：HTTP 语义判定 MCP Server（CORS 放行判定 + 缓存新鲜度 + 条件请求 + Vary 命中）
- **性质**：不参赛项目题（模拟项目），发布 GitHub **公开仓库**，署名 `yuluo554`
- **版本**：v1（2026-10-17 定稿；检索基准日 2026-10-17，实测窗口 2026-10-18 10:33–11:05 UTC）
- **当前里程碑**：M5 schema 与自检 ✅（2026-10-18：五个 tool 的 schema 描述符落地并逐字节镜像，契约门 / 确定性门 / WPT 全量对账 / 端到端 stdio 全部就位）；M6 发布待开工
- **交付形态**：**MCP Server（stdio 传输）**，唯一形态，不设备选
- **一句话定位**：把 Fetch Standard 的 CORS 协议算法与 RFC 9111 缓存新鲜度算法编译成可调用的 oracle——给一组请求/响应头，返回 `allow|block`、违反的规则编号 + 规范条款、以及该改哪个 header。**不联网、不抓包、不做安全打分。**

## 一、文档索引

| 文档 | 内容 | 状态 |
| --- | --- | --- |
| `plan/00-README总览.md` | 本文档：索引、决策记录、承诺-证据台账、里程碑 | ✅ 已建立 |
| `plan/01-题目文档.md` | 十段式题目定稿（**定稿不改写**；后续勘误走新版本号 + 版本史行） | ✅ 已建立 |
| `plan/02-架构与技术选型.md` | 交付形态、分层架构、目录结构、stdio 协议与错误契约 | ✅ M0 定稿 |
| `plan/03-模块详设.md` | T1–T5 判定算法、规则编号表、`spec_ref` 生成方式 | ✅ M0 定稿 |
| `plan/04-数据计划.md` | golden case 组织、WPT 映射台账、假时钟用例、oracle 独立性 | ✅ M0 定稿；M1 已按实况补记（不降级、递归覆盖） |
| `plan/05-里程碑.md` | M0–M6 DoD 与状态 | ✅ M0 定稿 |
| `plan/06-交付对标与决策记录.md` | 评分对标、决策细化（D19–D50）、待定决策回写 | ✅ M0 定稿；M1 增补 D35–D40；M2 增补 D41–D43；M3 增补 D44–D46；M4 增补 D47–D49；M5 增补 D50 |
| `data/README.md` | 依据查证记录（三态）、数据源可获取性、合成数据纪律、**数值口径（唯一出处）** | ✅ M1 §4 定稿（条款全核对、输出键集合登记） |

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
| WPT `cors/` 语料可得 | `web-platform-tests/wpt` 仓库（commit `850b36a5`） | `data/README.md` §2、`data/wpt-mapping.json` | 目录可访问 + 映射台账逐条对照 | ✅ M5（45 条 = 15 mapped + 30 unmappable；15/15 mapped 行实跑与 golden 期望逐字节一致） |
| T1 `cors_evaluate` | 本题设计 | MCP tool + `schemas/tools/cors_evaluate.json` | golden case 正反例 | ✅ M2（24 条 golden 逐字节相等；schema 见 M5） |
| T2 `cors_simulate_fetch` | 本题设计 | MCP tool + schema | 重定向事件 golden case | ✅ M2（10 条 golden；事件顺序/条数被锁定） |
| T3 `cache_evaluate` | 本题设计 | MCP tool + schema | 假时钟 golden case | ✅ M3（18 条 golden 逐字节相等；7 条 `_time` 锁定两种时间格式） |
| T4 `conditional_evaluate` | 本题设计 | MCP tool + schema | RFC 9110 §13 优先级 golden case | ✅ M4（19 条 golden 逐字节相等；§13.2.2 四条件两两组合与短路被锁定） |
| T5 `vary_match` | 本题设计 | MCP tool + schema | 归一化 + `Vary: *` golden case | ✅ M4（9 条 golden 逐字节相等；归一化策略表从 `codes.json` 读取） |
| 字节级确定性 | 本题设计 | 全部 tool | 同输入双跑序列化 sha256 相等 | ✅ M5（五 tool × 全部 golden 双跑 sha256 相等；输出无时间戳/随机/路径） |
| stdio server 可被真实客户端调用 | MCP 协议 | `README.md` 安装说明 | 客户端启动 + `tools/list` 五个 tool 全列 | ✅ M5（`tests/test_stdio_end_to_end.py`：握手 → 列五 tool → 五 tool 各成功调用一次 → 未知 tool `-32602`） |
| WPT `cors/` 全量映射 | 本题设计 | `data/wpt-mapping.json` | 可转写用例全绿 + 不可转写逐条登记原因 | ✅ M5（15/15 mapped 行实跑对账；30 行逐条有 `reason`） |
| 发布三件套 | M6 DoD | tag / Release 附产物 / `plan/RELEASE-M6.md` | `scripts/check_release.py` | ⬜ 待 M6 |

## 四、里程碑

| 里程碑 | 内容 | DoD | 状态 |
| --- | --- | --- | --- |
| **M0 计划与骨架** | plan/02–06 定稿；可启动空 server；全套工程门 | 双解释器 pytest 全绿；stdio 握手通过；三道静态门可证伪 | ✅ 完成（2026-10-18） |
| **M1 数据先行** | 规范条款核对（RFC 9111 / 9110 / 5861 + Fetch 算法锚点）+ golden case 组织方式 + WPT `cors/` 用例 JSON 化 + `data/wpt-mapping.json` 初版 | 每个 `code` 至少 1 条 golden case；WPT 可转写用例全部映射；不可转写用例逐条登记原因；`data/README.md` §4 口径定稿 | ✅ 完成（2026-10-18） |
| **M2 CORS** | T1 `cors_evaluate` + T2 `cors_simulate_fetch` 判定实现（M2 用内联 `inputSchema`，正式 schema 随 M5） | golden case 全绿；重定向事件（`origin_set_to_null` / `credentials_dropped`）显式输出；`no-cors` / `same-origin` 模式可见性正确 | ✅ 完成（2026-10-18） |
| **M3 缓存** | T3 `cache_evaluate` | 假时钟注入可用；RFC 9111 新鲜度 / 年龄 / 动作判定 golden case 全绿；`reasons[]` 带条款号 | ✅ 完成（2026-10-18） |
| **M4 条件请求与 Vary** | T4 `conditional_evaluate` + T5 `vary_match` | §13.2.2 求值顺序与短路正确；强弱比较分离；`Vary: *` 与归一化用例全绿 | ✅ 完成（2026-10-18） |
| **M5 schema 与自检** | 五个 tool schema 定稿、server 组装、确定性守门、WPT 全量映射跑通 | schema 与实现字段集合相等；同输入双跑字节一致；stdio 客户端可启动并列出五个 tool；WPT 映射全量通过 | ✅ 完成（2026-10-18） |
| **M6 发布** | 发布 GitHub **公开仓库** | **M6 DoD = 三件套：①git tag ②GitHub Release（附产物：至少一个手工上传附件，本地留副本 + sha256）③发布留档文件 `plan/RELEASE-M6.md`（tag 之前写好并进 tag 树）**；发布后跑 `scripts/check_release.py` | ⬜ 待开工 |

> 发布留档文件必须在 tag **之前**入库；tag 之后只允许追加类提交（回写实测值 / 对账 / 补记），并在留档里分栏写"tag 时点事实 / tag 后追加事实"。

## 五、当前状态

### M5（2026-10-18）已完成

- **契约载体**：五个 tool 各有一份 JSON Schema 描述符，落在包内 `src/http_semantics_mcp/schemas/tools/<tool>.json`（含 `name` / `description` / `inputSchema` / `outputSchema`），顶层 `schemas/tools/*.json` 为逐字节镜像。`registry.py` 改为运行时读取包内描述符（缺件抛 `DescriptorError`，不会静默退化成空表）；`tools/list` 现在同时发布 `inputSchema` 与 `outputSchema`。
- **生成器**：`tools/gen_schemas.py --check` 逐字节比对镜像 + 形状校验（`required ⊆ properties`、带 `properties` 的对象必须 `additionalProperties: false`、纯 map 形状对象必须显式声明 `additionalProperties`、`outputSchema.properties` 与 `required` 都等于 `data/README.md` §4.10 键集合、文件必须处于规范形式）；`tools/spectable.py::read_output_fields` 把 §4.10 读成机器可读键集合。
- **契约门**：`tests/test_schema_parity.py`（18 项）——描述符文件集合 == §4.10 工具集合 == 注册集合；五 tool 各自 `outputSchema.properties` == §4.10 == 实跑输出键集合（80 条 tool golden：78 成功 + 2 错误，错误结果固定 `{"error": {...}}`）；成功输出按 schema 逐字段校验类型/枚举/嵌套；且断言"参与比对的用例数 > 0 且五 tool 各自有用例"，并把 7 条 `_time` 样例纳入 §4.10 的覆盖（全量 87 条）。
- **确定性门**：`tests/test_determinism.py`（4 项）——五 tool × 全部 golden 双跑 `sha256(canonical.dumps(...))` 相等，且输出无机器绝对路径、无调用方未提供的日期、无 `\r`。
- **WPT 全量对账**：`tests/test_wpt_ledger.py::test_mapped_rows_reconcile_with_the_production_output` 由台账驱动，遍历 15 条 `mapped=true` 行、逐条实跑其 `case_ids` 指向的 golden 并与冻结 `expected` 逐字节对账（25 条引用），打印 `15/15` 计数；30 条 `mapped=false` 行只校验 `reason` 在枚举内。
- **端到端**：`tests/test_stdio_end_to_end.py`（2 项）——真实子进程 + 真实 stdio：`initialize` → `notifications/initialized` → `tools/list`（五个 tool、ASCII 升序）→ 五 tool 各成功调用一次（用服务器自己发布的 `outputSchema` 校对键集合）→ 未知 tool 走 JSON-RPC `-32602`；并验证跨进程边界的双跑字节一致。
- **门与变异**：8 道静态门全绿（合计扫 730 文件项）；`tools/mutate_check.py` 43/43 变异变红（新增 5 条：schema 少一个 property、`additionalProperties` 改 `true`、顶层镜像改一字节、§4.10 掉一个字段、tool face 注入 volatile 键）。
- **生成物复算**：`gen_codes --check`（9468 字节 + 镜像 + `rules.py` 16772 字节）、`gen_golden --check`（87 case / 0 problem）、`gen_schemas --check`（5 tool / 0 problem）逐字节一致；覆盖率 31/31/0/0；双解释器收集数一致（379 / 379）。
- **stdout 指标段**：README 新增"Measured on this build"（golden 87/87、WPT 15/45 + 30/45、5 描述符、8 门、43 变异、378/378 测试），并保留"本地等价校验（未接远端，CI 待首推验证）"措辞。
- **决策**：D50（schema 真相源路线 A：包内 JSON 为唯一可编辑真相、registry 读它、gen_schemas 只镜像+校验；附带澄清 `additionalProperties: false` 只落在带 `properties` 的对象上）。

### M4（2026-10-18）已完成

- **判定层**：`judgement/conditional.py`（T4，E1–E5 固定短路；`strong_compare` / `weak_compare` 分开写）、`judgement/vary.py`（T5，V1–V4；归一化策略从 `catalog["vary_normalization"]` 读，代码里没有第二份策略分支）。判定层仍是无时钟、无网络、无盘、无 env 的纯函数。
- **工具面**：`toolface.FUNCTIONS` 注册 `conditional_evaluate` / `vary_match`；`registry.build_registry()` 现注册五个 tool（ASCII 升序 `cache_evaluate` < `conditional_evaluate` < `cors_evaluate` < `cors_simulate_fetch` < `vary_match`），`tools/list` 由 3 → 5；`inputSchema.required` 分别取 `["method","request_headers","resource"]` 与 `["cached","incoming"]`。
- **golden**：19 条 conditional + 9 条 vary 逐字节相等（`canonical.dumps(实际) == canonical.dumps(expected)`）；错误用例（`cond-014` 小写 `w/`）返回 `isError: true` 且 `field = request_headers.if-none-match`。
- **新增测试**：`tests/test_conditional_golden.py`（43 项）与 `tests/test_vary_golden.py`（27 项）——golden 逐字节相等之外，把 golden 未覆盖的分支直接钉住：强弱比较关系、`*` 与 ETag 的绑定、`If-Modified-Since` 的方法门、秒级边界（`>` / `<=`）、策略表换行即翻转判定（`evaluate_vary` 接收改写过的 catalog）、重复字段只报一次。
- **门与变异**：8 道静态门全绿（合计扫 700 文件项）；`tools/mutate_check.py` 38/38 变异变红（新增 12 条：T4 弱比较、次序颠倒、`*` 语义、304/412 分叉、小写 `w/`、IMS 方法门、非法日期改报错 7 条 + T5 star 短路、缺字段、策略分支、重复提示、逗号排序 5 条）。
- **生成物复算**：`gen_codes --check` 三件逐字节一致（`codes.json` 9468 字节 + 镜像 + `rules.py` 16772 字节）；`gen_golden --check` 87 case / 0 problem；覆盖率 31 declared / 31 covered / 0 uncovered / 0 unknown。
- **双解释器**：3.8 → 354 passed；3.12 → 354 passed；收集数一致（各 354）。
- **stdio**：5 响应 / 5 tool / 7514 字节，两个解释器一致。
- **发布门**：`--pre-tag` 提交前 5 PASS / 1 FAIL（git-clean，预期）/ 4 SKIP；提交后 6 PASS / 0 FAIL / 4 SKIP（干净树，700 文件项，退出 0）。
- **决策**：D47（T4 三处边缘口径：`*` 绑 ETag、IMS 方法门、`resource` 字段严格校验 vs 请求头日期忽略）、D48（T5 重复字段只报一次 + `Vary: *` 短路）、D49（生产侧相对 oracle 的三处有意偏差：必填键更严、资源日期错误码取 `INVALID_TIME_FORMAT`、空数组不崩）。
- **DoD 勘误**：`plan/HANDOFF-M4.md` §五 的"非法日期一律忽略"收窄为"请求头日期忽略（`cond-012`）/ `resource.last_modified` 非法 → `INVALID_TIME_FORMAT`"，依据 `data/README.md` §4.4/§4.6；勘误段写在 `plan/05` 的 M4 节，差异登记在 D47③/D49②。

### M3（2026-10-18）已完成

- **判定层**：`judgement/cache.py`（T3，C1–C11）、`judgement/timeparse.py`（`YYYY-MM-DDTHH:MM:SSZ` 与 IMF-fixdate 两种格式 + 拒绝路径）。判定层仍是无时钟、无浮点的纯函数：`now` 是参数，整数秒算术。
- **工具面**：`toolface.FUNCTIONS` 注册 `cache_evaluate`；`registry.build_registry()` 现注册三个 tool（ASCII 升序 `cache_evaluate` < `cors_evaluate` < `cors_simulate_fetch`），`tools/list` 由 2 → 3；`inputSchema.required = ["now", "stored"]`。
- **golden**：18 条 cache golden 逐字节相等；`_time` 7 条（4 正例 + 3 反例）由 `tests/test_cache_golden.py` 直接调 `parse_time` 锁定。
- **门与变异**：8 道静态门全绿（合计扫 680 文件项）；`tools/mutate_check.py` 26/26 变异变红（新增 6 条，含 `is_fresh` 边界、`no-store` 短路、swr 等号、`Age` informational、HTTP-date 星期、亚秒进位）。
- **双解释器**：3.8 → 284 passed；3.12 → 284 passed；收集数一致。
- **stdio**：5 响应 / 3 tool / 5276 字节，两个解释器一致。
- **决策**：D44（Age 取值优先级 `stored.age` > 响应头）、D45（截断纪律覆盖亚秒与闰秒）、D46（swr 边界用测试钉住而非新 golden）。

### M2（2026-10-18）已完成

- **判定层**：`judgement/cors.py`（T1）、`judgement/fetch_sim.py`（T2）、共享 `judgement/normalise.py` 与 `judgement/errors.py`；`toolface.py` 把判定结果渲染成 MCP tool 结果（`isError` 只由"调用方输入坏"触发，`decision: block` 仍是 `isError: false`）。
- **工具面**：`registry.build_registry()` 注册两个 tool（ASCII 升序 `cors_evaluate` < `cors_simulate_fetch`），`tools/list` 由 0 → 2；正式 schema 与"schema 键集合 == 输出键集合"门在 M5（D43）。
- **规则引用**：`gen_codes.py` 新增渲染 `src/http_semantics_mcp/rules.py`（`codes.json` 的 Python 形态 + 每个 `code` 一个同名常量），判定层按名 import；`code_literals` 门对该生成文件单点豁免并断言其存在（D41/D42）。
- **golden**：34 条 CORS golden（eval 24 / sim 10）逐字节相等；错误用例返回 `isError: true` 载荷。
- **门与变异**：8 道静态门全绿（扫 664 文件）；`tools/mutate_check.py` 20/20 变异变红（新增 6 条）。
- **双解释器**：3.8 → 248 passed；3.12 → 248 passed；收集数一致。
- **stdio**：5 响应 / 2 tool / 3719 字节，两个解释器一致。

### M1（2026-10-18）已完成

- **规则表**：`references/codes.json`（包内真相源）+ 顶层镜像，31 个 `code`，由 `data/README.md` §4.1 生成；`gen_codes --check` 逐字节比对。
- **golden**：87 条（cors 24 / sim 10 / cache 18 / cond 19 / vary 9 / _time 7），期望值全部由 `tools/golden_oracle/` 产出；`gen_golden --check` 逐字节比对且检出 orphan。
- **覆盖**：31 declared / 31 covered / 0 uncovered / 0 unknown。
- **WPT**：`data/wpt/cors-index.json`（45 条，commit `850b36a5`，数据日 2026-10-18）；`data/wpt-mapping.json` 15 converted + 30 unmappable = 45。
- **门**：8 道静态门（新增 oracle 独立性 / golden 卫生 / code 字面量）；`tools/mutate_check.py` 14/14 变异变红。
- **双解释器**：3.8 → 198 passed；3.12 → 198 passed；收集数一致。

### M0（2026-10-18）已完成

- **计划**：`plan/02`–`06` 定稿；`plan/00` 索引与状态回写；`data/README.md` 保持为口径唯一出处。
- **代码骨架**：`src/http_semantics_mcp/` 下 server / protocol / registry / canonical / errors / selfcheck / `_utf8` 全部落地，**运行时零第三方依赖**。
- **可运行证据**：
  - `python -m http_semantics_mcp --version` → `0.1.0.dev0`，退出 0。
  - `python -m http_semantics_mcp --selftest` → 6 项 PASS，退出 0（新装 venv 的 `http-semantics-mcp.exe` 同验）。
  - `tools/smoke_stdio.py` 真实子进程握手：5 响应、0 tool、446 字节 stdout，无 `\r`，退出 0（3.8 与 3.12 各一次）。
  - 双解释器 pytest：`py -3.8` 129 passed / `py -3.12` 129 passed。
  - `tools/run_gates.py`：purity / absolute-paths / crlf 三门前绿，扫描 48 个文件。
  - `scripts/check_release.py --pre-tag`：5 PASS / 1 FAIL（工作树未提交，预期）/ 4 SKIP。
- **M5 后仍未建立**：tag / GitHub Release / 发布附件（M6）。五个 tool 的正式 schema 文件、`schema properties == 实跑输出键集合` 门、确定性全量 sha256 扫描、WPT 全量映射对账均已在 M5 落地。`tools/list` 返回五个已实现的 tool，这是当前正确行为。

### 诚实口径

- **未推送远端**：本项目的 CI 从未运行过。任何"CI 绿"的说法在此刻都不成立；M0–M5 的等价证据只有本地实跑项（双解释器 / 真实子进程 / 静态门 / 生成物复算 / 变异验证）。README 的指标段只写本地实测值，并保留"本地等价校验（未接远端，CI 待首推验证）"措辞。
- M6 首推后据实补记 run id 与首跑结果；历史文档保留"本地等价校验"原措辞，补记是追加事实。
- `tools/list` 在 M0/M1 返回空列表是**正确行为**，README 已如实写明；M2 起返回两个 CORS tool，M3 起再返回 `cache_evaluate` 共三个，M4 起返回全部五个；五个 tool 的正式 schema（`inputSchema` + `outputSchema`）与"schema 键集合 == 输出键集合"门已在 M5 落地（字段集合由 `data/README.md` §4.10 冻结，D50）。
