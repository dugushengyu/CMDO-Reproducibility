# Dense-Lambda stress test 快速运行

在 repo 根目录的 MATLAB 中运行：

```matlab
csvPath = RUN_FIGURE5_STRESS_RECONSTRUCTED;
```

它会调用重建后的 Python generator，并返回刚生成的 `CMDO_SystemStress_AUC_StateSummary_v1_1.csv` 路径。该 generator 明确标注为 reconstruction，不冒充遗失的 2026-08-31 原始脚本。
