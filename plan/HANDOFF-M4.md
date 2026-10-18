# HANDOFF-M4（缓存：T4 + T5）

> 写于 2026-10-18（M3 收尾）。下一棒：**M4 条件请求与 Vary（T4 `conditional_evaluate` + T5 `vary_match`）**。
> 本文是续接的唯一入口：新对话只需给绝对路径 + "读 plan/HANDOFF-M4.md 继续"。

## 一、当前进度与证据

### 已完成（M3，2026-10-18）

| 产出 | 位置 | 证据 |
| --- | --- | --- |
| T3 判定 | `src/http_semantics_mcp/judgement/cache.py` | 18 条 `cache_evaluate` golden 逐字节相等 |
| 时间解析 | `src/http_semantics_mcp/judgement/timeparse.py` | 7 条 `_time` 样例（4 正例 + 3 反例）全绿 |
| tool 注册 | `toolface.py` + `registry.py` | `tools/list` 返回 3 个 tool，ASCII 升序 |
| cache golden 对账测试 | `tests/test_cache_golden.py` | 36 项；`canonical.dumps(实际) == canonical.dumps(expected)` |
| 门 + 变异 | `tools/gates.py` / `tools/mutate_check.py` | 8 门全绿（合计扫 680 文件项）；26/26 变异变红（M3 新增 6 条） |
| 测试 | 全量 | 3.8 → 284 passed；3.12 → 284 passed（收集数一致） |
| 决策 | `plan/06` | D44（Age 取值优先级）、D45（截断纪律覆盖亚秒与闰秒）、D46（swr 边界用测试钉住） |

### 当前事实（下一棒必须知道）

- **`tools/list` 现在返回 3 个 tool**：`cache_evaluate`、`cors_evaluate`、`cors_simulate_fetch`（ASCII 升序）。M4 注册 T4/T5 后变 5 个，以下是**必须同步的期望名单**：
  - `tests/test_registry.py::test_build_registry_declares_the_shipped_tools`（名字列表）
  - `tests/test_registry.py::_minimal_arguments`（要给 `conditional_evaluate` / `vary_match` 各补一份最小参数）
  - `tests/test_protocol.py::test_tools_list_reports_the_registered_tools_in_ascii_order`
  - `tests/test_stdio_process.py::test_server_starts_and_answers_the_handshake`
  - README 状态段 + Tools 表（`tests/test_readme_gate.py::test_readme_state_matches_the_registry` 要求 README 用反引号点名每个注册 tool）
- **golden 已经是 T4/T5 的验收基线**：`data/golden/conditional_evaluate/`（19 条）与 `data/golden/vary_match/`（9 条）。M4 的目标不是改 golden，而是**让生产实现输出与它们逐字节相等**。
- **`expected` 键集合已冻结**（`data/README.md` §4.10）：
  - `conditional_evaluate` = `explain` / `rule_applied` / `status` / `weak_comparison_used`
  - `vary_match` = `differing_headers` / `match` / `normalized_vary` / `reasons`
- **输入形状（照 golden 的 `input` 抄，不要自创）**：
  - `conditional_evaluate`：`{"method", "request_headers", "resource": {"etag", "last_modified"}}`；`resource.last_modified` 可为 `null`。
  - `vary_match`：`{"cached": {"vary", "request_headers_at_store"}, "incoming": {"request_headers"}}`。
- **`detail` 文案只存在于生成物**：`rules.py`（= `references/codes.json`）。判定层必须从 `CATALOG` 取 `template` / `spec_ref` / `severity`。
- **判定层怎么指名 code（M2 定，D41/D42）**：`from ..rules import COND_..., VARY_...` 拿常量，**禁止**在 `src/**` 手写 code 字面量（唯一豁免 `rules.py`）。签名沿用 `evaluate_xxx(arguments, catalog)`，`catalog` 由 `toolface.py` 传入。
- **`informational` 级 code 也进 findings 数组**，但不翻转 `status` / `match`（D36）。T4 的 `COND_WEAK_COMPARISON_USED` / `COND_IGNORED_INVALID_DATE`、T5 的 `VARY_DUPLICATE_FIELD` 都是 informational。
- **`explain[]` / `reasons[]` 排序**：按 `(code, detail)` ASCII 字典序；header 名列表小写 + 字典序；对象键固定 `{code, spec_ref, detail}`。
- **时间解析已就位**：`judgement/timeparse.py` 的 `parse_time(value, field)` → `(form, timestamp)` 或抛 `invalid_time_format`。T4 的 `Last-Modified` / `If-Modified-Since` / `If-Unmodified-Since` 就用它；日期非法 → 条件**被忽略**并记 `COND_IGNORED_INVALID_DATE`（**不要**抛错——`cond-012` 期望 200，不是 tool error）。
- **Vary 归一化策略表是数据**：`CATALOG["vary_normalization"]` = `{"default": {...}, "fields": {字段名: {...}}}`，四条策略布尔键 `trim` / `fold_whitespace` / `case_sensitive` / `sort_comma_segments`。**不要**在代码里写第二份策略分支。
- **`CATALOG` 顶层键**：`codes` / `error_codes` / `notes` / `preflight_cache_key` / `schema_version` / `source` / `vary_normalization` / `verified_spec_refs`。
- **远端未建**：`git remote -v` 为空。一切 CI 结论只能写"本地等价校验（未接远端，CI 待首推验证）"。

## 二、M4 待办（按顺序）

1. **读透 19 条 `data/golden/conditional_evaluate/` 与 9 条 `data/golden/vary_match/`**，当成规格读一遍。重点：
   - `cond-013`（`If-Match` 先于 `If-None-Match`，后者不评估）、`cond-015`–`019`（四条件两两组合的优先级）；
   - `cond-004` / `cond-009`（`*` 的两种语义：`If-Match: *` 通过；`If-None-Match: *` → 304 GET / 412 PUT）；
   - `cond-007` / `cond-008`（弱比较命中：GET → 304，PUT → 412）；
   - `cond-014`（`w/` 小写 → `INVALID_HEADER_VALUE`，`field = "request_headers.if-none-match"`）；
   - `cond-012`（非法日期 → 忽略条件 + informational，`detail` 里的 header 名是**小写**的 `if-modified-since`）；
   - `vary-003`（`Vary: *` 短路 miss）、`vary-004`（一侧缺字段 → `VARY_FIELD_MISSING`）、`vary-005`（`accept` 大小写不敏感）、`vary-006`（空白折叠）、`vary-007`（重复字段 → informational 且去重）、`vary-009`（`accept` 逗号分段排序）。
2. **写 `judgement/conditional.py`（T4）**：按 `plan/03` §四 的 E1–E5 固定短路顺序，**不要照抄** `tools/golden_oracle/conditional.py`（D27）。两个比较函数分开写（`strong_compare` 用于 `If-Match`，`weak_compare` 用于 `If-None-Match`）；`opaque-tag` 保留引号逐字节比较；`W/` 前缀恰好一个且必须大写。
3. **写 `judgement/vary.py`（T5）**：按 `plan/03` §五 的 V1–V4；归一化策略**从 `catalog["vary_normalization"]` 读**（数据不是代码）。
4. **注册两个 tool**：`toolface.FUNCTIONS` 各加一项；`registry.py` 的 `TOOL_DESCRIPTIONS` / `INPUT_SCHEMAS` 各加两项（`required` 取实际必填：T4 = `method`/`request_headers`/`resource`；T5 = `cached`/`incoming`）。同步改上一节列出的 5 处期望与 README。
5. **测试**：新增 `tests/test_conditional_golden.py` 与 `tests/test_vary_golden.py`——跑全部 golden，断言 `canonical.dumps(实际) == canonical.dumps(expected)`；另加"双跑字节一致""键集合精确相等""错误用例 `isError: true`"三类用例。
6. **守门**：`tools/mutate_check.py` 给新实现配变异（至少：`If-Match` 用弱比较；求值顺序改成 `If-None-Match` 在前；`Vary: *` 不再短路；缺字段不记 `VARY_FIELD_MISSING`；`accept` 忽略大小写那条策略失效），全红。
7. **收尾**：双解释器 pytest 全绿 → 回写 `plan/00`/`plan/05`（必要时 `plan/06` 追加 D 编号）→ 写 `plan/HANDOFF-M5.md` → commit。

## 三、既定口径清单（K 编号，动了会打挂测试）

| 编号 | 口径 | 位置 |
| --- | --- | --- |
| K1 | 序列化唯一入口 `canonical.dumps` / `encode_message`：`sort_keys=True`、`ensure_ascii=False`、`separators=(",",":")`、`allow_nan=False` | `src/http_semantics_mcp/canonical.py`；`tools/gates.py:single_serialiser` |
| K2 | 帧格式 = 一行一条 UTF-8 JSON + `\n`；读侧剥 `\r`；写侧永不产 `\r` | `tests/test_server_transport.py` |
| K3 | 单条消息上限 8 MiB，超限排空该行并回 `-32600`，进程继续 | `protocol.MAX_MESSAGE_BYTES` |
| K4 | 协议版本集合冻结为 `2025-06-18` / `2025-03-26` / `2024-11-05`，未知版本回默认 | `protocol.SUPPORTED_PROTOCOL_VERSIONS`（D22） |
| K5 | `tools/list` 按 name ASCII 升序 | `Registry.names()` |
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

## 五、DoD 逐项 checklist（M4）

- [ ] `judgement/conditional.py` + `judgement/vary.py` 落地，`CATALOG` 的模板是唯一文案来源
- [ ] 19 条 conditional golden 逐字节相等
- [ ] 9 条 vary golden 逐字节相等
- [ ] §13.2.2 求值顺序与短路正确（`If-Match` → `If-Unmodified-Since` → `If-None-Match` → `If-Modified-Since`），`rule_applied` 记录实际生效的那条
- [ ] 强/弱比较分离；`W/` 恰好一个且必须大写；`w/` 小写 → `INVALID_HEADER_VALUE`
- [ ] `If-Match: *` 通过；`If-None-Match: *` → GET/HEAD 304、其它方法 412
- [ ] 非法 `Last-Modified` / `If-*` 日期 → 条件被忽略 + `COND_IGNORED_INVALID_DATE`（不抛错）
- [ ] `Vary: *` 永不命中（短路 miss）；重复字段去重并记 `VARY_DUPLICATE_FIELD`
- [ ] 归一化策略从 `catalog["vary_normalization"]` 读，代码里没有第二份策略分支
- [ ] `differing_headers` / `normalized_vary` 小写 + 字典序；`explain[]` / `reasons[]` 按 `(code, detail)` 排序
- [ ] `tools/list` 返回 5 个 tool，ASCII 升序
- [ ] 8 道静态门全绿；新增实现的变异全部使门/测试变红
- [ ] 双解释器 pytest 全绿（收集数一致）
- [ ] `plan/00`、`plan/05` 状态回写；`plan/HANDOFF-M5.md` 落盘 + commit

## 六、关键命令速查

```bash
# 双解释器全量测试
PYTHONPATH=src py -3.8 -m pytest -q
PYTHONPATH=src py -3.12 -m pytest -q

# 只跑 M4 相关
PYTHONPATH=src py -3.12 -m pytest -q tests/test_conditional_golden.py tests/test_vary_golden.py

# 静态门 + 变异验证
PYTHONPATH=src py -3.12 tools/run_gates.py --verbose
py -3.12 tools/mutate_check.py

# 生成物复算
py -3.12 tools/gen_codes.py --check
py -3.12 tools/gen_golden.py --check
py -3.12 tools/golden_coverage.py

# 真实子进程握手（两个解释器都跑）
PYTHONPATH=src py -3.12 tools/smoke_stdio.py
PYTHONPATH=src py -3.8 tools/smoke_stdio.py

# 发布终态门（tag 之前）
PYTHONPATH=src py -3.12 scripts/check_release.py --pre-tag
```

## 七、启动提示词（下一棒）

```
/goal 读取 "<项目绝对路径>\plan\HANDOFF-M4.md" 继续完成任务
```

（`<项目绝对路径>` 由用户侧填写；库内不写本机路径。）
