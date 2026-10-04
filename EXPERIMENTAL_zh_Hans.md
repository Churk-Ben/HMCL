# HMCL 实验版渠道（非官方）

> [!IMPORTANT]
> **本项目并非官方项目。**
> 本仓库是由社区维护的 HMCL 实验性下游分支，与 [HMCL-dev/HMCL](https://github.com/HMCL-dev/HMCL) 没有任何
> 隶属关系。此处发布的构建可能随时新增或移除功能，且**不**受 HMCL 官方团队支持。如需官方启动器，请访问
> <https://github.com/HMCL-dev/HMCL> 或 <https://hmcl.huangyuhui.net>。

第一次使用请先完整阅读本文档。

## 这是什么

本 fork 以相当激进的策略跟随上游：频繁合并上游 `main`、提前集成尚未合并的上游 PR，并通过自有的
`experimental` 渠道发布构建。因此：

- 功能可能在版本之间出现或消失；
- 当上游采用不同实现、或某个被跟踪的 PR 被上游合并后，本仓库对应的功能可能被移除；
- 不提供任何稳定性保证。

如果你需要稳定、由官方支持的启动器，请使用官方项目。

## 更新渠道

启动器在“稳定版 / 开发版”之外，新增了一等公民级别的**实验版**渠道。

| 项目 | 取值 |
| --- | --- |
| 渠道标识 | `experimental` |
| 显示名称 | 实验版 |
| 产物命名 | `HMCL-<主版本>-<build number>.exp.<短SHA>.<扩展名>` |
| Linux 包名 | `hmcl-exp` |
| Linux 命令 | `hmcl-exp` |
| Linux 实例目录 | `$HMCL_USER_HOME/local-exp` |
| 更新元数据 | 最新 Release 的 `update-exp.json` |

实验版构建**锁定在实验版渠道**（类似 Canary 渠道）：渠道选择项不可切换，应用内也没有降级通道。
如需回到稳定版或开发版，请卸载本 fork 后安装官方版本。

## 分支模型

| 分支 | 用途 |
| --- | --- |
| `main` | 上游 `HMCL-dev/HMCL` 的 `main` 镜像，不在此开发。 |
| `experimental` | 集成分支与默认分支，发布从此构建。 |
| `pr/<编号>-<slug>` | 每个被跟踪的 PR 一个分支。 |
| `workspace/<名称>` | 自动化维护分支（上游同步、每日聚合），以 PR 形式合并进 `experimental`。 |

被跟踪功能的生命周期：

1. 功能位于 `pr/*` 分支并集成进 `experimental`。
2. 当对应 PR 被上游合并后，本仓库删除自身实现与分支。
3. 定期把上游 `main` 合并进 `experimental`，被删除的功能改由上游提供。

## 发布策略

计划由自动化工作流**每天**发版，同时保留手动触发。每次发布可在上游 `main` 之上聚合少量高优先级的上游
PR，并叠加本 fork 自身的改动。具体的选取规则以及如何手动增减，仍在定义中。

## 参与贡献

欢迎社区贡献，但请注意合并策略较为激进，功能可能短命。

- 功能开发：向 `experimental` 发起 PR。
- 分支命名：功能用 `pr/*`，自动化维护用 `workspace/*`。
- 若上游采用了不同方案，你的改动可能被重构或移除。

## 回到官方启动器

1. 卸载本 fork（例如 `sudo dnf remove hmcl-exp`）。
2. 从 <https://hmcl.huangyuhui.net/download> 安装官方版本。
3. 如需保留账号与设置：它们位于 `~/.local/share/hmcl`，与官方启动器共用；除非确实想重置，否则不要删除该目录。
