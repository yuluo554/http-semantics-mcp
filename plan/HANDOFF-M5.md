# HANDOFF-M5（schema 与自检）

> 写于 2026-10-18（M4 收尾）。下一棒：**M5 五个 tool 的正式 schema + 契约门 + 确定性全量 + WPT 全量对账 + 端到端 stdio**。
> 本文是续接的唯一入口：新对话只需给绝对路径 + "读 plan/HANDOFF-M5.md 继续"。

## 一、当前进度与证据

### 已完成（M4，2026-10-18）

| 产出 | 位置 | 证据 |
| --- | --- | --- |
| T4 判定 | `src/http_semantics_mcp/judgement/conditional.py` | 19 条 `conditional_evaluate` golden 逐字节相等（含 `cond-014` 的 `isError: true` 载荷） |
| T5 判定 | `src/http_semantics_mcp/judgement/vary.py` | 9 条 `vary_match` golden 逐字节相等 |
| tool 注册 | `toolface.py` + `registry.py` | `tools/list` 返回 5 个 tool，ASCII 升序 |
| T4/T5 测试 | `tests/test_conditional_golden.py`（43 项）/ `tests/test_vary_golden.py`（27 项） | golden 逐字节 + golden 未覆盖分支（强弱比较、`*` 与 ETag、IMS 方法门、秒级边界、策略表换行、重复字段一次） |
| 门 + 变异 | `tools/gates.py` / `tools/mutate_check.py` | 8 门全绿（合计扫 698 文件项）；38/38 变异变红（M4 新增 12 条） |
| 测试 | 全量 | 3.8 → 354 passed；3.12 → 354 passed（收集数各 354） |
| 决策 | `plan/06` | D47（T4 三处边缘口径）、D48（T5 重复字段 + star 短路）、D49（生产侧相对 oracle 的两处有意偏差） |

### 当前事实（下一棒必须知道）

- **`tools/list` 现在返回 5 个 tool**（ASCII 升序）：`cache_evaluate`、`conditional_evaluate`、`cors_evaluate`、`cors_simulate_fetch`、`vary_match`。名单已同步的 5 处（M5 若加/改 tool 才需要再动）：
  - `tests/test_registry.py::test_build_registry_declares_the_shipped_tools` + `_minimal_arguments`
  - `tests/test_protocol.py::test_tools_list_reports_the_registered_tools_in_ascii_order`
  - `tests/test_stdio_process.py::test_server_starts_and_answers_the_handshake`
  - README 状态段 + Tools 表（`tests/test_readme_gate.py::test_readme_state_matches_the_registry` 要求 README 用反引号点名每个注册 tool）
- **87 条 golden 已冻结且全部逐字节对账**：cors 24 / sim 10 / cache 18 / conditional 19 / vary 9 / `_time` 7。M5 **不新增、不改写** golden 与 `code`（`data/README.md` §4.1 的 31 个枚举原样）。
- **schema 的现状（M5 的主战场）**：`registry.py` 用**内联** `TOOL_DESCRIPTIONS` + `INPUT_SCHEMAS` 作为客户端可见面（D43）；`src/http_semantics_mcp/schemas/tools/` 与顶层 `schemas/tools/` 目前**只有 README.md**，一个 JSON 都没有。`plan/02` §三 与 D24 要求：**包内 JSON 是唯一可编辑真相源，顶层是逐字节镜像**；`plan/03` §六 要求 schema `output` 段声明全部字段、"schema `properties` 键集合 == 实跑输出键集合"是**集合等式**（不是包含），且 `additionalProperties: false`。
- **打包已经就绪**：`pyproject.toml` 的 `[tool.setuptools.package-data]` 已含 `http_semantics_mcp = ["references/*.json", "schemas/tools/*.json"]` —— 新落地的 schema JSON 会自动进发行包，无需改打包配置。
- **`expected` 键集合已冻结**（`data/README.md` §4.10），嵌套形状也要进 schema：
  - 五个 tool 的顶层键集合见 §4.10；错误结果固定 `{"error": {"code","field","detail"}}`；
  - `cors_simulate_fetch` 的 `hops[]` 每项键集合 `{decision,status,url,violations}`，`events[]` 取值枚举 `origin_set_to_null`/`credentials_dropped`；`_time.form` 枚举 `iso8601`/`http-date`（`_time` 不是注册 tool，但 §4.10 有它的键集合）。
- **确定性口径**（`data/README.md` §4.5）：同一输入连续两次调用的**序列化结果 sha256 相等**，该断言"M5 作为守门测试常驻"。M3/M4 的逐 tool 双跑是 `canonical.dumps` 相等，M5 要升级为 sha256 且覆盖**五 tool × 全部 golden**。
- **判定层怎么指名 code（M2 定，D41/D42）**：`from ..rules import COND_..., VARY_...` 拿常量，**禁止**在 `src/**` 手写 code 字面量（唯一豁免生成物 `rules.py`）。签名一律 `evaluate_xxx(arguments, catalog)`，`catalog` 由 `toolface.py` 传入。
- **golden 未覆盖处的口径由测试钉住**（D47/D48）：动 T4/T5 时不要以为"golden 没覆盖就可以随便改"，`tests/test_conditional_golden.py` / `tests/test_vary_golden.py` 与 `mutate_check.py` 的 27–38 条变异会同时打红。
- **生产侧与 oracle 的两处有意偏差**（D49，M5 若做双侧输入面扫描不算漂移）：①T4/T5 把 `request_headers`/`resource`/`cached`/`incoming` 列为 `required` 并在缺失时报 `INVALID_INPUT`，oracle 对缺键按空对象兜底；②`golden_oracle` 对**空数组**值取首值时抛 `IndexError`，生产侧 `first_value` 按"没有该值"处理。
- **WPT 台账已是 M1 产物**：`data/wpt-mapping.json`（45 = 15 converted + 30 unmappable，commit `850b36a5`），`tests/test_wpt_ledger.py` 已钉住形状、集合划分、`case_ids` 指向真实 golden、不夹带 WPT 原文。M5 要补的是 `data/README.md` §3.4 最后一条：**`mapped=true` 的用例逐条与 golden 期望一致**（按台账驱动实跑，而不是只查存在性）。
- **未推送远端**：`git remote -v` 为空。一切 CI 结论只能写"本地等价校验（未接远端，CI 待首推验证）"。
- `plan/06` §二 的 skill 门写有"**基准可重复、指标入 README**（golden 全绿率 + WPT 映射率）→ M5"：README 需要一个量化指标段，这是 M5 的对外承诺，不是可选项。

## 二、M5 待办（按顺序）

1. **先定 schema 的真相源与生成路线**（这一步定错，后面全要重做）。两条路都能满足 D24/`plan/03` §六，二选一并写进 `plan/06` 的新 D 编号：
   - **A（推荐）**：包内 `src/http_semantics_mcp/schemas/tools/<tool>.json` 是唯一可编辑真相源；`registry.py` 改为 `importlib.resources` 读它（`json.loads` 是允许的，`single_serialiser` 门只管 `json.dumps`）；`tools/gen_schemas.py` 只负责**镜像**（写顶层 `schemas/tools/*.json`）与**校验**（`required ⊆ properties`、`additionalProperties: false`、键集合 == §4.10）。理由：符合 D24 的字面口径、契约只有一份可编辑副本、`tools/list` 与文档面不会各自演化。
   - **B**：`registry.py` 的内联 dict 仍是真相，`gen_schemas.py` 从 `registry.INPUT_SCHEMAS` 渲染 JSON（包内 + 顶层两份产物），并加一门断言"包的 JSON 与 registry 内联一致"。代价：同一契约在包内存在两份（内联 + JSON），要额外一门守着它们不漂。
2. **写 `tools/gen_schemas.py`**：`--check`（默认）逐字节比对 + 形状校验，无 `--check` 时写盘；**不要**在这里生成 `inputSchema` 之外的自由文本。顶层镜像与包内文件必须同字节（`scripts/check_release.check_dist_mirrors` 按文件对逐个比，`tests/test_mirrors.py` 已能证明该门会红）。
3. **写契约门 `tests/test_schema_parity.py`**：
   - 五个 tool：`set(outputSchema.properties) == set(data/README.md §4.10 的键集合)`；
   - 跑**全部 87 条 golden**，收集实际输出键集合（成功用例 → 顶层键集合；错误用例 → `{"error"}`）并与 `properties` **双向相等**；
   - `additionalProperties is False` 出现在每个 object 段；`required` 与"每条成功用例都出现的字段"一致；
   - 元门：断言"参与比对的用例数 > 0 且五个 tool 各自都有用例"，避免门扫到 0 条也显绿（本项目的既有口径：零扫描即失败）。
4. **写确定性门 `tests/test_determinism.py`**：五 tool × 全部 golden，同一输入跑两次 → `sha256(canonical.dumps(...))` 相等；并断言输出里不出现时间戳/随机/路径（`data/README.md` §4.5 的禁用清单）。
5. **补 WPT 全量对账**：新增测试（或扩展 `tests/test_wpt_ledger.py`）——遍历 `mapped=true` 的 15 行，逐条执行 `case_ids` 指向的 golden，断言生产输出 == 冻结 `expected`（与 golden 测试同口径但由台账驱动），并输出"15/15 一致"的计数；`mapped=false` 的 30 行只校验 `reason` 在枚举内（已有）。
6. **写 `tests/test_stdio_end_to_end.py`**：真实子进程 + 真实 stdio 客户端路径——`initialize` → `notifications/initialized` → `tools/list`（五个 tool、ASCII 升序）→ 对**五个 tool 各发一次 `tools/call`**（用最小参数，断言 `isError: false` 且键集合正确）→ 未知 tool 走 JSON-RPC error。两个解释器都跑。
7. **README 指标段**：把 `plan/06` §二 要求的量化指标写进 README（golden 全绿率 `87/87`、WPT 映射率 `15/45 mapped + 30/45 unmappable（逐条有 reason）`、双解释器收集数、变异条数、门数），并保留"本地等价校验（未接远端）"措辞。
8. **守门**：给 M5 新增的每个门配变异（至少：schema 少一个 `properties` 键；`additionalProperties` 改 `true`；顶层镜像改一个字节；确定性门比对目标改成"两次都序列化"但注入随机键 → 必红）。
9. **收尾**：双解释器 pytest 全绿（收集数一致）→ `gen_schemas --check` / `gen_codes --check` / `gen_golden --check` / `golden_coverage` → 回写 `plan/00`/`plan/05`（必要时 `plan/06` 追加 D 编号）→ 写 `plan/HANDOFF-M6.md` → commit → `scripts/check_release.py --pre-tag`（提交后应 6 PASS / 0 FAIL / 4 SKIP，且 `dist-mirrors` 的文件数从 1 涨到 6）。

## 三、既定口径清单（K 编号，动了会打挂测试）

| 编号 | 口径 | 位置 |
| --- | --- | --- |
| K1 | 序列化唯一入口 `canonical.dumps` / `encode_message`：`sort_keys=True`、`ensure_ascii=False`、`separators=(",",":")`、`allow_nan=False` | `src/http_semantics_mcp/canonical.py`；`tools/gates.py:single_serialiser` |
| K2 | 帧格式 = 一行一条 UTF-8 JSON + `\n`；读侧剥 `\r`；写侧永不产 `\r` | `tests/test_server_transport.py` |
| K3 | 单条消息上限 8 MiB，超限排空该行并回 `-32600`，进程继续 | `protocol.MAX_MESSAGE_BYTES` |
| K4 | 协议版本集合冻结为 `2025-06-18` / `2025-03-26` / `2024-11-05`，未知版本回默认 | `protocol.SUPPORTED_PROTOCOL_VERSIONS`（D22） |
| K5 | `tools/list` 按 name ASCII 升序（现为 5 个 tool） | `Registry.names()`；3 处测试期望名单 + README |
| K6 | 判定层禁 `time/datetime/random/secrets/socket/ssl/http/urllib/requests/os/subprocess/sys/pathlib/shutil/tempfile/uuid`，禁 `open`/`read_text` | `tools/gates.py:JUDGEMENT_FORBIDDEN` |
| K7 | 全运行时包禁时钟/随机/网络；`os.environ`/`getenv` 全仓禁 | `tools/gates.py:no_nondeterminism` |
| K8 | 包内路径是唯一可编辑真相源，顶层 `references/`、`schemas/tools/` 是逐字节镜像 | `plan/02` §三；`scripts/check_release.check_dist_mirrors` |
| K9 | `code` 枚举 / `spec_ref` 格式 / 排序 / 时间解析 / 输出键集合只在 `data/README.md` §4 定义一次 | `data/README.md` §四 |
| K10 | 判定为 `block` 不是错误（`isError: false`）；tool 级坏输入走 result 的 `isError: true`；协议级错误走 JSON-RPC error | `toolface.py`、`protocol._tools_call` |
| K11 | 发布终态门不进 CI；三种模式 `--offline`（默认）/ `--pre-tag` / `--online` | `scripts/check_release.py`（D34） |
| K12 | `NotAchieved`（exit 1）与 `EnvironmentMissing`（exit 3）必须是两类异常 | `scripts/check_release.py` |
| K13 | 生成侧 oracle 与生产实现分开书写，只靠逐字节测试对账 | `plan/04` §三（D27）；`tools/gates.py:oracle_independence` |
| K14 | golden 里出现 `observed_*` 字段即红 | `tools/gates.py:golden_hygiene` |
| K15 | EUC/行尾：所有文本 LF-only，`.gitattributes` 必须含 `eol=lf` | `tools/gates.py:crlf` |
| K16 | 版本唯一定义处是 `src/http_semantics_mcp/__init__.py:__version__`，`pyproject.toml` 必须一致 | `tests/test_packaging.py`、`selfcheck._check_version_parity` |
| K17 | **手写**包内 `*.py` 不得出现 `CORS_/CACHE_/COND_/VARY_` 形式的 code 字面量；唯一豁免是生成物 `src/http_semantics_mcp/rules.py`（该文件必须存在且含 `CATALOG`，缺件即红） | `tools/gates.py:code_literals`（M2 修订，D41/D42） |
| K18 | `expected` 键集合 = `data/README.md` §4.10 的表；不许多不许少 | `tests/test_golden.py:test_expected_key_sets_are_exact` |
| K19 | header 名列表输出小写；findings 按 `(code, detail)` 排序 | `data/README.md` §4.3（D35） |
| K20 | `informational` code 进 findings 但不翻转判定 | `data/README.md` §4.1（D36） |
| K21 | 判定层按名引用 code：`from ..rules import <CODE>`，`catalog` 由 `toolface.py` 传入 | `tools/gates.py:code_literals`；`src/http_semantics_mcp/rules.py`（D41） |
| K22 | 生成物三件由 `gen_codes.py` 同时产出、逐字节守门：`references/codes.json`（包内）+ 顶层镜像 + `rules.py` | `tools/gen_codes.py --check`；`tests/test_gen_codes.py` |
| K23 | T3 的 Age 取值优先级：`stored.age` > 响应头 `Age`；时间解析"只截断不进位"覆盖亚秒与闰秒（`min(second, 59)`） | `judgement/cache.py`；D44/D45 |
| K24 | T4/T5 的 golden 未覆盖边缘由测试钉住：`*` 绑定"当前表示是否带 ETag"、`If-Modified-Since` 只对 GET/HEAD、`resource` 字段严格校验 vs 请求头日期忽略、`Vary` 重复字段只报一次（源顺序）、`Vary: *` 短路先于重复提示 | `tests/test_conditional_golden.py`、`tests/test_vary_golden.py`；`mutate_check.py` 第 27–38 条（D47/D48） |
| K25 | tool 级必填面必须自洽：`registry.INPUT_SCHEMAS[<tool>]["required"]` 里的每个键缺失时 handler 必须回 `isError: true`；T4/T5 因此比 oracle 更严 | `tests/test_registry.py::test_declared_required_fields_are_the_ones_the_handler_rejects`（D49） |

## 四、本机环境坑（均为本机实测，日期 2026-10-18）

| 坑 | 现象 | 处置 |
| --- | --- | --- |
| `py -3.8` 没有 `tomllib` | 读 `pyproject.toml` 会 `ImportError` | 统一用 `tools/toml_lite.py`（受限子集 + `TomlSubsetError`） |
| `py -3.8` 的 `Path.write_text` 无 `newline` 参数 | `TypeError: unexpected keyword argument 'newline'` | 测试里写文件一律 `open(..., "w", encoding="utf-8", newline="\n")` |
| 本机 `python` 裸命令是 WindowsApps stub | 直接 `python` 不稳；`py` 可用 | 一律用 `py -3.8` / `py -3.12` |
| **pytest 收集偶发崩溃（M2 实测一次）** | `py -3.12 -m pytest -q` 单次报 `TypeError: required field "func" missing from ...`，仅 `test_ci_workflow.py` 收集失败；**原命令重跑即全绿** | 判为机器抖动，不是代码缺陷：先**原样重跑**；只有重跑仍红才当真实失败。别据此改代码 |
| 新建 venv 缺 setuptools | `pip install -e .` 报 `Cannot import 'setuptools.build_meta'` | 先 `NO_PROXY="*" no_proxy="*" <venv>/Scripts/python.exe -m pip install setuptools` |
| 本机代理污染 pip | 安装可能走 `127.0.0.1:7897` | 一律 `NO_PROXY="*" no_proxy="*"` |
| Git Bash 路径 | `/tmp` 与 Windows Python 不通 | 临时文件放工作区或系统临时目录 |
| `gh` 是原生程序 | 不认 `/tmp/...` 路径 | 传 Windows 原生路径（`cygpath -w` 转换） |
| `raw.githubusercontent.com` 被重置 | `curl` 报 `Recv failure` | 改用 `gh api .../contents/<path> --jq .content \| base64 -d` |
| 无远端 | `git remote -v` 为空 | 所有 CI 结论写"本地等价校验"，M6 首推后据实补记 |
| `golden_oracle` 对空数组值会抛 `IndexError` | 探针输入 `{"Accept": []}` 时 oracle 崩，生产侧按"没有该值"处理 | 这是 oracle 的边界缺陷、不是契约；见 D49。**不要**为了让两侧一致而改生产侧行为 |

## 五、DoD 逐项 checklist（M5）

- [ ] 五个 tool 的 schema 落地：包内 `src/http_semantics_mcp/schemas/tools/<tool>.json` + 顶层 `schemas/tools/<tool>.json` 逐字节镜像（现状：两侧只有 README.md）
- [ ] schema 真相源路线写进 `plan/06` 新 D 编号（A：包内 JSON 为真相、registry 读它；B：registry 内联为真相、JSON 为产物）
- [ ] `tools/gen_schemas.py --check` 逐字节一致 + 形状校验（`required ⊆ properties`、`additionalProperties: false`）
- [ ] 契约门：五个 tool 各自 `outputSchema.properties` 键集合 == §4.10 == 实跑输出键集合（跑全部 87 条 golden，双向相等，且断言参与比对的用例数 > 0）
- [ ] 确定性门：五 tool × 全部 golden 同输入双跑 **sha256** 相等；输出无时间戳/随机/路径
- [ ] WPT：`mapped=true` 的 15 行逐条实跑且与 golden 期望一致；`mapped=false` 的 30 行逐条有 `reason`（已有）
- [ ] `tests/test_stdio_end_to_end.py`：真实子进程列出五个 tool，并对五个 tool 各成功调用一次
- [ ] README 量化指标段（golden 全绿率、WPT 映射率、双解释器收集数、门数、变异条数）+ 状态行转 M5
- [ ] 8 道静态门全绿；新增的门各配至少 1 条变异并使门/测试变红
- [ ] 双解释器 pytest 全绿（收集数一致）
- [ ] `gen_codes --check` / `gen_golden --check` / `golden_coverage` 全绿（87 case / 31 code）
- [ ] `plan/00`、`plan/05` 状态回写；`plan/HANDOFF-M6.md` 落盘 + commit；`--pre-tag` 提交后 6 PASS / 0 FAIL / 4 SKIP

## 六、关键命令速查

```bash
# 双解释器全量测试
PYTHONPATH=src py -3.8 -m pytest -q
PYTHONPATH=src py -3.12 -m pytest -q

# 只跑 M5 相关（新门落地后）
PYTHONPATH=src py -3.12 -m pytest -q tests/test_schema_parity.py tests/test_determinism.py tests/test_stdio_end_to_end.py

# 静态门 + 变异验证
PYTHONPATH=src py -3.12 tools/run_gates.py --verbose
py -3.12 tools/mutate_check.py

# 生成物复算
py -3.12 tools/gen_codes.py --check
py -3.12 tools/gen_golden.py --check
py -3.12 tools/golden_coverage.py
py -3.12 tools/gen_schemas.py --check      # M5 新增

# 真实子进程握手（两个解释器都跑）
PYTHONPATH=src py -3.12 tools/smoke_stdio.py
PYTHONPATH=src py -3.8 tools/smoke_stdio.py

# 发布终态门（tag 之前）
PYTHONPATH=src py -3.12 scripts/check_release.py --pre-tag
```

## 七、启动提示词（下一棒）

```
/goal 读取 "<项目绝对路径>\plan\HANDOFF-M5.md" 继续完成任务
```

（`<项目绝对路径>` 由用户侧填写；库内不写本机路径。）
