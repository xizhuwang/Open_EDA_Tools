# 原創 SRAM 行為模型

| 模型 | 介面 | 讀取 | 同位址讀寫 |
|---|---|---|---|
| `sram_1rw` | 一個讀寫埠 | 同步、一拍 | read-first，回傳舊值 |
| `sram_1r1w` | 一讀一寫，共用時脈 | 同步、一拍 | read-first |
| `sram_2rw` | 兩讀寫埠，共用時脈 | 同步、一拍 | read-first；同位址雙寫禁止 |

`ADDR_WIDTH=6/8/10` 對應 64/256/1024 words；`DATA_WIDTH=8/16/32/64`。位寬必須為正的 8 倍數，位址寬至少 1。`byte_en[0]` 控制最低 8 bits；讀取停用時輸出保持。沒有 reset，初始資料未知；不得假設上電為 0。請在 project.json 的 `rtl` 列出模型，並把檔案放入該專案目錄。

這些是可模擬／可推導的 RTL 記憶體，不是 TSMC 或其他晶圓廠的 IP，不含真實 SRAM 時序／面積或 GDS。合成後可能展開成大量暫存器與 mux；**不能以此估計 SRAM macro 面積與功耗**。2RW 的雙寫仲裁是呼叫端責任。

使用真實 macro 必須另外取得授權相容的 Liberty、LEF、GDS、Verilog 與 LVS/SPICE 模型，在 LibreLane `MACROS` 設定明確指定。未設定時不得把記憶體當成免費的 black box。
