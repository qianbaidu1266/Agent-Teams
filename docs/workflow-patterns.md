# Multi-Agent Workflow Patterns

> 本文档分析 Multi-Agent-Playground 中四种工作流模式的功能特点与实现方案。

---

## Table of Contents

1. [Overview](#1-overview)
2. [Router Specialists](#2-router-specialists)
3. [Planner Executor](#3-planner-executor)
4. [Supervisor Dynamic](#4-supervisor-dynamic)
5. [Peer Handoff](#5-peer-handoff)
6. [Comparison](#6-comparison)

---

## 1. Overview

四种工作流都基于 **LangGraph StateGraph** 构建，共同使用：

- `RouterState` / `PlannerState` / `SupervisorState` / `PeerState` 作为跨节点的共享状态
- `call_llm` + `llm_gateway.run_agent` 执行 LLM 调用
- `trace` 事件流记录执行轨迹
- `WorkflowGraph` / `WorkflowRunResponse` 作为输出格式

核心差异在于**路由决策的执行位置**和**循环控制机制**：

| Pattern | Decision Maker | Loop Mechanism | Task Model |
|---------|---------------|---------------|------------|
| Router Specialists | Central Router | None (single pass) | One specialist, full request |
| Planner Executor | Central Planner | Plan-validate loop | Pre-decomposed task list |
| Supervisor Dynamic | Central Supervisor | Cycle-counted loop | Dynamic focus tasks per cycle |
| Peer Handoff | Each peer agent | Hop-bounded loop | Self-directed handoffs |

---

## 2. Router Specialists

### 2.1 功能特点

**一句话描述：** 单次路由，一次决策，一个专家处理全程。

- **静态单跳路由**：由中心路由器根据用户输入选择最合适的单一专家 agent
- **无循环**：选定专家后直接执行，不存在迭代
- **双重路由策略**：优先 LLM 语义路由 → 失败后关键词匹配 → 再失败则默认第一个 agent
- **可选终态整理**：Finalizer 节点将专家回答压缩为对用户友好的回复

**适用场景：**
- 简单、单一目标的请求（如"帮我写一封邮件"）
- 不需要任务拆解或多轮协作的场景
- 需要快速响应的场景

**不适用：**
- 复杂、多阶段、需要来回调整的任务
- 需要多个 agent 协作完成的请求

---

### 2.2 技术架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Router Specialists                     │
│                  (StateGraph Architecture)               │
└─────────────────────────────────────────────────────────┘

  START
    │
    ▼
┌──────────────┐
│    Router    │  LLM semantic route  →  fallback keyword  →  fallback first
│  (logic node)│  Returns: selected_agent_id, route_reason
└──────┬───────┘
       │ route_next(state) reads selected_agent_id
       ▼
   ┌───────────────────┐
   │  Specialist A     │◄── dynamic node, one per agent
   │  Specialist B     │     agent.id → make_specialist_node(agent)
   │  Specialist C     │     llm_gateway.run_agent(agent, user_input)
   │       ...         │
   └─────────┬─────────┘
             │ (workflow.finalizer_enabled?)
             ├── true  ──► ┌────────────┐
             │             │  Finalizer │  Compress specialist answer
             │             └──────┬─────┘
             └── false           ▼
                               END
```

### 2.3 时序图

```
User        Router      Specialist A     Finalizer       LLM Gateway
 │              │             │              │                │
 │──请求────────▶│             │              │                │
 │              │──Route─────▶│              │                │
 │              │             │              │                │
 │              │◀─selected──│              │                │
 │              │             │              │                │
 │              │─────────────│─────────────▶│                │
 │              │             │──run_agent───▶│                │
 │              │             │◀─────────────│                │
 │              │             │◀──answer─────│                │
 │              │◀────────────│──────────────│                │
 │              │             │              │                │
 │              │──────────────────────────▶│──Finalize────▶│
 │              │             │              │◀──compressed──│
 │              │             │              │                │
 │◀─────────────────────────────END─────────────────────────│
```

### 2.4 核心实现

**状态定义：**

```python
class RouterState(TypedDict, total=False):
    user_input: str
    selected_agent_id: str
    selected_agent_name: str
    route_reason: str
    specialist_answer: str
    assistant_message: str
```

**路由决策函数 `route_next`：**

```python
def route_next(state: RouterState) -> str:
    return state.get("selected_agent_id", agents[0].id)
```

**路由提示词（prompts.py）：**

```
你是 workflow router。请从下面的 specialist agent 中选出最适合处理用户请求的一个。
只返回一行，格式必须是：agent_id|reason
```

**降级策略（prompts.py）：**

```python
FALLBACK_ROUTE_KEYWORDS: dict[str, list[str]] = {
    "architecture": ["架构", "architecture", "design"],
    "writing": ["写", "总结", "文档"],
    "learning": ["学习", "路径", "建议"],
}

def fallback_route_keyword(user_input: str, agents):
    # 1. LLM semantic route 失败
    # 2. 关键词匹配 FALLBACK_ROUTE_KEYWORDS
    # 3. 默认第一个 agent
```

---

## 3. Planner Executor

### 3.1 功能特点

**一句话描述：** 先规划任务清单，再逐个分配执行，类似"列清单 → 按序完成"。

- **任务分解**：Planner 将用户请求拆解为最多 4 个可执行任务
- **规划验证循环**：Validator 检查计划质量，若任务列表太粗（单一任务但请求复杂），触发重规划
- **顺序分发**：Dispatcher 每次只分配一个任务给一个 worker，完成后再分配下一个
- **报告收集**：每个 worker 的执行结果汇总为 `task_reports`，最终由 Synthesizer 合成

**适用场景：**
- 复杂、多阶段的任务（如"写前端 + 后端 + 测试"）
- 任务边界清晰、可独立执行的请求
- 需要明确执行顺序的场景

**不适用：**
- 任务边界模糊、需要动态调整的场景
- 需要 agent 之间实时协作/交接的场景

---

### 3.2 技术架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Planner Executor                      │
│                  (StateGraph Architecture)               │
└─────────────────────────────────────────────────────────┘

  START
    │
    ▼
┌─────────────────┐
│  Planner Core   │  LLM decomposes user request → task list (max 4)
└────────┬────────┘
         │ validator_next(state)
         ▼
┌─────────────────┐   replan_required=True
│ Plan Validator  │────────────────────────────┐
│  (logic node)   │   replan_required=False     │
└────────┬────────┘                            │
         │                                      │
         ▼                                      │
┌─────────────────┐                             │
│ Task Dispatcher │  Reads task_index, assigns task to worker
│  (logic node)   │                             │
└────────┬────────┘                             │
         │ dispatch_next(state) reads            │
         │   task_index vs len(tasks)           │
    ┌────┴────────────────────────┐              │
    │                             │              │
    ▼                             ▼              │
┌──────────┐               ┌────────────────┐   │
│ Worker A │               │   Synthesizer   │◀──┘ (if finalizer_enabled)
│ Worker B │               │   (optional)    │
│ Worker C │               └────────────────┘
│   ...    │
└────┬─────┘
     │ worker_next(state) always → DISPATCH_NODE
     ▼
  (back to Dispatcher)
```

### 3.3 时序图

```
User      Planner     Validator    Dispatcher     Worker A       LLM
 │           │            │            │              │            │
 │──请求─────▶│            │            │              │            │
 │           │──Plan─────▶│            │              │            │
 │           │◀─tasks────│            │              │            │
 │           │            │            │              │            │
 │           │───────────▶│──Validate──▶│              │            │
 │           │◀──replan──│            │              │            │
 │           │            │            │              │            │
 │           │◀───── replan_required=False ──────────│            │
 │           │            │            │              │            │
 │           │            │──Assign task[0]─────────▶│            │
 │           │            │            │──run_agent───▶│            │
 │           │            │            │◀──report──────│            │
 │           │            │◀────────────│◀─────────────│            │
 │           │            │            │              │            │
 │           │            │──Assign task[1]─────────▶│            │
 │           │            │            │──run_agent───▶│            │
 │           │            │            │◀──report──────│            │
 │           │            │            │              │            │
 │           │            │            │  (all done)  │            │
 │           │            │──────────────────────────▶│─Synthesize▶│
 │           │            │            │◀──answer──────│            │
 │◀───────────────────────────────────────────────────────────────│
```

### 3.4 核心实现

**状态定义：**

```python
class PlannerState(TypedDict, total=False):
    tasks: list[str]           # 任务列表
    plan_source: str           # "llm" | "fallback"
    planning_round: int        # 规划轮次
    replan_required: bool     # 是否需要重规划
    task_index: int           # 当前任务索引
    current_task: str         # 当前任务文本
    task_reports: list[str]   # 所有 worker 报告汇总
    current_worker_id: str
```

**重规划逻辑：**

```python
def _needs_replan(user_input: str, tasks: list[str]) -> bool:
    if len(tasks) >= 2:
        return False
    # 关键词暗示复合请求
    multi_hints = (" and ", " also ", " then ", "同时", "另外", "并且", "然后")
    return any(hint in user_input.lower() for hint in multi_hints) or len(user_input) > 120
```

**验证-分发条件路由：**

```python
# validator_next: Validator → Planner（重规划）或 Dispatcher（通过）
validator_next(state):
    return PLANNER_NODE if state["replan_required"] else DISPATCH_NODE

# dispatch_next: Dispatcher → Worker 或 Synthesizer 或 END
dispatch_next(state):
    if state["task_index"] < len(state["tasks"]):
        return selected_worker_id
    return SYNTH_NODE if finalizer else END

# worker_next: Worker → Dispatcher（继续下一个任务）
worker_next(state):
    return DISPATCH_NODE
```

**规划提示词：**

```
You are a planning module.
Decompose the user request into at most {max_tasks} executable tasks.
Prefer at least 2 tasks when the request includes multiple intents.
Return ONLY a JSON array of strings.
```

---

## 4. Supervisor Dynamic

### 4.1 功能特点

**一句话描述：** 监督者按轮次驱动，每轮决定要不要继续，类似"领导盯着你做，做完一轮领导评估一次"。

- **轮次限制**：由 `supervisor_intake` 估算 `max_cycles`（2-5 轮），循环不依赖任务是否完成
- **动态任务分配**：每轮由 `delegation_policy` 重新决定当前焦点任务，不预设任务列表
- **工件累积**：每次 worker 执行后的文件/报告累积在 `artifacts` 和 `reports` 中，供监督者评估
- **监督者评估**：每轮结束后 `supervisor_review` 读取累积结果，判断是否继续迭代

**适用场景：**
- 需要多轮迭代优化的场景（如"设计一个页面 → 评审 → 修改 → 再评审"）
- 任务边界不清晰、需要在执行中逐步明确的工作
- 需要人工监督但又希望自动化的场景

**不适用：**
- 任务边界清晰、可一次性完成的工作
- 不需要反复优化调整的场景

---

### 4.2 技术架构图

```
┌─────────────────────────────────────────────────────────┐
│                   Supervisor Dynamic                    │
│                  (StateGraph Architecture)               │
└─────────────────────────────────────────────────────────┘

  START
    │
    ▼
┌─────────────────┐
│ Supervisor      │  _estimate_max_cycles(user_input)
│    Intake       │  → 2-5 (based on request length & complexity hints)
└────────┬────────┘
         │ cycle=1
         ▼
┌─────────────────┐
│ Delegation      │  LLM selects next worker + focus task
│   Policy        │  delegation_next(state): returns worker_id
│  (logic node)   │
└────────┬────────┘
         │ delegation_next
         ▼
   ┌───────────────────┐
   │  Worker A         │  Dynamic node per agent
   │  Worker B         │  Reads current_focus_task from state
   │  Worker C         │  Appends report to reports[]
   │       ...         │
   └─────────┬─────────┘
             │ (every worker → REVIEW_NODE)
             ▼
┌─────────────────┐
│ Supervisor      │  LLM reviews reports + artifacts
│    Review       │  Returns: continue_loop, next_focus_task
│  (logic node)   │
└────────┬────────┘
         │ review_next(state)
         │   cycle < max_cycles and continue_loop → DELEGATION
         │   else → FINALIZE or END
         ▼
    ┌────┴────┐
    │         │
    ▼         ▼
 DELEGATION  FINALIZE / END
   (loop)     (exit)
```

### 4.3 时序图

```
User    Intake   Delegation   Worker B    Review     Supervisor   LLM
 │         │         │            │          │           │         │
 │──请求───▶│         │            │          │           │         │
 │◀─max────│         │            │          │           │         │
 │         │──cycle=1▶│            │          │           │         │
 │         │         │──Assign────▶│          │           │         │
 │         │         │──run_agent───────────────────────▶│         │
 │         │         │◀──report────────────────────────│         │
 │         │         │◀─worker───┘          │           │         │
 │         │         │            │──Review────────────────▶│    │
 │         │         │◀──continue=true, next_task──────│         │
 │         │◀────────│◀───────────────│          │           │    │
 │         │──cycle=2▶│            │          │           │    │
 │         │         │──Assign────▶│          │           │    │
 │         │         │──run_agent───────────────────────▶│         │
 │         │         │◀──report────────────────────────│         │
 │         │         │            │──Review────────────────▶│    │
 │         │         │◀──continue=false───────────────│         │
 │         │         │            │          │           │         │
 │         │         │            │          │──Finalize─▶│         │
 │         │         │            │          │◀─answer───│         │
 │◀───────────────────────────────────────────────────────────────│
```

### 4.4 核心实现

**状态定义：**

```python
class SupervisorState(TypedDict, total=False):
    max_cycles: int           # 2-5，由 intake 估算
    cycle: int                # 当前轮次
    workspace_dir: str         # 工件目录（由 artifacts 推导共同前缀）
    artifacts: list[str]      # 所有已生成的文件路径
    tool_evidence: list[str]  # 工具执行证据
    current_focus_task: str   # 当前轮次的焦点任务
    reports: list[str]        # 累积报告
    continue_loop: bool       # 监督者决定：是否继续
```

**轮次估算逻辑：**

```python
def _estimate_max_cycles(user_input: str) -> int:
    if len(user_input) >= 180:          return 5
    if any(t in text for t in ("compare", "tradeoff", "vs", "step by step")): return 4
    if any(t in text for t in ("以及", "并且", "同时", "对比", "先", "再")): return 4
    return 3  # 默认 3 轮
```

**工件目录推导（工作空间共享）：**

```python
def _derive_workspace_dir(artifacts: list[str]) -> str:
    # 从所有 artifact 路径中提取共同前缀作为工作目录
    # 供后续 worker 共享
```

**监督审查提示词：**

```
You are a supervisor loop controller.
Given the original user request and worker reports, decide whether to continue delegation.
Respond with JSON: {"continue": true/false, "next_focus_task": "...", "reason": "..."}
Rules:
- If current output is sufficient and coherent, set continue=false.
- If key requirements are missing, set continue=true and provide the next focus task.
- Current cycle: {cycle}, max cycles: {max_cycles}.
```

---

## 5. Peer Handoff

### 5.1 功能特点

**一句话描述：** 每个 agent 自己决定下一步做什么（继续 / 交接 / 评审 / 完成），同伴间自主协作。

- **双阶段执行**：每个 agent 每轮经历"执行阶段"（做任务）+ "决策阶段"（决定下一步）
- **6 种行动类型**：`continue`、`handoff`、`review`、`complete`、`respond_user`、`block`
- **Hop 预算**：通过 `max_hops` 限制总跳转次数，防止无限循环（约 11 次上限）
- **根完成审查**：即使 agent 返回 `complete`，`_review_root_completion()` 仍会验证用户原始请求是否真正满足
- **行动修复层**：对 agent 返回格式错误的行动 JSON 进行自动修复
- **工作空间确认**：`confirmed_workspace` 和 `confirmed_paths` 在 agent 间传递，确保文件写入位置统一

**适用场景：**
- 复杂、多角色协作的任务（如 PRD → 设计 → 开发 → 测试）
- 任务边界需要在执行中动态确定的场景
- 需要 agent 之间自主交接和评审的场景

**不适用：**
- 需要严格线性执行顺序的场景
- 不希望 agent 自主决定流程走向的场景

---

### 5.2 技术架构图

```
┌─────────────────────────────────────────────────────────┐
│                     Peer Handoff                        │
│                  (StateGraph Architecture)               │
└─────────────────────────────────────────────────────────┘

  START
    │
    ▼
┌─────────────────────┐
│ First Owner Router  │  LLM selects initial owner agent
│  (logic node)       │  (same router prompt as other workflows)
└──────────┬──────────┘
           │ sets current_owner_id
           ▼
   ┌──────────────────────────────────────────┐
   │           Peer Execution Loop             │
   │                                          │
   │  ┌─────────────────────────────────────┐ │
   │  │  peer_exec__<agent_id>               │ │  Dynamic node per agent
   │  │  Phase 1: Execute Task              │ │  _build_peer_execution_prompt
   │  │    - llm_gateway.run_agent()         │ │  No action JSON, just do the task
   │  │    - Tool calls → write files etc.   │ │  Update confirmed_workspace
   │  │    - Return execution result         │ │  Append to reports
   │  └───────────────┬─────────────────────┘ │
   │                  │                      │
   │                  ▼                      │
   │  ┌─────────────────────────────────────┐ │
   │  │  handoff_decision                   │ │  Single shared decision node
   │  │  Phase 2: Decide Next Action        │ │  _build_peer_decision_prompt
   │  │    - Parse JSON action              │ │  _repair_agent_action()
   │  │    - _review_root_completion()      │ │  _resolve_action()
   │  │    - _extract_action()              │ │
   │  └───────┬────────────────┬───────────┘ │
   │          │ decision_next  │              │
   │          ▼                ▼              │
   │   ┌──────────────┐  ┌──────────────────┐ │
   │   │ continue/    │  │ complete/respond_ │ │
   │   │ handoff/    │  │ user/block/max_  │ │
   │   │ review      │  │ hops/review_root  │ │
   │   └──────┬──────┘  └────────┬─────────┘ │
   │          │ (set next owner)│            │
   │          └─────────┬────────┘            │
   │                    │ (hop_count++)      │
   └────────────────────┼────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │    Finalize      │  (optional)
              │  (Synthesizer)   │
              └────────┬────────┘
                       ▼
                      END
```

### 5.3 时序图

```
Specialist A           Decision Node         Specialist B         Specialist C
    │                        │                    │                    │
    │──Execute────────────────▶                    │                    │
    │◀──execution result─────│                    │                    │
    │                        │                    │                    │
    │──Decide (action?)─────▶│                    │                    │
    │                        │                    │                    │
    │◀─{"action":"handoff"}──│                    │                    │
    │                        │                    │                    │
    │          ◀──handoff to B, next_task───────│                    │
    │                        │                    │                    │
    │                        │──Execute─────────▶│                    │
    │                        │◀──result──────────│                    │
    │                        │                    │                    │
    │                        │──Decide───────────│                    │
    │                        │◀─{"action":"continue"}                 │
    │                        │                    │                    │
    │                        │────Continue────────▶│ (same agent)      │
    │                        │◀──result───────────│                    │
    │                        │                    │                    │
    │                        │────Decide──────────▶│                    │
    │                        │◀─{"action":"complete"}                  │
    │                        │                    │                    │
    │                        │──_review_root_completion()               │
    │                        │  (LLM check: is request satisfied?)      │
    │                        │                    │                    │
    │◀──────────────────────────────────────────────────────────────────│
```

### 5.4 核心实现

**状态定义：**

```python
class PeerState(TypedDict, total=False):
    user_input: str
    current_task_title: str
    confirmed_workspace: str           # 经确认的工作目录
    confirmed_paths: list[str]          # 已确认的文件路径
    current_owner_id: str              # 当前负责的 agent
    last_worker_id: str
    reports: list[str]                 # 所有 agent 报告汇总
    hop_count: int                     # 已跳转次数
    max_hops: int                      # 上限（≈11）
    terminal_status: str               # "complete" | "max_hops" | "blocked"
    pending_action: str
    pending_target_agent_id: str
    pending_task_title: str
```

**6 种行动定义：**

| Action | 触发条件 | 效果 |
|--------|---------|------|
| `continue` | 当前 agent 认为任务未完成但可继续 | 同一 agent 继续执行 |
| `handoff` | 当前 agent 认为另一个 agent 更适合 | 切换到 `target_agent_id` |
| `review` | 当前 agent 认为另一个 agent 需要评审 | 切换到 `target_agent_id`，任务为评审 |
| `complete` | 当前 agent 认为任务完成 | 触发根完成审查，通过则退出 |
| `respond_user` | 当前 agent 认为需要直接回复用户 | 直接返回给用户 |
| `block` | 当前 agent 遇到无法解决的障碍 | 强制退出 |

**Hop 预算计算：**

```python
def _estimate_max_hops(agent_count: int, user_input: str) -> int:
    base = max(5, min(12, agent_count * 3 + 2))
    if len(user_input) > 220:
        return min(14, base + 2)
    return base
# 典型值: 3 agents → 11 hops
```

**双阶段 Prompt 分离（核心设计）：**

```python
# 阶段 1：执行阶段 - 只做任务，不输出 action JSON
# prompts.py _build_peer_execution_prompt
"Execute the current task directly. Do not output workflow action JSON in this step."

# 阶段 2：决策阶段 - 只输出 action JSON
# prompts.py _build_peer_decision_prompt
"Return exactly one JSON object and nothing else. Do not use markdown outside the JSON object."
```

**行动修复（处理格式错误的 LLM 输出）：**

```python
# _repair_agent_action() 修复以下情况：
# - 输出中包含 markdown 代码块包裹的 JSON
# - 输出中有多余的引号或转义字符
# - JSON 中包含 INTERNAL_RUNTIME_MARKERS（如 TOOL_EXECUTION_NO_FINAL_ANSWER）
```

**工作空间确认传递：**

```python
# 每个 agent 执行后，工作空间信息被更新到 state
artifacts = latest_tool_artifacts[agent.id]
if artifacts.get("output_dir"):
    confirmed_workspace = artifacts["output_dir"]  # 新路径覆盖旧路径
for path in artifacts.get("generated_files") or []:
    if path not in confirmed_paths:
        confirmed_paths.append(path)
```

---

## 6. Comparison

### 6.1 核心维度对比

| 维度 | Router Specialists | Planner Executor | Supervisor Dynamic | Peer Handoff |
|------|-------------------|-----------------|-------------------|-------------|
| **决策位置** | 中心路由器（单次） | 中心规划器（规划时） | 中心监督者（每轮） | 每个 agent 自己 |
| **循环依据** | 无循环 | 任务列表耗尽 | 轮次上限 | Hop 预算 |
| **任务模型** | 单专家处理 | 预拆解任务列表 | 动态焦点任务 | 自主交接协作 |
| **多 agent 协作** | 不支持 | 顺序分发 | 监督者指派 | 同伴自主交接 |
| **工具执行** | 专家 agent 调用 | Worker agent 调用 | Worker agent 调用 | 每个 peer 调用 |
| **状态共享** | 无 | 无 | artifacts + reports | confirmed_workspace + reports |
| **退出条件** | 专家执行完毕 | 所有任务完成 | 轮次耗尽或监督者判断完成 | Hop 耗尽或 action=complete |

### 6.2 架构形态对比图

```
Router Specialists:          Planner Executor:
  START → Router → [A|B|C] → END        START → Planner → Validator
  (无循环，单路径)                        ↕ replan      ↓ Dispatch
                                          (plan-validate loop)
                                                       Worker → Dispatch → ... → END

Supervisor Dynamic:          Peer Handoff:
  START → Intake → Delegation          START → Router → [Exec → Decision]*
    (cycle loop)    → Worker                                 ↕ (action routing)
                     → Review ─────────────────────────────▶ END
                     ↕ (continue_loop)
                   Delegation
```

### 6.3 选择指南

```
用户请求是否复杂、多阶段？
  否 → Router Specialists（简单直接）
  是 ↓

是否需要明确的任务分解和顺序执行？
  是 → Planner Executor（任务列表驱动）
  否 ↓

是否需要中心监督者按轮次迭代优化？
  是 → Supervisor Dynamic（轮次驱动）
  否 ↓

是否需要 agent 之间自主协作和交接？
  是 → Peer Handoff（同伴自组织）
  否 → Router Specialists（最简单）
```

### 6.4 状态体积对比（State 字段数量）

| Workflow | State 字段数 | 最大状态来源 |
|---------|------------|------------|
| Router Specialists | 6 | 最轻量 |
| Planner Executor | 10 | 任务列表 + 报告 |
| Supervisor Dynamic | 12 | 工件 + 证据 |
| Peer Handoff | 16 | 最重：工作空间确认 + Hop 追踪 + 行动待定 |

---

## Appendix: 文件位置

| 文件 | 路径 |
|------|------|
| Router Specialists | `backend/app/workflows/router_specialists/workflow.py` |
| Planner Executor | `backend/app/workflows/planner_executor/workflow.py` |
| Supervisor Dynamic | `backend/app/workflows/supervisor_dynamic/workflow.py` |
| Peer Handoff | `backend/app/workflows/peer_handoff/workflow.py` |
| Prompts | `backend/app/workflows/<workflow>/prompts.py` |
