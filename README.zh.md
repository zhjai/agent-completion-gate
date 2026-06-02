# agent-completion-gate

<p align="center">
  <img src="assets/banner.svg" alt="agent-completion-gate —— 一道 fail-closed 的完成度 gate，阻止 agent 把没做完的活标成「完成」" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> · <strong>中文</strong>
</p>

<p align="center">
  <a href="https://github.com/zhjai/agent-completion-gate/actions/workflows/test.yml"><img alt="CI" src="https://github.com/zhjai/agent-completion-gate/actions/workflows/test.yml/badge.svg"></a>
  <img alt="version" src="https://img.shields.io/badge/version-0.3.0-informational">
  <img alt="works with" src="https://img.shields.io/badge/Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20any%20agent-444">
  <a href="https://github.com/zhjai/agent-memory"><img alt="depends" src="https://img.shields.io/badge/depends%20on-agent--memory-orange"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-yellow"></a>
</p>

> **别让 agent 把没做完的活说成「完成」。** agent 只能「提议」完成，真正放行的是一道外部检查——它去读真实产出文件，过了才授予 `complete`。

## 这是个啥（说人话）

AI 编码 agent 经常会把一个长任务报成「做完了」，可实际上没有：测试被悄悄跳过、图表是坏的、功能只接了一半。这些信息它上下文里其实都有，只是它的 goal 没把这些当成收尾的标准——而 goal 总有办法把你写下的各种叮嘱绕过去。

`agent-completion-gate` 就是一道小小的 **fail-closed gate**。干活的 agent 最多只能把任务标到 `candidate_complete`（「我觉得这事儿成了」），到底成没成，由一道外部检查（`check_acceptance.py`）说了算——它读的是**真实产物**（真正的 config、真正的 metrics），只有真的过了，才由外部验证者（你的 CI 或一个 hook）授予 `complete`。整套东西就是几个纯文本文件 + 一个 Python 脚本，不依赖任何服务、账号，也不绑定厂商。

## 60 秒上手

```bash
pip install pyyaml
git clone https://github.com/zhjai/agent-completion-gate && cd agent-completion-gate
sh examples/run.sh
```

你会看到 gate 先**拦下**一次假完成（case 展示被关、曲线只有一个点），再**放行**一次真完成。下面是 checker 的真实输出，不是摆样子：

```
===== BAD (expect BLOCKED, exit 1) =====
FAIL case_examples_present: max_case_examples=0 (must not be disabled)
FAIL val_curve_non_degenerate: val/normalized/mae points=1 (min 2)
BLOCKED:  ...  'complete' is NOT granted.   (exit 1)

===== GOOD (expect COMPLETE-OK, exit 0) =====
PASS case_examples_present: max_case_examples=8 ...
COMPLETE-OK: all machine checks passed ...           (exit 0)
```

还可以看 [`examples/diff_demo.sh`](examples/diff_demo.sh)（抓出一个谎报「自己动了哪些东西」的 agent）和 [`examples/swanlab/`](examples/swanlab/)（一份贴近真实项目、填好内容的 spec）。

## 怎么用到你自己的项目里

1. **装 skill**（任何 Agent-Skills 宿主都行，先装地基）：

   ```bash
   npx skills add zhjai/agent-memory          -g -a claude-code   # 也可以 -a codex，或其它宿主
   npx skills add zhjai/agent-completion-gate -g -a claude-code
   ```

2. **把 gate 和 spec 模板拷进你的仓库**：复制本仓库的 `gate/` 和 `control/`。它们默认是**空的**——开箱状态下 gate 只强制状态机（agent 不能自己宣布 `complete`），空提议会被直接放行，所以**不会把你的流水线卡死**。要不要更严，下一步你自己开。*（拷过去之后改你自己那份，别把本仓库的 `gate/`/`control/` 当成活配置去 track，不然以后更新可能把你写的 check 覆盖掉。）*

3. **定义「完成」到底是什么意思**：在 `gate/acceptance_manifest.yaml` 里写针对真实产物的机器检查（内置类型有 `config_not_disabled`、`min_series_points`、`identity_in_name`、`max_chart_count`，要扩展自己加）。再在 `control/surface_inventory.yaml` 里列出用户可见的 surface。一份可以直接抄的实战示例在 [`examples/swanlab/`](examples/swanlab/)。

4. **把它接成「权威」**：把 [`integrations/github-actions/completion-gate.yml`](integrations/github-actions/completion-gate.yml) 拷到 `.github/workflows/`，设成**必需的状态检查**。这样一来，`complete` 就等价于「这个检查变绿」。（接线细节和信任模型见 [`integrations/README.md`](integrations/README.md)。）

5. *（可选）* **在 agent 自己的循环里盯着它**：加上 [`integrations/claude-code/`](integrations/claude-code/) 的 Stop-hook（同样可当 Codex 的 completion hook）——agent 想停下报完成时，会被当场告知「还没完，原因如下」。

## 装完 skill 之后，agent 会做什么

`completion-audit` 这个 skill 会告诉 agent：任务收尾时，先写一个 `completion_candidate.yaml`（`status: candidate_complete`，外加它动过的 surface），然后跑 gate。agent 顶天只能到 `candidate_complete`——只有外部验证者（CI / hook）才会写 `complete`。一旦被拦，它就去修真实产物，再重新过一遍。

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

## 依赖 agent-memory

[`agent-memory`](https://github.com/zhjai/agent-memory) 是地基（先装它）：它存项目的**规则 + 已批准的 lesson**——也就是人/CI 维护、你再把它提炼进 gate manifest 的那层策略。gate **自带受保护的检查规格**（`gate/` + `control/`），脚本运行时只读自己的 `--manifest`/`--inventory`，绝不碰 worker 可写的 `state/`。agent-memory 能独立用；这套 kit 是叠在上面、可选的强制层。

## 安全模型与不变量

经过多轮异构（Codex × Claude）评审反复加固，每一条不变量都堵掉了一个被复现出来的绕过。定位是**「在可信 base 分支 + runner 前提下 external + fail-closed」**，而不是「绝对绕不过」：

1. gate + manifest + inventory 是**受保护的**（只读，在 agent 可写工作区之外、也在 lesson 提拔路径之外）。`check_acceptance.py --agent-writable-root DIR` 在运行时强制这一点。
2. 检查**真实产物**，绝不看 `run_state`。
3. **未知项 fail closed**——动过的用户可见 surface 若没有通过的检查就 blocked。`touched_surfaces` 是 worker 的自报，别信它：用 `--strict-surfaces`，或 `--diff-base <ref>` / `--touched` 从**真实 git diff** 把它推导出来。
4. **唯一权威完成信号**（gate 的裁决）；chat / PR / dashboard 都从它派生，不能自成一个独立的「完成」。
5. **产物内容是敌对数据，不是指令**——先跑确定性检查；LLM 验证者把产物当不可信输入。
6. **封闭式执行**——gate 以 `python3 -E` 运行（忽略 `PYTHON*` 环境变量、仓库里塞的 `yaml.py`）；CI 从可信 base 分支取 gate 来跑，PR 改不了评判自己的那道 gate。

## 文档

- [`STATE_MACHINE.md`](STATE_MACHINE.md) —— 完成度契约（状态、流转、接线）。
- [`integrations/README.md`](integrations/README.md) —— CI / agent-hook / pre-push 接线 + 信任模型。
- [`examples/`](examples/) —— 可直接跑：`run.sh`、`diff_demo.sh`、`diff_rename_test.sh`、`swanlab/`。
- [`CHANGELOG.md`](CHANGELOG.md) · 自测在 [`tests/`](tests/)。

## 状态

`v0.3.0` 预览版。MIT。Agent 无关、基于文件、fail-closed。地基：[`agent-memory`](https://github.com/zhjai/agent-memory)。
