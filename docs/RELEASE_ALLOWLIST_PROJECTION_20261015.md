# 论文发布 allowlist 投影

日期：2026-10-15
状态：**provisional；不授权 stage、commit 或 push**

## 结论

当前 46 个 paper-manifest 路径不能原样全部发布。结构审计将其中 42 个列为“可继续进行逐文件发布审查”的候选，将 4 个列为必须先生成安全投影或排除的路径。另有三个清单控制文件应进入最终发布，两个已跟踪的 `results/private` 文件应从公开树排除。

这里的“候选”不等于法律、隐私或语义审查已经通过，也不等于可以批量执行 `git add`。

## 必须替换或排除的四个 manifest 文件

| 当前文件 | 风险 | 建议发布投影 |
|---|---|---|
| `experiments/mixed_skill_confirmation_bundle_20261014.json` | 140 条上游 `public_text` | 题目身份、来源 revision、文本 hash、family、顺序和路由元数据；正文从固定上游重建 |
| `results/or_debug_confirmation_evaluation_20261014.json` | 含逐记录 corrected/released repair identity | 发布总分母、group membership hash、两种 endpoint、correction/regression 类型和终态 hash |
| `results/or_debug_confirmation_method_outputs_20261014.json` | 含逐记录 static/evolved repair object | 发布 membership hash、status/candidate count、route 和 output hash |
| `results/mixed_skill_confirmation_outputs_20261014.json` | mixed output 内含 OR-Debug repair object | 发布 route、status、direct/mixed output hash 和 exact-equivalence 结果 |

这些投影仍能支撑论文中的准确率、endpoint sensitivity 和路由等价性主张，同时不直接发布题面、repair identity 或完整 repair object。

## 可继续审查的 42 个候选

其余 42 个 manifest 路径没有发现大于等于 500 字符的正文型值，也没有匹配 Bearer token、OpenAI 风格 key 或带引号 secret assignment。它们主要是：

- 聚合结果、终态 closure 和证据 ledger；
- 理论、主稿、复现附录与引用；
- source-data 聚合 CSV；
- 候选/修复 certificate 和 metadata-only readiness audit；
- Data/Code Availability 与发布审计。

每个文件仍必须逐项通过：最小披露、来源权利、凭据与正文检查、最终 hash 重绑定、许可证归属和干净克隆重建。尤其是包含候选对象的 typed-count certificate，只能在确认其不包含参考答案或受限题面后发布。

## Manifest 外的发布控制和排除项

最终发布还必须明确加入 paper manifest、goal audit JSON 和 goal audit 人读版；它们因为自引用问题不在 46 个 self-bound 路径中。

两个已经被 Git 跟踪的 private 文件不得因目录名含 `private` 就被忽略：一个含上游题面，另一个含派生候选输出。二者默认从公开树排除，由作者另行决定是否需要处理既有 Git 历史。

## 下一发布动作

1. 作者选择第一方许可证；
2. 为四个受限 manifest 文件生成 metadata-only 投影，并让 paper manifest 改绑投影；
3. 对 42 个候选和三个控制文件逐一执行内容与权利审查；
4. 明确排除两个 tracked private 路径；
5. 补全执行与重建环境；
6. 仅对最终 allowlist 进行 stage；
7. 从无凭据递归干净克隆重建全部主张后再 commit、push 和归档。

本报告没有修改 Git index、历史、远程仓库、许可证或任何实验状态。
