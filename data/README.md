# data/ — 依据查证、数据源与口径纪律

> **查证基准日：2026-10-17**。
> **实测窗口（必须原样保留）**：GitHub 检索的实际执行时间为 **2026-10-18 10:33–11:05 UTC**，与登记的基准日 **跨日不足 1 天**。所有检索计数都是该窗口的快照，会随时间漂移，一律与基准日成对出现，只作**软论据**。
> 三态标记：`✅ 已核对`（可直接访问 / 已实测）/ `⬜ 待核对`（路径已登记但未取得或未复核）/ 软论据（检索计数，不可硬化为能力结论）。
> **不可获取或未复核的源不得作规则来源。**

## 复核周期（机读锚）

| 字段 | 值 | 含义 |
| --- | --- | --- |
| `last_reviewed` | `2026-10-20` | 本文件各源最近一次逐条复核/确认的日期 |
| `review_interval` | `annual` | 复核节奏：每年一次（Fetch Standard 是活文档，WPT pin 也会漂） |
| `next_review` | `2027-10-20` | 到期日；到点后应重跑 §一 的检索、重核 §二 的 pin 与 §四 的口径，并更新本表三格 |
| `watched_sources` | `Fetch Standard`、`RFC 9110`、`RFC 9111`、`RFC 6265`、`web-platform-tests/wpt@cors/` | 漂移风险最高的来源；其中 Fetch 与 WPT 目录为活文档 |

> 本表只记录**复核时点**，不是规则来源；任何取值/排序/字段集合口径仍以 §四 为唯一出处（K9）。

## 一、依据查证记录

### 1.1 `gh api` 检索式与 `total_count`（基准日 2026-10-17；实测窗口 2026-10-18 10:33–11:05 UTC）

| 检索式 | `total_count` | 主要命中与判读 | 三态 |
| --- | --- | --- | --- |
| `mcp cors preflight simulation` | **0** | 无 | ✅ 实测 |
| `mcp cors checker` | **0** | 无 | ✅ 实测 |
| `mcp conditional request` | **0** | 无 | ✅ 实测 |
| `mcp stale-while-revalidate` | **0** | 无 | ✅ 实测 |
| `mcp vary header` | **0** | 无 | ✅ 实测 |
| `mcp http cache semantics` | **0** | 无 | ✅ 实测 |
| `mcp cors debugging` | 2 | 0★ `jeffereychown-Max/mcp-http-inspect`（请求重放，需真实请求） | ✅ 实测 |
| `mcp cache freshness` | 5 | 最高 9★ `claude-code-memory-cache`（与 HTTP 缓存无关）；2★ `freshprobe` | ✅ 实测 |
| `mcp etag` | 6 | 0–12★，均非 HTTP 语义判定 | ✅ 实测 |
| `mcp 304` | 6 | 0–12★，均非 HTTP 语义判定 | ✅ 实测 |
| `cors mcp server` | 42 | 6★ 示例工程、4★ middleware toolkit、3★ HAR 扫描 | ✅ 实测 |
| `mcp http cache` | 71 | 135★ `uwaserver/uwas` 为 Web 服务器本体，非 MCP 判定器 | ✅ 实测 |

**判读纪律**：六条"判定语义"检索式为 0 只说明**该措辞下未被占用**，不构成"领域空白"结论。CORS 与 HTTP 缓存是成熟领域（见 §1.3），本题只主张"判定层未被做成 MCP tool 且无条款级输出"。

### 1.2 相邻但不同形态（✅ 实测，必须写进任何对外表述）

| 仓库 | 星数 | 形态 | 差别 |
| --- | --- | --- | --- |
| `snapspecter/mitmproxy-mcp` | **129★** | 代理中间人 | 需把真实流量导入代理 |
| `usestring/powhttp-mcp` | **83★** | 流量捕获 / 重放 | 需真实抓包 |
| `rog0x/mcp-cache-tools` | **0★** | 自述 "HTTP cache header analyzer" | 0★、单作者批量发布序列中的第 30 号；无条款映射 / 无 golden case / 无确定性契约 |
| `jeffereychown-Max/mcp-http-inspect` | 0★ | 请求重放 | 需真实请求 |

> 本题**不宣称唯一**。差异点只有三条：`spec_ref` 条款级可追溯、golden case 冻结、同输入字节级一致。这三条在已检索到的命中中均未出现（⬜ 软论据，基于仓库自述与结构，基准日 2026-10-17）。

### 1.3 底层成熟引擎与生态体量（✅ 已核对）

| 项目 | 星数 / 数值 | 口径 | 与本题关系 |
| --- | --- | --- | --- |
| `kornelski/http-cache-semantics` | **262★** | GitHub 星数，基准日 2026-10-17 | 参照测试思路；**不作运行时依赖**（决策 D6） |
| `expressjs/cors` | **6194★** | 同上 | 服务端配置器，非反向判定器 |
| npm `cors` 周下载 | **51,816,047** | npm registry，2026-10-10 ~ 2026-10-16 | 配置层高频 |
| npm `etag` 周下载 | **72,561,945** | 同上 | 配置层高频 |
| npm `cache-control` 周下载 | **418** | 同上 | 语义层近零 |

> npm 数值为**周下载快照**，每周变化；引用时必须带区间"2026-10-10 ~ 2026-10-16"，不得写成"当前下载量"。

### 1.4 三态结论

| 结论 | 三态 | 说明 |
| --- | --- | --- |
| 判定层未被做成 MCP tool | ⬜ 软论据 | 六条检索式 0 命中；计数会漂移，不得写成"绝对空白" |
| 抓包 / 代理形态已被占据 | ✅ 事实区分 | 129★ / 83★ / 0★ 三个仓库在场，可逐条查看 |
| 缓存 header 分析动作已有人做过 | ✅ 事实区分 | `rog0x/mcp-cache-tools` 0★ 自述如此；本题差异仅在条款映射 + golden case + 确定性 |
| 底层实现成熟 | ✅ 事实区分 | 262★ / 6194★ 两个项目可直接查看源码与测试 |

## 二、数据源可获取性记录

| 数据源 | 三态 | 获取方式 | 阻断原因 / 降级处置 |
| --- | --- | --- | --- |
| `web-platform-tests/wpt` 的 `cors/` 目录 | ✅ 可获取 | `gh api` 读目录树（commit `850b36a5`，数据日 2026-10-18）；路径 + blob sha + 大小落 `data/wpt/cors-index.json`；可转写判定落 `data/wpt-mapping.json` | 无阻断。**只读取测试文件文本用于人工判定**，不复制正文入仓、不运行浏览器、不联网 |
| WPT 中依赖真实网络 / 证书 / 时序的用例 | ⬜ 不可转写 | — | 逐条登记到 `data/wpt-mapping.json` 的 `reason`；**不伪造期望值** |
| RFC 9111 / RFC 9110 / RFC 5861 / Fetch Standard 条款 | ✅ 已核对 | 规范原文（公开）；M1 逐条对照发布版原文核对，条款号与算法锚点见 §4.2 | Fetch Standard 为活文档，用**算法锚点名**而非数字节号；核对日 2026-10-18 |
| `http-cache-semantics`（262★） | ✅ 可获取 | 公开仓库 | 只作参照，不复制代码；不引入运行时依赖 |
| 真实站点响应头 | — | **禁止采集** | 隐私红线 + 确定性纪律：golden case 只用合成 header 组合 |
| 运行时网络请求 | — | **禁止** | 纯本地；server 不发起任何 DNS / TCP / HTTP |

### 2.1 WPT 台账口径（M1 建立）

- 索引：`data/wpt/cors-index.json` 固定 `wpt_commit`、`fetched_at`（数据日）、`directory`、`total` 与逐文件 `path` / `type` / `blob_sha` / `size`。
- 映射：`data/wpt-mapping.json` 固定 `wpt_commit`、`fetched_at`、`total`、`converted`、`unmappable`，并满足集合划分 `converted + unmappable == total`。
- **`total` 是索引里的文件条目数**（含 `cors/resources/` 下的后端脚本）；目录条目不计数。
- `mapped=true` 的条目必须指向已存在的 golden `case_id`；M5 已逐条实跑对账（`tests/test_wpt_ledger.py::test_mapped_rows_reconcile_with_the_production_output`，15/15 行与冻结 `expected` 逐字节一致）。
- WPT 测浏览器行为，本题做规范推导；两者不一致时以规范为准，差异写进对应 golden 的 `notes`，**不修改期望值去迁就浏览器**。

> 本题**没有**需要联网核对的法规文号或官方统计口径；因此不设"权威数据源待核对"条目。**不得为了凑格式编造数据源。**

## 三、合成数据纪律

### 3.1 golden case 的合成规则

- golden case 的输入是**手写的 header 组合**，来自规范条款的构造，**不得引用任何真实站点的响应头**（真实响应头可能含 token、cookie、内部域名）。
- 域名一律使用保留示例域：`example.com`、`example.org`、`example.net`，或 `localhost`。禁止使用真实公司域名。
- 端口使用 `80` / `443` / `8080` / `3000` 等常规值，不出现可识别内网地址（`10.*` / `192.168.*` 等）。
- ETag / token 一律使用显式假值，如 `"abc123"`、`W/"abc123"`。
- 时间一律使用固定字面量（如 `2026-01-01T00:00:00Z`），**不得取当前时间**。
- 每个 golden case 文件必须包含：`case_id`、`tool`、`input`、`expected`、`spec_basis[]`（该用例依据的条款 / 算法锚点）、`source`（`synthetic` 或 `wpt:<path>`）。

### 3.2 golden case 文件组织（M1 建立）

```
data/
  golden/
    _time/<case_id>.json
    cors_evaluate/<case_id>.json
    cors_simulate_fetch/<case_id>.json
    cache_evaluate/<case_id>.json
    conditional_evaluate/<case_id>.json
    vary_match/<case_id>.json
  wpt/
    cors-index.json
  wpt-mapping.json
tools/
  cases/<tool>/<case_id>.json    # 手写输入（生成侧输入面，不含 expected）
```

- **输入面**在 `tools/cases/<tool>/<case_id>.json`：只含 `case_id` / `tool` / `input` / `spec_basis` / `source` / `notes`（可选）。
- **冻结面**在 `data/golden/<tool>/<case_id>.json`：输入面全部字段 + `expected`（由 `tools/gen_golden.py` 用独立复算器产出）。
- 一个文件一个用例；文件名 = `case_id`，只允许 `[a-z0-9_-]`。
- `expected` 必须是**完整输出对象**（含所有字段），不允许只写部分字段。
- 用例冻结后只读；修改需另立 `case_id` 并在 `wpt-mapping.json` 或决策记录中注明原因。
- `data/golden/_time/` 是时间解析样例集，`tool` 固定为 `_time`，不属于五个判定 tool。

### 3.3 覆盖度最低要求

| 维度 | 最低要求 |
| --- | --- |
| 每个 `code` | 至少 1 条正例或反例 golden case（§4.1 的每个枚举值） |
| CORS 边界 | `Origin: null`、`Access-Control-Allow-Origin: *` + `credentials=include`、`Access-Control-Allow-Credentials: true` + `*`、预检缺失 `Access-Control-Allow-Methods`、`Access-Control-Max-Age` 缺省 |
| 重定向 | 同源 → 跨源、跨源 → 跨源、credentials 丢弃事件、Origin 置 `null` 事件 |
| 缓存 | fresh / stale / `no-store` / `must-revalidate` / `stale-while-revalidate` / `Expires` 缺失 / `Age` 大于新鲜期 |
| 条件请求 | 四个条件两两组合 + 单条件 + 无条件；`W/` 弱标签；`If-None-Match: *` |
| Vary | 单字段、多字段、`Vary: *`、字段缺失、大小写差异、空白差异 |

- 覆盖度由 `tools/golden_coverage.py` 从 `codes.json` ∪ golden 目录实算，输出表并作为测试断言。
- **"每个 code 至少一条"是集合等式**：`set(codes.json 的 code) - set(golden 覆盖的 code) == ∅`。反向（golden 里出现 codes.json 之外的 code）也必须为空。

### 3.4 WPT 映射纪律

- `data/wpt-mapping.json` 每条记录：`wpt_path`、`case_ids`、`mapped`（布尔）、`reason`（不可转写时必填）、`spec_basis[]`。
- **可转写用例必须 100% 映射**；不可转写用例必须逐条写明原因（依赖真实网络 / 证书 / 时序 / 浏览器专有行为 / 不在题面范围）。
- 发布前跑通全量映射：`mapped=true` 的用例逐条与 golden case 期望一致。

### 3.5 期望值独立性的落地口径（M1 登记）

`plan/04` §三 允许的降级**不启用**：M1 的 `tools/golden_oracle/` 是完整的第二份实现（五个 tool + 时间解析），不是"只算部分中间量"。

- 生成侧（`tools/golden_oracle/`）在 M1 按**规范原文**写成，只从 `codes.json` 读取 `code` / `spec_ref` / 模板，不 import `http_semantics_mcp` 任何模块。
- 生产侧（`src/http_semantics_mcp/judgement/`）在 M2–M4 按 `plan/03` 写成，**不复制生成侧源码**；两侧只靠 golden 逐字节测试对账。
- 该纪律由 AST 门（`tools/gates.py:oracle_independence`）与 `tools/mutate_check.py` 的变异共同钉住。

## 四、数值口径纪律（唯一一处定义）

> 本节只定义一次。`plan/01`、`plan/03`、代码常量、schema、README 只**引用**，不得手写第二份表述；如需修改，改本节并同步全部断言与 golden case。

### 4.1 `code` 枚举（唯一真相源）

- 命名格式：`大写下划线标识符`，前缀表示来源：`CORS_` / `CACHE_` / `COND_` / `VARY_`。
- 机器可读形态在 M1 落地为 `references/codes.json`（`code` → `{severity, spec_ref, template, meaning}`）；**该文件是本节的渲染产物，不得出现本节之外的 `code`**。
- `severity` 取 `decisive`（决定 `decision` / `action` / `status` / `match`）或 `informational`（只解释，不单独改变结果）。
- `spec_ref` 为字符串数组，按字典序排序，**首项为主依据**。
- `detail` 是固定模板：只用 `{param}` 占位，参数值来自判定过程；不含自由文本、不含时间戳。
- 首期最小枚举（M1 可增补，不可改名）：

| 前缀 | `code` | 严重度 | `spec_ref` | `detail` 模板 | 含义 |
| --- | --- | --- | --- | --- | --- |
| `CORS_` | `CORS_MISSING_ALLOW_ORIGIN` | decisive | `Fetch §CORS check` | response has no Access-Control-Allow-Origin (origin={origin}) | 非 simple 响应缺少 `Access-Control-Allow-Origin` |
| `CORS_` | `CORS_ORIGIN_MISMATCH` | decisive | `Fetch §CORS check` | Access-Control-Allow-Origin={allow_origin} does not match origin={origin} | `Access-Control-Allow-Origin` 值不匹配请求 Origin |
| `CORS_` | `CORS_WILDCARD_WITH_CREDENTIALS` | decisive | `Fetch §CORS check` + `Fetch §CORS protocol and credentials` | Access-Control-Allow-Origin=* cannot satisfy credentials=include | `*` 与 `credentials=include` 同时出现 |
| `CORS_` | `CORS_MISSING_ALLOW_CREDENTIALS` | decisive | `Fetch §CORS check` | credentials=include requires Access-Control-Allow-Credentials: true | credentials 模式缺少 `Access-Control-Allow-Credentials: true` |
| `CORS_` | `CORS_MISSING_ALLOW_METHODS` | decisive | `Fetch §CORS-preflight fetch` | preflight response does not allow method {method} | 预检响应缺少 `Access-Control-Allow-Methods` 或不含请求方法 |
| `CORS_` | `CORS_MISSING_ALLOW_HEADERS` | decisive | `Fetch §CORS-preflight fetch` | preflight response has no Access-Control-Allow-Headers (request header {header}) | 预检响应缺少 `Access-Control-Allow-Headers` |
| `CORS_` | `CORS_PREFLIGHT_REQUIRED` | decisive | `Fetch §CORS protocol` + `Fetch §CORS-preflight fetch` | method {method} with non-safelisted request headers requires a preflight | 请求需要预检但 `is_preflight=false` |
| `CORS_` | `CORS_DISALLOWED_HEADER_NOT_EXPOSED` | decisive | `Fetch §CORS-preflight fetch` | request header {header} is not listed in Access-Control-Allow-Headers | 请求头未被 `Access-Control-Allow-Headers` 覆盖 |
| `CORS_` | `CORS_NULL_ORIGIN` | informational | `Fetch §CORS check` + `Fetch §CORS protocol and credentials` | Origin: null is an opaque origin | `Origin: null` 的判定（含 `Allow-Credentials` 交互） |
| `CORS_` | `CORS_MODE_OPAQUE` | informational | `Fetch §CORS protocol` + `Fetch §HTTP fetch` | no-cors response is opaque; response headers are not visible | `no-cors` 模式下响应为 opaque（作 informational，不翻转 decision） |
| `CORS_` | `CORS_REDIRECT_NOT_SAME_ORIGIN` | decisive | `Fetch §HTTP-redirect fetch` + `Fetch §CORS protocol` | same-origin mode cannot follow a redirect to {target} | `same-origin` 模式下跨源重定向（Fetch §HTTP-redirect fetch 的 fetch 模式约束） |
| `CACHE_` | `CACHE_NO_STORE` | decisive | `RFC9111 §5.2.2.5` | Cache-Control: no-store forbids reuse | 响应声明 `no-store` |
| `CACHE_` | `CACHE_NO_CACHE` | decisive | `RFC9111 §5.2.2.4` | Cache-Control: no-cache requires revalidation | 响应声明 `no-cache`，须回源验证 |
| `CACHE_` | `CACHE_MAX_AGE_ZERO` | informational | `RFC9111 §4.2.1` + `RFC9111 §5.2.2.1` | max-age=0 makes the response stale immediately | `max-age=0` |
| `CACHE_` | `CACHE_MUST_REVALIDATE_STALE` | decisive | `RFC9111 §4.2.4` + `RFC9111 §5.2.2.2` | stale response with must-revalidate must not be served | stale 且 `must-revalidate` |
| `CACHE_` | `CACHE_STALE_WHILE_REVALIDATE` | decisive | `RFC5861 §3` | stale response is inside the stale-while-revalidate window of {window} seconds | 处于 `stale-while-revalidate` 窗口 |
| `CACHE_` | `CACHE_HEURISTIC_FRESHNESS` | informational | `RFC9111 §4.2.2` | no explicit freshness; heuristic freshness_lifetime={freshness_lifetime} | 无显式新鲜度，按启发式计算 |
| `CACHE_` | `CACHE_AGE_EXCEEDS_LIFETIME` | decisive | `RFC9111 §4.2` + `RFC9111 §4.2.3` | current_age={current_age} is not below freshness_lifetime={freshness_lifetime} | `current_age >= freshness_lifetime` |
| `CACHE_` | `CACHE_EXPIRES_IN_PAST` | decisive | `RFC9111 §5.3` | Expires={expires} is not later than Date={date} | `Expires` 早于或等于 `Date` |
| `CACHE_` | `CACHE_INVALID_MAX_AGE` | informational | `RFC9111 §4.2.1` | invalid max-age={max_age}; directive ignored | `max-age` 非非负整数（该指令按不存在处理） |
| `CACHE_` | `CACHE_INVALID_AGE` | informational | `RFC9111 §5.1` | invalid Age={age}; treated as 0 | `Age` 非非负整数（按 0 处理） |
| `COND_` | `COND_IF_MATCH_FAILED` | decisive | `RFC9110 §13.1.1` + `RFC9110 §13.2.2` | If-Match did not match any current entity tag | `If-Match` 不匹配 → 412 |
| `COND_` | `COND_IF_UNMODIFIED_SINCE_FAILED` | decisive | `RFC9110 §13.1.4` + `RFC9110 §13.2.2` | resource was modified after If-Unmodified-Since={date} | `If-Unmodified-Since` 不满足 → 412 |
| `COND_` | `COND_IF_NONE_MATCH_MATCHED` | decisive | `RFC9110 §13.1.2` + `RFC9110 §13.2.2` | If-None-Match matched the current entity tag | `If-None-Match` 匹配 → 304/412 |
| `COND_` | `COND_IF_MODIFIED_SINCE_NOT_MODIFIED` | decisive | `RFC9110 §13.1.3` + `RFC9110 §13.2.2` | resource was not modified after If-Modified-Since={date} | 未修改 → 304 |
| `COND_` | `COND_WEAK_COMPARISON_USED` | informational | `RFC9110 §13.1.2` + `RFC9110 §8.8.3.2` | If-None-Match is evaluated with weak comparison | 使用弱比较（`If-None-Match`） |
| `COND_` | `COND_IGNORED_INVALID_DATE` | informational | `RFC9110 §13.1.3` | {header} is not a valid HTTP-date and was ignored | 日期格式非法，条件被忽略 |
| `VARY_` | `VARY_STAR_NEVER_MATCHES` | decisive | `RFC9111 §4.1` | Vary: * always fails to match | `Vary: *` |
| `VARY_` | `VARY_FIELD_MISMATCH` | decisive | `RFC9111 §4.1` | Vary field {header} differs between stored and incoming request | 字段值不一致导致 miss |
| `VARY_` | `VARY_FIELD_MISSING` | decisive | `RFC9111 §4.1` | Vary field {header} is absent on one side | 存储时或请求时缺少 Vary 声明的字段 |
| `VARY_` | `VARY_DUPLICATE_FIELD` | informational | `RFC9111 §4.1` | Vary lists {header} more than once; duplicates removed | `Vary` 内重复字段（归一化时去重） |

- 新增 `code` 必须同时：写进本节表格 → 重生成 `references/codes.json` → 至少 1 条 golden case。
- **`informational` 条目仍进 `violations[]` / `reasons[]` / `explain[]`**（唯一 findings 通道），但不参与 `decision` / `action` / `status` / `match` 的翻转；`CORS_MODE_OPAQUE` 因此不需要第二套"notes 通道"。
- `missing_headers[]` 等 header 名列表**输出小写**（本节 §4.3 第 2 条为唯一口径；`plan/01` 的"大写规范名"措辞按此统一，见 `plan/06` D35）。

### 4.2 `spec_ref` 格式与核对状态

- 格式：`<doc> <locator>`，`<doc>` 取固定枚举：`Fetch` / `RFC9110` / `RFC9111` / `RFC5861`。
- RFC 类：`RFC9111 §4.2.1`（章节号），必要时附小节名：`RFC9111 §4.2.1 (Calculating Freshness Lifetime)`。
- Fetch 类：**不使用数字节号**（活文档会漂移），用算法锚点名：`Fetch §CORS-preflight fetch`、`Fetch §HTTP fetch`、`Fetch §CORS check`。
- 一个 `code` 可对应多个 `spec_ref`；输出中 `spec_ref` 为**字符串数组**，按字典序排序，首项为主依据。
- 条款号核对状态：M1 逐条对照发布版原文后在本表登记 ✅；未核对的条款**不得进入 `references/codes.json`**。

**核对方式**：2026-10-18 下载 `rfc-editor.org` 的 RFC 9110 / 9111 / 5861 纯文本与 `fetch.spec.whatwg.org` 活文档，按标题号与算法锚点名逐条比对；Fetch 锚点用 `dfn` 名与章节标题双重确认。

| 文档 | 定位 | 原文标题 / 算法锚点 | 状态 |
| --- | --- | --- | --- |
| `Fetch` | `§CORS check` | 4.10. CORS check | ✅ 2026-10-18 |
| `Fetch` | `§CORS protocol` | 3.3. CORS protocol | ✅ 2026-10-18 |
| `Fetch` | `§CORS protocol and credentials` | 3.3.5. CORS protocol and credentials | ✅ 2026-10-18 |
| `Fetch` | `§CORS-preflight fetch` | 4.8. CORS-preflight fetch | ✅ 2026-10-18 |
| `Fetch` | `§CORS-preflight cache` | 4.9. CORS-preflight cache | ✅ 2026-10-18 |
| `Fetch` | `§HTTP fetch` | 4.4. HTTP fetch | ✅ 2026-10-18 |
| `Fetch` | `§HTTP-redirect fetch` | 4.5. HTTP-redirect fetch | ✅ 2026-10-18 |
| `RFC9110` | `§5.6.7` | Date/Time Formats | ✅ 2026-10-18 |
| `RFC9110` | `§8.8.3.2` | Comparison (entity tags) | ✅ 2026-10-18 |
| `RFC9110` | `§13.1.1` | If-Match | ✅ 2026-10-18 |
| `RFC9110` | `§13.1.2` | If-None-Match | ✅ 2026-10-18 |
| `RFC9110` | `§13.1.3` | If-Modified-Since | ✅ 2026-10-18 |
| `RFC9110` | `§13.1.4` | If-Unmodified-Since | ✅ 2026-10-18 |
| `RFC9110` | `§13.2.2` | Precedence of Preconditions | ✅ 2026-10-18 |
| `RFC9111` | `§4.1` | Calculating Cache Keys with the Vary Header Field | ✅ 2026-10-18 |
| `RFC9111` | `§4.2` | Freshness | ✅ 2026-10-18 |
| `RFC9111` | `§4.2.1` | Calculating Freshness Lifetime | ✅ 2026-10-18 |
| `RFC9111` | `§4.2.2` | Calculating Heuristic Freshness | ✅ 2026-10-18 |
| `RFC9111` | `§4.2.3` | Calculating Age | ✅ 2026-10-18 |
| `RFC9111` | `§4.2.4` | Serving Stale Responses | ✅ 2026-10-18 |
| `RFC9111` | `§5.1` | Age | ✅ 2026-10-18 |
| `RFC9111` | `§5.2.2.1` | max-age (response directive) | ✅ 2026-10-18 |
| `RFC9111` | `§5.2.2.2` | must-revalidate | ✅ 2026-10-18 |
| `RFC9111` | `§5.2.2.4` | no-cache | ✅ 2026-10-18 |
| `RFC9111` | `§5.2.2.5` | no-store | ✅ 2026-10-18 |
| `RFC9111` | `§5.2.2.10` | s-maxage | ✅ 2026-10-18 |
| `RFC9111` | `§4.3` | Validation | ✅ 2026-10-18 |
| `RFC9111` | `§5.3` | Expires | ✅ 2026-10-18 |
| `RFC5861` | `§3` | The stale-while-revalidate Cache-Control Extension | ✅ 2026-10-18 |

### 4.3 排序规则（唯一）

1. `violations[]` / `reasons[]` / `explain[]`：先按 `code` 的 ASCII 字典序升序；同一 `code` 多条时按 `detail` 的 ASCII 字典序升序。
2. header 名列表（`missing_headers[]`、`visible_headers[]`、`differing_headers[]`、`normalized_vary[]`）：先转小写再按 ASCII 字典序升序；输出时统一为小写。
3. `events[]`：按**发生顺序**（不排序）。
4. 对象键（`recommended_headers`、`notes`）：按 ASCII 字典序升序序列化。
5. 排序比较一律使用 Python 字符串默认比较（Unicode 码点序，等价于 ASCII 序用于本题字符集），不使用 locale。

### 4.4 时间解析（唯一）

- 只接受两种格式：`YYYY-MM-DDTHH:MM:SSZ`（UTC，允许尾随小数秒）与 HTTP-date `Day, DD Mon YYYY HH:MM:SS GMT`。
- 解析为 **UTC 秒级整数时间戳**；亚秒部分直接截断（不四舍五入）。
- 解析失败 → 返回结构化错误（`error.code = "INVALID_TIME_FORMAT"`），**不做猜测性容错**、不回退到系统时钟。
- 计算一律用整数秒；不引入浮点秒。
- `Age` 头解析：只接受非负十进制整数；非法值按 `0` 处理并在 `reasons[]` 记 `CACHE_INVALID_AGE`。

### 4.5 确定性与序列化

- 输出 JSON 序列化固定：`sort_keys=true`、`ensure_ascii=false`、分隔符 `(",", ":")`、无尾随空格。
- 输出中禁止出现：时间戳、随机数、进程 ID、绝对路径、主机名、locale 相关格式、执行耗时。
- 同一输入连续两次调用的序列化结果 **sha256 相等**；该断言在 M5 作为守门测试常驻。

### 4.6 错误契约（与 MCP 协议一致）

- 输入非法（缺字段 / 类型错误 / 枚举越界 / 时间解析失败）→ 返回 `isError: true` 的 tool 结果，`content` 内含 `{"error": {"code": "...", "field": "...", "detail": "..."}}`；**不抛异常、不退出进程**。
- 判定为 `block` **不是错误**：`isError: false`，`decision: "block"`。
- `error.code` 固定枚举（唯一真相源）：

| `error.code` | 触发场景 |
| --- | --- |
| `INVALID_INPUT` | 缺必填字段、类型错误、枚举越界 |
| `INVALID_TIME_FORMAT` | 时间字面量不属于 §4.4 的两种格式 |
| `INVALID_HEADER_NAME` | header 名不符合 RFC 9110 token 字符集 |
| `INVALID_HEADER_VALUE` | header 值无法按规范解析（如 ETag 引号不配对、`w/` 小写前缀） |
| `UNSUPPORTED_METHOD` | 方法不在允许集合 |

### 4.7 `preflight_cache_key` 派生（唯一）

- 输入：请求 Origin 的序列化值（`null` 用字面量 `null`）+ 换行 + 目标 URL 的规范化 origin 形式。
- 规范化：`scheme://host[:port]`，scheme/host 小写，默认端口（`http:80` / `https:443`）省略，丢弃 path / query / fragment。
- 取 `sha256` 的**前 16 位小写 hex**；不读时钟、不加盐、不含随机数。
- 机器可读形态（由 `gen_codes.py` 取本节代码块）：

```json
{
  "algorithm": "sha256",
  "input": "origin + \"\\n\" + canonical_url",
  "canonical_url": "scheme://host[:port]",
  "hex_prefix": 16
}
```

### 4.8 `vary_normalization` 策略表（唯一）

- 字段名永远小写。
- `trim`：去掉首尾 OWS。
- `折叠内部空白`：连续空格 / 制表折叠为单个空格。
- `大小写敏感`：为"否"时比较前统一转小写。
- `逗号分段排序`：按逗号拆分、各自 trim、排序后以 `,` 重连（用于顺序无语义的协商字段）。
- 缺失字段按空串参与比较，但另行记 `VARY_FIELD_MISSING`。

| 字段名 | trim | 折叠内部空白 | 大小写敏感 | 逗号分段排序 |
| --- | --- | --- | --- | --- |
| `*`（默认） | 是 | 是 | 是 | 否 |
| `accept` | 是 | 是 | 否 | 是 |
| `accept-encoding` | 是 | 是 | 否 | 是 |
| `accept-language` | 是 | 是 | 否 | 是 |
| `user-agent` | 是 | 否 | 是 | 否 |

> `*` 行即"未单列的字段"的默认策略；单个字段的差异只覆盖表中写明的列。

### 4.9 `notes` 键枚举（唯一）

`notes` 是固定键的对象，不临时起名；缺失的键也必须以 `false` 输出（`max_age_capped_by_client` 恒为 `false`）。

| 键 | 类型 | 含义 |
| --- | --- | --- |
| `wildcard_with_credentials` | bool | `Access-Control-Allow-Origin: *` 与 `credentials=include` 同时出现 |
| `allow_credentials_null_origin` | bool | `Origin: null` 且 `Access-Control-Allow-Credentials: true` |
| `max_age_capped_by_client` | bool | 恒为 `false`：不替浏览器裁剪 `Access-Control-Max-Age` |

### 4.10 输出字段集合（每个 tool 的 `expected` 键集合，唯一）

- `expected` 必须**恰好**是下表列出的键集合，不多不少；M5 的 schema 守门以本表为准。
- 错误结果例外：`expected` 为 `{"error": {"code", "field", "detail"}}`，`error.code` 取自 §4.6。
- 数组内的对象键同样是固定集合（`violations[]` / `reasons[]` / `explain[]` 均为 `{code, spec_ref, detail}`）。

| tool | `expected` 键集合 |
| --- | --- |
| `_time` | `form`, `timestamp` |
| `cors_evaluate` | `decision`, `missing_headers`, `notes`, `recommended_headers`, `violations` |
| `cors_simulate_fetch` | `decision`, `events`, `final_type`, `hops`, `max_age_effective`, `preflight_cache_key`, `preflight_occurred`, `visible_headers` |
| `cache_evaluate` | `action`, `current_age`, `freshness_lifetime`, `is_fresh`, `must_revalidate`, `reasons`, `stale_while_revalidate_window` |
| `conditional_evaluate` | `explain`, `rule_applied`, `status`, `weak_comparison_used` |
| `vary_match` | `differing_headers`, `match`, `normalized_vary`, `reasons` |

- `cors_simulate_fetch` 的 `hops[]` 每项键集合：`decision`, `status`, `url`, `violations`；`hops[]` 按发生顺序（不排序）。
- `events[]` 取值固定枚举：`origin_set_to_null` / `credentials_dropped`；跨源重定向时同一跳内前者先于后者。
- `_time` 的 `form` 取值固定枚举：`iso8601` / `http-date`。

## 五、隐私与品牌

- 纯本地：server 不发起任何网络请求，不写用户输入到磁盘（除非调用方显式要求生成 golden case）。
- header 可能含 `Authorization` / `Cookie`：文档与日志中一律用 `Bearer <redacted>` / `<redacted>` 占位。
- 本题方向为 **HTTP 协议语义判定**；文档、仓库名、tool 名不引用本系列其他项目的名称、路径、素材或文档模板。
- 不编造文号、数值、日期；检索计数与星数一律与基准日 2026-10-17 成对出现，并注明实测窗口 2026-10-18 10:33–11:05 UTC。
