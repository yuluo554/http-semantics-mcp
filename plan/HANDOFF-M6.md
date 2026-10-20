# HANDOFF-M6（发布）

> 写于 2026-10-18（M5 收尾）。下一棒：**M6 发布——远端仓库 + 手工源码包 + annotated tag + GitHub Release + `plan/RELEASE-M6.md`**。
> 本文是续接的唯一入口：新对话只需给绝对路径 + "读 plan/HANDOFF-M6.md 继续"。

## 一、当前进度与证据

### 已完成（M5，2026-10-18）

| 产出 | 位置 | 证据 |
| --- | --- | --- |
| 五个 tool 的描述符 | `src/http_semantics_mcp/schemas/tools/<tool>.json` | 每份含 `name`/`description`/`inputSchema`/`outputSchema`；4129 / 3022 / 4297 / 6373 / 3384 字节 |
| 包内 → 顶层镜像 | `tools/gen_schemas.py` + `schemas/tools/*.json` | `gen_schemas --check` → 5 tool / 0 problem（逐字节） |
| §4.10 读成机器可读 | `tools/spectable.py::read_output_fields` | 生成器与契约门共用同一输入 |
| registry 读描述符 | `registry.py` | 运行时读包内 JSON；缺件抛 `DescriptorError`；`tools/list` 现发布 `outputSchema` |
| 契约门 | `tests/test_schema_parity.py`（18 项） | 五 tool `outputSchema.properties` == §4.10 == 实跑输出键集合（80 条 tool golden；另把 7 条 `_time` 纳入 §4.10，全量 87 条） |
| 确定性门 | `tests/test_determinism.py`（4 项） | 五 tool × 全部 golden 双跑 sha256 相等；无机器路径 / 无凭空日期 |
| WPT 全量对账 | `tests/test_wpt_ledger.py` | 15/15 mapped 行实跑逐字节一致（25 条 golden 引用）；30 行各有 `reason` |
| 端到端 stdio | `tests/test_stdio_end_to_end.py`（2 项） | 真实子进程：握手 → 列五 tool → 五 tool 各成功调用一次 → 未知 tool `-32602` |
| README 指标段 | `README.md` | golden 87/87、WPT 15/45 + 30/45、5 描述符、8 门、43 变异、379/379 |
| 门 + 变异 | `tools/gates.py` / `tools/mutate_check.py` | 8 门全绿（合计 730 文件项）；43/43 变异变红（M5 新增 5 条） |
| 测试 | 全量 | 3.8 → 379 passed；3.12 → 379 passed（收集数各 379） |
| 决策 | `plan/06` | D50（schema 真相源路线 A + `additionalProperties` 口径澄清） |

### 当前事实（下一棒必须知道）

- **M5 的决定：schema 真相源 = 包内 JSON（路线 A，D50）**。`src/http_semantics_mcp/schemas/tools/<tool>.json` 是**唯一可编辑副本**（四个键：`name` / `description` / `inputSchema` / `outputSchema`）；`registry.build_registry()` 运行时读它；顶层 `schemas/tools/*.json` 是逐字节镜像，**只由** `tools/gen_schemas.py` 写。**不要手改顶层镜像**（`gen_schemas --check` 与 `check_release.check_dist_mirrors` 会同时打红）。
- **M6 不改 schema 内容**：`outputSchema.properties` 必须继续等于 `data/README.md` §4.10 的键集合（D50/K27）。若 M6 只想发布，不动这一层。
- **87 条 golden 与 31 个 code 已冻结**：M6 **不新增、不改写** golden / `code` / `rules.py`。`gen_codes --check`（9468 字节 codes.json 包内 + 镜像 + `rules.py` 16772 字节）、`gen_golden --check`（87 case / 0 problem）、`gen_schemas --check`（5 tool）必须保持逐字节一致。
- **`dist-mirrors` 现在是 6 个文件**：`references/codes.json`（1）+ `schemas/tools/*.json`（5）。`--pre-tag` 提交后应为 **6 PASS / 0 FAIL / 4 SKIP**（干净树）。
- **版本唯一定义处**：`src/http_semantics_mcp/__init__.py:__version__` 与 `pyproject.toml` 的 `version` 必须一致（`tests/test_packaging.py`、`selfcheck._check_version_parity`）。**M6 定版** `0.1.0.dev0 → 0.1.0`（两处一起改）。
- **`scripts/check_release.py` 的常量**：`TAG = "v0.1.0"`、`DISTRIBUTION = "http-semantics-mcp"`、`RELEASE_DOC = plan/RELEASE-M6.md`。`--pre-tag` / `--offline` / `--online` 三模；**不进 CI**（D34）；两类异常 `NotAchieved`（exit 1）与 `EnvironmentMissing`（exit 3）必须分开（K12）。
- **`plan/RELEASE-M6.md` 必须在 tag 之前入库**，且必须含两个小标题：`tag 时点事实` 与 `tag 后追加事实`（`check_release.check_release_doc` 逐字匹配这两个串）。
- **发布附件 sha256 只进 Release 正文**，包内只写复验方法（D29，写进包内会自指失效）。
- **未推送远端**：`git remote -v` 为空。一切 CI 结论只能写"本地等价校验（未接远端，CI 待首推验证）"，首推后据实补记 run id。
- **`raw.githubusercontent.com` 被重置**：`curl` 会 `Recv failure`，用 `gh api .../contents/<path> --jq .content | base64 -d`。
- **本机 `python` 裸命令是 WindowsApps stub**：一律 `py -3.8` / `py -3.12`；pip 一律 `NO_PROXY="*" no_proxy="*"`。
- **M5 新增的 5 条变异**（M6 若动 schema/README/§4.10/toolface 会一起打红）：schema 少一个 property、`additionalProperties` 改 `true`、顶层镜像改一字节、§4.10 掉一个字段、tool face 注入 volatile 键。

## 二、M6 待办（按顺序）

1. **定版**：`__init__.py:__version__` 与 `pyproject.toml` 的 `version` 同步 `0.1.0.dev0 → 0.1.0`；跑 `tests/test_packaging.py` 与 `--selftest` 复验（K16）。
2. **写 `plan/RELEASE-M6.md`（tag 之前入库）**：两栏 `tag 时点事实` / `tag 后追加事实`；tag 时点栏写：版本、commit、双解释器 379/379、8 门、43 变异、87/87 golden、WPT 15/45+30/45、schema 5 描述符、`--pre-tag` 结论、**本地等价校验（未接远端）**的诚实措辞；tag 后栏留空待补（run id、Release URL、附件 sha256、真下载复验）。
3. **建远端并首推**：`gh repo create yuluo554/http-semantics-mcp --public --source . --remote origin` → push `main` → 等 `.github/workflows/ci.yml` 四矩阵（`{ubuntu,windows} × {3.8,3.12}`）全绿；**push 数 = run 数**按事件对账（不按提交）；据实回写 run id。
4. **手工源码包**：`git archive --format=tar --prefix=<name>/ <tag> | gzip -9n > <file>.tar.gz`；本地留副本 + `sha256sum`；**sha256 只写 Release 正文**，不写进包内（D28/D29）。
5. **annotated tag + Release**：`git tag -a v0.1.0 -m ...`（tagger 邮箱已脱敏）→ push tag → `gh release create v0.1.0 <file>.tar.gz --notes-file ...`（正文含 sha256）。
6. **干净 clone 复验**：`git clone --no-local <repo> <中立目录>` → 新建 venv → 按 README 逐条跑通（`--version` / `--selftest` / stdio 握手），逐条记退出码。
7. **发布物本体复核**：真下载 → `sha256sum -c` → 与本地构建件 `cmp` → 附件解包树 vs `git archive <tag>` 解包树 `diff -r` 无差异 → 中立目录解包 → 新 venv 三命令。
8. **`--online` 全绿**：`scripts/check_release.py --online`（tag 指向、Release 非 draft、附件集合、逐附件 sha256）。
9. **脱敏四步**：`git log --format='%ae%n%ce'` 去重检查、annotated tag tagger 邮箱、树内零本机路径（`absolute-paths` 门）、产物扫描。
10. **回写与收尾**：README 状态行转正（M6 → Released）；`plan/00` 全部状态回写、`plan/05` M6 DoD 打勾；写 `plan/WRAPUP-M6.md`（收官档）；**tag 之后只允许文档面提交**（`git diff --name-only <tag>..HEAD` 只含 `plan/` 与 `README.md`）。

## 三、既定口径清单（K 编号，动了会打挂测试）

| 编号 | 口径 | 位置 |
| --- | --- | --- |
| K1 | 序列化唯一入口 `canonical.dumps` / `encode_message`：`sort_keys=True`、`ensure_ascii=False`、`separators=(",",":")`、`allow_nan=False` | `src/http_semantics_mcp/canonical.py`；`tools/gates.py:single_serialiser` |
| K2 | 帧格式 = 一行一条 UTF-8 JSON + `\n`；读侧剥 `\r`；写侧永不产 `\r` | `tests/test_server_transport.py` |
| K3 | 单条消息上限 8 MiB，超限排空该行并回 `-32600`，进程继续 | `protocol.MAX_MESSAGE_BYTES` |
| K4 | 协议版本集合为 `2025-11-25` / `2025-06-18` / `2025-03-26` / `2024-11-05`（D51 追加首项），未知版本回默认 `2025-06-18` | `protocol.SUPPORTED_PROTOCOL_VERSIONS`（D22 + D51） |
| K5 | `tools/list` 按 name ASCII 升序（现为 5 个 tool） | `Registry.names()`；3 处测试期望名单 + README |
| K6 | 判定层禁 `time/datetime/random/secrets/socket/ssl/http/urllib/requests/os/subprocess/sys/pathlib/shutil/tempfile/uuid`，禁 `open`/`read_text` | `tools/gates.py:JUDGEMENT_FORBIDDEN` |
| K7 | 全运行时包禁时钟/随机/网络；`os.environ`/`getenv` 全仓禁 | `tools/gates.py:no_nondeterminism` |
| K8 | 包内路径是唯一可编辑真相源，顶层 `references/`、`schemas/tools/` 是逐字节镜像 | `plan/02` §三；`scripts/check_release.check_dist_mirrors`；M5 起含 5 个 schema JSON |
| K9 | `code` 枚举 / `spec_ref` 格式 / 排序 / 时间解析 / 输出键集合只在 `data/README.md` §4 定义一次 | `data/README.md` §四 |
| K10 | 判定为 `block` 不是错误（`isError: false`）；tool 级坏输入走 result 的 `isError: true`；协议级错误走 JSON-RPC error | `toolface.py`、`protocol._tools_call` |
| K11 | 发布终态门不进 CI；三种模式 `--offline`（默认）/ `--pre-tag` / `--online` | `scripts/check_release.py`（D34） |
| K12 | `NotAchieved`（exit 1）与 `EnvironmentMissing`（exit 3）必须是两类异常 | `scripts/check_release.py` |
| K13 | 生成侧 oracle 与生产实现分开书写，只靠逐字节测试对账 | `plan/04` §三（D27）；`tools/gates.py:oracle_independence` |
| K14 | golden 里出现 `observed_*` 字段即红 | `tools/gates.py:golden_hygiene` |
| K15 | EUC/行尾：所有文本 LF-only，`.gitattributes` 必须含 `eol=lf` | `tools/gates.py:crlf` |
| K16 | 版本唯一定义处是 `src/http_semantics_mcp/__init__.py:__version__`，`pyproject.toml` 必须一致 | `tests/test_packaging.py`、`selfcheck._check_version_parity` |
| K17 | **手写**包内 `*.py` 不得出现 `CORS_/CACHE_/COND_/VARY_` 形式的 code 字面量；唯一豁免是生成物 `src/http_semantics_mcp/rules.py`（必须存在且含 `CATALOG`） | `tools/gates.py:code_literals`（D41/D42） |
| K18 | `expected` 键集合 = `data/README.md` §4.10 的表；不许多不许少 | `tests/test_golden.py:test_expected_key_sets_are_exact` |
| K19 | header 名列表输出小写；findings 按 `(code, detail)` 排序 | `data/README.md` §4.3（D35） |
| K20 | `informational` code 进 findings 但不翻转判定 | `data/README.md` §4.1（D36） |
| K21 | 判定层按名引用 code：`from ..rules import <CODE>`，`catalog` 由 `toolface.py` 传入 | `tools/gates.py:code_literals`；`rules.py`（D41） |
| K22 | 生成物三件由 `gen_codes.py` 同时产出、逐字节守门：`references/codes.json`（包内）+ 顶层镜像 + `rules.py` | `tools/gen_codes.py --check`；`tests/test_gen_codes.py` |
| K23 | T3 的 Age 取值优先级：`stored.age` > 响应头 `Age`；时间解析"只截断不进位"（`min(second, 59)`） | `judgement/cache.py`（D44/D45） |
| K24 | T4/T5 的 golden 未覆盖边缘由测试钉住（`*` 绑 ETag、IMS 方法门、`resource` 严格校验、`Vary` 重复只报一次、star 短路） | `tests/test_conditional_golden.py`、`tests/test_vary_golden.py`；`mutate_check.py` 第 27–38 条（D47/D48） |
| K25 | tool 级必填面必须自洽：`registry.INPUT_SCHEMAS[<tool>]["required"]` 里的每个键缺失时必须回 `isError: true` | `tests/test_registry.py::test_declared_required_fields_are_the_ones_the_handler_rejects`（D49） |
| K26 | **schema 真相源 = 包内 `schemas/tools/<tool>.json`**（四键描述符）；`registry.py` 运行时读它（缺件 → `DescriptorError`）；顶层镜像只由 `tools/gen_schemas.py` 写 | `registry.py`、`tools/gen_schemas.py`；D50 |
| K27 | `outputSchema.properties` == §4.10 键集合 == **实跑输出键集合**（双向），`required` == 同一键集合；`additionalProperties: false` 落在**带 `properties` 的对象**上，纯 header-map 对象声明 `additionalProperties`（schema 形式） | `tests/test_schema_parity.py`、`tools/gen_schemas.py:validate_descriptor`；D50 |
| K28 | 五 tool × 全部 golden 双跑 `sha256(canonical.dumps(...))` 相等；输出无机器绝对路径、无调用方未提供的日期 | `tests/test_determinism.py`；`data/README.md` §4.5 |
| K29 | `data/README.md` §4.10 由 `spectable.read_output_fields` 读成机器可读形态，是 schema 门与生成器共用的唯一输入（不许在代码里另抄一份键集合） | `tools/spectable.py`；`tools/gen_schemas.py` |

## 四、本机环境坑（均为本机实测）

| 坑 | 现象 | 处置 |
| --- | --- | --- |
| `py -3.8` 没有 `tomllib` | 读 `pyproject.toml` 会 `ImportError` | 统一用 `tools/toml_lite.py`（受限子集 + `TomlSubsetError`） |
| `py -3.8` 的 `Path.write_text` 无 `newline` 参数 | `TypeError: unexpected keyword argument 'newline'` | 写文件一律 `open(..., "w", encoding="utf-8", newline="\n")` |
| 本机 `python` 裸命令是 WindowsApps stub | 直接 `python` 不稳；`py` 可用 | 一律用 `py -3.8` / `py -3.12` |
| pytest 收集偶发崩溃 | 单次报 `TypeError: required field "func" missing from ...`，原命令重跑即全绿 | 判为机器抖动：先**原样重跑**；只有重跑仍红才当真实失败 |
| 新建 venv 缺 setuptools | `pip install -e .` 报 `Cannot import 'setuptools.build_meta'` | 先 `NO_PROXY="*" no_proxy="*" <venv>/Scripts/python.exe -m pip install setuptools` |
| 本机代理污染 pip | 安装可能走 `127.0.0.1:7897` | 一律 `NO_PROXY="*" no_proxy="*"` |
| Git Bash 路径 | `/tmp` 与 Windows Python 不通 | 临时文件放工作区或系统临时目录 |
| `gh` 是原生程序 | 不认 `/tmp/...` 路径 | 传 Windows 原生路径（`cygpath -w` 转换） |
| `raw.githubusercontent.com` 被重置 | `curl` 报 `Recv failure` | 改用 `gh api .../contents/<path> --jq .content \| base64 -d` |
| 无远端（M6 待建） | `git remote -v` 为空 | 首推前所有 CI 结论写"本地等价校验"；首推后据实补记 |
| `github.com` / API 不稳时 | push / `gh` 超时 | 重试；不要据此改代码 |
| `golden_oracle` 对空数组值会抛 `IndexError` | 探针输入 `{"Accept": []}` 时 oracle 崩，生产侧按"没有该值"处理 | oracle 的边界缺陷、不是契约（D49）。**不要**为了一致而改生产侧行为 |
| 顶层 schema 镜像手改 | `gen_schemas --check` 与 `dist-mirrors` 同时红 | 只改包内 JSON，再跑 `py tools/gen_schemas.py` 重写镜像 |

## 五、DoD 逐项 checklist（M6）

- [x] 版本定版 `0.1.0`（`__init__.py` + `pyproject.toml` 一致）；`--version` / `--selftest` 通过
      — 证据：`git show v0.1.0:pyproject.toml` → `version = "0.1.0"`；`git show v0.1.0:src/http_semantics_mcp/__init__.py` → `__version__ = "0.1.0"`。
- [x] `plan/RELEASE-M6.md` **tag 之前**入库，含 `tag 时点事实` / `tag 后追加事实` 两栏
      — 证据：`git cat-file -e v0.1.0:plan/RELEASE-M6.md` 成功（tag 树内存在），且两栏标题齐备（`check_release.check_release_doc` 逐字匹配）。
- [x] 远端仓库建好并首推 `main`；CI 四矩阵全绿（run id 回写）；push 数 = run 数对账
      — 证据：`git remote -v` → `origin https://github.com/yuluo554/http-semantics-mcp.git`；`gh run view 39141511111` → `conclusion: success`（四腿）；run id 已回写本文件与 `plan/RELEASE-M6.md`。
- [x] 手工源码包（`git archive` + `gzip -9n`）+ 本地 sha256 副本；sha256 只在 Release 正文
      — 证据：由 tag 重算 `git archive --format=tar --prefix=… v0.1.0 | gzip -9n` → sha256 `8cc8892c…f8b2`，与 Release 附件 `cmp` **identical**；`git grep -l "8cc8892c\|3fa920e3" v0.1.0` 无命中（tag 树内不含摘要）。
- [x] annotated tag `v0.1.0`（tagger 邮箱脱敏）+ GitHub Release + 附件上传
      — 证据：`git cat-file -t v0.1.0` → `tag`，指向 `d50011f9800e…`；tagger `yuluo554 <…@users.noreply.github.com>`；Release 两个附件均 `state=uploaded`。
- [x] 干净 clone（`--no-local`）+ 新 venv + README 逐条跑通（逐条记退出码）
      — 证据：见 `plan/RELEASE-M6.md`「干净 clone 复验」栏（`--no-local` 与 https 两条路径 rc=0，README 各命令 rc=0，`pytest` 379 passed）。
- [x] 真下载 → `sha256sum -c` → `cmp` → 解包树 `diff -r` 无差异 → 中立目录三命令
      — 证据（本次复跑 2026-10-20）：`gh release download v0.1.0` → `sha256sum -c SHA256SUMS` → `http-semantics-mcp-0.1.0.tar.gz: OK`（rc=0）；与本地由 tag 重打的件 `cmp` identical；解包树 vs `git archive v0.1.0` 解包树 `diff -r` 无差异。
- [x] `scripts/check_release.py --online` 全绿
      — 证据：`summary: 10 passed, 0 failed, 0 skipped (10 checks)`，退出 0。注：**当时该检查只比附件名**，本轮已改为真比摘要（D54 后记写在 `plan/RELEASE-M6.md`）。
- [x] 脱敏四步完成并留档
      — 证据：`git log --format='%ae%n%ce' | sort -u` → 单一 `282769740+yuluo554@users.noreply.github.com`；tagger 一致；`absolute-paths` 门在 tag 树 283 文件项 0 findings；解包树 284 文件无 `.venv` / `__pycache__` / `.pyc`。
- [x] README 状态行转正；`plan/00` 状态回写；`plan/05` M6 DoD 打勾；`plan/WRAPUP-M6.md` 落盘
      — 证据：`plan/WRAPUP-M6.md` 存在；`plan/05` 的 M6 DoD 已勾；`plan/00` M6 段已在。
- [x] tag 后仅文档面提交（`git diff --name-only <tag>..HEAD` 只含 `plan/` 与 `README.md`）
      — 证据：`git diff --name-only v0.1.0..7fb8ea1` → `README.md` + `plan/{00,05,RELEASE-M6,WRAPUP-M6}.md`，无代码文件。（口径按**每次发版**计：M6 收官时成立；二次迭代为 0.2.0 做的代码改动在 tag 之后，属下一轮。）

## 六、关键命令速查

```bash
# 全量测试（D53 起 floor 为 3.12；下面第一行是 M6 当时的口径，保留以便复算历史）
# PYTHONPATH=src py -3.8 -m pytest -q
PYTHONPATH=src py -3.12 -m pytest -q

# M5 新增门直跑
PYTHONPATH=src py -3.12 -m pytest -q tests/test_schema_parity.py tests/test_determinism.py tests/test_stdio_end_to_end.py

# 静态门 + 变异验证
PYTHONPATH=src py -3.12 tools/run_gates.py --verbose
py -3.12 tools/mutate_check.py

# 生成物复算（三件都必须逐字节一致）
py -3.12 tools/gen_codes.py --check
py -3.12 tools/gen_golden.py --check
py -3.12 tools/gen_schemas.py --check        # M5 新增
py -3.12 tools/golden_coverage.py

# 真实子进程握手（D53 起只需 3.12；3.8 一行保留为 M6 当时口径）
PYTHONPATH=src py -3.12 tools/smoke_stdio.py
# PYTHONPATH=src py -3.8 tools/smoke_stdio.py

# 发布终态门
PYTHONPATH=src py -3.12 scripts/check_release.py --pre-tag    # 提交后 6 PASS / 0 FAIL / 4 SKIP
PYTHONPATH=src py -3.12 scripts/check_release.py --online      # M6 tag 之后
```

## 七、启动提示词（下一棒）

```
/goal 读取 "<项目绝对路径>\plan\HANDOFF-M6.md" 继续完成任务
```

（`<项目绝对路径>` 由用户侧填写；库内不写本机路径。）
