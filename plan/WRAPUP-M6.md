# WRAPUP-M6（收官档）

> 写于 2026-10-18，M6 发布收尾。本项目 **M0–M6 全部完成**，`v0.1.0` 已公开发布。
> 本档是收官入口：一句话结论、交付物、DoD → 证据索引、复现路径、边界与后续。

## 一句话结论

把 HTTP 里最容易静默失败的四块语义（CORS 放行、RFC 9111 缓存新鲜度、RFC 9110
条件请求、`Vary` 命中）做成一个**零运行时依赖**的 stdio MCP server：输入是调用方给
的 header 字面量，输出是**带规范条款引用**的确定性判定，同输入必得同字节。已在
`yuluo554/http-semantics-mcp` 以 `v0.1.0` 公开发布。

## 交付物

| 交付物 | 位置 |
| --- | --- |
| 公开仓库 | https://github.com/yuluo554/http-semantics-mcp （public，署名 `yuluo554`） |
| 版本 | `0.1.0`（`src/http_semantics_mcp/__init__.py:__version__` 与 `pyproject.toml` 一致） |
| annotated tag | `v0.1.0` → 提交 `d50011f…`（tag 对象 `d20ba5fe…`） |
| GitHub Release | https://github.com/yuluo554/http-semantics-mcp/releases/tag/v0.1.0 （非 draft） |
| 发布附件 | `http-semantics-mcp-0.1.0.tar.gz`（手工源码包，231914 字节）+ `SHA256SUMS` |
| 发布留档 | `plan/RELEASE-M6.md`（tag 时点事实 / tag 后追加事实两栏） |
| 计划与口径 | `plan/00`–`06`、`data/README.md` §4（数值口径唯一出处） |

## DoD → 证据索引

| M6 DoD | 证据 |
| --- | --- |
| 版本定版 `0.1.0`，`--version` / `--selftest` 通过 | `--version` → `0.1.0`；`--selftest` → 6 passed / 0 failed（3.8 与 3.12 各一次）；`selfcheck._check_version_parity` PASS |
| `plan/RELEASE-M6.md` tag 之前入库、含两栏 | 提交 `9cb9960`（文件入库）→ `d50011f`（校正 tag 树实测）；`check_release.check_release_doc` 逐字匹配两个小标题 |
| 远端建好并首推；四矩阵全绿；push 数 = run 数 | push 事件 2 = run 2：`main` run [`39141511111`](https://github.com/yuluo554/http-semantics-mcp/actions/runs/39141511111)、`v0.1.0` run [`39141686281`](https://github.com/yuluo554/http-semantics-mcp/actions/runs/39141686281)，四腿全 success |
| 手工源码包 + 本地 sha256 副本；sha256 只在 Release 正文 | `git archive --format=tar --prefix=http-semantics-mcp-0.1.0/ v0.1.0 \| gzip -9n`；sha256 `8cc8892c…`；tag 树内 `plan/RELEASE-M6.md` 无 digest 行（自指检查：`_registered_digests` 在包内文件上返回空） |
| annotated tag（tagger 邮箱脱敏）+ Release + 附件 | tagger `yuluo554 <282769740+yuluo554@users.noreply.github.com>`；Release 两附件 `state=uploaded` |
| 干净 clone（`--no-local`）+ 新 venv + README 逐条 | `--no-local` rc=0、https clone rc=0；`pip install -e ".[dev]"` rc=0；`--version`/`--selftest`/控制台脚本/stdio 握手 rc 全 0；`pytest` 379 passed |
| 真下载 → `sha256sum -c` → `cmp` → `diff -r` → 中立目录三命令 | `sha256sum -c` OK；`cmp` identical；解包树 `diff -r` 无差异（284 文件）；中立 venv 三命令 rc 全 0 |
| `check_release.py --online` 全绿 | 见 `plan/RELEASE-M6.md`「`--online` 复核」 |
| 脱敏四步 | ①`git log --format='%ae%n%ce'` 去重 = 单一 noreply；②tag tagger 邮箱脱敏；③`absolute-paths` 门在 tag 树 / 解包树 0 findings；④产物扫描无 `.venv`/`__pycache__`/`.pyc` |
| README 转正；`plan/00` 回写；`plan/05` M6 打勾；本档落盘 | 本提交（tag 之后仅 `plan/` 与 `README.md` 变更，`git diff --name-only v0.1.0..HEAD` 可验） |

## 从零复现

```bash
git clone https://github.com/yuluo554/http-semantics-mcp.git
cd http-semantics-mcp
python -m pip install -e ".[dev]"
python -m http_semantics_mcp --version     # 0.1.0
python -m http_semantics_mcp --selftest    # 6 passed, 0 failed
python -m pytest -q                        # 379 passed
python tools/run_gates.py                  # 8 gate(s), 0 failing
python tools/mutate_check.py               # 43 mutation(s), 0 gate(s) failed to notice
```

从发布附件复现（不依赖 git）：

```bash
sha256sum -c SHA256SUMS
tar -xzf http-semantics-mcp-0.1.0.tar.gz && cd http-semantics-mcp-0.1.0
python -m http_semantics_mcp --selftest
```

## 边界与明确不做

- **不做安全评分**（D2）：不输出等级 / 严重度 / "这个站安不安全"。
- **零网络、零抓包**（D3）：`url` 只解析 scheme/host/port；不接代理、不读 HAR、不抓流
  量。相邻形态由 `mitmproxy-mcp` / `powhttp-mcp` 覆盖。
- **判定是规范推导，不是浏览器实测**（P2）：实现与规范分歧时以规范为准并登记。
- **不做 CLI 判定命令**（D26）：判定只经 MCP 暴露。
- **不做 tag 后的代码变更**：`v0.1.0` 之后只允许 `plan/` 与 `README.md` 的文档面提交。

## 本机环境坑（发布相关，已踩过并留档）

- 本机 `python` 裸命令是 WindowsApps stub：一律 `py -3.8` / `py -3.12`。
- **`github.com:443` 直连会超时/重置，但本机有本地代理 `127.0.0.1:7897`**：
  `git push` / `git clone` / `ls-remote` 需 `-c http.proxy=http://127.0.0.1:7897`；
  `gh`（走 `api.github.com`）与 `curl codeload` 直连可用。首推时正是踩这个。
- 新 venv（3.12）不再自带 `setuptools`，但 `pip install -e .` 的构建隔离会自动取；
  仅当 PyPI 不可达时才需先手工装 `setuptools`。
- pip 需 `NO_PROXY="*" no_proxy="*"` 以免被本机代理污染。

## 后续可选（不在 M0–M6 范围内）

- 仓库 description / topics 可在 GitHub 侧补充（已设 description；topics 未设）。
- 若 MCP 协议版本集合演进，按 `protocol.SUPPORTED_PROTOCOL_VERSIONS` 常量集中更新（P1）。
