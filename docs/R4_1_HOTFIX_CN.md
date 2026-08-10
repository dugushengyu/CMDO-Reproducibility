# CMDO R4.1 汇总器修补说明

适用错误：

```text
Unrecognized table variable name 'status'.
Error in RUN_ALL_CMDO (line 57)
```

该错误发生在 13 张图和 13 个兼容 PDF 已生成之后，只影响最终验收摘要。

## 应用方法

1. 将修补包内的三个 `.m` 文件复制到现有 `F:\C\CMDO-R4` 根目录，并确认覆盖旧的 `RUN_ALL_CMDO.m` 与 `RUN_ALL_FIGURES.m`。
2. MATLAB Current Folder 保持为 `F:\C\CMDO-R4`。
3. 执行：

```matlab
RUN_ALL_CMDO('Mode','finalize')
```

该命令只验证现有环境与三份运行报告，并补写
`outputs\reports\local_acceptance_summary.json`。它不会重新生成图件、重跑 U8 或访问 U9 outcome。

正常输出应包括：

```text
Tests: 10 passed, 0 failed
Figures: 13 passed, 0 failed
Compatibility PDFs: 13 passed, 0 failed
```

随后打包视觉验收文件：

```matlab
reviewItems = {fullfile('outputs','reports'), fullfile('outputs','figures')};
zip(fullfile(pwd,'CMDO_R4_visual_acceptance.zip'),reviewItems,pwd);
```
