# 驗證紀錄 — 2026-10-30

環境：Windows / Ubuntu 24.04.3 WSL2，WSLg，x86_64，約 8 GiB WSL RAM。沒有 Docker、沒有安裝商業 EDA。使用官方 LibreLane 3.0.17 AppImage；下載前後核對 toolchain.lock.json 的 SHA-256，於 Linux 檔案系統解壓並執行。

## 已實際執行

- 純 Python 單元測試：project 載入／快照／path confinement、保留 DRC/LVS、CDC 候選辨識、多位元 coherency 警告、STA report parser、未執行檢查不冒充零錯誤、TT interface / non-acceptance tests。
- 真工具整合測試：counter 自動 checker、錯誤 RTL 必須失敗、Verilator / Yosys lint、netlist CDC、三種 SRAM read-first / byte mask / output hold、silent process timeout 與 cancellation；TT counter 600 cycles 與 Yosys port check。
- 原生 Tk UI：在 WSLg 建立、切換分頁、讀取工具狀態、reload 與關閉。實際桌面檢查發現無 CJK 字型時顯示方框，已改用英文工具介面，繁中文件保留。
- 一般 counter 的 **完整 80-stage Classic flow**，包含 Yosys mapping、placement、CTS、routing、RCX、multi-corner STA、Magic streamout / DRC / extraction、Netgen LVS。
- 確認存在真實 `.gds` / `.def` / `.odb` / `.spef`；從 OpenSTA reports 解析多條 timing paths，不是 RTL 層數估算。
- 上述 counter **Magic DRC = 0、LVS error count = 0**；另有 antenna passed 報告。`scripts/check_physical.py` 用缺檔／缺 metric 即失敗的方式驗收。
- Tiny Tapeout SKY 交接：官方 template commit 固定；本機執行 `tapeout` 匯出，保留 upstream license、GDS/precheck/GL workflows，加入 counter RTL／checker／metadata。沒有向 Tiny Tapeout 送件。

## 必須保留的限制

1. 流程通過仍有 upstream warnings，包括 library 重複載入、部分 floating nets、未支援 LEF58 的部分項目、未設定 wire-length threshold、IR-drop source locations 未提供。它們保留在 console.log，未改成無警告。
2. **KLayout DRC 在 generic profile 未啟用**，不能稱為 Magic 與 KLayout 兩套 DRC 都過；本版驗收是 Magic DRC + Netgen LVS。
3. Power 為預設 switching/activity 模型的估計；沒有自動匯入使用者 VCD。沒有 foundry-qualified sign-off、實測功耗、晶片良率或製造保證。
4. CDC 只驗證結構分析器會辨認已知測試圖；不是 SpyGlass 等級 protocol、RDC、MTBF 或實體 CDC sign-off。
5. Tiny Tapeout 的官方工具版號、PDK、tile geometry、precheck、gate-level test 與供應商受理須分別完成。generic SKY130 GDS 不等於官方可接受的 shuttle macro。本次沒有購買、付款、提交或回片測試。
6. 官方 TT exporter 首版針對 counter 示範。其他 RTL 要自己的 wrapper、testbench/cocotb 與文件，不能沿用 counter 的通過結果。

## 重跑

```bash
bash eda unit-test
bash eda test
bash eda run verify --jobs 2
python3 scripts/check_physical.py examples/counter/project.json
bash eda run sim --project examples/tiny_tapeout/project.json
bash eda run ttcheck --project examples/tiny_tapeout/project.json
```

`.github/workflows/validate.yml` 的一般 push 跑 unit tests；大型 toolchain／PDK／physical regression 透過 workflow_dispatch 明確啟動，不在每次 commit 反覆下載數 GB。最終執行紀錄仍以你自己的 `.runs/` 原始報告為準。
