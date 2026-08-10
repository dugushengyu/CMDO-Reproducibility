# CMDO 完整便携包：从这里开始

1. 完整解压本 ZIP；不要只拖出某个 `.m` 文件。
2. 在 MATLAB 的 **Current Folder** 中打开解压后的仓库根目录。这个目录应能直接看到 `RUN_ALL_CMDO.m`。
3. 在 Command Window 运行：

```matlab
RUN_ALL_CMDO
```

这个安全入口依次执行：环境与哈希检查、非数据单元测试、全部当前主图与
Extended Data 图。它不会重跑 U8，也不会访问或解封 U9 outcome。

正常标志：

- `Canonical archives verified: 7/7`
- `Imported-source hashes: 20/20`
- `Ready for all figures: 1`
- `outputs/reports/test_run_report.csv` 中全部测试均为 `passed=true`
- `outputs/reports/figure_run_report.csv` 中所有行均为 `PASS`
- `outputs/reports/pdf_compatibility_report.csv` 中所有行均为 `PASS`
- `outputs/reports/local_acceptance_summary.json` 中测试、图件生成和兼容 PDF 失败数均为 0

如果图件与兼容 PDF 已全部生成，但旧版 R4 在最终读取 CSV 时出现
`Unrecognized table variable name 'status'`，更新根目录运行器后执行：

```matlab
RUN_ALL_CMDO('Mode','finalize')
```

这只复核现有报告并补写验收摘要，不会重画图、重跑 U8 或访问 U9 outcome。

`figure_run_report.csv` 的 `PASS` 只代表代码成功生成文件；其
`visualReview` 会保留为 `PENDING_EXTERNAL_QA`，直到导出的 PNG/TIFF/PDF 经过逐图版式检查。

每张图会同时保留普通的矢量 `.pdf` 和由相同 600-dpi PNG 生成的
`*_compat.pdf`。如果 Poppler 或投稿系统预览器把矢量 PDF 的字距显示异常，
请使用 `*_compat.pdf` 或像素完全一致的 TIFF；不要把预览器兼容问题误判为
数值或 MATLAB 运行错误。

如果已有 PNG 无需重画、只需重建兼容 PDF，可运行：

```matlab
REBUILD_COMPATIBILITY_PDFS
RUN_ALL_CMDO('Mode','finalize')
```

兼容 PDF 写入器直接、无损地嵌入 PNG 像素和完整画布，避免 MATLAB 隐藏
axes 导出时对右侧或底部边缘进行紧裁切。

生成结果位于：

- `outputs/figures/main/`
- `outputs/figures/extended/`
- `outputs/reports/`

在外部视觉验收完成以前，不要据此删除 Google Drive、原始数据、模型权重、
U8/U9 workdir、seal 或 authorization 文件。

如果 MATLAB 仍调用旧解压目录中的函数，请关闭并重新打开 MATLAB，然后只把
Current Folder 指向本便携包根目录，再运行上述命令。
