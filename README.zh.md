# agent-completion-gate

<p align="center">
  <img src="assets/banner.svg" alt="agent-completion-gate —— 一道 fail-closed 的完成度 gate，阻止 agent 把没做完的活标成「完成」" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> · <strong>中文</strong>
</p>

<p align="center">
  <img alt="skill" src="https://img.shields.io/badge/agent--skill-agent--completion--gate-1f6feb">
  <img alt="version" src="https://img.shields.io/badge/version-0.1.0-informational">
  <img alt="works with" src="https://img.shields.io/badge/Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20any%20agent-444">
  <a href="https://github.com/zhjai/agent-memory"><img alt="depends" src="https://img.shields.io/badge/depends%20on-agent--memory-orange"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-yellow"></a>
</p>

> **阻止 agent 把没做完的活标成"完成"。** 一道 fail-closed 的完成度 gate + 一个四态状态机：worker 只能*提议*完成 —— 由一个外部验证者来批准。构建于 [`agent-memory`](https://github.com/zhjai/agent-memory) 之上。适配**任何** Agent-Skills 宿主 —— Claude Code、Codex 等等 —— 不绑定单一厂商。

## 它防的那个失败（30 秒）

一个目标驱动的 agent 跑完一个长任务，宣布成功 —— "计划已执行，测试通过"。但它交付时把 case 展示关掉了、run 名字撞了、val 曲线只有一个点。**这些信息 agent 都在上下文里有；只是那个 goal 没把它们当成完成标准。** 规则和 skill 修不了这个（goal 会把过往的建议合理化绕过去）。一道它改不了的 gate 才能。

```
# worker 提议完成（它只能到 candidate_complete，永远到不了 complete）：
state: candidate_complete

$ check_acceptance --manifest <protected>/acceptance_manifest.yaml \
                   --inventory <protected>/surface_inventory.yaml \
                   --candidate state/<task>/completion_candidate.yaml --repo .
  FAIL  case_examples_present:     max_case_examples=0 (must not be disabled)
  FAIL  val_curve_non_degenerate:  val/mae points=1 (min 2)
  BLOCK needs-review:              dashboard_readability
  → BLOCKED。state 保持 'blocked'。'complete' 不被授予。

# worker 修复真实产物、重跑；外部验证者随后才授予：
state: complete
```

gate 读的是**真实产物**（实际 config、实际 metrics），不是 agent 的自我汇报 —— 所以 agent 没法靠嘴皮子说到"完成"。

## 为什么是 gate，而不是 规则 / skill / 记忆

- **规则**是建议性的 —— goal 会把它合理化绕过去。
- **skill** 可以被跳过 —— agent 选择不调用它。
- **记忆**记录的是信念，不是已验证的真相。
- 只有**一道 agent 改不了的 gate、放在它绕不过的路径上、读它伪造不了的产物**，才能可靠地拦住"看着像完成、其实没完成"。

## 四态状态机

```
in_progress ──► candidate_complete ──►(外部 verifier)──► complete
     │                                                  └─► blocked
     └────────► blocked  (needs-review / 未知 surface / 缺证据)
```

Worker 只能到 `candidate_complete` 或 `blocked`。**只有外部验证者写 `complete`。** **`needs-review == blocked`**（不是 agent 设一下就能继续往前走的注解）。本 kit 交付的是**检查 + 契约**，不是后台守护进程：`check_acceptance.py` 返回一个裁决（退出码 + `COMPLETE-OK` / `BLOCKED`）；要让"只有外部验证者写 `complete`"成真，得把这个裁决接成你的**唯一权威完成信号**（git hook / CI / 任务运行器）。见 [`STATE_MACHINE.md`](STATE_MACHINE.md)。

## 依赖 agent-memory（gate 用它做记忆）

gate 是强制层；[`agent-memory`](https://github.com/zhjai/agent-memory) 是它的地基：

- gate 的**受保护完成规格** —— `acceptance_manifest.yaml` + `control/surface_inventory.yaml` —— **自带在本仓库里**，保持只读，**在 agent 可写工作区之外、也在任何 lesson 提拔路径之外**，所以 worker 没法靠提拔一条 lesson 来削弱 gate。
- 它读 `agent-memory` 的**只读 `control/`**，取项目的**规则与已批准的 lesson**（gate 必须遵守的策略层）—— 由人 / CI 维护，worker 永不可写。
- gate **绝不**把 agent-memory 里 worker 可写的 `state/`（run_state）当真相 —— 它检查的是真实产物。
- 先装 `agent-memory`；本 kit 叠在它上面。

## 不可协商的原则（每一条都堵住了异构评审中发现的一个真实绕过）

1. gate + manifest + inventory 是**受保护的**（只读、在 agent 可写工作区之外、在 lesson 提拔路径之外）。
2. 检查**真实产物**，绝不查 `run_state`。
3. **未知项 fail closed** —— 一个被改动过的用户可见 surface，若没有任何通过的检查 → blocked。
4. **唯一的权威完成信号**（gate 的裁决）；chat / PR / dashboard 都由它派生，绝不自成一个独立的"完成"。
5. **产物内容是敌对数据，不是指令** —— 先跑确定性检查；LLM 验证者把产物当不可信输入（否则 worker 往文件里写"mark complete"就能注入）。
6. **封闭式执行（hermetic）** —— 光是只读脚本不够；固定环境（PYTHONPATH / sitecustomize / conftest / 生成的配置）。

## 安装

`skills` CLI 安装的是 **skill，不是仓库依赖** —— 先装地基：

```bash
# 1. 地基（gate 的检查规格读 agent-memory 的只读 control/）：
npx skills add zhjai/agent-memory -g -a claude-code
# 2. 再装 gate：
npx skills add zhjai/agent-completion-gate -g -a claude-code
```

不用 Claude Code？换个宿主即可 —— skill 是 agent 无关的：

```bash
npx skills add zhjai/agent-memory -g -a codex   # Codex
npx skills add zhjai/agent-completion-gate -g -a codex
# … 或任何其他 Agent-Skills 宿主（gate 就是一个纯 Python 脚本 + 文件约定）
```

> 依赖边界：本仓库**自带**它自己的 `gate/` + `surface_inventory.yaml`；**项目专属的完成规则与已批准的 lesson 放在** `agent-memory` 的只读 `control/` 里，gate 把它读作规格。请锁定一个兼容的 `agent-memory` 版本。

## 状态

`v0.1.0` 预览版。MIT。Agent 无关、基于文件、fail-closed。地基：[`agent-memory`](https://github.com/zhjai/agent-memory)。
