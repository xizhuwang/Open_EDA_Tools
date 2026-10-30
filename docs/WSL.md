# WSL2 / WSLg 環境

## 先準備

Windows 11 + Ubuntu 24.04 WSL2 建議使用。必須能從 WSL 開啟 Linux GUI（`DISPLAY` 非空）。WSLg 不需要另外啟動網頁 server。

專案的 setup **不自動改系統、不安裝 Docker、不關閉 AppArmor**。如果系統缺基本套件，由你在 Ubuntu 明確執行：

```bash
sudo apt-get update
sudo apt-get install -y git curl python3 python3-tk fonts-noto-cjk uidmap
```

工具包依賴 Linux user namespaces；AppImage 已一次性解壓縮，因此不依賴 FUSE。若出現 `cannot write uid_map`，先查閱 [LibreLane 官方 AppImage 故障排除](https://librelane.readthedocs.io/en/latest/installation/appimage_installation/installation_linux.html)。不要為了跑專案就盲目停用系統安全設定；可改用官方 Nix 安裝，進入工具 shell 後：

```bash
EDA_USE_SYSTEM_TOOLS=1 bash eda doctor
EDA_USE_SYSTEM_TOOLS=1 bash eda gui
```

`EDA_USE_SYSTEM_TOOLS=1` 不驗證你自備工具的版本／組合，相容性由該環境負責；manifest 會記錄實際路徑。內建 portable bundle 是預設路徑。

## 硬體與磁碟

官方工具建議至少 8 GiB RAM，建議 16 GiB；這裡預設 2 threads、一次一個工作，小型 counter 即可先走流程。**8 GB 不能保證大型 CPU/SoC 跑完**。預留至少 20 GB 給工具、PDK 與多次 flow；實際需求隨 PDK/設計改變。無月費，但耗用本機儲存、時間與電力。

下載一次工具包約 1.4 GB。首次實體流程由 LibreLane / Ciel 自動下載其匹配的 SKY130 PDK revision；resolved.json 記錄所用版本。不要混用來源不明的 PDK。PDK 放 `.pdks/` 或你指定的 `PDK_ROOT`。

## 常見問題

- **解壓縮很慢**：請 clone 到 `~/Open_EDA_Tools`，而非 `/mnt/c/...`。首次解壓縮有數萬小檔，不是 UI 卡死；看 `.tools/<arch>/extract.log`。
- **setup 中斷**：若 `.tools/<arch>/squashfs-root` 只解到一半，將該目錄改名備份後重跑 setup。已驗證的 AppImage 可保留。
- **沒有桌面**：Windows 執行 `wsl --update`，重新開啟 WSL；確認 `echo "$DISPLAY"`。遠端 SSH / headless 不支援桌面時仍可用 CLI。
- **中文字變方框**：安裝 `fonts-noto-cjk` 並重新啟動工作台。
- **OpenROAD / KLayout 黑畫面**：launcher 已使用 software rendering；詳查該 run 的 `openroad-viewer.log` / `layout-viewer.log`。
- **No run yet**：先執行相對應流程。模擬產物與物理流程是不同次 run；改跑其他 stage 後預設 Latest run 會切換，舊產物仍在 `.runs/`，可用獨立工具直接開啟。
- **已有工作鎖**：先確認 `.runs/.eda-lock` 裡 PID 的工作確實不存在，再刪除那一個 lock；不要同時跑同一專案。
- **沒有 code 指令**：在 Windows 安裝 VS Code + WSL 擴充功能後，從 WSL 執行 `code .`；不要安裝 Linux VS Code 取代 WSL Remote。
- **DRC / LVS / timing fail**：這是設計／條件／flow 的失敗，並不會被工作台改成通過。檢查原始 step report，修改 RTL、SDC、die / PDN / placement 參數後重新跑。

## 更新

`git pull` 只更新程式；工具包仍由 `toolchain.lock.json` 固定版本。請先完成運算、備份專案再更新。`.runs` 不會被 setup 清除。更新工具版本必須重新檢查整套 regression；不使用 `latest` 靜默升級。
