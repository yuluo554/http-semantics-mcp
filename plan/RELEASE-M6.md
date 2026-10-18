# RELEASE-M6（v0.1.0 发布留档）

> 本文件在 **tag 之前**入库，因此它是 tag 树的一部分，也会出现在发布附件
> `http-semantics-mcp-0.1.0.tar.gz` 里。
>
> 它只有两栏：`tag 时点事实`（tag 之前写定、不再改动）与 `tag 后追加事实`
> （tag 之后才知道的事实，只回填在后一栏）。两栏分离不是排版偏好：发布附件的
> sha256 一旦写进 tag 树，就会改变它所描述的那份字节，自指失效（D28/D29）。
> 附件从 **tag 树**构建，所以 tag 树内的本文件里没有任何 sha256；sha256 只出现在
> ①GitHub Release 正文 ②tag 之后 `main` 上的本文件「tag 后追加事实」栏。

---

## tag 时点事实

写定于 tag 之前。数值全部来自本机双解释器实跑，不是 CI。

| 项 | 值 |
| --- | --- |
| 分发名（distribution） | `http-semantics-mcp` |
| 版本 | `0.1.0`（`src/http_semantics_mcp/__init__.py:__version__` 与 `pyproject.toml` 一致，`selfcheck._check_version_parity` PASS） |
| 公开仓库 | `yuluo554/http-semantics-mcp`（public） |
| tag | `v0.1.0`（annotated；tagger 邮箱已脱敏为 GitHub noreply） |
| tag 目标 | `main` 上本文件所在提交（提交哈希见「tag 后追加事实」栏——tag 树内无法写自身哈希，自指） |
| 版本定版前置提交 | `c1f566f`（`0.1.0.dev0 → 0.1.0` 两处同步 + README 克隆地址改为 `http-semantics-mcp`） |
| 双解释器全量测试 | Python 3.8 → **379 passed / 379 collected**；Python 3.12 → **379 passed / 379 collected** |
| 静态门 | `tools/run_gates.py` → **8 gate(s), 0 failing**，合计扫描 **730** 文件项 |
| 变异验证 | `tools/mutate_check.py` → **43 mutation(s), 0 gate(s) failed to notice**（43/43 使门或测试变红） |
| 冻结 golden | **87 / 87** 与生产输出逐字节一致（cors 24 / sim 10 / cache 18 / cond 19 / vary 9 / _time 7） |
| 规则码覆盖 | **31 declared / 31 covered / 0 uncovered / 0 unknown**（双向集合等式） |
| WPT `cors/` 台账 | 45 = **15 mapped** + **30 unmappable**（逐条有 `reason`）；15/15 mapped 行实跑与生产输出逐字节一致 |
| tool 描述符 | **5** 个（`inputSchema` + `outputSchema`）；4129 / 3022 / 4297 / 6373 / 3384 字节 |
| 生成物复算 | `gen_codes --check`（codes.json 9468 字节 ×2 + rules.py 16772 字节）、`gen_golden --check`（87 case）、`gen_schemas --check`（5 tool）→ 全部 OK |
| `dist-mirrors` | 6 文件逐字节相等（`references/codes.json` 1 + `schemas/tools/*.json` 5） |
| 发布终态门 | `scripts/check_release.py --pre-tag`（干净树、提交后）→ **6 PASS / 0 FAIL / 4 SKIP**，退出 0 |
| 剩余 4 项 SKIP | `tag` / `release` / `attachments` / 网络项——tag 之后由 `--online` 复核 |
| CI | **本地等价校验（未接远端，CI 待首推验证）** |

> 诚实口径：发版时点本机 `git remote -v` 曾为空，本项目 CI 从未运行过。上表
> 所有"绿"均为**本地等价校验**；首推后的 run id 与首跑结论回填在下一栏。

### 本文件的复验路径（包内只写方法，不写 sha256）

拿到附件后，读者可自行复算、无需信任本文：

```bash
# 1. 校验附件完整性（sha256 见 GitHub Release 正文）
sha256sum -c <(printf '%s  %s\n' '<release 正文中的 sha256>' http-semantics-mcp-0.1.0.tar.gz)

# 2. 解包并逐条复跑（运行时零第三方依赖）
tar -xzf http-semantics-mcp-0.1.0.tar.gz
cd http-semantics-mcp-0.1.0
python -m http_semantics_mcp --version     # 期望 0.1.0，退出 0
python -m http_semantics_mcp --selftest    # 期望 summary: 6 passed, 0 failed，退出 0
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python -m http_semantics_mcp            # 期望一行 serverInfo + 一行五 tool 列表
```

---

## tag 后追加事实

写定于 tag 之后。以下各行在 **tag 树里为空**——它们是 tag 之后才存在的事实，
只回填在 `main` 上。

| 项 | 值 |
| --- | --- |
| tag 提交（`v0.1.0` 指向） | 待回填 |
| tag 对象 / tagger | 待回填 |
| 首推事件与 run 数对账 | 待回填（push 数 = run 数，按事件） |
| CI 四矩阵 run id 与结论 | 待回填（`{ubuntu,windows} × {3.8,3.12}`） |
| GitHub Release URL | 待回填 |
| 附件清单 | 待回填（手工源码包 + `SHA256SUMS`） |
| 附件 sha256 | 待回填（正文与下方 digest 行） |
| 真下载复验 | 待回填（`sha256sum -c` / `cmp` / `diff -r` / 中立目录三命令） |
| 干净 clone 复验 | 待回填（`--no-local` + 新 venv + README 逐条退出码） |
| `check_release.py --online` | 待回填 |
| 脱敏四步 | 待回填 |

<!--
注册行格式（check_release._registered_digests 逐字解析，tag 后回填时保持此形态）：

  行首为 "sha256:"，随后一个空格、64 位小写十六进制、两个空格、附件文件名，行尾结束。

tag 后回填时在本注释之外、本小节表格下方，逐附件写一行（本注释内不写示例行，
避免占位值被正则当成真值注册）。
-->
