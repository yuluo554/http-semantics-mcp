# HANDOFF-M2（CORS：T1 + T2）

> 写于 2026-10-18（M1 收尾）。下一棒：**M2 CORS（T1 `cors_evaluate` + T2 `cors_simulate_fetch`）**。
> 本文是续接的唯一入口：新对话只需给绝对路径 + "读 plan/HANDOFF-M2.md 继续"。

## 一、当前进度与证据

### 已完成（M1，2026-10-18）

| 产出 | 位置 | 证据 |
| --- | --- | --- |
| 规范条款核对 | `data/README.md` §4.2 | 27 条 `spec_ref` 全部 ✅（RFC 9110/9111/5861 原文 + Fetch 活文档锚点名） |
| 规则表生成器 | `tools/spectable.py` + `tools/gen_codes.py` | `--check` 逐字节一致；表缺项/未核对条款 → `SpecTableError` |
| `codes.json` + 镜像 | `src/http_semantics_mcp/references/`、`references/` | 31 个 code，9468 字节，逐字节相等 |
| 独立复算器 | `tools/golden_oracle/`（8 文件） | 完整第二实现（T1–T5 + 时间解析）；AST 门禁 import |
| golden 生成器 | `tools/gen_golden.py` | 输入面 `tools/cases/**`（87 条）→ 冻结面 `data/golden/**`；`--check` 含 orphan 检测 |
| 覆盖度 | `tools/golden_coverage.py` | 31 declared / 31 covered / 0 unknown |
| WPT 索引 + 台账 | `data/wpt/cors-index.json`、`data/wpt-mapping.json` | 45 = 15 converted + 30 unmappable，commit `850b36a5` |
| 三道新门 | `tools/gates.py`：`oracle_independence` / `golden_hygiene` / `code_literals` | 8 门全绿，扫 235 文件 |
| 变异验证 | `tools/mutate_check.py` | 14/14 变异使门变红 |
| 测试 | `tests/test_gen_codes.py`、`test_golden.py`、`test_wpt_ledger.py`、`test_m1_gates.py` | 3.8 → 198 passed；3.12 → 198 passed（收集数一致） |

### 当前事实（下一棒必须知道）

- **`tools/list` 仍返回 `[]`**：M1 只做数据面，没有任何 tool 注册。M2 起注册两个，`tests/test_readme_gate.py::test_readme_does_not_claim_tools_at_m0` 在注册数 > 0 时自动失效（该测试只在 0 tool 时断言）。
- **golden 已经是 T1/T2 的验收基线**：`data/golden/cors_evaluate/`（24 条）与 `data/golden/cors_simulate_fetch/`（10 条）。M2 的目标不是改 golden，而是**让生产实现输出与它们逐字节相等**。
- **`expected` 的键集合已冻结**：`data/README.md` §4.10。实现不得多键、不得少键。
- **`detail` 文案只存在于 `codes.json`**：生产实现必须从该表取 `template` / `spec_ref` / `severity`，否则 `code_literals` 门会红。
- **`informational` 级 code 也进 findings 数组**，但不翻转 `decision`（D36）。
- **`missing_headers[]` 等 header 名列表输出小写**（D35）。
- **远端未建**：`git remote -v` 为空。一切 CI 结论只能写"本地等价校验（未接远端，CI 待首推验证）"。

## 二、M2 待办（按顺序）

1. **读透两个 golden 目录**：先把 34 条 CORS 用例的 `input` / `expected` 当规格读一遍，尤其是：
   - `cors-eval-011-preflight-required`（`is_preflight=false` 但方法/头要求预检）
   - `cors-eval-014-null-origin-credentials`（`notes.allow_credentials_null_origin`）
   - `cors-eval-015-authorization-not-wildcard`（`*` 不覆盖 `Authorization`）
   - `cors-eval-020-preflight-star-method-credentials`（credentials 下 `*` 不覆盖方法/头）
   - `cors-eval-023-allow-origin-whitespace`（值两侧 OWS 先剥）
   - `cors-sim-002` / `-006`（事件顺序与每跳追加）
   - `cors-sim-005`（`same-origin` 模式跨源重定向 → `CORS_REDIRECT_NOT_SAME_ORIGIN`）
   - `cors-sim-007` / `-009`（`preflight_cache_key`、`max_age_effective`）
2. **写 `judgement/cors.py`（T1）**：按 `plan/03` §一 的 A/P 分支顺序，**不要照抄** `tools/golden_oracle/cors.py`（D27 的两份实现纪律；Oracle 是规范读法，生产实现要独立写一遍，再靠 golden 对账）。
3. **写 `judgement/fetch_sim.py`（T2）**：`plan/03` §二。事件顺序恒为 `origin_set_to_null` → `credentials_dropped`；`hops[]` 按发生顺序不排序。
4. **共享规范化**：新建 `judgement/normalise.py`（header 名/值、方法、URL、origin 序列化）。注意判定层禁 `os` / `sys` / `pathlib` 等（K6），只能用纯字符串操作；`hashlib` 允许（`preflight_cache_key`）。
5. **`codes.json` 的读取方式**：判定层**不能** `open()`（K6 禁盘）。两个可行做法，二选一并在 `plan/06` 追加决策：
   - (a) `judgement/spec.py` 里放一份 `importlib.resources` 读到的常量——但 `importlib` 读包内文件仍走 `open`，会被 AST 门抓到；
   - (b) 由 `gen_codes.py` 额外生成一个 `references/codes.py`（纯 Python 字面量模块），判定层 `from ..references import CODES`——**推荐**，需同步加镜像/守门。
   > 这一条是 M2 第一个真实设计岔口，先定再写代码。
6. **注册 tool**：`registry.build_registry()` 注册两个 `Tool`；`inputSchema` 先内联（M5 才生成正式 schema）。
7. **测试**：新增 `tests/test_cors_golden.py`——跑全部 `cors_evaluate` / `cors_simulate_fetch` golden，断言 `canonical.dumps(实际输出) == canonical.dumps(expected)`；错误用例断言 `isError` 载荷。
8. **守门**：`tools/mutate_check.py` 给新实现配变异（例如去掉 `Authorization` 特例、交换事件顺序、去掉 OWS 剥离），全红。
9. **收尾**：双解释器 pytest 全绿 → 回写 `plan/00`/`plan/05` → 写 `plan/HANDOFF-M3.md` → commit。

## 三、既定口径清单（K 编号，动了会打挂测试）

| 编号 | 口径 | 位置 |
| --- | --- | --- |
| K1 | 序列化唯一入口 `canonical.dumps` / `encode_message`：`sort_keys=True`、`ensure_ascii=False`、`separators=(",",":")`、`allow_nan=False` | `src/http_semantics_mcp/canonical.py`；`tools/gates.py:single_serialiser` |
| K2 | 帧格式 = 一行一条 UTF-8 JSON + `\n`；读侧剥 `\r`；写侧永不产 `\r` | `plan/02` §四；`tests/test_server_transport.py` |
| K3 | 单条消息上限 8 MiB，超限排空该行并回 `-32600`，进程继续 | `protocol.MAX_MESSAGE_BYTES` |
| K4 | 协议版本集合冻结为 `2025-06-18` / `2025-03-26` / `2024-11-05`，未知版本回默认 | `protocol.SUPPORTED_PROTOCOL_VERSIONS`（D22） |
| K5 | `tools/list` 按 name ASCII 升序 | `Registry.names()` |
| K6 | 判定层禁 `time/datetime/random/secrets/socket/ssl/http/urllib/requests/os/subprocess/sys/pathlib/shutil/tempfile/uuid`，禁 `open`/`read_text` | `tools/gates.py:JUDGEMENT_FORBIDDEN` |
| K7 | 全运行时包禁时钟/随机/网络；`os.environ`/`getenv` 全仓禁 | `tools/gates.py:no_nondeterminism` |
| K8 | 包内路径是唯一可编辑真相源，顶层 `references/`、`schemas/tools/` 是逐字节镜像 | `plan/02` §三；`scripts/check_release.check_dist_mirrors` |
| K9 | `code` 枚举 / `spec_ref` 格式 / 排序 / 时间解析 / 输出键集合只在 `data/README.md` §4 定义一次 | `data/README.md` §四 |
| K10 | 判定为 `block` 不是错误（`isError: false`）；tool 级坏输入走 result 的 `isError: true`；协议级错误走 JSON-RPC error | `plan/02` §5.4、§七 |
| K11 | 发布终态门不进 CI；三种模式 `--offline`（默认）/ `--pre-tag` / `--online` | `scripts/check_release.py`（D34） |
| K12 | `NotAchieved`（exit 1）与 `EnvironmentMissing`（exit 3）必须是两类异常 | `scripts/check_release.py` |
| K13 | 生成侧 oracle 与生产实现分开书写，只靠逐字节测试对账 | `plan/04` §三（D27）；`tools/gates.py:oracle_independence` |
| K14 | golden 里出现 `observed_*` 字段即红 | `plan/04` §三；`tools/gates.py:golden_hygiene` |
| K15 | EUC/行尾：所有文本 LF-only，`.gitattributes` 必须含 `eol=lf` | `tools/gates.py:crlf` |
| K16 | 版本唯一定义处是 `src/http_semantics_mcp/__init__.py:__version__`，`pyproject.toml` 必须一致 | `tests/test_packaging.py`、`selfcheck._check_version_parity` |
| K17 | 包内任何 `*.py` 不得出现 `CORS_/CACHE_/COND_/VARY_` 形式的 code 字面量 | `tools/gates.py:code_literals`（M1 新增） |
| K18 | `expected` 键集合 = `data/README.md` §4.10 的表；不许多不许少 | `tests/test_golden.py:test_expected_key_sets_are_exact` |
| K19 | header 名列表输出小写；findings 按 `(code, detail)` 排序 | `data/README.md` §4.3（D35） |
| K20 | `informational` code 进 findings 但不翻转 `decision` | `data/README.md` §4.1（D36） |

## 四、本机环境坑（均为本机实测，日期 2026-10-18）

| 坑 | 现象 | 处置 |
| --- | --- | --- |
| `py -3.8` 没有 `tomllib` | 读 `pyproject.toml` 会 `ImportError` | 统一用 `tools/toml_lite.py`（受限子集 + `TomlSubsetError`） |
| `py -3.8` 的 `Path.write_text` 无 `newline` 参数 | `TypeError: unexpected keyword argument 'newline'` | 测试里写文件一律 `open(..., "w", encoding="utf-8", newline="\n")` |
| `tools/coverage.py` 与标准库同名 | 3.8 上被真包遮蔽，测试收集 `TypeError` | 已改名 `tools/golden_coverage.py`（D40）；新增工具别再撞名 |
| 新建 venv 缺 setuptools | `pip install -e .` 报 `Cannot import 'setuptools.build_meta'` | 先 `NO_PROXY="*" no_proxy="*" <venv>/Scripts/python.exe -m pip install setuptools` |
| 本机代理污染 pip | 安装可能走 `127.0.0.1:7897` | 一律 `NO_PROXY="*" no_proxy="*"` |
| Git Bash 路径 | `/tmp` 与 Windows Python 不通 | 临时文件放工作区或系统临时目录 |
| `gh` 是原生程序 | 不认 `/tmp/...` 路径 | 传 Windows 原生路径（`cygpath -w` 转换） |
| `raw.githubusercontent.com` 被重置 | `curl` 报 `Recv failure` | 改用 `gh api .../contents/<path> --jq .content \| base64 -d` |
| 无远端 | `git remote -v` 为空 | 所有 CI 结论写"本地等价校验"，M6 首推后据实补记 |

## 五、DoD 逐项 checklist（M2）

- [ ] `judgement/cors.py` + `judgement/fetch_sim.py` 落地，`codes.json` 的模板是唯一文案来源
- [ ] 34 条 CORS golden 逐字节相等（`canonical.dumps(实际) == canonical.dumps(expected)`）
- [ ] 错误用例返回 `isError: true` 载荷，进程不退出
- [ ] 同输入不同 header 书写顺序 → 输出字节一致（有 golden 锁定：`cors-eval-018`/`019`）
- [ ] `events[]` 顺序与条数被 golden 锁定（`cors-sim-002`/`-006`）
- [ ] `tools/list` 返回两个 tool，ASCII 升序（`cors_evaluate` < `cors_simulate_fetch`）
- [ ] 8 道静态门全绿；新增实现的变异全部使门/测试变红
- [ ] 双解释器 pytest 全绿（收集数一致）
- [ ] `plan/00`、`plan/05` 状态回写
- [ ] `plan/HANDOFF-M3.md` 落盘 + commit

## 六、关键命令速查

```bash
# 双解释器全量测试
PYTHONPATH=src py -3.8 -m pytest -q
PYTHONPATH=src py -3.12 -m pytest -q

# 只跑 CORS golden（M2 起）
PYTHONPATH=src py -3.12 -m pytest -q tests/test_cors_golden.py

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

# CI 文件本地解析（推之前必做）
py -3.12 -c "import yaml;d=yaml.safe_load(open('.github/workflows/ci.yml',encoding='utf-8'));print(list(d['jobs']), len(d['jobs']['test']['steps']))"
```

## 七、启动提示词（下一棒）

```
/goal 读取 "<项目绝对路径>\plan\HANDOFF-M2.md" 继续完成任务
```

（`<项目绝对路径>` 由用户侧填写；库内不写本机路径。）
