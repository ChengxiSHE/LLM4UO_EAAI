# 理论驱动知识库的组件可识别性审计

日期：2026-10-15  
状态：**尚不可冻结或启动实验**

## 结论

当前知识库及其构造过程能够、也应该与理论框架结合。最合适的统一表述是：在一个版本化 skill library 上执行**带证明约束的结构风险最小化**。候选知识由有限的反例引导过程产生；语义与资源证明义务决定其能否进入候选库；描述长度控制选择复杂度；公开输入上的选择性路由决定知识何时部署；独立端点评价与序贯晋级规则决定新版本能否替代旧版本。

这种结合不是给已有工程步骤补充理论术语。理论必须改变方法的可执行规则，并产生可以失败的预测。当前框架中的五个理论部件分别对应：

1. 有限 CEGIS：反例应单调缩小冻结候选空间；
2. proof-carrying admission：未经语义和资源验证的候选不能晋级；
3. prefix-code/MDL 控制：候选或整库复杂度必须进入选择规则；
4. selective routing：只有唯一 guard 命中才部署，否则精确回退；
5. alpha-spent promotion：只有冻结候选在独立端点通过预设门槛才能改写版本。

现有证据已经说明这个框架可以解释和约束 TSP、OR-Debug、count 以及 mixed router 的行为。但它还没有因果识别验证、资源准入、复杂度控制和选择性路由各自带来的平均收益。因此论文现在可以声称“理论指导的可审计知识工程”，还不能声称“四个组件均被实验证明必要”。

## 为什么不能只做一张六臂准确率表

四个组件发生在不同层次，实验单位也不同：

| 部件 | 理论作用层 | 合法实验单位 | 主要结果 |
|---|---|---|---|
| 语义验证 | 候选准入 | 冻结候选 proposal | 错误准入、旁路改变、端点回退 |
| 精确资源准入 | 候选准入与执行 | 冻结候选 proposal | hard-cap 命中、不可用、端点准确率 |
| 复杂度控制 | 整库选择 | 独立 library-selection episode 或 lineage group | 库长度、promotion-confirmation gap、端点准确率 |
| 选择性路由 | 部署 | 包含零/单/多重命中的冻结公开 envelope | 覆盖、歧义、回退、correction/regression |
| Full vs static | 端到端价值 | benchmark identity/group | 满分母建模准确率与成本 |

同一批 38 道 RCPSP/VRPTW 题适合比较 Base、static 和 full 的端点表现，也能发现很大的组件失效。但如果所有题都由已知 family guard 唯一命中，那么“关闭路由”和“保留路由”会得到完全相同的处理，路由价值没有统计对比。类似地，复杂度控制选择的是一个 library；把 38 个题目当成 38 次独立的 library 选择，会产生伪重复。

## 四个可执行的组件干预

### 1. 去除语义验证

从同一个内容寻址候选池中移除语义 proof obligation，但保留不可移除的 parser、compiler、资源 hard cap 和 endpoint scorer。完整系统拒绝而消融系统接受的候选只能在隔离的离线 evaluator 中评分，不能部署。主要比较错误准入率、collateral change、regression 和晋级后的端点准确率。

现有 count proposer 通过 20,977 个语义赋值后仍在资源项失败，证明“某一类检查通过不等于候选可用”；它不是 matched no-verifier 消融，不能估计验证器的平均因果收益。

### 2. 去除方法层资源准入

移除方法自己的预测性资源 gate，同时保留 evaluator 的绝对变量、约束、非零元、字节、内存和时间上限。触发 hard cap 的候选直接计错，不能通过真正取消安全限制来制造对照。主要结果是 cap-hit、resource rejection、unavailable mass 和满分母端点准确率。

### 3. 去除复杂度控制

两臂接收完全相同的候选池、硬验证规则、producer 预算和 promotion 数据；唯一变化是将预先固定的 MDL/prefix-code 系数设为零。比较最终 library 长度、开发到确认的泛化差、以及等预算 confirmation accuracy。该实验必须以独立的构库 episode 或 lineage-separated group 为单位。当前 Occam 界只说明为何应做这个比较，不能替代经验结果。

### 4. 去除选择性路由

固定同一组 skills，将 exactly-one + fallback 替换为预先规定的 forced-family 或 relaxed-guard 策略。评价集必须专门包含零匹配、唯一匹配和多重匹配机会，并覆盖 paraphrase、schema shift 和新 family。所有臂仍保留外层安全 cap；危险路径仅离线评分。现有 mixed router 的 2,985/2,985 等价性证明已知 envelope 上不会破坏旧行为，但没有提供路由干预的对照。

## 统计与样本量边界

四个 confirmatory contrast 共同使用 Holm familywise alpha 0.05；保守规划可按每项 alpha=0.0125。对现有 38 题，用单侧 exact conditional McNemar/sign test 得到：

| discordance rate `r` | `q=.65` | `q=.70` | `q=.75` | `q=.80` |
|---:|---:|---:|---:|---:|
| .20 | 3.1% | 5.6% | 9.5% | 15.4% |
| .30 | 6.5% | 12.1% | 20.8% | 33.2% |
| .40 | 9.3% | 17.8% | 30.8% | 48.0% |
| .50 | 11.8% | 23.2% | 39.9% | 60.0% |

这里 `r` 是两臂不一致的概率，`q` 是在不一致题上 full 获胜的概率。即使零回退，也至少需要 7 个 corrections 才能让单项原始单侧 p 值低于 .0125。38 题因此可用作规模外确认和机制诊断，但不足以同时确认四个中等效应。候选准入、整库选择和路由必须分别按自己的实验单位扩样，最终端点结论还需要更大的独立 cohort 或第二条 source lineage。

## 对论文 methodology 的具体包装

论文的方法不应写成“让 Codex 自己迭代”。可以写成以下受控算法：

> **Benchmark-Grounded Proof-Carrying Knowledge Compilation** maintains a versioned library of typed modeling skills. Development failures induce finite candidate transformations; immutable semantic and resource checkers issue proof obligations and counterexamples; a label-independent description code regularizes library selection; an exactly-one public router confines deployment; and an independently scored, alpha-controlled promotion rule commits a new library version only when endpoint corrections exceed regressions under the frozen denominator.

这个叙事的贡献点是把知识获取、验证、选择、路由和版本晋级连接成一个可执行、可审计、可证伪的过程。BIND、CoE、OptiTrust 或其他 agent 可以作为候选知识 producer 接入，但必须经过相同 admission 和 endpoint；兼容性因此来自接口与证书，而不是假设任何 producer 都会带来提升。

## 现在可说与不可说的结论

可以说：

- 当前知识库是理论约束的版本化系统，不是无结构 prompt 集合；
- TSP 与 OR-Debug 已证明 authored proof-carrying skills 能在各自冻结端点提高建模准确率；
- mixed router 已证明已知 envelope 上的组合不会改变直接 family 输出；
- count 反例证明语义与资源义务之间存在真实交互，验证失败会阻止错误晋级。

暂时不能说：

- 四个组件都被因果证明必要；
- 38 题足以确认四个中等大小的组件效应；
- 已知 envelope 的路由等价性证明了分布偏移鲁棒性；
- 理论复杂度界已经带来经验准确率提升；
- 自动 proposer 已经优于 flat feedback 或 authored skill。

## 后续闭环顺序

1. 冻结共同候选池及 proposal-level 语义/资源对照；
2. 冻结 library-level MDL 选择对照，并以独立构库 episode 或 lineage group 评价；
3. 单独构造不含答案的 routing shift/ambiguity cohort；
4. 在 38 题上做 Base/static/full 和描述性的安全组件分析；
5. 根据 pilot 的真实 discordance 扩充独立端点样本，再进行四项 Holm-controlled confirmatory tests；
6. 将所有拒绝、弃答、hard-cap 和回退保留在预设分母中。

在候选池、路由偏移集、复杂度编码、multiplicity plan 和 custody 尚未冻结前，本审计不授权 prepare、freeze、API dispatch 或执行不安全消融。
