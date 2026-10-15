# Headline 重建 Python 静态闭包

日期：2026-10-15
状态：**保守静态投影；不是发布授权或完整运行时闭包**

机器可读路径与逐文件 SHA-256 位于
[`headline_static_python_closure_20261015.json`](../experiments/headline_static_python_closure_20261015.json)。

## 结果

从 13 个 headline 重建脚本和 9 个定向测试模块出发，递归解析仓库内 Python `import` 与 `from ... import ...` 后得到 121 个文件：

| 根目录 | 文件数 | 已 Git 跟踪 | 未跟踪 |
| --- | ---: | ---: | ---: |
| `llm4or/` | 93 | 31 | 62 |
| `scripts/` | 16 | 3 | 13 |
| `tests/` | 9 | 4 | 5 |
| 根目录 DCP reference modules | 3 | 0 | 3 |
| **总计** | **121** | **38** | **83** |

因此，即使把 13 个顶层入口补入 Git，当前仍不能得到完整 Python 执行闭包。大量核心 verifier、evaluation、count、OR-Debug 和辅助模块仍只存在于当前工作区。

## 分组 import-time 探针

将每个入口在独立 Python 进程中以非 `__main__` 模块导入，并把入口本身计入后，得到：

| 轴 | 入口/测试 | import-time + 入口文件 | tracked | untracked |
| --- | ---: | ---: | ---: | ---: |
| TSP | 4 | 74 | 23 | 51 |
| OR-Debug | 3 | 18 | 7 | 11 |
| Mixed | 7 | 27 | 27 | 0 |
| External common-40 | 4 | 11 | 6 | 5 |
| Count | 4 | 76 | 16 | 60 |

Mixed 的 Python import-time 闭包已经全部被跟踪，但数据投影、Gurobi、upstream revision 和运行时分支仍需单独验证。OR-Debug 的缺口相对集中。TSP 和 count 的大闭包主要来自两个审计入口的历史耦合：

- TSP preparation 通过 `object_feedback_pilot_inputs` 复用了固定读取/owner 功能，同时导入了 object transport、semantic review、provider 和 packing 模块；
- count terminal audit 导入历史 acquisition runner，从而带入 provider 与 preparation 栈；
- 相比之下，count certificate launcher 在校验源码 hash 后才延迟导入 verifier，import-time 只有入口自身，说明窄 trust root 是可行的设计方向。

External common-40 的 pytest 风格测试在当前环境无法导入，因为 `requirements-offline.txt` 没有 pytest；此前 11 条等价断言不能冒充原 pytest 文件已运行。

## 冻结证据实际绑定的源码集合

除 import 探针外，还从已经冻结的 plan 和 closure 中提取了显式 path/hash：

| 链 | 显式绑定 Python 文件 | tracked | untracked | 当前 hash 偏差 |
| --- | ---: | ---: | ---: | ---: |
| TSP confirmation union | 11 | 2 | 9 | 0 |
| OR-Debug confirmation union | 17 | 6 | 11 | 0 |
| Typed-count exact repair | 11 | 3 | 8 | 0 |
| Typed-count terminal audit plan | 432 | 89 | 343 | 0 |

TSP 的 11 个文件包括一个 `data/raw` 下的上游 evaluator、四个 launcher、两个测试以及四个 TSP 实现/评分模块。OR-Debug 的 17 个文件与 import-time 缺口基本一致。Exact-repair certificate 自己声明的 verifier closure 较小且边界清楚。

Count terminal plan 则存在相反问题：历史计划有意锁定全部 `llm4or/*.py` 及其审查面，导致当前终态审计继承 432 个项目 Python 身份，其中 343 个未跟踪。该做法适合证明“历史工作区没有悄悄换代码”，却不适合作为公开重建的最小闭包。正确处理应保留原计划作为 provenance，再建立一个单独、行为等价、只绑定实际终态验证输入和 verifier 的 slim projection；当前还不存在该 projection，不能提前宣称已经解决。

Mixed 终态 artifact 绑定了输入和 direct-output 身份，但没有给出完整 source-code manifest；external summary 只绑定汇总脚本，没有绑定完整推理与 official-adapter closure。因此最终 release 仍需要独立的分层代码 manifest。

## 未跟踪源码的初筛

83 个未跟踪 Python 文件共 669,532 bytes，全部可以被 Python AST 解析。对原始字节执行不输出字面值的三类凭据扫描，Bearer、OpenAI 风格 key 和带引号 secret assignment 命中均为 0。

这仍不能直接进入 allowlist：19 个文件含至少一个 500 字符以上字符串，共 23 个，最长 4,055 字符；16 个文件提到 private 或 evaluator 路径；没有文件出现 SPDX、Copyright 或 `Licensed under` 信号。长字符串可能是合法的 prompt、schema 或说明，也可能扩大披露面，必须逐文件做语义和权利审查。缺少文件级许可证头也不证明代码无权发布，但在根许可证尚未选择时不能默认已获公开许可。

## 解释边界

该闭包是保守静态结果：包的 `__init__.py` 可能急切导入某些单条命令实际不用的模块，因此 121 不是已经证明的最小集。反过来，静态 AST 也不能发现动态 import、子进程二进制、数据文件、实验计划、终态输入、上游仓库、provider 服务或求解器许可，因此 121 也不是完整运行时依赖集。

每条路径仍需独立检查：

- 是否真的属于一个或多个重建层的最小运行闭包；
- 是否包含第三方正文、答案、凭据或不应发布的派生对象；
- 是否有明确第一方或上游许可证；
- 是否应被固定为源码、从上游重建，或仅作为用户自备依赖；
- 是否有对应的测试和 expected hash。

下一步应按离线完整性、本地求解器、外部推理和发布重建四层拆分 83 个未跟踪文件，获得经过测试的最小闭包，而不是直接把 121 个文件批量加入 Git。

建议的依赖收敛方向是将固定文件读取、hash、canonical serialization、路径约束、独占写入和 owner/lock 机制提取成最小 evidence-I/O trust root，使各重建层只导入自身 verifier 与 backend。当前仅证明了耦合与候选方向，没有验证重构后的字节等价、锁语义或失败关闭行为，因此没有修改生产代码；任何替换都必须先保持这些行为和现有反例测试逐项等价。

本审计未运行网络、模型/API、solver、native evaluator 或 VM，未读取题目正文、响应正文、答案或凭据，也未修改 Git index、历史或远程仓库。
