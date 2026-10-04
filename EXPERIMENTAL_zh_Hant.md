# HMCL 實驗版頻道（非官方）

> [!IMPORTANT]
> **本專案並非官方專案。**
> 本倉庫是由社群維護的 HMCL 實驗性下游分支，與 [HMCL-dev/HMCL](https://github.com/HMCL-dev/HMCL) 沒有任何
> 隸屬關係。此處發布的建置可能隨時新增或移除功能，且**不**受 HMCL 官方團隊支援。如需官方啟動器，請前往
> <https://github.com/HMCL-dev/HMCL> 或 <https://hmcl.huangyuhui.net>。

第一次使用請先完整閱讀本文件。

## 這是什麼

本 fork 以相當激進的策略跟隨上游：頻繁合併上游 `main`、提前整合尚未合併的上游 PR，並透過自有的
`experimental` 頻道發布建置。因此：

- 功能可能在版本之間出現或消失；
- 當上游採用不同實作、或某個被追蹤的 PR 被上游合併後，本倉庫對應的功能可能被移除；
- 不提供任何穩定性保證。

如果你需要穩定、由官方支援的啟動器，請使用官方專案。

## 更新頻道

啟動器在「穩定版 / 開發版」之外，新增了一等公民等級的**實驗版**頻道。

| 項目 | 取值 |
| --- | --- |
| 頻道識別 | `experimental` |
| 顯示名稱 | 實驗版 |
| 產物命名 | `HMCL-<主版本>-<build number>.exp.<短SHA>.<副檔名>` |
| Linux 套件名 | `hmcl-exp` |
| Linux 指令 | `hmcl-exp` |
| Linux 實例目錄 | `$HMCL_USER_HOME/local-exp` |
| 更新中繼資料 | 最新 Release 的 `update-exp.json` |

實驗版建置**鎖定在實驗版頻道**（類似 Canary 頻道）：頻道選項無法切換，應用內也沒有降級通道。
如需回到穩定版或開發版，請移除本 fork 後安裝官方版本。

## 分支模型

| 分支 | 用途 |
| --- | --- |
| `main` | 上游 `HMCL-dev/HMCL` 的 `main` 鏡像，不在此開發。 |
| `experimental` | 整合分支與預設分支，發布從此建置。 |
| `pr/<編號>-<slug>` | 每個被追蹤的 PR 一個分支。 |
| `workspace/<名稱>` | 自動化維護分支（上游同步、每日聚合），以 PR 形式合併進 `experimental`。 |

被追蹤功能的生命週期：

1. 功能位於 `pr/*` 分支並整合進 `experimental`。
2. 當對應 PR 被上游合併後，本倉庫刪除自身實作與分支。
3. 定期把上游 `main` 合併進 `experimental`，被刪除的功能改由上游提供。

## 發布策略

計畫由自動化工作流**每天**發版，同時保留手動觸發。每次發布可在上游 `main` 之上聚合少量高優先級的上游
PR，並疊加本 fork 自身的改動。具體的選取規則以及如何手動增減，仍在定義中。

## 參與貢獻

歡迎社群貢獻，但請注意合併策略較為激進，功能可能短命。

- 功能開發：向 `experimental` 發起 PR。
- 分支命名：功能用 `pr/*`，自動化維護用 `workspace/*`。
- 若上游採用了不同方案，你的改動可能被重構或移除。

## 回到官方啟動器

1. 移除本 fork（例如 `sudo dnf remove hmcl-exp`）。
2. 從 <https://hmcl.huangyuhui.net/download> 安裝官方版本。
3. 如需保留帳號與設定：它們位於 `~/.local/share/hmcl`，與官方啟動器共用；除非確實想重置，否則不要刪除該目錄。
