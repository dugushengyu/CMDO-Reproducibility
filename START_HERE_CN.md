# CMDO 审稿人便携包：从这里开始

最终包把三个问题彻底分开：**工程是否可运行、fresh raw-to-science 是否复现、历史 accepted chain 的下游实现是否可审计**。不要把三者写成同一种“复现成功”。

## 最快检查

Python 3.11 环境安装完成后：

```powershell
python .\RUN_REPRODUCTION.py audit
python .\RUN_REPRODUCTION.py frozen
```

最终 **Portable** 包的一键工程验收直接运行：

```powershell
python .\scripts\final_reviewer_acceptance.py --require-canonical
```

如果只是普通 GitHub clone、没有 Portable-only canonical/bootstrap 大文件，则做静态验收：

```powershell
python .\scripts\final_reviewer_acceptance.py --skip-runtime
```

`audit` 检查代码、哈希、DAG、bootstrap/provenance 和 adapter；`frozen` 校验七个 canonical ZIP 并重画当前图。

MATLAB 图件入口仍可运行：

```matlab
RUN_ALL_CMDO
```

## Fresh raw-to-science replay

完整 fresh replay 必须使用本 **Portable** 包，因为几个大型历史 bootstrap 被 Git 忽略，不在普通 GitHub clone 里。Windows 请使用短路径，例如 `$HOME\P` 和 `$HOME\R`。

先把六个历史 Stage11C official receipt 文件放到：

`$HOME\P\00_Data_Acquisition\Stage11C_Manual_Official_Receipts\`

它们的精确文件名、大小和 SHA-256 在 `provenance/historical_receipts.json`。这些是历史先决条件，不是“重新下载的新 receipt”。

```powershell
python .\RUN_REPRODUCTION.py full-claim `
  --run-id CMDO-FRESH-FULL `
  --output-root "$HOME\R" `
  --project-root "$HOME\P" `
  --allow-network `
  --acknowledge-retrospective-replay
```

当前 reference fresh replay 会在 T2-D 得到真实的科学 non-reproduction：历史 v0.1 是 11/11，但 fresh current-runtime 是 10/11，G4 没有复现。最终 runner 会明确输出 `SCIENTIFIC_DIVERGENCE_BOUNDARY` 并以 **exit code 4** 停止；这不是代码 crash，也不会偷偷放宽阈值继续跑下游。

## 历史链下游审计

如果要继续验证 historical accepted T2-D/T2-E 之后的实现，用**单独项目根目录**：

```powershell
python .\RUN_REPRODUCTION.py archival-continuation `
  --run-id CMDO-ARCHIVAL `
  --output-root "$HOME\R" `
  --project-root "$HOME\A" `
  --allow-network `
  --acknowledge-retrospective-replay
```

这个模式会写明 `ARCHIVAL_HISTORICAL_ACCEPTED_PARENT_CONTINUATION`，绝不能表述成 fresh raw-to-end reproduction。U9/eICU 不在默认审稿流程里。

## Exit code

- `0`：所选 profile 完成。
- `1`：工程/完整性/阶段执行失败。
- `3`：明确的先决条件阻断（runtime、license/receipt、network、Windows path、governance）。
- `4`：科学边界；阶段成功执行，但 frozen authorisation 没有复现。

在本地验收、哈希核验和至少两份独立备份完成以前，不要删除 Google Drive、raw data、模型或 seal/authorization 文件。
