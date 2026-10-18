# HANDOFF-M1（数据先行）

> 写于 2026-10-18（M0 收尾）。下一棒：**M1 数据先行**。
> 本文是续接的唯一入口：新对话只需给绝对路径 + "读 plan/HANDOFF-M1.md 继续"。

## 一、当前进度与证据

### 已完成（M0，2026-10-18）

| 产出 | 位置 | 证据 |
| --- | --- | --- |
| 计划文档 02–06 | `plan/02-…` 至 `plan/06-…` | 定稿，`plan/00` 索引已翻转 |
| 可启动 MCP server（stdio） | `src/http_semantics_mcp/` | 真实子进程握手 5 响应 / 0 tool / 446 字节 |
| 运行时零依赖 | `pyproject.toml` | `dependencies = []`，`tests/test_packaging.py` 钉住 |
| 五道静态门 | `tools/gates.py` + `tools/run_gates.py` | 干净树 0 findings，扫 50 文件 |
| 变异验证 | `tools/mutate_check.py` | 8/8 变异使门变红 |
| 发布终态门 | `scripts/check_release.py` | `--pre-tag` 5 PASS / 1 FAIL（预期）/ 4 SKIP |
| CI 四矩阵 | `.github/workflows/ci.yml` | 本地 YAML 解析通过：1 job / 9 step |
| 测试套件 | `tests/`（13 个文件） | 3.8 → 143 passed；3.12 → 143 passed |
| 安装态验证 | 临时 venv | `http-semantics-mcp --version` / `--selftest` / 握手全通过 |

### 当前事实（下一棒必须知道）

- **`tools/list` 返回 `[]`**，这是 M0 的正确行为，README 已写明。M2 起改为两个 tool，M3 加一个，M4 再加两个。
- **`schemas/tools/` 与 `references/` 目前只有 README**：真实内容在 M1（codes）/ M2（schemas）落地。
- **远端未建**：`git remote -v` 为空。一切 CI 结论只能写"本地等价校验（未接远端，CI 待首推验证）"。
- 已有一个提交 `e695bc0`（出题定稿）；M0 的产出在本次收尾提交里。

## 二、M1 待办（按顺序）

1. **规范条款核对**：逐条对照 RFC 9111 / RFC 9110 / Fetch Standard 原文，把 `data/README.md` §4.1 的每个 `code` 补上真实条款号与算法锚点名。核对状态记进 `data/README.md` §4.2 的表；未核对的条款不得进 `codes.json`。
2. **写 `tools/gen_codes.py`**：从 `data/README.md` §4.1 的表格生成 `src/http_semantics_mcp/references/codes.json` + 顶层镜像，支持 `--check`（重算到内存 → 逐字节比对 → 差异即 exit 1 并打印首个差异）。
3. **写 `tools/golden_oracle/`**：与生产侧分开书写的复算器。至少覆盖 T3 的年龄/新鲜度算术与 T4 的强弱比较。**禁止** import `http_semantics_mcp.judgement`（AST 门）。
4. **写 `tools/gen_golden.py` + `--check`**：产出 `data/golden/<tool>/<case_id>.json`。
5. **建立 golden 覆盖**：`data/README.md` §4.1 每个 `code` 至少 1 条；`plan/04` §四 的覆盖度矩阵逐格填满。
6. **WPT 索引与映射**：`gh api` 读 `web-platform-tests/wpt` 的 `cors/` 目录树 → `data/wpt/cors-index.json`（路径 + blob sha + 数据日）；人工判定可转写性 → `data/wpt-mapping.json`（`converted + unmappable == total`）。
7. **`data/README.md` §4 增补**：`preflight_cache_key` 派生方式、`vary_normalization` 策略表、`CACHE_INVALID_AGE` 等新增 code。
8. **守门**：`codes.json` ↔ `data/README.md` 双向集合等式；生成器 `--check`；golden 无 `observed_*`；oracle 不得 import 判定层。
9. **收尾**：双解释器 pytest 全绿 → 回写 `plan/00`/`plan/05` → 写 `plan/HANDOFF-M2.md` → commit。

## 三、既定口径清单（K 编号，动了会打挂测试）

| 编号 | 口径 | 位置 |
| --- | --- | --- |
| K1 | 序列化唯一入口 `canonical.dumps` / `encode_message`：`sort_keys=True`、`ensure_ascii=False`、`separators=(",",":")`、`allow_nan=False` | `src/http_semantics_mcp/canonical.py`；`tools/gates.py:single_serialiser` |
| K2 | 帧格式 = 一行一条 UTF-8 JSON + `\n`；读侧剥 `\r`；写侧永不产 `\r` | `plan/02` §四；`tests/test_server_transport.py` |
| K3 | 单条消息上限 8 MiB，超限排空该行并回 `-32600`，进程继续 | `protocol.MAX_MESSAGE_BYTES` |
| K4 | 协议版本集合冻结为 `2025-06-18` / `2025-03-26` / `2024-11-05`，未知版本回默认 | `protocol.SUPPORTED_PROTOCOL_VERSIONS`（决策 D22） |
| K5 | `tools/list` 按 name ASCII 升序 | `Registry.names()` |
| K6 | 判定层禁 `time/datetime/random/secrets/socket/ssl/http/urllib/requests/os/subprocess/sys/pathlib/shutil/tempfile/uuid`，禁 `open`/`read_text` | `tools/gates.py:JUDGEMENT_FORBIDDEN` |
| K7 | 全运行时包禁时钟/随机/网络；`os.environ`/`getenv` 全仓禁（判定层连 `os` 都禁） | `tools/gates.py:no_nondeterminism` |
| K8 | 包内路径是唯一可编辑真相源，顶层 `references/`、`schemas/tools/` 是逐字节镜像 | `plan/02` §三；`scripts/check_release.check_dist_mirrors` |
| K9 | `code` 枚举 / `spec_ref` 格式 / 排序 / 时间解析只在 `data/README.md` §4 定义一次 | `data/README.md` §四 |
| K10 | 判定为 `block` 不是错误（`isError: false`）；tool 级坏输入走 result 的 `isError: true`；协议级错误走 JSON-RPC error | `plan/02` §5.4、§七 |
| K11 | 发布终态门不进 CI；三种模式 `--offline`（默认）/ `--pre-tag` / `--online` | `scripts/check_release.py`（决策 D34） |
| K12 | `NotAchieved`（exit 1）与 `EnvironmentMissing`（exit 3）必须是两类异常 | `scripts/check_release.py` |
| K13 | 生成侧 oracle 与生产实现分开书写，只靠逐字节测试对账 | `plan/04` §三（决策 D27） |
| K14 | golden 里出现 `observed_*` 字段即红 | `plan/04` §三 |
| K15 | EUC/行尾：所有文本 LF-only，`.gitattributes` 必须含 `eol=lf` | `tools/gates.py:crlf` |
| K16 | 版本唯一定义处是 `src/http_semantics_mcp/__init__.py:__version__`，`pyproject.toml` 必须一致 | `tests/test_packaging.py`、`selfcheck._check_version_parity` |

## 四、本机环境坑（均为本机实测，日期 2026-10-18）

| 坑 | 现象 | 处置 |
| --- | --- | --- |
| `py -3.8` 没有 `tomllib` | 读 `pyproject.toml` 会 `ImportError` | 统一用 `tools/toml_lite.py`（受限子集 + `TomlSubsetError`） |
| 新建 venv 缺 setuptools | `pip install -e .` 报 `Cannot import 'setuptools.build_meta'` | 先 `NO_PROXY="*" no_proxy="*" <venv>/Scripts/python.exe -m pip install setuptools` |
| 本机代理污染 pip | 安装可能走 `127.0.0.1:7897` | 一律 `NO_PROXY="*" no_proxy="*"` |
| Git Bash 路径 | `/tmp` 与 Windows Python 不通 | 临时文件放工作区或系统临时目录 |
| `gh` 是原生程序 | 不认 `/tmp/...` 路径 | 传 Windows 原生路径（`cygpath -w` 转换） |
| 无远端 | `git remote -v` 为空 | 所有 CI 结论写"本地等价校验"，M6 首推后据实补记 |
| 当前 `gh` 未建仓 | `check_release --online` 会报仓库不存在 | M6 先 `gh repo create`；`--pre-tag` 模式不受影响 |

## 五、DoD 逐项 checklist（M1）

- [ ] `codes.json` 生成；顶层镜像逐字节相等；代码内零第二份 code 字面量
- [ ] 每个 `code` ≥1 golden；`set(codes) == set(golden 覆盖)` 双向成立
- [ ] WPT 索引落盘（含 commit sha + 数据日）；台账满足 `converted + unmappable == total`
- [ ] `gen_codes --check` / `gen_golden --check` 重生成逐字节一致
- [ ] 时间解析正反例齐（`Z` 格式 / HTTP-date / 非法 / 亚秒截断）
- [ ] `tools/golden_oracle/` 不 import 判定层（AST 门红一次验证过）
- [ ] 双解释器 pytest 全绿（3.8 + 3.12，收集数一致）
- [ ] `tools/mutate_check.py` 新增的 gate 各配一条变异，全红
- [ ] `plan/00`、`plan/05` 状态回写
- [ ] `plan/HANDOFF-M2.md` 落盘 + commit

## 六、关键命令速查

```bash
# 双解释器全量测试
PYTHONPATH=src py -3.8 -m pytest -q
PYTHONPATH=src py -3.12 -m pytest -q

# 静态门 + 变异验证
PYTHONPATH=src py -3.12 tools/run_gates.py --verbose
py -3.12 tools/mutate_check.py

# 真实子进程握手（这两个解释器都跑）
PYTHONPATH=src py -3.12 tools/smoke_stdio.py
PYTHONPATH=src py -3.8 tools/smoke_stdio.py

# 入口自检
PYTHONPATH=src py -3.12 -m http_semantics_mcp --version
PYTHONPATH=src py -3.12 -m http_semantics_mcp --selftest

# 发布终态门（tag 之前）
PYTHONPATH=src py -3.12 scripts/check_release.py --pre-tag

# CI 文件本地解析（推之前必做）
py -3.12 -c "import yaml;d=yaml.safe_load(open('.github/workflows/ci.yml',encoding='utf-8'));print(list(d['jobs']), len(d['jobs']['test']['steps']))"
```

## 七、启动提示词（下一棒）

```
/goal 读取 "<项目绝对路径>\plan\HANDOFF-M1.md" 继续完成任务
```

（`<项目绝对路径>` 由用户侧填写；库内不写本机路径。）
