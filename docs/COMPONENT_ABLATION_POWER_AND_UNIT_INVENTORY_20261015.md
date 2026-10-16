# 组件消融的精确功效与实验单位盘点

日期：2026-10-15  
状态：**离线设计分析闭合；实验尚不可冻结或启动**

## 目的

本报告回答两个问题：经过四项 component contrast 的多重比较控制，需要多少合法单位；当前历史材料是否已经包含这些单位。结论是：样本量可以精确规划，但旧轨迹不能被重新标注为有效样本。

## 精确样本量

四项主对比分别为 full 对 no-semantic-verifier、no-resource-admission、no-complexity-control 和 no-selective-routing。最终使用 Holm familywise alpha .05；保守规划按每项 alpha .0125。设 `r` 为两臂不一致概率，`q` 为不一致时 full 获胜概率，满分母差异为 `r(2q-1)`。

达到 80% 功效所需总单位数：

| `r` | `q=.65` | `q=.70` | `q=.75` | `q=.80` |
|---:|---:|---:|---:|---:|
| .20 | 549 | 308 | 196 | 135 |
| .30 | 366 | 205 | 131 | 90 |
| .40 | 274 | 153 | 98 | 67 |
| .50 | 220 | 123 | 78 | 54 |

达到 90% 功效所需总单位数：

| `r` | `q=.65` | `q=.70` | `q=.75` | `q=.80` |
|---:|---:|---:|---:|---:|
| .20 | 706 | 395 | 251 | 170 |
| .30 | 471 | 263 | 167 | 113 |
| .40 | 353 | 197 | 125 | 84 |
| .50 | 282 | 158 | 100 | 67 |

以中等规划情形 `r=.30,q=.70` 为例，80% 和 90% 功效分别需要 205 和 263 个合法单位。现有 38 题的精确功效只有 12.09%。这些数字不能跨层机械套用：proposal、library selection 和 routing envelope 是不同单位。

## 现有单位是否可用

| 层次 | 当前材料 | 可用于 confirmatory component effect | 原因 |
|---|---:|---|---|
| Typed proposal | 5 个 DCP identity，其中共同冻结 typed grammar 内只有 1 个 | 否 | 其余为 free-text 或顺序修订，不能组成 matched population |
| Per-instance trajectory | 229 条 | 否 | 它们是逐题 formulation attempt，不是知识 proposal trial |
| Legacy VERA skill identity | 6 个 | 否 | 协议不兼容且 outcome 已打开 |
| Independent library-selection episode | 0 个 | 否 | TSP/OR-Debug 是不同 family 上分别 authored 的库，不是同一候选池的有/无 MDL 重选 |
| Known mixed envelope | 2,985 条 | 否，针对 routing effect | 140 条只路由 TSP skill，2,845 条只路由 OR skill；没有零匹配或多重匹配结果，只有 preservation 证据 |
| Fresh endpoint identity | 38 条 | 只可作描述性 panel | 对四项中等效应功效不足，且不能替代 proposal/library/envelope 单位 |

这排除了一个看似省事但科学上错误的做法：将历史五个 proposal、229 条逐题轨迹和六个 legacy identity 合并成一个更大的 `n`。它们的生成机制、grammar、反馈、parent lineage、预算和 outcome-access 状态均不同。

## 对后续实验的直接约束

1. 语义验证与资源准入可以共享一个前瞻冻结的 candidate pool，但各自保留配对结果和失败类型。
2. 复杂度控制必须重复“从同一候选池选择 library”这一动作；benchmark 题数不是构库次数。
3. 路由实验必须另建无答案的 envelope 集，预先包含 zero、unique 和 multiple matches，以及 paraphrase、schema shift 和 new-family cases。
4. 小型 pilot 仅用于估计 `r`、失败类型和成本；确认样本量必须由独立或 alpha-accounted 规则冻结。
5. 如果独立 library-selection episode 的规模不可实现，论文应把 complexity control 保留为理论指导的设计原则，并把经验因果主张收窄到 verifier/resource 与 routing，而不能声称四个组件均被证明有效。

## 当前边界

本报告只完成离线精确功效与 metadata-level 单位盘点。它没有创建候选、打开新题目、生成路由变体、冻结计划或授权任何 API、solver、native evaluator、VM 调用。
