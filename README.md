# CMDO reproducibility repository

这是 CMDO 项目的代码与可重复性仓库。现在提供统一的审稿人入口，把公开数据获取、预处理、training、T/U 阶段、结果比较和出图明确拆成 `audit`、`smoke`、`frozen`、`full-claim` 与 `historical-replay` 五种范围。

## 现在能做什么

- Python 审稿人单入口：`python RUN_REPRODUCTION.py <profile>`
- `smoke`：官方 UCI 数据下载 → 预处理 → 小模型训练 → AUC → ROC 图
- `frozen`：逐字节校验七个 canonical ZIP，再生成全部当前图
- `full-claim`：55 节点的公开/授权原始数据 → 训练 → T/U0–U8 → 容差比较 → 出图回放
- MATLAB 安全单入口：`RUN_ALL_CMDO`（环境检查、单元测试、全部当前图）
- 环境、路径、GPU 和导入哈希检查：`RUN_ENVIRONMENT_CHECK`
- 从本地 canonical records 生成全部当前图：`RUN_ALL_FIGURES`
- 原生 MATLAB 阶段：U8 v1.1 canonical rerun、U9 v1.0 pre-outcome workflow
- U0–U7 当前权威 Python/Notebook 原件保留在 `legacy/original_authoritative`

> U0–U7 仍使用权威 Python/Notebook 实现，不伪装成 MATLAB 等价改写。运行器只生成非破坏性的本地路径适配副本，并保留原始字节及哈希。所有已经解盲的 prospective 阶段只能标记为 retrospective replay。

默认的 `RUN_ALL_CMDO` 不会重跑 U8，也不会触发 U9 ADAPT、PREPARE 或
UNSEAL；这些有封存边界的阶段仍必须单独、按授权顺序执行。

审稿人从 [REVIEWER_QUICKSTART.md](docs/REVIEWER_QUICKSTART.md) 开始。完整数据与训练契约见 [END_TO_END_REPRODUCTION.md](docs/END_TO_END_REPRODUCTION.md)，数据许可闸门见 [DATA_LICENSE_GATES.md](docs/DATA_LICENSE_GATES.md)。

## 完整便携包第一次运行

如果使用名称含 `Portable` 的完整本地包，七个 canonical ZIP 已位于
`data/canonical_records/`，无需创建路径配置。把整个文件夹解压到本地后，
在 MATLAB 中打开仓库根目录并运行：

```matlab
RUN_ALL_CMDO
```

成功后，运行报告和全部导出图位于 `outputs/`。不要只复制其中某个 `.m`
文件运行；应保留完整目录结构。

## 从 GitHub clone 后第一次运行

1. 克隆仓库，在 MATLAB 中打开仓库根目录。
2. 复制 `config/local_paths.example.json` 为 `config/local_paths.json`。
3. 修改其中的本地数据、canonical ZIP 和输出路径。
4. 运行：

```matlab
SETUP_CMDO
RUN_ENVIRONMENT_CHECK
RUN_ALL_CMDO
```

批量运行图时不会等待拖拽标签；需要人工微调标签时，直接单独调用相应 Figure/ED 函数。

## 存储边界

GitHub 保存：代码、配置模板、测试、协议/授权记录、哈希清单、小型 SourceData。

本地磁盘保存：原始数据、canonical ZIP、`.mat`/模型权重、缓存、全部运行结果、PNG/TIFF/PDF。完整便携包可随包携带 canonical ZIP，但这些文件仍被 Git 忽略。路径文件 `config/local_paths.json` 也被 Git 忽略。

## 封存边界

U3C、U4C、U5B、U5F、U6、U7 以及 U8/U9 的 reserve/unseal 流程有明确的授权与哈希边界。顶层运行器不会自动重开封存结果，也不会自动执行 U9 `UNSEAL`。Drive 清理必须等到：本地完整运行通过、清单哈希通过、且至少有两份独立备份。

## 目录

- `matlab/` — MATLAB 公共层、运行器、U8/U9 和图源
- `legacy/original_authoritative/` — 从 Drive 导入的当前权威原始代码
- `source_data/` — 可公开、体积小的图表 SourceData
- `provenance/` — Drive 清单、导入哈希、阶段状态
- `governance/` — 迁移与封存规则
- `data/`、`outputs/` — 本地挂载点说明；内容不进入 Git
