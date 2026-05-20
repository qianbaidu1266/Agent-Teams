# Multi-Agent Workflow Patterns

> 本文档详细介绍 Multi-Agent 系统的四种主流协作模式，以及 Multi-Agent-Playground 项目中的实现方案。

---

## Table of Contents

1. [Overview](#1-overview)
2. [Pattern 1: Supervisor（主管模式）](#2-pattern-1-supervisor主管模式)
3. [Pattern 2: Swarm（蜂群模式）](#3-pattern-2-swarm蜂群模式)
4. [Pattern 3: Pipeline（流水线模式）](#4-pattern-3-pipeline流水线模式)
5. [Pattern 4: Mesh（网状模式）](#5-pattern-4-mesh网状模式)
6. [Project Implementation](#6-project-implementation)
7. [Comparison](#7-comparison)

---

## 1. Overview

### 为什么需要 Multi-Agent？

单 Agent 系统在面对复杂任务时会遇到三个典型问题：

| 问题 | 描述 | Multi-Agent 解法 |
|------|------|-----------------|
| **上下文窗口污染** | 一个 Agent 挂了 12 个工具，每个工具描述占几百 token，关键信息被挤出上下文 | 每个 Agent 只挂自己需要的工具，上下文精简 |
| **角色混乱** | 一个 Agent 被要求"调研 + 写代码 + 写总结"，三组指令互相抢占优先级 | 每个 Agent 只干一件事，角色清晰 |
| **故障扩散** | 第 3 步出错，第 4-10 步全部污染，没有隔离层 | 出错只影响一个节点，可独立重试 |

### 四种主流协作模式

| 模式 | 核心特点 | 决策者 | 适用场景 |
|------|---------|--------|---------|
| **Supervisor** | 一个中央 Supervisor 统一调度 | Supervisor | 需要中央协调、子任务边界清晰的场景 |
| **Swarm** | Agent 之间直接 handoff，无中央控制 | 每个 Agent | 需要灵活协作、动态调整的场景 |
| **Pipeline** | 固定的执行顺序，阶段式处理 | 预定义流程 | 任务边界清晰、可独立执行的场景 |
| **Mesh** | 每个 Agent 都可以和其他任何 Agent 直接通信 | 所有 Agent | 需要频繁协作、信息共享的场景 |

---

## 2. Pattern 1: Supervisor（主管模式）

### 2.1 核心思想

一个中央 Supervisor Agent 接收用户请求，决定派给哪个 Worker，收到结果后再决定下一步——直到任务完成。

**数据流：**
```
User → Supervisor → Researcher/Writer/Fact-Checker → Supervisor → Final Answer
```

**关键特点：**
- Workers 之间互相不认识，所有信息都经过 Supervisor
- Supervisor 既是路由层也是汇聚层
- 路由逻辑集中在一处，可控性强

### 2.2 架构图

```
                    ┌─────────────┐
                    │    User     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Supervisor │ ◄─── 中央决策者
                    │   (Router)  │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Researcher│    │  Writer  │    │Fact-Checker│
    └─────┬────┘    └─────┬────┘    └─────┬────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Supervisor │ ◄─── 汇聚结果，决定下一步
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Final Answer │
                    └─────────────┘
```

### 2.3 工作流程

1. **接收请求**：Supervisor 接收用户输入
2. **路由决策**：Supervisor 决定派给哪个 Worker
3. **执行任务**：Worker 执行并返回结果
4. **评估结果**：Supervisor 评估结果，决定是否继续
5. **循环或结束**：如果需要，回到步骤 2；否则输出最终答案

### 2.4 优缺点

| 优点 | 缺点 |
|------|------|
| 可控性强，路由逻辑集中 | Supervisor 容易成为瓶颈 |
| 出错容易追踪 | 任务分解出错会影响所有下游 Worker |
| 适合需要中央协调的场景 | 不适合需要 Agent 之间直接协作的场景 |

### 2.5 适用场景

- 客服工单路由
- 内容生成流水线
- 代码审查工作流
- 子任务边界清晰、需要中央协调的场景

---

## 3. Pattern 2: Swarm（蜂群模式）

### 3.1 核心思想

**没有中央 Supervisor**，Agent 之间直接 handoff。每个 Agent 执行完后自己决定下一步给谁。

**数据流：**
```
User → Agent A → (Agent A 决定) → Agent B → (Agent B 决定) → Agent C → Final Answer
```

**关键特点：**
- 每个 Agent 都是平等的，没有"领导"
- Agent 自己决定是否 handoff 给其他 Agent
- 决策分散在每个 Agent 中

### 3.2 架构图

```
                    ┌─────────────┐
                    │    User     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Initial     │ ◄─── 初始路由（只选第一个 Agent）
                    │ Router      │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Agent A    │ ◄─── Agent A 执行后自己决定下一步
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Agent B  │ │ Agent C  │ │ Complete │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             └────────────┼────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │Final Answer │
                   └─────────────┘
```

### 3.3 工作流程

1. **初始路由**：选择第一个 Agent（只执行一次）
2. **执行任务**：Agent 执行当前任务
3. **自主决策**：Agent 决定下一步动作：
   - `continue`：继续当前任务
   - `handoff`：交给另一个 Agent
   - `complete`：任务完成
   - `respond_user`：直接回复用户
4. **循环或结束**：如果 handoff，转到目标 Agent；否则结束

### 3.4 与 Supervisor 的关键区别

| 特性 | Supervisor 模式 | Swarm 模式 |
|------|----------------|-----------|
| **决策者** | 中央 Supervisor | 每个 Agent 自己 |
| **信息流** | 都经过 Supervisor | Agent 之间直接传递 |
| **角色关系** | Supervisor > Workers | 所有 Agent 平等 |
| **灵活性** | 低（依赖 Supervisor 判断） | 高（Agent 自主决策） |

### 3.5 优缺点

| 优点 | 缺点 |
|------|------|
| 灵活性高，Agent 自主决策 | 调试困难，决策分散 |
| 没有 Supervisor 瓶颈 | 可能出现循环 handoff |
| 适合需要动态调整的场景 | 需要 Agent 有良好的决策能力 |

### 3.6 适用场景

- 需要灵活协作的场景
- Agent 之间需要直接传递信息
- 任务边界不清晰、需要在执行中逐步明确的工作

---

## 4. Pattern 3: Pipeline（流水线模式）

### 4.1 核心思想

**固定的执行顺序**，每个阶段只做一件事，输出是下一阶段的输入。类似工厂流水线。

**数据流：**
```
User → Stage A → Stage B → Stage C → Stage D → Final Answer
```

**关键特点：**
- 执行顺序固定，不可改变
- 每个阶段专注一件事
- 上游输出是下游输入

### 4.2 架构图

```
                    ┌─────────────┐
                    │    User     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Stage A   │ ◄─── 规划任务
                    │  (Planner)  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Stage B   │ ◄─── 验证计划
                    │ (Validator) │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Stage C   │ ◄─── 分发执行
                    │ (Dispatcher)│
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Worker 1 │    │ Worker 2 │    │ Worker 3 │
    └─────┬────┘    └─────┬────┘    └─────┬────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Stage D   │ ◄─── 汇总结果
                    │(Synthesizer)│
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Final Answer │
                    └─────────────┘
```

### 4.3 工作流程

1. **规划**：将用户请求拆解为任务列表
2. **验证**：检查任务列表是否合理
3. **分发**：按顺序分配任务给 Worker
4. **执行**：Worker 执行任务
5. **汇总**：将所有结果合并为最终答案

### 4.4 优缺点

| 优点 | 缺点 |
|------|------|
| 流程清晰，易于理解 | 不够灵活，无法动态调整 |
| 每个阶段专注一件事 | 如果上游出错，下游全部受影响 |
| 适合任务边界清晰的场景 | 不适合需要反复迭代的场景 |

### 4.5 适用场景

- 复杂、多阶段的任务（如"写前端 + 后端 + 测试"）
- 任务边界清晰、可独立执行的请求
- 需要明确执行顺序的场景

---

## 5. Pattern 4: Mesh（网状模式）

### 5.1 核心思想

**每个 Agent 都可以和其他任何 Agent 直接通信**，没有固定的路由逻辑或层级关系。

**数据流：**
```
        ┌─────────────────────────────────────┐
        │                                     │
        ▼                                     │
   ┌──────────┐                         ┌──────────┐
   │ Agent A  │◄───────────────────────►│ Agent B  │
   └────┬─────┘                         └────┬─────┘
        │                                    │
        │         ┌──────────┐               │
        └────────►│ Agent C  │◄──────────────┘
                  └────┬─────┘
                       │
                       ▼
                ┌─────────────┐
                │Final Answer │
                └─────────────┘
```

**关键特点：**
- 所有 Agent 地位平等
- 任意两个 Agent 之间都可以直接通信
- 没有"领导"或"路由器"

### 5.2 适用场景

- 需要频繁协作、信息共享的场景
- 多人协作编辑
- 实时讨论、头脑风暴

### 5.3 项目现状

Multi-Agent-Playground 项目**暂未实现** Mesh 模式。

---

## 6. Project Implementation

### 6.1 项目中的四种模式

| 项目模式 | 对应博客模式 | 说明 |
|---------|-------------|------|
| `router_specialists` | Supervisor 简化版 | 只有一轮路由，没有循环 |
| `planner_executor` | ✅ **Pipeline** | 规划 → 验证 → 分发 → 执行 → 汇总 |
| `supervisor_dynamic` | ✅ **Supervisor** | Supervisor 循环调度直到完成 |
| `peer_handoff` | ✅ **Swarm** | Agent 之间直接 handoff |

### 6.2 模式详解

#### 6.2.1 router_specialists（路由专家模式）

**一句话描述：** 单次路由，一次决策，一个专家处理全程。

```
START → Router → Specialist → Finalizer → END
```

**特点：**
- 只有一轮路由，没有循环
- Router 选择一个 Specialist 后直接执行
- 适合简单、单一目标的请求

**与 Supervisor 的区别：**
- Supervisor 模式有循环，Router 选择 → Worker 执行 → Supervisor 评估 → 循环
- router_specialists 没有循环，Router 选择 → Worker 执行 → 结束

---

#### 6.2.2 planner_executor（规划执行模式）↔ Pipeline ✅

**一句话描述：** 先规划任务清单，再逐个分配执行，类似"列清单 → 按序完成"。

```
START → Planner Core → Plan Validator → Task Dispatcher → Workers → Synthesizer → END
```

**特点：**
- 任务分解：Planner 将用户请求拆解为最多 4 个可执行任务
- 规划验证循环：Validator 检查计划质量
- 顺序分发：Dispatcher 每次只分配一个任务

**完全匹配 Pipeline 模式！**

---

#### 6.2.3 supervisor_dynamic（动态监督模式）↔ Supervisor ✅

**一句话描述：** 监督者按轮次驱动，每轮决定要不要继续。

```
START → Supervisor Intake → Delegation Policy → Worker → Supervisor Review → (循环或结束)
```

**特点：**
- 轮次限制：估算 max_cycles（2-5 轮）
- 动态任务分配：每轮重新决定焦点任务
- 监督者评估：每轮结束后判断是否继续

**完全匹配 Supervisor 模式！**

**节点说明：**

| 节点 | 职责 |
|------|------|
| `Supervisor Intake` | 接收用户请求，估算最大轮次 |
| `Delegation Policy` | 决定派给哪个 Worker，分配焦点任务 |
| `Worker` | 执行任务，生成报告 |
| `Supervisor Review` | 评估结果，决定是否继续迭代 |

---

#### 6.2.4 peer_handoff（同伴交接模式）↔ Swarm ✅

**一句话描述：** Agent 之间直接 handoff，没有中央 Supervisor。

```
START → First Owner Router → Agent A → (Agent A 决定) → Agent B → ... → Finalizer → END
```

**关键澄清：`first_owner_router` 不是 Supervisor！**

| 特性 | Supervisor | first_owner_router |
|------|-----------|-------------------|
| **职责** | 全程调度、评估、决策 | 只选择第一个 Agent |
| **参与时机** | 每轮都参与 | 只在开始时参与一次 |
| **决策权** | 决定每一步 | 只决定第一步 |
| **评估权** | 评估每轮结果 | 不评估任何结果 |

**Agent 自主决策的动作：**

| 动作 | 说明 |
|------|------|
| `continue` | 继续当前任务 |
| `handoff` | 交给另一个 Agent |
| `complete` | 任务完成 |
| `respond_user` | 直接回复用户 |
| `block` | 遇到阻塞，无法继续 |

**完全匹配 Swarm 模式！**

---

## 7. Comparison

### 7.1 模式对比表

| 特性 | Supervisor | Swarm | Pipeline | Mesh |
|------|-----------|-------|----------|------|
| **决策者** | 中央 Supervisor | 每个 Agent | 预定义流程 | 所有 Agent |
| **灵活性** | 中 | 高 | 低 | 最高 |
| **可控性** | 高 | 中 | 高 | 低 |
| **调试难度** | 低 | 高 | 低 | 最高 |
| **协作方式** | 间接（通过 Supervisor） | 直接（Agent 之间） | 顺序（上游→下游） | 任意（网状） |

### 7.2 项目模式与博客模式对应

| 博客模式 | 项目对应 | 匹配度 |
|---------|---------|-------|
| Supervisor | supervisor_dynamic | ✅ 完全匹配 |
| Swarm | peer_handoff | ✅ 完全匹配 |
| Pipeline | planner_executor | ✅ 完全匹配 |
| Mesh | 无 | ❌ 未实现 |
| - | router_specialists | 项目特有（Supervisor 简化版） |

### 7.3 选型指南

| 场景 | 推荐模式 |
|------|---------|
| 简单任务，只需一个专家 | router_specialists |
| 复杂任务，需要多阶段执行 | planner_executor（Pipeline） |
| 需要多轮迭代优化 | supervisor_dynamic（Supervisor） |
| 需要灵活协作、动态调整 | peer_handoff（Swarm） |
| 需要频繁协作、信息共享 | Mesh（未实现） |

---

## 8. References

- [Multi-Agent 的四种协作模式：Supervisor、Swarm、网状、流水线](https://mp.weixin.qq.com/s/OBG19jVnqP_xa8_IjomC8Q)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
