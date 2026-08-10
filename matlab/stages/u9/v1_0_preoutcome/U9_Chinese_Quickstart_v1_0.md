# U9 中文运行说明（先读这个）

可以像 U8 一样下载后在你本机 MATLAB 跑，但 U9 分成“封存前”和“获授权后”两段，不能一口气把 reserve outcome 打开。

## 你需要先有 eICU-CRD v2.0

U9 包里不含患者数据。eICU 是 PhysioNet credentialed 数据库，需要账号认证、完成人体研究/CITI 培训，并签署项目 DUA：

- 数据页：<https://physionet.org/content/eicu-crd/2.0/>
- DUA：<https://physionet.org/content/eicu-crd/view-dua/2.0/>

本地至少准备这三个官方表，`.csv` 或 `.csv.gz` 都可以，不必手动解压：

- `patient.csv(.gz)`
- `apachePatientResult.csv(.gz)`
- `hospital.csv(.gz)`

把它们放在同一个 eICU 根目录或其子目录中。

## MATLAB 要求

- 建议 MATLAB R2022b 或更新版本。
- 需要 Statistics and Machine Learning Toolbox。
- 把整个 U9 文件夹解压到可写目录；不要只单独拷贝主 `.m` 文件。

## 第一次运行：只做到 PREPARE

按顺序运行：

1. `RUN_SELFTEST.m`
2. 在 `RUN_DATA_ADAPTER.m` 里只改一处 `u9RawDataRoot`，指向 eICU 根目录；再运行该脚本。
3. `RUN_PREPARE.m`
4. 到这里停止，不要运行 `RUN_UNSEAL.m`。

正确时你会看到：

- `CMDO U9 SELFTEST PASSED`
- adapter 明确写出没有计算或打印 reserve outcome 统计量
- PREPARE 打印 seal SHA-256，并写出 `DO NOT RUN UNSEAL`

然后按 `U9_Results_Return_Checklist_v1_0.md`，只把其中六个 share-safe 文件和 MATLAB 命令窗口结果发给我。绝对不要发：

- `00_RESTRICTED_DO_NOT_SHARE` 中的任何文件
- 官方 eICU 表
- outcome-free row-level roster 或 target-score CSV
- `.mat` observer asset

## 第二次运行：收到匹配授权后

我核对 seal、代码、协议和 vault 哈希后，会给你一个已签发的：

`StageU9_EXECUTION_AUTHORIZATION_v1_0.json`

按 checklist 放到指定目录，不要编辑，然后只运行一次 `RUN_UNSEAL.m`。脚本会要求你键入：

`UNSEAL U9 ONCE`

完成后只发回：

- `CMDO_U9_Canonical_Shareable_Record_v1_0.zip`
- `StageU9_Canonical_Zip_Commit_v1_0.json`
- MATLAB 最后输出

如果 `StageU9_ONE_SHOT_ANALYSIS_STARTED_v1_0.json` 已经出现，即使后面报错，也不要删 marker 或重跑；保留整个 workdir，把报错和日志发给我做 forensic review。

## 常见报错

- `eICU folder not found`：路径没改对，或环境变量 `CMDO_EICU_ROOT` 未设置。
- `Missing required MATLAB functions`：Statistics and Machine Learning Toolbox 未安装/未启用。
- `Multiple candidates found`：同一根目录下放了两份同名 eICU 表；保留一个明确版本。
- `Only ... hospitals`：当前输入不是完整官方 eICU v2.0，或表被预先筛选过；不要改 frozen hospital threshold。
- `AuthorityMismatch`：文件在 PREPARE 后被改动；不要手工修哈希或 authorization。

