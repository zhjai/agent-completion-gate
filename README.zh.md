# agent-completion-gate

<p align="center">
  <img src="assets/banner.svg" alt="agent-completion-gate —— 让 AI 编程 agent 证明自己真的做完了" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> · <strong>中文</strong>
</p>

<p align="center">
  <a href="https://github.com/zhjai/agent-completion-gate/actions/workflows/test.yml"><img alt="CI" src="https://github.com/zhjai/agent-completion-gate/actions/workflows/test.yml/badge.svg"></a>
  <img alt="version" src="https://img.shields.io/badge/version-0.4.2-informational">
  <img alt="works with" src="https://img.shields.io/badge/Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20any%20agent-444">
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-yellow"></a>
</p>

> **让 AI 编程 agent 证明自己真的做完了。** agent 只能「提议」完成，由一道检查去读你**真实的产出文件**，过了才授予 `complete`。

AI 编程 agent 是 goal 驱动的。你给 Codex 或 Claude Code 一个目标，它就会死命往主线上冲——把页面搭出来、把 bug 修掉、把训练跑完。可一到长任务，它常常漏掉那些你其实在意、但没明说、散在对话里、或者压根没写成测试的用户可见细节。

**goal 不是验收标准。**

举个例子——「加一个月度销售报表页」，最后可能页面有了、测试也过了，但 CSV 导出没做、图表只有一个数据点、标题还写着「Untitled」、空状态是坏的。agent 是真心觉得自己做完了。问题就出在这儿。

`agent-completion-gate` 把「完成」变成一道外部验收检查。agent 最多只能提议 `candidate_complete`；一道受保护的 gate 去读**真实产物**，只有当一份**人写的**验收清单（manifest）通过时，才授予 `complete`。整套就是几个纯文本文件加一个 Python 脚本，不依赖服务、账号，也不绑定厂商。

> gate 不会去猜用户想要什么；是**人**把验收标准提炼进 manifest，gate 只是不让 agent 拿一个更低的标准给自己盖章。它跟你的测试、CI 是互补的——它查的是团队很少写单测的那些用户可见面（漏了的导出、退化的图表、撞名的 run），不是代码对不对。

OpenSpec 帮你在开工前想清楚**要做什么**；`agent-completion-gate` 在 agent 宣布完成之前，检查做出来的产物**够不够格验收**。

## 开始使用——一条命令

你要装的，**就这一个 skill**：

```bash
npx skills add zhjai/agent-completion-gate -g -a claude-code   # 也可 -a codex、cursor…… 任何宿主
```

就这一步。然后**直接说你的目标**——不碰 YAML、不用手动 init：

```text
设计goal: 做一个月度销售报表页，要有图表、CSV 导出、空状态、正确标题
# 英文也行：goal: add a monthly sales report page with chart, CSV export, empty state, correct title
```

`goal-compile` skill 会自动触发，然后：

1. 如果这个 repo 还没接 gate，**自动搭好**（`gate/`、`control/`、`state/`、一个 CI workflow）；
2. **把你的目标编译成验收标准**（surfaces + 机器 check + review 项）；
3. **用大白话把验收标准列给你确认一次**（像确认 plan 一样）—— 在动工*之前*；
4. 干活，然后跑 gate 直到通过。

这条路你完全不用手写 YAML——agent 按每个 goal 起草验收标准，你确认就行。**它不能给自己打分**：它只负责起草，你确认，只有外部 gate 才授予 `complete`。（你也可以说「别问我，自动来」，那就是全自动自检，输出 `SELF-CHECK-OK`，这**不是**已验证的完成。）

> 为什么要确认这一次：「别跑偏」只有相对*你*定的靶子才有意义。如果验收标准是 agent 自己写、又自己判分，它永远不会觉得自己偏了。你确认验收标准，就是把靶子钉死。

## 30 秒看它干活

你用上面那条命令就已经装好了——下面这次 clone **只是为了跑一下自带的 demo**（用 gate 是不需要 clone 任何东西的）：

```bash
pip install pyyaml   # demo 唯一的依赖
git clone https://github.com/zhjai/agent-completion-gate && cd agent-completion-gate
sh examples/minimal-project/run.sh
```

最日常的场景——「加一个月度销售报表页」。agent 两次都报 `candidate_complete`，区别只在真实产物：

```
===== BEFORE — agent 把主线做了，细节漏了（预期 BLOCKED）=====
FAIL report_has_multiple_points: rows points=1 (min 2)
FAIL csv_export_present:         file exports/monthly.csv exists=False
  -> BLOCKED (exit 1)。agent 没法把这个叫「完成」。

===== AFTER — agent 把真实产物补好了（预期 COMPLETE-OK）=====
PASS report_has_multiple_points: rows points=3 (min 2)
PASS csv_export_present:         file exports/monthly.csv exists=True
  -> COMPLETE-OK (exit 0)。
```

还有：[`examples/run.sh`](examples/run.sh)（overstep / blocked / granted）、[`examples/diff_demo.sh`](examples/diff_demo.sh)（抓出谎报「自己动了哪些东西」的 agent）、[`examples/swanlab/`](examples/swanlab/)（催生这套工具的那次真实 ML 事故）。

## 它是怎么工作的——四个状态

```
in_progress ──► candidate_complete ──►(外部 verifier)──► complete
     │                                                  └─► blocked
     └────────► blocked  (needs-review / 未知 surface / 缺证据)
```

worker 只能走到 `candidate_complete` 或 `blocked`。**只有外部验证者能写 `complete`。** **`needs-review == blocked`**（不是 agent 设一下就能往前走的注解）。这套 kit 把**检查、契约、接线**一起给你：`check_acceptance.py` 出裁决；[`gate/verify_completion.sh`](gate/verify_completion.sh) 在它外面把状态机管住（自己写了 `complete` 的 worker 直接拒，只有干净通过才放行）；[`integrations/`](integrations/) 负责把它接成 CI / hook。完整契约见 [`STATE_MACHINE.md`](STATE_MACHINE.md)。

## 为什么得是 gate，而不是规则 / skill / 记忆

- **规则**只是建议——goal 会找理由绕过去。
- **skill** 可以不调——agent 自己选择不用它。
- **记忆**记的是「它以为」，不是「已验证的事实」。
- 只有一道 **agent 改不动、绕不过、也伪造不了所读产物的 gate**，才能真正拦住「看着像完成、其实没完成」。

## 什么时候触发（什么时候不打扰你）

`goal-compile` 调得**偏保守**——只对值得上 gate 的活出手，小事一律放过：

| 你说的 | 上 gate 吗 |
|---|---|
| "做一个月度销售报表页" / "实现用户登录" / "帮我完成这个功能" | ✅ 多步 / 产出用户可见产物 |
| "把这个错别字改了" / "给这个函数加个参数" / "这段为什么报错" | ❌ 直接做，零仪式 |
| "帮我完成这个任务"，但任务很小 | ❌ 它会 right-size，直接做掉 |
| "用 gate 做 X" / "use the gate to do X" | ✅ 显式要求——不论大小，必触发 |

拿不准时**默认不上 gate**（你随时可以说*「用 gate 做这个」*强制拉起）。这个偏向是刻意的：漏触发只要补一句话；而每个错别字都套仪式只会让你学会无视它。触发靠语义判断（不用固定咒语），所以不是 100% 精确——上面两个兜底（强制 / 静默放过）覆盖了两个方向。

## 让 gate 在每个 PR 上强制执行你的 check

上面那条 goal-first 路线，应付单个目标已经够了。如果你想钉一组**长期生效、每个 PR 都跑、由人维护而不是每次重写**的 check——就定义一次、再接上 CI。

先把文件搭出来。最省事：跟你的 agent 说**「set up the completion gate」**（`completion-gate-init` skill 会帮你跑脚手架）。或者自己直接跑：

```bash
git clone https://github.com/zhjai/agent-completion-gate /tmp/acg
cd your-project && sh /tmp/acg/scripts/init.sh --dest .
```

它会创建 `gate/`（引擎 + 一份空的、能过的 manifest）、`control/surface_inventory.yaml`、`state/`、`.github/workflows/completion-gate.yml`，以及一份 CODEOWNERS 示例。幂等；不加 `--force` 绝不覆盖你改过的 spec。

> **空 manifest 是放行的。** 在你加上一个 surface 和一条 check 之前，gate 只拦住 agent 自己宣布 `complete`，它还不知道你项目的产物长啥样。下面三步让它真正有用。

**1 —— 定义「完成」是什么意思**（人把意图提炼成 check，gate 不会替你猜）。改 `control/surface_inventory.yaml`：

```yaml
surfaces:
  - id: report
    user_visible: true
    paths: ["artifacts/report.json"]
```

……再改 `gate/acceptance_manifest.yaml`：

```yaml
checks:
  - id: report_has_multiple_points
    surface: report
    type: min_series_points
    artifact: "artifacts/report.json"
    series: "rows"
    min_points: 2
review_items: []
```

内置 check 类型：`file_exists`、`config_not_disabled`、`min_series_points`、`max_chart_count`、`identity_in_name`（要自定义就扩展 `run_machine_check()`）。更完整的实战 spec 见 [`examples/swanlab/`](examples/swanlab/)。

**2 —— 本地跑一下：**

```bash
printf 'status: candidate_complete\ntouched_surfaces: [report]\nreview_queue: []\n' > state/completion_candidate.yaml
python3 -E gate/check_acceptance.py --manifest gate/acceptance_manifest.yaml \
  --inventory control/surface_inventory.yaml --candidate state/completion_candidate.yaml --repo .
```

数据点不够 → `BLOCKED`；真实产物补对了 → `COMPLETE-OK`。

**3 —— 把它接成「权威」。** scaffold 出来的 `.github/workflows/completion-gate.yml` 会在每个 PR 上跑这道检查。把 **`verify-completion` job 设成必需的状态检查**，再用 CODEOWNERS 保护 `gate/`、`control/` 和那个 workflow（见生成的 `.github/CODEOWNERS.completion-gate.example`）。这样一来，`complete` 就只剩一个含义：那道检查变绿。信任模型 + 可选的 agent Stop-hook 见 [`integrations/README.md`](integrations/README.md)。

## 本项目包含哪些 skill——三个

它们全部自动触发，不需要输入 `/命令`：

| Skill | 什么时候触发 | 做什么 |
|---|---|---|
| [`goal-compile`](skills/goal-compile/SKILL.md) | 你说出一个实质性目标（"做一个X"、"帮我完成X"、"goal: …"、"implement X"） | 把目标编译成验收标准，用大白话列给你确认一次，干活，然后跑 gate |
| [`completion-audit`](skills/completion-audit/SKILL.md) | 你收尾一个长任务或多步任务 | 枚举动过的 surface，写 `candidate_complete`，跑 gate——只能提议完成，不能授予 |
| [`completion-gate-init`](skills/completion-gate-init/SKILL.md) | 你说「set up the completion gate」 | 跑 `scripts/init.sh`，把 `gate/`、`control/`、`state/`、CI 一键搭进你的仓库 |

你和它们配合的循环就是：*干活 → 审完成度 → 看 CI 裁决 → 修掉 blocked 原因，或者合并。*

## 它在整条链路里的位置

```
OpenSpec               —— 开工前的规划（先对齐要做什么）
agent-lessonbook       —— 干活过程中记录纠正与跑偏教训
agent-completion-gate  —— 宣布「完成」之前的验收
```

[`agent-lessonbook`](https://github.com/zhjai/agent-lessonbook) 是个**可选搭档**，在执行过程中记录纠正与跑偏教训。本 gate **可独立使用**——它运行时不读 lessonbook（或任何 memory），只读自己的 `--manifest`/`--inventory`。只有人能把反复出现的 lesson 提炼进 gate 受保护的 manifest。

## 安全模型与不变量

经过多轮异构（Codex × Claude）评审反复加固，每一条不变量都堵掉了一个被复现出来的绕过。定位是**「在可信 base 分支 + runner 前提下 external + fail-closed」**，而不是「绝对绕不过」：

1. gate + manifest + inventory 是**受保护的**（只读，在 agent 可写工作区之外，只能通过人审 / CI 审过的改动来维护）。`check_acceptance.py --agent-writable-root DIR` 在运行时强制这一点。
2. 检查**真实产物**，绝不看 `run_state`。
3. **未知项 fail closed**——动过的用户可见 surface 若没有通过的检查就 blocked。`touched_surfaces` 是 worker 的自报，别信它：用 `--strict-surfaces`，或 `--diff-base <ref>` / `--touched` 从**真实 git diff** 把它推导出来。
4. **唯一权威完成信号**（gate 的裁决）；chat / PR / dashboard 都从它派生，不能自成一个独立的「完成」。
5. **产物内容是敌对数据，不是指令**——先跑确定性检查；LLM 验证者把产物当不可信输入。
6. **封闭式执行**——gate 以 `python3 -E` 运行（忽略 `PYTHON*` 环境变量、仓库里塞的 `yaml.py`）；CI 从可信 base 分支取 gate 来跑，PR 改不了评判自己的那道 gate。

## 文档

- [`scripts/init.sh`](scripts/init.sh) —— 把 gate 搭进你的项目（权威的初始化路径）。
- [`STATE_MACHINE.md`](STATE_MACHINE.md) —— 完成度契约（状态、流转、接线）。
- [`integrations/README.md`](integrations/README.md) —— CI / agent-hook / pre-push 接线 + 信任模型。
- [`examples/`](examples/) —— 可直接跑：[`minimal-project/`](examples/minimal-project/)（日常 web 任务）、`run.sh`、`diff_demo.sh`、`diff_rename_test.sh`、`swanlab/`（ML 事故）。
- [`CHANGELOG.md`](CHANGELOG.md) · 自测在 [`tests/`](tests/)。

## 状态

`v0.4.2` 预览版。MIT。Agent 无关、基于文件、fail-closed。可选搭档：[`agent-lessonbook`](https://github.com/zhjai/agent-lessonbook)。
