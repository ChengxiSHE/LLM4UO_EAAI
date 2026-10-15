# CoE官方artifact与许可证复核

日期：2026-10-15
状态：**官方代码可用；许可证与正式release package仍未核实**

## 复核结果

作者仓库仍明确将自身描述为论文“Chain-of-Experts: When LLMs Meet
Complex Operation Research Problems”的官方实现。当前可见根目录列出README、
requirements、controller和dataset等文件，但没有可见的`LICENSE`或等价根
许可证文件，GitHub资源栏也没有显示识别出的许可证。

官方releases页面显示没有任何release，因此没有可绑定的版本化发布包或release
asset。README仍要求用户安装`requirements.txt`并设置自己的API key；它说明
LPWP已上传、ComplexOR只有raw version，同时仍写明论文所述正式37个数据集
“will be released soon”。

## 对当前研究的影响

该结果不改变已完成的本地CoE复现。项目已经分别固定paper-era commit
`9d96bcc2f067177eb0e122b1aae8227748dc6830`和current commit
`afb89bf602690ea621f13a23c42722f20f653a43`，并披露安全适配器无法覆盖任意
生成代码的边界。本轮无需重新调用模型或求解器。

发布时应继续采用“固定上游URL与commit + 本项目adapter与聚合结果”的重建
方式。除非作者以后发布可验证许可，不应把CoE源码或数据vendor进本项目，也不
应暗示本项目可以替作者重新许可。

这是一条provenance和release边界，不是CoE方法效果差的证据。官方代码仍可用于
从固定上游重建；缺许可证只限制再分发方式。

## 边界

可用网页读取器没有提供当前默认分支的精确commit hash，因此本审计不声称线上
main与本地固定current snapshot逐字相同。未看到根许可证或GitHub许可证标识也
不是对所有潜在授权来源的法律意见。

官方来源：

- <https://github.com/xzymustbexzy/Chain-of-Experts>
- <https://github.com/xzymustbexzy/Chain-of-Experts/releases>
- <https://openreview.net/forum?id=HobyL1B9CZ>

本轮没有下载仓库归档或数据正文，没有读取请求、响应、凭据或evaluator-only
答案，也没有调用实验API、模型、求解器、native evaluator或VM。
