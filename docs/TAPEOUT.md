# 接到實際製造：先從 Tiny Tapeout SKY 開始

查核日期：2026-10-30。這是**本機準備與官方流程交接**，不是販售晶片、代理接單或自動付款。

## 成本與選擇

第一次做小型數位 ASIC，建議先做 **Tiny Tapeout 的 1-tile digital design**。你買的是共乘晶片中的設計空間，並透過共用硬體存取；不是一顆自己的獨立封裝產品，也不是自己的完整 SoC。

當日直接查看官方 [計價器](https://app.tinytapeout.com/calculator)：選 **Individual / Digital / 1 tile / 1 PCB**，SKY130、GF180 和 IHP 顯示的 tile 為 €70；若個人補助名額仍有，DevKit 為 €100，加 €15 economy shipping，合計 **€185**。沒有個人優惠的同條件計價為 €385。補助數量有限，**不能把 €185 當保證報價或終身最低價**；稅、地區、運送與最終服務條款以實際結帳為準。這只是讀取試算，不是訂位／購買。

不能只付 €70 就宣稱會收到可獨立使用的封裝晶片。官方 FAQ 說明交付的 kit／breakout 與額外數量政策；請先確認你要的是 learning silicon，還是可出貨的獨立 IC。

更大規模的替代方案：當日 [wafer.space](https://wafer.space/) 的 quarter slot 標準價 US$3,000（1,000 dies；過期的 US$2,000 early bird 不當現價），COB 包裝加購另列 US$1,500。它與 Tiny Tapeout 的 tile / 共用套件不是同一產品；單顆裸晶便宜，不代表首次總預算便宜。[chipIgnite](https://chipfoundry.io/faqs) 的標準專案是 US$14,950。這裡不做匯率換算，也不推薦先囤數千顆。

## 為什麼先選 SKY，而不是把所有製程都塞進來

本工作台一般流程已實際驗證 SKY130A / sky130_fd_sc_hd 的 RTL → GDS → Magic DRC / Netgen LVS。因此先把同製程家族的 Tiny Tapeout SKY 介面接好，最能降低首次導入範圍。**這不表示它的 generic GDS 就符合 Tiny Tapeout。**

官方 [shuttle 清單](https://tinytapeout.com/chips/) 在查核日列出 TTSKY26d（2026-11-30 截止）與 TTGF26c（2026-12-07 截止）；日期、空位與預估交付都可能變更。不要為了趕截止而省略功能、gate-level、reset／CDC 與 post-silicon 測試規劃。

GF180 / IHP 有 [獨立官方 templates](https://tinytapeout.com/hdl/templates/)，不能把 SKY130 的 GDS、tile 尺寸、library 或 rule deck 拿過去直接用。本版只整合 SKY handoff；不把未測試的其他製程列成已支援。

## 先跑本機範例

```bash
bash eda gui --project examples/tiny_tapeout/project.json
bash eda run sim --project examples/tiny_tapeout/project.json
bash eda run ttcheck --project examples/tiny_tapeout/project.json
```

原創 `tt_um_openeda_counter` 有固定介面：8 個 dedicated input、8 個 output、8-bit bidirectional 的 in/out/OE，加上 ena、clk、rst_n。`ui[0]` 使能、`ui[1]` 清除、`uo[7:0]` 計數輸出，bidirectional 永不驅動。測試涵蓋 reset、600 cycles、stall、ena、clear、overflow 與輸出使能。

`TT Check` 用 Yosys 展開後的真實 ports 檢查名稱、方向、寬度及 top 前綴；**不代表 tile fit、官方 precheck 或流片已受理**。輸出明確保留 `official_precheck: NOT RUN`。

## 匯出到真正的官方模板

```bash
bash eda tapeout \
  --project examples/tiny_tapeout/project.json \
  --out .exports/tt-counter \
  --author 'Your public author name'
```

GUI 的 `TT Export` 也能建立新的 handoff 目錄；作者欄空白，請提交前填入。匯出器會下載固定 commit 的官方 SKY template，保留 LICENSE、官方 GDS/precheck/GL-test workflows、tile/pin config，再放入 counter RTL 與**真的會檢查 counter 的 cocotb test**，不沿用加法器範例假裝有驗證。`OPEN_EDA_HANDOFF.json` 記錄來源與 SHA-256。

這個首版匯出器先專門處理 counter 示例。自己的 RTL 需要先實作 TT wrapper、I/O 設計、自己的 checker / cocotb、datasheet，不能只改 top 名字就使用 counter 的測試。現有目錄不覆寫，不自動建立遠端 repository、不傳送 RTL、不下單。

## 官方 hardening 是最後的準則

重要版本差異：本工作台 generic flow 固定 LibreLane **3.0.17**；當日 [ttsky26d GDS action](https://github.com/TinyTapeout/tt-gds-action/tree/ttsky26d) 的預設是 **3.0.14**。**不能把本機 generic flow 通過，直接當作官方指定版本通過。**

要實際提交：

1. 重新核對當期 shuttle 的官方 template / action / PDK / tool version；確認 tile 數與 pinout。
2. 把匯出內容放到你選擇的 GitHub 專案，填完作者、授權、功能、測試與硬體操作說明。
3. 跑官方 GDS、precheck、RTL test 和 gate-level test，確認的是同一個 commit。官方 workflow 是否使用 GitHub Pages 是上游展示功能，不是本工作台需要架網站。
4. 審查 timing、DRC、LVS、antenna、pin geometry、power／reset 與 clock assumptions；保留官方 `tt_submission` artifact。
5. 由你在 Tiny Tapeout 官方網站選方案、檢查套件／運費／條款、提交與付款，等待供應商受理。

若要全部在 WSL 做，官方 [local-hardening guide](https://tinytapeout.com/guides/local-hardening/) 有完整依賴。查核的 tt-support-tools 也有 `--no-docker`；它需要與 shuttle 匹配的工具 shell 及其 Python dependencies，不能保證本工作台 3.0.17 環境可直接取代 3.0.14。對應方式為：

```bash
# 在已配置官方指定版本的工具 shell / 專案內，不是 generic flow：
python tt/tt_tool.py --pdk sky130A --create-user-config
python tt/tt_tool.py --pdk sky130A --harden --no-docker
python tt/tt_tool.py --pdk sky130A --create-tt-submission
```

本版驗證的是 generic physical flow、TT counter simulation／interface check 與模板交接。**沒有宣稱完成官方 shuttle precheck、供應商接受、付款或實際投片。**

## 接近實物後還要準備什麼

第一顆建議是 small controller / timer / SPI register / 小型資料路徑，不是 LLM accelerator 或 HBM controller。目標是在回片後用已規劃的 clock、reset、I/O stimulus 與可觀察輸出確認功能。prototype 成功後，再評估多 tiles、外接記憶體、較完整 SoC 或 wafer.space / chipIgnite；不要把 tile 費當整顆產品的全部成本。
