# Open EDA Tools · WSL 本機 EDA 工作台

**不是網頁，也不需要雲端 server。** VS Code 寫 RTL / testbench；原生桌面工作台執行模擬、檢查、合成、STA、APR、DRC / LVS，並開啟專用 GUI 看波形與實體電路。

整合程式是 MIT；工具包下載自固定版本的 LibreLane，驗證 SHA-256 後執行。不包含商業 EDA、TSMC/NDA 資料或從商業工具複製的 UI。

## 開始使用（Ubuntu 22.04+ / WSL2 + WSLg）

建議放在 **WSL Linux 檔案系統** `~/Open_EDA_Tools`，不要放 `/mnt/c`；大量小檔案的 PDK/工具解壓縮會慢很多。

```bash
git clone https://github.com/xizhuwang/Open_EDA_Tools.git
cd Open_EDA_Tools
bash eda setup         # 首次下載約 1.4 GB；驗證、解壓縮，不自動 sudo
bash eda gui           # 原生桌面工作台；不是 HTTP 網頁
```

Windows 安裝 VS Code 與 WSL 擴充功能，在此目錄執行 `code .`。若尚未有 Git / Python / Tk 或字型，請先依 [WSL 環境說明](docs/WSL.md) 準備。**初次實體流程還會下載開放 PDK**，需要網路、額外磁碟與時間；不是 git clone 後離線零安裝。後續在工具與 PDK 齊備時本機執行。

## 功能對應與邊界

| 熟悉的工作類型 | 實際執行的工具 | 這份專案提供什麼 |
|---|---|---|
| VCS 類 RTL simulation | Icarus Verilog | RTL + testbench 編譯、執行、自動檢查、VCD；不是完整 SystemVerilog / UVM 相容 |
| Verdi 類 waveform debug | GTKWave + VS Code | 階層訊號、搜尋、游標、縮放、數值與 VCD/FST 波形；不是 FSDB 或完整 source tracing |
| SpyGlass 類 static checks | Verilator + Yosys + 結構 CDC review | 語法、位寬、latch、未驅動、多重驅動、組合迴圈與跨時脈資料錐；**不是 CDC/RDC sign-off** |
| DC 類 synthesis | Yosys / ABC，由 LibreLane 管理 | 技術映射至 SKY130 真實開放 standard-cell library，netlist / cells / area |
| STA / PPA | OpenROAD 內 OpenSTA + OpenRCX | 真實 Liberty / SDC / corners；多條 setup / hold path、slack，佈線後 SPEF 與功耗估計 |
| ICC2 類 physical design | OpenROAD / LibreLane Classic | floorplan → PDN → placement → CTS → routing → RC extraction → GDS；原生 OpenROAD GUI |
| Calibre 類 physical checks | Magic DRC / extraction + Netgen LVS + KLayout | 真正依開放 PDK 規則檢查幾何與連通性；不是 foundry-certified Calibre deck / sign-off |

這是**可執行的開源 ASIC 工作流程**，不是上述商業產品的完整替代品。支援程度受工具、語言、PDK 與設計規模限制。完整流程不代表任意 RTL 都能自動達到 timing / DRC closure。

## 桌面使用方式

1. `Open` 選取 `project.json`；預設是可自動驗證的 8-bit counter。
2. 左側檔案雙擊後用 VS Code 編輯；按 `Sim`，再開 GTKWave。
3. `Lint` 跑 Verilator 與 Yosys 結構檢查。`CDC Review` 產生 `cdc.json`，人工審查 crossing 與 2FF 候選。
4. `Synth` 只跑到映射合成；`STA` 跑到 pre-PnR STA；`APR` 跑到 route + RC extraction + post-PnR STA。
5. **`DRC / LVS` 是從 RTL 開始的完整 physical flow**，含 Magic / Netgen 檢查。`Full` 先跑 sim / lint / CDC review，再跑這個完整流程。
6. `PPA / Checks` 看原始 metrics，`Timing` 看多條 critical path 與實際 slack；選取路徑後到 `Detail` 看逐 cell 報告。來源 report 檔案全部保留，corner / timing units 以報告為準。
7. 由 `Run history` 切換舊的 simulation / physical 結果。OpenROAD 看 ODB 與 placement/routing，KLayout 看實際 GDS。視窗未出現時看對應 `*-viewer.log`。

按停止可取消整個工具 process group；運算放在背景執行緒，畫面只保留有限 log 行數。沒有持續動畫、瀏覽器、廣告或遠端程式碼上傳。每個專案一次一個計算工作。

## CLI / VS Code tasks

```bash
bash eda doctor
bash eda unit-test
bash eda test                      # 真工具 smoke / regression tests
bash eda run sim
bash eda view wave
bash eda run lint
bash eda run cdc
bash eda run synth
bash eda run sta
bash eda run apr --jobs 2 --timeout 3600
bash eda run verify                # RTL → GDS → DRC / extraction / LVS
bash eda view openroad
bash eda view layout
bash eda run full
bash eda report
```

其他專案：`bash eda gui --project /path/to/project.json` 或 `bash eda run verify --project ...`。`.vscode/tasks.json` 的預設任務使用 counter，請為自己的專案加上 `--project`。

## 真實製程、頻率與限制

預設 **SKY130A / sky130_fd_sc_hd**，counter 的 clock period 為 **20 ns / 50 MHz**。不是虛擬製程。SDC 中有實際 I/O delay、clock uncertainty、transition / load；不是從 RTL 層數猜測 slack。

`STA` 是 pre-PnR 的時序結果，不含實際繞線寄生；`APR` / `verify` 之後才有 extracted RC 與 post-route timing。Power 使用工具的預設切換活動模型；本版**未把 simulation VCD 自動注入功耗分析**，因此不可當作實測功耗或 workload-accurate 功耗。時序通過不代表產品所有 mode、corner、CDC、SI/PI、封裝與可靠度均通過。

`project.json` 的 `clock_period_ns` 與 SDC 要一致；**改 clock period 時兩個都要改**。`physical` 可增加 LibreLane 設定來調整 die、density、PDN 或 macro。不要把 NAND flash / SRAM 行為模型誤當實體 IP。

## SRAM 與自己的 RTL

提供原創 [1RW / 1R1W / 2RW 模型](models/sram/README.md)，參數化深度、位寬與 byte enables，行為有測試。它們是 RTL models，不含假造的 SRAM macro timing / area / GDS。欲使用硬巨集請讀 [專案與 macro 設定](docs/PROJECTS.md)。

## 可重現與隱私

每個專案 `.runs/<timestamp-id>/` 保存：

- `input/`：本次 RTL、TB、SDC 快照，編輯中的新內容不影響該次執行。
- `manifest.json`：來源 SHA-256、工具包版本、工具路徑、完整 argv、退出狀態。
- `console.log`、`summary.json`、`cdc.json`、LibreLane 原始 reports / resolved.json / state snapshots。
- 物理流程的 netlist、DEF、ODB、SPEF、LEF、GDS、SPICE 等產物（依實際完成階段）。

`.tools/`、`.pdks/`、`.runs/` 預設忽略，不推到 GitHub。RTL / TB / SDC 是可信任的本機輸入，**不是不可信程式的沙箱**：testbench 系統任務、Tcl、外部 include 或工具漏洞可能存取本機資料；不要執行陌生人提供的專案。bootstrap / PDK manager 會連網下載上游資產，沒有應用遙測或帳號系統。

## 文件

- [WSL 安裝、硬體需求與故障排除](docs/WSL.md)
- [專案設定、時序與 macro](docs/PROJECTS.md)
- [授權與商用注意事項](THIRD_PARTY_NOTICES.md)
- [實際驗證紀錄](docs/VALIDATION.md)
- [接到 Tiny Tapeout：成本、原創範例與官方模板交接](docs/TAPEOUT.md)

## Tiny Tapeout 製造準備

另提供 `examples/tiny_tapeout`，使用官方固定 I/O 介面的原創 counter。`TT Check` 檢查 elaborated ports，`TT Export` 交接到固定 commit 的官方 SKY template（含真正 counter checker），**不是直接把 generic GDS 標成可下線**。

```bash
bash eda gui --project examples/tiny_tapeout/project.json
bash eda run ttcheck --project examples/tiny_tapeout/project.json
bash eda tapeout --project examples/tiny_tapeout/project.json --out .exports/tt-counter
```

本工作台 generic toolchain 3.0.17 與查核日官方 SKY action 3.0.14 不同，正式提交必須跑當期官方流程／precheck／gate-level test，不能把本機開發檢查視為受理證明。沒有訂位、送件或付款功能；費用與優惠查核見 [TAPEOUT.md](docs/TAPEOUT.md)。

Independent project; no affiliation with Synopsys, Siemens, Cadence, LibreLane or the OpenROAD project. Commercial product names describe workflow categories only.
