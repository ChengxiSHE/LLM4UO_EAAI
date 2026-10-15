# 复现环境合同审计

日期：2026-10-15
状态：**环境缺口已绑定，尚不能证明clean-clone复现**

## 结论

当前`requirements-offline.txt`在其声明范围内是有效的：它固定了用于离线
论文证据核验的Python 3.11.16以及NumPy、SciPy、jsonschema和scikit-learn。
它从未承诺覆盖provider、求解器、native evaluator、完整测试或绘图环境。

因此不能把“离线四包已锁定”写成“整个项目环境已锁定”。当前shell也不能
替代正式环境证据：它运行Python 3.10.1，NumPy为2.2.6，缺少SciPy、
scikit-learn、psutil、pytest、cpmpy和gurobipy；虽然安装了PyYAML、OpenAI
SDK和requests，但这些版本没有进入项目锁文件。该差异不推翻已有的Python
3.11离线核验，只说明当前shell本身不是clean-clone复现环境。

## 代码依赖面

对`llm4or/`、`scripts/`和`tests/`中Python源码进行有界字面扫描，发现41个
文件提及cpmpy、43个提及Gurobi、32个提及psutil、1个提及PyYAML、240个
提及pytest、1个提及scikit-learn。这些是依赖审查线索，不等于所有文件都应
进入公开release，也不证明import-time可达性。

## 求解器和子模块

稿件记录的求解器为Gurobi 13.0.1，其商业许可证必须由复现者自行提供。
当前shell能定位`gurobi_cl`，但没有gurobipy；本审计没有执行二进制或读取
许可证内容。`vendor/solver-in-the-loop`固定在commit
`c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010`，当前状态前缀为`-`，即子模块
尚未初始化。固定commit只证明上游身份，不证明递归克隆后已经成功重建。

## 必须拆分的五层环境

1. **离线证据层**：Python 3.11.16、现有四包、无凭据核验命令。
2. **测试与静态重建层**：pytest、psutil、PyYAML及明确测试子集。
3. **solver/native层**：cpmpy、Gurobi 13.0.1兼容性、无泄漏license preflight、
   初始化子模块和平台特定sandbox要求。
4. **provider层**：实际HTTP/SDK精确版本、无凭据配置schema、request/retry/
   ledger/concurrency合同以及离线replay路径。
5. **图件层**：持久化Python或R选择、绘图依赖和PDF QA命令。

不应把当前shell里观察到的包一次性追加到一个总requirements文件。这会把
商业求解器、平台相关native依赖、provider依赖和离线核验混为一个无法兑现的
环境声明。正确的下一产物是经架构确认的分层环境规范与重建命令图，然后从无
凭据递归clean clone实际执行全部适用层。

机器可读审计：
`experiments/reproduction_environment_contract_audit_20261015.json`。

本审计没有联网、安装包、初始化子模块、执行求解器、读取许可证或凭据，也没有
调用模型、API、native evaluator或VM。
