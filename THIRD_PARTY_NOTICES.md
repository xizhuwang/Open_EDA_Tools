# 授權與來源

本 repository 的原創整合程式、桌面 UI、SRAM RTL 與範例：Copyright 2026 Xi-Zhu Wang，MIT（見 LICENSE）。使用者獨立撰寫的 RTL / TB 不會因此改變授權。

外部工具以**分開程序**執行，固定下載 LibreLane 3.0.17 官方 release；本 repo 不上傳／重新散布工具二進位檔與 PDK。工具包本身包含多種授權，不能把本專案 MIT 當作整套工具包授權。重新散布 bundle、修改二進位或製作產品前，必須檢視 bundle 內每一項 notice、完整對應原始碼與建置腳本等義務。

| 項目 | 官方來源 / 授權入口 |
|---|---|
| LibreLane infrastructure | [upstream 3.0.17](https://github.com/librelane/librelane/tree/3.0.17)，Apache-2.0 主授權，部分檔案另有 MIT notices |
| Icarus Verilog | [COPYING 與相關例外](https://github.com/steveicarus/iverilog)，GPL 系列，依檔案與 runtime exceptions |
| Verilator | [COPYING](https://github.com/verilator/verilator/blob/master/COPYING)，依 upstream 的 LGPL / Artistic 選項與檔案 notices |
| Yosys / ABC | [Yosys COPYING](https://github.com/YosysHQ/yosys/blob/main/COPYING)；Yosys ISC，ABC / dependencies 另列 |
| OpenROAD | [LICENSE](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/LICENSE)，BSD-3-Clause 與 dependencies |
| OpenSTA | [LICENSE](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/LICENSE)，GPL-3.0 |
| Magic | [upstream](https://github.com/RTimothyEdwards/magic)，依 COPYING / 來源 notices |
| Netgen | [upstream](https://github.com/RTimothyEdwards/netgen)，依 COPYING / 來源 notices |
| KLayout | [upstream](https://github.com/KLayout/klayout)，依 LICENSE 與 dependencies |
| GTKWave | [upstream](https://github.com/gtkwave/gtkwave)，依 COPYING 與元件 notices |
| SKY130 / open_pdks | [SkyWater](https://github.com/google/skywater-pdk)、[open_pdks](https://github.com/RTimothyEdwards/open_pdks)；按個別 library / file 授權與版本 |

工具的固定版號與 patch 清單見官方 release 的 [tool_versions.txt](https://github.com/librelane/librelane/releases/download/3.0.17/tool_versions.txt)。PDK 版本由該版 LibreLane / Ciel 匹配下載，原始 resolved configuration 記錄版本。

Tiny Tapeout exporter 在使用者執行匯出時才下載 [官方 SKY template](https://github.com/TinyTapeout/ttsky-verilog-template) 的固定 commit，保留該模板 Apache-2.0 LICENSE。原創 counter 與 checker 另附 MIT LICENSE-OPEN-EDA；不把 upstream 模板改標成 MIT。此 repo 不包含上游 template 的複製品。Tiny Tapeout 名稱用於相容介面／交接說明，沒有代理、轉售、官方合作或受理承諾。

沒有使用 VCS、Verdi、SpyGlass、Design Compiler、ICC2、Calibre 的專有程式、圖像、manual 或 rule deck；名稱僅用於說明工作類型，沒有官方關聯或相容性認證。沒有附帶 TSMC 時序表、NDA PDK、SRAM compiler 產物。

不承諾任何設計可製造、符合晶圓廠 sign-off 或免除專利／IP 授權。本文件是工程授權盤點，不是法律意見；商用、代工投片、再散布或處理第三方設計時，請按實際版本、PDK 與交付方式再審查授權。工具輸出可能攜帶 library material，其條件也要個別確認。
