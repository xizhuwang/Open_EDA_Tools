# 自己的專案

複製 `examples/counter` 到自己的目錄，修改 `project.json`。RTL、testbench、SDC、include 檔案必須放在此專案資料夾內，以相對路徑列出；逃出目錄的 symlink / `../` 不允許。`support_files` 用來列入 `.vh` 等快照檔，不會自動當 RTL 編譯。

```json
{
  "top": "my_core",
  "testbench_top": "tb",
  "clock": "clk",
  "clock_period_ns": 10,
  "rtl": ["rtl/my_core.v", "rtl/block.v"],
  "testbench": ["tb/tb.v"],
  "support_files": ["constants.vh"],
  "sdc": "constraints.sdc",
  "pdk": "sky130A",
  "scl": "sky130_fd_sc_hd",
  "physical": {"DIE_AREA": [0, 0, 200, 200]}
}
```

testbench 建議使用 `$fatal(1, ...)` 在 mismatch 時終止，並加入模擬 timeout。工作台只知道工具退出碼；**不會幫未寫 checker 的 testbench 宣稱功能正確**。使用 `$dumpfile("dump.vcd"); $dumpvars(0, tb);` 才會產生波形。Icarus 支援部分 SV 語法，但 lint / synthesis 的語言子集不同；預設以可合成 Verilog 為主。

## Timing 與 Power

`clock_period_ns` 用於 GUI 與 flow；實際 SDC 則用於 STA。兩者必須一致。本版不自動重寫使用者 SDC，避免破壞多 clock / false path 等意圖。自己設定 input/output delay、loads、clock uncertainty、generated clocks、時序例外與 reset policy。

真實 STA 數字需要實際 library、corner、SDC，post-route 還需 SPEF。`Timing` 頁的 slack 與 path detail 都取自工具 report；沒有工具 report 就是未產生，不提供替代的假數字。

功耗是 OpenSTA 在其 Liberty / activity 假設下的估計；預設未自動匯入使用者 VCD。需要 workload-accurate 分析時自行配置 upstream 支援的 activity flow，並核對 scope、activity coverage、clock 與 time window；不可把預設 power 直接當實測。

## Physical stages

- synth: `LibreLane Classic --to Yosys.Synthesis`
- sta: `--to OpenROAD.STAPrePNR`
- apr: `--to OpenROAD.STAPostPNR`（route / RC extraction 後）
- verify: 不截斷 Classic，執行 streamout / Magic DRC / extraction / Netgen LVS 與 closure check。

每個按鈕都是**新的快照、新的 run**，不是把不同 RTL 或不同次結果拼在一起。verify 不會只檢查一張示意圖，也不會把無 DRC / LVS 報告當作通過。自訂 `physical` 不能關掉本工作台要求的 Magic DRC / LVS。

## 硬 SRAM macro

行為模型只是功能描述。要接真實 SRAM macro，需要你有權使用的下列 views：functional Verilog（含正確 read latency / collision policy）、blackbox netlist、各 timing corner Liberty、LEF、GDS、SPICE / LVS 與 power pins。依 [LibreLane macro 文件](https://librelane.readthedocs.io/en/latest/usage/using_macros.html) 設定 `MACROS`、instances、placement、power connections。

本版預設輸入快照只收 manifest 列出的檔案；macro 的所有 views 也必須放專案內並放 `support_files`，`physical.MACROS` 使用 `dir::...` 相對於快照 `input`。**不要參照原始工作目錄的可變檔案**，否則破壞可重現性。外部受 NDA 的 macro / PDK 絕不能提交到公開 GitHub。

## 不支援的宣稱

這不是製造簽核工具、全功能 UVM / FSDB debugger、完整 CDC/RDC/DFT sign-off 或商業 STA 的所有 mode/corner 功能。封裝、SI/PI、EM/IR sign-off、DFM 與 foundry 認證不在本專案保證範圍。RTL / SDC / testbench 可執行本機行為，本專案不是公共多租戶服務或安全沙箱。
