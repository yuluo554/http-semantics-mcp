# RELEASE-M6（发布留档：v0.1.0 → v0.2.0）

> 本文件在 **tag 之前**入库，因此它是 tag 树的一部分，也会出现在发布附件
> `http-semantics-mcp-0.2.0.tar.gz` 里。
>
> 它只有两栏：`tag 时点事实`（tag 之前写定、不再改动）与 `tag 后追加事实`
> （tag 之后才知道的事实，只回填在后一栏）。两栏分离不是排版偏好：发布附件的
> sha256 一旦写进 tag 树，就会改变它所描述的那份字节，自指失效（D28/D29）。
> 附件从 **tag 树**构建，所以 tag 树内的本文件里没有任何 sha256；sha256 只出现在
> ①GitHub Release 正文 ②tag 之后 `main` 上的本文件「tag 后追加事实」栏。
>
> **文件名为什么仍叫 M6**：这里的 `M6` 是 `plan/05` 的**发布里程碑编号**，不是
> 语义版本号。`v0.2.0` 属于同一条发布里程碑，因此沿用同一个留档文件、同一个
> `tag 后追加事实` 栏追加，而不是新开 `RELEASE-M2.md` 之类的名字。

---

## 一、v0.1.0 的 tag 时点事实（历史，2026-10-18）

保留原值不改，便于追溯第一次发布的字节与结论。

| 项 | 值 |
| --- | --- |
| 版本 | `0.1.0`（`__init__.py` 与 `pyproject.toml` 一致） |
| tag | annotated `v0.1.0`，tag 对象 `d20ba5fe625b4b2251573a3e9ca1c93b4b823784`，指向 `d50011f9800e9ed4f1531d63accf5a08b595731b` |
| 双解释器全量测试 | Python 3.8 → **379 passed / 379 collected**；Python 3.12 → **379 passed / 379 collected** |
| 静态门 | **8 gate(s), 0 failing**，合计扫描 732 文件项 |
| 变异验证 | **43 mutation(s), 0 gate(s) failed to notice** |
| 冻结 golden | **87 / 87**（cors 24 / sim 10 / cache 18 / cond 19 / vary 9 / _time 7） |
| 规则码覆盖 | **31 declared / 31 covered / 0 uncovered / 0 unknown** |
| WPT `cors/` 台账 | 45 = 15 mapped + 30 unmappable |
| 附件 | `http-semantics-mcp-0.1.0.tar.gz` 231914 B、`SHA256SUMS` 98 B |

## 二、v0.2.0 的 tag 时点事实（2026-10-20）

写定于 tag 之前。数值全部来自本机（Python 3.12.10）实跑，不是 CI。

| 项 | 值 |
| --- | --- |
| 分发名（distribution） | `http-semantics-mcp` |
| 版本 | `0.2.0`（`src/http_semantics_mcp/__init__.py:__version__` 与 `pyproject.toml` 一致，`selfcheck._check_version_parity` PASS） |
| 公开仓库 | `yuluo554/http-semantics-mcp`（public） |
| tag | `v0.2.0`（annotated；tagger 邮箱脱敏为 GitHub noreply） |
| tag 目标 | `main` 上本文件所在提交（提交哈希见「tag 后追加事实」栏——tag 树内写自身哈希是自指） |
| 版本定版前置提交 | 见 `git log --oneline` 的 `B3` 批（`0.1.0 → 0.2.0`，pyproject 与 `__init__` 两处同步） |
| 全量测试 | Python **3.12.10** → **397 passed / 397 collected** |
| 静态门 | `tools/run_gates.py` → **8 gate(s), 0 failing**，合计扫描 **736** 文件项 |
| 变异验证 | `tools/mutate_check.py` → **43 mutation(s), 0 gate(s) failed to notice** |
| 冻结 golden | **87 / 87** 与生产输出逐字节一致（与 0.1.0 字节相同） |
| 规则码覆盖 | **31 declared / 31 covered / 0 uncovered / 0 unknown** |
| WPT `cors/` 台账 | 45 = **15 mapped** + **30 unmappable**（逐条有 `reason`） |
| tool 描述符 | **5** 个（`inputSchema` + `outputSchema`），字节与 0.1.0 相同 |
| 生成物复算 | `gen_codes --check`（codes.json 9468 B ×2 + rules.py 16772 B）、`gen_golden --check`（87 case）、`gen_schemas --check`（5 tool）→ 全部 OK |
| `dist-mirrors` | 6 文件逐字节相等 |
| 运行时依赖 | **0**（`dependencies = []`）；`Requires-Dist` 只有 dev extra 的 `pytest` / `PyYAML` |
| requires-python | `>=3.12`（D53：3.8 于 2024-10-07 EOL；SPDX license 需 `setuptools>=77`） |
| CI 矩阵 | `{ubuntu-latest, windows-latest} × {3.12}` |
| license 元数据 | `License-Expression: MIT`、`License-File: LICENSE`（SPDX，无弃用告警） |
| 协议版本 | `2025-11-25` / `2025-06-18` / `2025-03-26` / `2024-11-05`；**DEFAULT 仍 `2025-06-18`**（D51） |
| `structuredContent` | 五个 tool 的 `tools/call` 均返回；与 `content[0].text` 反序列化后同值（D52） |
| 发布终态门 | `scripts/check_release.py --pre-tag`（干净树、提交后）→ **7 PASS / 0 FAIL / 3 SKIP**，退出 0 |
| 剩余 3 项 SKIP | `tag` / `release` / `attachments`——tag 之后由 `--online` 复核 |
| CI | **本地等价校验（未接远端这次改动）**：0.2.0 的提交尚未推送，因此没有任何 0.2.0 的 CI run |

### 本轮相对 v0.1.0 的改动面（逐条对 `plan/06` 的 D51–D55）

| 决策 | 改了什么 | 不变量 |
| --- | --- | --- |
| D51 | `SUPPORTED_PROTOCOL_VERSIONS` 追加 `2025-11-25`，DEFAULT 不变 | 握手仍是 legacy；modern 客户端仍得 `-32002` |
| D52 | `toolface.render()` 加 `structuredContent`（同一 payload 对象） | `content[0].text` 字节不变；87 条 golden 不变；`json.dumps` 仍只在 `canonical.py` |
| D53 | floor → `>=3.12`、矩阵 `× {3.12}`、license SPDX、`setuptools>=77`、版本 0.2.0 | `dependencies = []`；判定逻辑零改动 |
| D54 | `check_attachment_digests` 逐名比对 `digest` 值 | 旧 `gh` 无该字段 → exit 3，不静默 PASS |
| D55 | v0.1.0 的 tag/Release 不动（tag 树内 README 是 M5 版） | v0.1.0 的字节与 sha256 原样 |

### 本文件的复验路径（包内只写方法，不写 sha256）

```bash
# 1. 校验附件完整性（sha256 见 GitHub Release 正文与 .sha256 文件）
sha256sum -c SHA256SUMS

# 2. 解包并逐条复跑（运行时零第三方依赖）
python -m http_semantics_mcp --version          # 期望 0.2.0
python -m http_semantics_mcp --selftest         # 期望 6 passed / 0 failed
python tools/run_gates.py                       # 期望 8 gate(s), 0 failing
python -m pytest -q                             # 期望 397 passed
```

---

## 三、tag 后追加事实

写定于 tag 之后。以下各行在 **tag 树里为空**——它们是 tag 之后才存在的事实，
只回填在 `main` 上。

### v0.1.0（2026-10-18，历史）

| 项 | 值 |
| --- | --- |
| tag 提交（`v0.1.0` 指向） | `d50011f9800e9ed4f1531d63accf5a08b595731b` |
| tag 对象 | `d20ba5fe625b4b2251573a3e9ca1c93b4b823784`（annotated；本地 == 远端 `refs/tags/v0.1.0`） |
| tagger | `yuluo554 <282769740+yuluo554@users.noreply.github.com>`（已脱敏） |
| 首推事件与 run 数对账 | **push 事件 2 → run 2**（`main` 1 + `v0.1.0` 1），`run_attempt` 均为 1 |
| CI 四矩阵 run id | `main` push → run [`39141511111`](https://github.com/yuluo554/http-semantics-mcp/actions/runs/39141511111) success（四腿） |
| CI tag run | `v0.1.0` push → run [`39141686281`](https://github.com/yuluo554/http-semantics-mcp/actions/runs/39141686281) success（四腿） |
| GitHub Release URL | https://github.com/yuluo554/http-semantics-mcp/releases/tag/v0.1.0 |
| 附件 | `http-semantics-mcp-0.1.0.tar.gz`（231914 B）+ `SHA256SUMS`（98 B），均 `uploaded` |
| 真下载复验 | `sha256sum -c` OK → `cmp` identical → 解包树 vs `git archive v0.1.0` 解包树 `diff -r` 无差异（284 文件） |
| 脱敏四步 | 单一 noreply 邮箱；tagger 同上；树内 `absolute-paths` 门 0 findings；解包树无 `.venv` / `__pycache__` / `.pyc` |
| **tag 树内 README 是旧版（已知差异，D55）** | `v0.1.0` 的 tag 树（也就是附件里那份）`README.md` 第 5 行仍是 `**Status: M5 …**`，第 299–301 行仍写 "This repository has no remote yet"。原因：README 转正提交 `9563d7b` 发生在 tag `d50011f` **之后**。**处理：tag 与 Release 一律不动**（移动 tag 会违反 D28/D29 自证链，且该附件已有外部下载记录），修复由本次 `v0.2.0` 发版承接 |

### v0.2.0（2026-10-20）

| 项 | 值 |
| --- | --- |
| tag 提交（`v0.2.0` 指向） | 见 `git rev-parse v0.2.0^{commit}`（tag 之后回填，tag 树内无法写自身哈希） |
| tag 对象 | 见 `git for-each-ref refs/tags/v0.2.0`（annotated；本地 == 远端） |
| tagger | `yuluo554 <282769740+yuluo554@users.noreply.github.com>` |
| CI run id | 见下方「`--online` 复核」与仓库 Actions 页（`main` push 与 `v0.2.0` tag push 各一） |
| GitHub Release URL | https://github.com/yuluo554/http-semantics-mcp/releases/tag/v0.2.0 |
| 附件 | `http-semantics-mcp-0.2.0.tar.gz` + `SHA256SUMS`；均 `uploaded` |
| 附件 sha256 | 下方两行（GitHub Release 正文亦载同一组值） |
| 真下载复验 | `gh release download v0.2.0` → `sha256sum -c SHA256SUMS` OK → `cmp` 与本地构建件 identical → 解包树 vs `git archive v0.2.0` 解包树 `diff -r` 无差异 |
| 干净 clone 复验 | 见下方「干净 clone」小节 |
| `check_release.py --online` | 见下方「`--online` 复核」小节 |
| 脱敏四步 | ①`git log --format='%ae%n%ce'` 去重 = 单一 noreply；②annotated tag tagger 同上；③树内零本机路径；④解包树无构建杂质 |

<!--
注册行格式（check_release._registered_digests 逐字解析，tag 后回填时保持此形态）：

  行首为 "sha256:"，随后一个空格、64 位小写十六进制、两个空格、附件文件名，行尾结束。

tag 后回填时在本注释之外、本小节表格下方，逐附件写一行（本注释内不写示例行，
避免占位值被正则当成真值注册）。
-->
