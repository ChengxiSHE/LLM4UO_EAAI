# 前瞻研究程序决策包

日期：2026-10-15  
状态：**方案A已于2026-10-15获真人确认，进入分阶段实施**

## 需要解决的核心问题

当前研究已经证明 authored proof-carrying skills 能够在 TSP 和 OR-Debug
上显著提高最终建模准确率，但尚未证明：

1. separating-witness 形式的反馈能提高自动技能构造；
2. semantic verification、resource admission、complexity control 和
   selective routing 各自具有可识别的经验作用；
3. 当前方法在与 BIND、CoE 相同的 fresh protocol 下仍具有竞争力。

这三个问题不能用同一批 benchmark rows 和一张六臂准确率表解决。
自动构造的实验单位是 typed proposal；复杂度控制的单位是一次独立
library selection；路由的单位是可能产生零、唯一或多重命中的公开
envelope；最终性能比较的单位才是 benchmark identity 或 lineage group。

## 三个方案

### A. 分阶段、多实验单位的前瞻程序（推荐）

分别执行 proposal-level acquisition、component-specific intervention 和
benchmark-level common comparison。每一阶段拥有独立分母、冻结规则和论文
主张。该方案能够真正检验自动构造机制，同时保留当前 authored-skill
故事作为失败时的可信回退。

代价是需要构造新的 proposal 和 routing-envelope population；38题不能单独
支撑广义优越性结论；如果不能产生独立 library-selection episode，MDL只能
保留为理论设计原则。

### B. 仅在38道fresh题上做六臂factorial（不推荐）

这个方案表面简单，但会把benchmark题目错误地当成skill proposal和library
selection的重复样本。38题在中等Holm规划情形下功效仅12.09%，且已知family
题目无法识别zero/multiple-match routing效果。因此它不能支持“四个组件均
必要”的主张。

### C. 停止自动构造主张，直接以authored skills投稿（保留为失败回退）

当前TSP和OR-Debug结果足以支持一个有边界的可信技能工程论文，但自动
proposer是负结果，fresh共同协议仍为空。该方案科学上安全，方法吸引力和
顶会新颖性弱于成功的方案A。

## 推荐方案A

### Stage 0：共同冻结

冻结atomic fact ledger、typed grammar、semantic oracle、resource checker、
模型与endpoint identity、请求/token/output/retry预算、custody与missingness
规则、serializer和parser。在这些对象完成内容寻址前，不生成任何treatment
payload或模型请求。

### Stage 1：八对acquisition canary

一个合法单位是“被拒绝的typed proposal + 冻结version-space state + parent
lineage”。八个单位按结果无关规则选取；现有model proposal与确定性synthetic
repair seed必须分层标注，不能混称model-generated。

flat arm按canonical顺序收到相同atomic fact IDs；treatment arm收到相同fact
IDs及verifier导出的partition结构，不得获得winner、winner hash、minimum
repair或endpoint label。teacher每轮选择使最大outcome cell最小的合法witness，
SHA-256字典序打破平局。两臂严格匹配模型、schema、轮数、输出、重试和token
预算。

主结果是共同预算内是否生成semantic-valid且resource-valid的skill。至少2个
净treatment-only wins、0个control-only win且无全局安全失败，只是进入正式
扩样的工程门，不是显著性结论。

### Stage 2：独立acquisition confirmation

从不包含canary及其后代lineage的新proposal population冻结138对单位。在
单侧alpha=.05、`r=.30,q=.70`规划情形下，该规模提供至少80% exact power。
报告满分母paired effect、discordant counts、exact paired test、confidence
interval以及请求/token成本。

若结果为正，允许声称separating-witness organization在冻结grammar、verifier、
model和budget下提高自动typed-skill acquisition。若结果为负，必须保留并撤销
自动演化主张，论文回到authored-skill方法线。

### Stage 3：组件程序

- semantic和resource使用同一prospective candidate pool，但分别记录matched
  offline outcomes；绝不取消外层parser/compiler/hard safety caps。
- routing另建answer-free envelope population，预设zero、unique、multiple
  matches，以及paraphrase、schema shift和new-family条件。
- complexity只有在能够重复独立common-pool library selection时才做因果主张；
  否则MDL只作为理论设计原则。
- confirmatory component contrasts使用Holm FWER .05。四对比中等规划情形需
  至少205个合法单位达到80%功效，否则明确标为exploratory。

### Stage 4：fresh common protocol

在已绑定的38道larger RCPSP/VRPTW题上运行Base、strong static、full method、
安全的关键消融、BIND first round和CoE safe-adapter。主表使用共同公开事实、
DeepSeek-V4-Flash和method-native budgets；equal-budget、author-native及BIND
answer-bearing final必须分表。

该阶段支持size generalization、compatibility和mechanism confirmation。除非
增加更大的独立cohort或第二条source lineage，否则不写成广义leaderboard
优越性结论。

## 论文主张升级路径

1. 当前证据：authored proof-carrying skills在两个来源提高建模准确率。
2. Stage 2为正：增加自动知识构造机制的因果主张。
3. Stage 3为正：只为具有合法单位和Holm-controlled结果的组件增加经验主张。
4. Stage 4：增加fresh共同协议下的规模外与外部方法兼容性证据。
5. 所有阶段均不证明普遍自然语言正确性、unrestricted RSI或分布无关的零回退。

## 当前实施边界

本文件已经完成方案比较和推荐设计。用户于2026-10-15明确确认：
“批准方案A作为G07–G09前瞻实验的整体架构。”架构门因此解除，但每个阶段仍
必须分别建立内容寻址计划、不可变预算、安全上限、custody和终态账本；不得把
该确认解释为无限请求、答案泄露、不安全候选执行、结果驱动换样或有利重跑。
实施顺序固定为Stage 0--1 acquisition canary，之后按预设工程门决定是否进入
Stage 2；Stage 3和Stage 4各自使用独立计划与正确统计单位。

机器可读版本：
`experiments/prospective_research_program_decision_20261015.json`。
