# R4.2 兼容 PDF 画布修补

R4 的 PNG、TIFF、数值、测试和图件布局均未改变。本修补只替换
`*_compat.pdf` 的生成方式：把已有 PNG 的原始无损像素直接嵌入 PDF，
避免隐藏 axes 导出时紧裁切右侧或底部边缘。

将修补包完整解压到 `F:\C\CMDO-R4` 并保留文件夹结构，确认覆盖
`matlab\figures\helpers\cmdo_build_compatibility_pdfs.m`。随后重启 MATLAB，
把 Current Folder 指向 `F:\C\CMDO-R4`，运行：

```matlab
REBUILD_COMPATIBILITY_PDFS
RUN_ALL_CMDO('Mode','finalize')
```

第一条命令只读取已经生成的 13 个 PNG 并重建兼容 PDF；不会重画图、
重跑 U8 或访问 U9 outcome。正常应显示：

```text
Passed: 13
Failed: 0
```

完成后重新打包：

```matlab
reviewItems = {fullfile('outputs','reports'), fullfile('outputs','figures')};
zip(fullfile(pwd,'CMDO_R4_2_visual_acceptance.zip'),reviewItems,pwd);
```

在新包完成外部视觉验收以前，不要删除 R4、Google Drive、原始数据、
模型权重或 U8/U9 的 workdir、seal、authorization 文件。
