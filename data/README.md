# data/ — 依据查证、数据源与口径纪律

> **查证基准日：2026-10-17**。
> **实测窗口（必须原样保留）**：GitHub 检索的实际执行时间为 **2026-10-18 10:33–11:05 UTC**，与登记的基准日 **跨日不足 1 天**。所有检索计数都是该窗口的快照，会随时间漂移，一律与基准日成对出现，只作**软论据**。
> 三态标记：`✅ 已核对`（可直接访问 / 已实测）/ `⬜ 待核对`（路径已登记但未取得或未复核）/ 软论据（检索计数，不可硬化为能力结论）。
> **不可获取或未复核的源不得作规则来源。**

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
| `web-platform-tests/wpt` 的 `cors/` 目录 | ✅ 可获取 | 公开仓库目录，含 `preflight-cache.htm` / `redirect-preflight.htm` / `credentials-flag.htm` / `origin.htm` / `cors-safelisted-request-header.any.js` 等测试文件 + `cors/resources/` 后端脚本；条目清单与计数以 M1 映射台账为准 | 无阻断。**只读取测试文件文本**，不运行浏览器、不联网 |
| WPT 中依赖真实网络 / 证书 / 时序的用例 | ⬜ 不可转写 | — | 逐条登记到 `data/wpt-mapping.json` 的 `unmappable[]`，写明原因；**不伪造期望值** |
| RFC 9111 / RFC 9110 / Fetch Standard 条款 | ✅ 可获取 | 规范原文（公开） | 条款号在 M1 逐条对照原文核对后登记；Fetch Standard 为活文档，用**算法锚点名**而非数字节号 |
| `http-cache-semantics`（262★） | ✅ 可获取 | 公开仓库 | 只作参照，不复制代码；不引入运行时依赖 |
| 真实站点响应头 | — | **禁止采集** | 隐私红线 + 确定性纪律：golden case 只用合成 header 组合 |
| 运行时网络请求 | — | **禁止** | 纯本地；server 不发起任何 DNS / TCP / HTTP |

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
    cors_evaluate/<case_id>.json
    cors_simulate_fetch/<case_id>.json
    cache_evaluate/<case_id>.json
    conditional_evaluate/<case_id>.json
    vary_match/<case_id>.json
  wpt-mapping.json
```

- 一个文件一个用例；文件名 = `case_id`，只允许 `[a-z0-9_-]`。
- `expected` 必须是**完整输出对象**（含所有字段与顺序），不允许只写部分字段。
- 用例冻结后只读；修改需另立 `case_id` 并在 `wpt-mapping.json` 或决策记录中注明原因。

### 3.3 覆盖度最低要求

| 维度 | 最低要求 |
| --- | --- |
| 每个 `code` | 至少 1 条正例或反例 golden case（§4.1 的每个枚举值） |
| CORS 边界 | `Origin: null`、`Access-Control-Allow-Origin: *` + `credentials=include`、`Access-Control-Allow-Credentials: true` + `*`、预检缺失 `Access-Control-Allow-Methods`、`Access-Control-Max-Age` 缺省 |
| 重定向 | 同源 → 跨源、跨源 → 跨源、credentials 丢弃事件、Origin 置 `null` 事件 |
| 缓存 | fresh / stale / `no-store` / `must-revalidate` / `stale-while-revalidate` / `Expires` 缺失 / `Age` 大于新鲜期 |
| 条件请求 | 四个条件两两组合 + 单条件 + 无条件；`W/` 弱标签；`If-None-Match: *` |
| Vary | 单字段、多字段、`Vary: *`、字段缺失、大小写差异、空白差异 |

### 3.4 WPT 映射纪律

- `data/wpt-mapping.json` 每条记录：`wpt_path`、`case_id`、`mapped`（布尔）、`reason`（不可转写时必填）、`spec_basis[]`。
- **可转写用例必须 100% 映射**；不可转写用例必须逐条写明原因（依赖真实网络 / 证书 / 时序 / 浏览器专有行为）。
- 发布前跑通全量映射：`mapped=true` 的用例逐条与 golden case 期望一致。

## 四、数值口径纪律（唯一一处定义）

> 本节只定义一次。`plan/01`、`plan/03`、代码常量、schema、README 只**引用**，不得手写第二份表述；如需修改，改本节并同步全部断言与 golden case。

### 4.1 `code` 枚举（唯一真相源）

- 命名格式：`大写下划线标识符`，前缀表示来源：`CORS_` / `CACHE_` / `COND_` / `VARY_`。
- 机器可读形态在 M1 落地为 `references/codes.json`（`code` → `{spec_ref, severity, template}`）；**该文件是本节的渲染产物，不得出现本节之外的 `code`**。
- 首期最小枚举（M1 可增补，不可改名）：

| 前缀 | `code` | 含义 |
| --- | --- | --- |
| `CORS_` | `CORS_MISSING_ALLOW_ORIGIN` | 非 simple 响应缺少 `Access-Control-Allow-Origin` |
| `CORS_` | `CORS_ORIGIN_MISMATCH` | `Access-Control-Allow-Origin` 值不匹配请求 Origin |
| `CORS_` | `CORS_WILDCARD_WITH_CREDENTIALS` | `*` 与 `credentials=include` 同时出现 |
| `CORS_` | `CORS_MISSING_ALLOW_CREDENTIALS` | credentials 模式缺少 `Access-Control-Allow-Credentials: true` |
| `CORS_` | `CORS_MISSING_ALLOW_METHODS` | 预检响应缺少 `Access-Control-Allow-Methods` 或不含请求方法 |
| `CORS_` | `CORS_MISSING_ALLOW_HEADERS` | 预检响应缺少 `Access-Control-Allow-Headers` 或不含请求头 |
| `CORS_` | `CORS_PREFLIGHT_REQUIRED` | 请求需要预检但 `is_preflight=false` |
| `CORS_` | `CORS_DISALLOWED_HEADER_NOT_EXPOSED` | 请求头未被 `Access-Control-Allow-Headers` 覆盖 |
| `CORS_` | `CORS_NULL_ORIGIN` | `Origin: null` 的判定（含 `Allow-Credentials` 交互） |
| `CORS_` | `CORS_MODE_OPAQUE` | `no-cors` 模式下响应为 opaque（非 violation，作 note） |
| `CACHE_` | `CACHE_NO_STORE` | 响应声明 `no-store` |
| `CACHE_` | `CACHE_NO_CACHE` | 响应声明 `no-cache`，须回源验证 |
| `CACHE_` | `CACHE_MAX_AGE_ZERO` | `max-age=0` |
| `CACHE_` | `CACHE_MUST_REVALIDATE_STALE` | stale 且 `must-revalidate` |
| `CACHE_` | `CACHE_STALE_WHILE_REVALIDATE` | 处于 `stale-while-revalidate` 窗口 |
| `CACHE_` | `CACHE_HEURISTIC_FRESHNESS` | 无显式新鲜度，按启发式计算 |
| `CACHE_` | `CACHE_AGE_EXCEEDS_LIFETIME` | `current_age >= freshness_lifetime` |
| `CACHE_` | `CACHE_EXPIRES_IN_PAST` | `Expires` 早于 `Date` |
| `CACHE_` | `CACHE_INVALID_MAX_AGE` | `max-age` 非非负整数 |
| `COND_` | `COND_IF_MATCH_FAILED` | `If-Match` 不匹配 → 412 |
| `COND_` | `COND_IF_UNMODIFIED_SINCE_FAILED` | `If-Unmodified-Since` 不满足 → 412 |
| `COND_` | `COND_IF_NONE_MATCH_MATCHED` | `If-None-Match` 匹配 → 304（GET/HEAD） |
| `COND_` | `COND_IF_MODIFIED_SINCE_NOT_MODIFIED` | 未修改 → 304 |
| `COND_` | `COND_WEAK_COMPARISON_USED` | 使用弱比较（`If-None-Match`） |
| `COND_` | `COND_IGNORED_INVALID_DATE` | 日期格式非法，条件被忽略 |
| `VARY_` | `VARY_STAR_NEVER_MATCHES` | `Vary: *` |
| `VARY_` | `VARY_FIELD_MISMATCH` | 字段值不一致导致 miss |
| `VARY_` | `VARY_FIELD_MISSING` | 存储时或请求时缺少 Vary 声明的字段 |
| `VARY_` | `VARY_DUPLICATE_FIELD` | `Vary` 内重复字段（归一化时去重） |

- 新增 `code` 必须同时：写进本节表格 → 写进 `references/codes.json` → 至少 1 条 golden case。

### 4.2 `spec_ref` 格式

- 格式：`<doc> <locator>`，`<doc>` 取固定枚举：`RFC9110` / `RFC9111` / `Fetch`。
- RFC 类：`RFC9111 §4.2.1`（章节号），必要时附小节名：`RFC9111 §4.2.1 (Calculating Freshness Lifetime)`。
- Fetch 类：**不使用数字节号**（活文档会漂移），用算法锚点名：`Fetch §CORS-preflight fetch`、`Fetch §HTTP fetch`、`Fetch §CORS check`。
- 一个 `code` 可对应多个 `spec_ref`；输出中 `spec_ref` 为**字符串数组**，按字典序排序，首项为主依据。
- 条款号核对状态：M1 逐条对照原文后在本表登记 ✅；未核对的条款**不得进入 `references/codes.json`**。

### 4.3 排序规则（唯一）

1. `violations[]` / `reasons[]`：按 `code` 的 ASCII 字典序升序。
2. header 名列表（`missing_headers[]`、`visible_headers[]`、`differing_headers[]`、`normalized_vary[]`）：先转小写再按 ASCII 字典序升序；输出时统一为小写。
3. `events[]`：按**发生顺序**（不排序）。
4. 对象键（`recommended_headers`、`notes`）：按 ASCII 字典序升序序列化。
5. 排序比较一律使用 Python 字符串默认比较（Unicode 码点序，等价于 ASCII 序用于本题字符集），不使用 locale。

### 4.4 时间解析（唯一）

- 只接受两种格式：`YYYY-MM-DDTHH:MM:SSZ`（UTC）与 HTTP-date `Day, DD Mon YYYY HH:MM:SS GMT`。
- 解析为 **UTC 秒级整数时间戳**；亚秒部分直接截断（不四舍五入）。
- 解析失败 → 返回结构化错误（`error.code = "INVALID_TIME_FORMAT"`），**不做猜测性容错**、不回退到系统时钟。
- 计算一律用整数秒；不引入浮点秒。
- `Age` 头解析：只接受非负十进制整数；非法值按 `0` 处理并在 `reasons[]` 记 `CACHE_INVALID_AGE`（该 `code` 在 M1 增补时登记）。

### 4.5 确定性与序列化

- 输出 JSON 序列化固定：`sort_keys=true`、`ensure_ascii=false`、分隔符 `(",", ":")`、无尾随空格。
- 输出中禁止出现：时间戳、随机数、进程 ID、绝对路径、主机名、locale 相关格式、执行耗时。
- 同一输入连续两次调用的序列化结果 **sha256 相等**；该断言在 M5 作为守门测试常驻。

### 4.6 错误契约（与 MCP 协议一致）

- 输入非法（缺字段 / 类型错误 / 枚举越界 / 时间解析失败）→ 返回 `isError: true` 的 tool 结果，`content` 内含 `{"error": {"code": "...", "field": "...", "detail": "..."}}`；**不抛异常、不退出进程**。
- `error.code` 固定枚举：`INVALID_INPUT` / `INVALID_TIME_FORMAT` / `INVALID_HEADER_NAME` / `INVALID_HEADER_VALUE` / `UNSUPPORTED_METHOD`。
- 判定为 `block` **不是错误**：`isError: false`，`decision: "block"`。

## 五、隐私与品牌

- 纯本地：server 不发起任何网络请求，不写用户输入到磁盘（除非调用方显式要求生成 golden case）。
- header 可能含 `Authorization` / `Cookie`：文档与日志中一律用 `Bearer <redacted>` / `<redacted>` 占位。
- 本题方向为 **HTTP 协议语义判定**；文档、仓库名、tool 名不引用本系列其他项目的名称、路径、素材或文档模板。
- 不编造文号、数值、日期；检索计数与星数一律与基准日 2026-10-17 成对出现，并注明实测窗口 2026-10-18 10:33–11:05 UTC。
