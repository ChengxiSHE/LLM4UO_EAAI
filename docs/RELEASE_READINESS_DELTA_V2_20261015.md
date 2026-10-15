# 发布就绪度差分审计 v2

日期：2026-10-15  
状态：**not ready**

## 当前结论

本地论文证据的完整性继续提高，但公开发布的准备程度没有同步提高。加入本差分审计后，当前 paper manifest 绑定 46 个唯一文件，其中 Git 已跟踪 7 个、未跟踪 39 个、缺失 0 个。旧审计是 26 个文件中的 7/19；因此新增的 20 个证据文件全部尚未进入版本控制。

这不影响本地数值结论，却直接阻止“GitHub 已同步”“干净克隆可复现”或“artifact ready”的说法。

## 当前发布差距

| 项目 | 当前状态 | 发布含义 |
|---|---:|---|
| Manifest-bound files | 46 | 当前论文直接证据范围 |
| Git tracked | 7 | 仅少量证据存在于仓库历史 |
| Git untracked | 39 | 必须逐文件审查后通过 allowlist 加入 |
| Missing | 0 | 本机证据没有文件缺失 |
| Root license | 0 | 第一方代码和文档没有明确发布许可 |
| Tracked environment spec | `requirements-offline.txt` | 足以固定离线证据核验的四个 Python 包；尚未锁定 provider、Gurobi、native evaluator 与上游重建环境 |
| Initialized required submodule | 否 | OR-Debug 依赖尚未在当前检出中初始化 |
| Credential-free clean clone rebuild | 否 | 尚不能声称独立复现 |
| DOI/archive | 无 | 最终 Data/Code Availability 仍不可填写 |

paper manifest 本身不能对自己做哈希，因此还有三个清单外、但发布必须包含的未跟踪控制文件：paper manifest、goal audit JSON 和 goal audit 人读版。它们不能因为不在 45 个自绑定路径中而被遗漏。

## 正文、隐私和凭据扫描

对 44 个原有非发布路径及两个新增 metadata-only 发布审计路径进行 key-aware JSON 扫描和凭据字面模式扫描后：

- Bearer token、OpenAI 风格 key 和带引号 secret assignment 的匹配均为 0；
- 唯一检测到非空正文型字段的 manifest 文件是已被 Git 跟踪的 `experiments/mixed_skill_confirmation_bundle_20261014.json`；
- 该文件含 140 个 `records[].public_envelope.public_text` 值，应在公开版本中替换为身份、哈希、路由元数据及固定上游重建说明；
- 其他 JSON 中出现的 `credentials_read`、`reference_answers_read` 等字段是布尔审计元数据，字段名本身不等于正文泄漏。

该扫描只能排除明显字面风险，不能替代逐文件语义审查或法律许可判断。

## 清单外的已跟踪风险

两个文件位于被忽略的 `results/private/` 目录，但已经进入 Git 历史：

1. `tsp_constraint_confirmation_public_20261014.json`，包含 `public_text` 字段；
2. `tsp_constraint_confirmation_candidates_20261014.json`，不含该字段，但仍需内容与上游权利审查。

“路径名是 private”不能撤销已跟踪状态。公开发行前应明确排除或替换这两个路径，并由作者决定是否需要处理既有 Git 历史。

## 正确的发布策略

不能对当前工作区执行 bulk add。项目包含大量实验历史、私有输出、旧计划和未审查数据。安全策略应是：

1. 作者先选择第一方许可证；
2. 建立只包含论文必需文件的显式 allowlist；
3. 将 39 个未跟踪 bound paths 和三个控制文件逐一做内容、权限与来源审查；
4. 替换 mixed public-text bundle，并排除两个 tracked private paths；
5. 在已有离线 requirements 基础上补齐 provider、solver、native evaluator 与上游重建环境说明；
6. 在无凭据、无 private 目录和无本地 cache 的递归干净克隆中核验当前 manifest 的全部哈希与断言；
7. 通过后再归档、生成 DOI 并定稿 Data/Code Availability。

本轮只读审计没有修改 Git index、历史、许可证、发布文件或子模块状态。
