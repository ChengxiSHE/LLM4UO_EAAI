# 论文 headline 结果重建入口审计

日期：2026-10-15
状态：**尚不能从无凭据的公开干净克隆重建**

机器可读审计位于
[`headline_reconstruction_entrypoint_audit_20261015.json`](../experiments/headline_reconstruction_entrypoint_audit_20261015.json)。

## 核心结论

当前本机证据的内部一致性较强，但“本机存在终态 JSON”“有局部核验测试”“能从公开仓库重建结果”是三个不同结论。论文清单包含 16 组 headline evidence；只有 5 组找到会生成同一 headline schema 的顶层脚本，11 组没有精确 producer。抽查的 13 个关键实验脚本中，只有 mixed-router 的 3 个已被 Git 跟踪，其余 10 个在当前公开分支的干净克隆中不会出现。

进一步的静态 Python import 闭包审计从这 13 个脚本和 9 个定向测试出发，得到 121 个本地 Python 文件，其中 38 个已跟踪、83 个未跟踪。该结果见
[`HEADLINE_STATIC_PYTHON_CLOSURE_20261015.md`](HEADLINE_STATIC_PYTHON_CLOSURE_20261015.md)。它是保守闭包，不包含动态 import、数据、二进制、许可或外部服务，也不等于可以批量发布的 allowlist。

因此，当前允许的表述是：**本机有若干可识别的局部重建链，并且已有终态证据可做离线完整性核验。** 当前不能表述为：**GitHub 仓库能够从头复现论文全部结果。**

## 四层重建含义

| 层级 | 任务 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| A：离线完整性 | 核 hash、schema、算术、合同和确定性 certificate | 现有证据在固定源身份下内部一致 | benchmark 推理已经重跑 |
| B：本地求解器重建 | 从固定公开输入重建 TSP、OR-Debug、mixed 输出 | 本地求解器路径在固定版本下可重建 | 公开干净克隆也能运行 |
| C：外部推理重放 | 使用冻结 provider、模型、预算和官方方法适配器重发请求 | 特定日期和协议下的 API 重跑 | 无凭据复现或各方法协议完全同质 |
| D：发布重建 | 从许可明确、rights-safe 的递归干净克隆完成 A/B，并说明 C 的授权运行方式 | 公开离线可复现性 | 无需用户凭据和商业求解器许可的完整在线重放 |

离线完整性不能替代本地求解器重建，已有结果汇总也不能替代外部推理重放。

## 当前命令图

### A. 离线合同与 certificate

现有记录保存了以下 40-test 命令：

```text
PYTHONPATH=scripts:. python3 -m unittest -v \
  tests.test_evaluate_tsp_constraint_confirmation \
  tests.test_or_debug_confirmation_inference \
  tests.test_mixed_skill_router \
  tests.test_mixed_skill_execution \
  tests.test_audit_mixed_skill_confirmation \
  tests.test_prepare_mixed_skill_confirmation_bundle \
  tests.test_typed_count_repair_certificate \
  tests.test_certify_typed_count_repair
```

它只能称为定向合同测试。列出的测试中，目前只有四个 mixed-router 测试模块已被 Git 跟踪。count 的确定性最小修复可由以下入口重建，但脚本和输入当前也未跟踪：

```text
python3 scripts/certify_typed_count_repair.py
```

该 launcher 要求输出不存在，并在第一次导入 verifier 前核对完整本地源码闭包。它不调用模型、API、solver、native evaluator 或 VM。

### B. 本地 benchmark 重建

TSP 的局部链为：

```text
python3 scripts/prepare_tsp_constraint_confirmation.py --dry-run
python3 scripts/prepare_tsp_constraint_confirmation.py
python3 scripts/run_tsp_constraint_confirmation.py
python3 scripts/evaluate_tsp_constraint_confirmation.py
```

它依赖固定 OPT-Engine 源、冻结计划、Gurobi CLI 和单独取得的许可。三个脚本均未跟踪；而且没有找到生成最终 `tsp-constraint-confirmation-root-closure-v1` 的脚本，所以即使局部链运行成功，也还缺 headline closure 的确定性生成器。

OR-Debug 的局部链为：

```text
python3 scripts/run_or_debug_confirmation_methods.py
python3 scripts/evaluate_or_debug_confirmation.py
```

它依赖固定 `solver-in-the-loop` 数据、Gurobi 13.0.1、冻结 split/plan 和空输出位置。两脚本均未跟踪。当前本地能读取固定 commit 和 dataset，但 `git submodule status` 仍返回 `-` 前缀；这不能替代递归干净克隆验证。

mixed-router 的三个脚本均已跟踪：

```text
python3 scripts/prepare_mixed_skill_confirmation_bundle.py
python3 scripts/run_mixed_skill_confirmation.py
python3 scripts/audit_mixed_skill_confirmation.py
```

但它们依赖当前未形成 rights-safe 发布闭包的 TSP/OR-Debug direct outputs。现有 bundle/output 还包含需要投影掉的题面或 repair object，因此这仍只是局部链。

### C. 外部方法重放与聚合

现有 common-40 汇总入口是：

```text
python3 scripts/summarize_external_common40.py --check-readiness
python3 scripts/evaluate_bind_common40_union.py
python3 scripts/evaluate_coe_common40_union.py
python3 scripts/summarize_external_common40.py
```

这些命令只重新评价和汇总已经存在的运行记录，不会生成新的 BIND 或 CoE 模型输出。真正的推理重放还需要冻结 provider、模型、请求预算、官方代码适配器、安全执行后端和 solver。三个显示出的评价/汇总脚本均未被 Git 跟踪。

OptiTrust 当前只有带日期的官方渠道可用性审计。没有找到可重放的审计 producer，也没有找到经过核实的作者可运行包，因此只能保留 `artifact unavailable under audited channels`，不能用论文数字填充复现结果。

## 缺少精确 producer 的 headline 组

以下组没有找到会生成当前 headline schema 的脚本：

- TSP 最终 root closure；
- OR-Debug group endpoint sensitivity；
- OptiTrust 官方 artifact 可用性复核；
- Figure 2 source-data audit；
- proposal provenance inventory；
- matched-acquisition power analysis；
- fresh common-protocol estimand audit；
- component identifiability audit；
- component power/unit inventory；
- release-readiness delta；
- targeted offline verification 报告本身。

其中部分是理论设计或元数据审计，本来不需要重跑模型；但仍应有确定性生成器，或者在发布文档中明确标记为不可机械重建的人工审计记录。

## 发布前必须闭合的动作

1. 为 16 组 headline evidence 建立 producer、测试、最小依赖和预期 hash 的明确 allowlist；
2. 为上述 11 组补确定性 producer，或降低其“可重建”表述；
3. 把 TSP/OR-Debug/external/count 的 10 个未跟踪关键脚本纳入逐文件内容与权利审查；
4. 按四个重建层拆分静态闭包中的 83 个未跟踪 Python 文件，消除 `__init__` 带来的非必要闭包后再形成最小 tested allowlist；
5. 以 metadata-only 投影替换四个正文/repair-bearing artifact；
6. 补全 provider、Gurobi/native 和官方适配器环境说明，凭据始终留在仓库外；
7. 建立一个分层的 paper reconstruction command contract，支持 readiness/dry-run、不可变输出和 expected-hash 核验；
8. 最终从递归干净克隆执行 A/B 层并记录实际 hash；C 层单独作为需要用户凭据的授权重放。

本审计没有执行网络、模型/API、solver、native evaluator 或 VM 调用，没有读取请求正文、响应正文、evaluator-only 答案或凭据，也没有修改 Git index、历史、许可证、submodule 或远程仓库。
