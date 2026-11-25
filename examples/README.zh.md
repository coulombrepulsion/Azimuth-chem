# “方位”示例

用于立即体验程序功能的文件。最方便的方式是 **“文件 → 打开示例…”**（对话框在此文件夹中打开）：计算结果进入光谱，结构和
CIF 文件进入罗盘，片段文件进入“我的片段”。也可以用普通的“文件 → 打开…”。

几乎所有结果都是 cclib 测试数据中的真实程序输出（BSD-3-Clause 许可，见 `LICENSE-cclib.txt`；来源见 `README.md`）。
其中许多是**节选**：需要的块原样保留，省略处标记为 `...  [lines omitted from the excerpt]`。分子大多是二乙烯基苯
（C₁₀H₁₀），部分是水。第 0 和 8–11 文件夹中的结构为“方位”准备。

| 文件夹 | 文件 | 操作 | 可以看到 |
|---|---|---|---|
| `0-molecules` | `water.xyz`、`methane.xyz`、`ammonia.xyz`、`benzene.xyz` | 打开（或拖入窗口）；模型下方的说明即点群按钮 | 入门用的简单分子：旋转、缩放、测量、编辑；点群 C₂v（水）、T_d（甲烷）、C₃v（氨）、D₆h（苯） |
| `1-properties` | `water_mp2_orca5.out`、`divinylbenzene_cation_orca6.out`、`divinylbenzene_cation_gaussian16.log` | 打开；在罗盘中点模型上方的“±”按钮 | Mulliken、Löwdin、Hirshfeld 电荷，阳离子的自旋布居，Mayer 键级，偶极矩——直接显示在模型上 |
| `2-optimization` | `divinylbenzene_opt_gaussian16.log`、`divinylbenzene_opt_psi4.out`、文件夹 `xtb_divinylbenzene_opt`（打开 `dvb_opt.out`） | 打开；模型左侧的 ☰ 步骤面板 | 优化步骤、能量曲线、播放、与初始结构比较、步骤 GIF |
| `3-scans` | `dihedral_scan_relaxed_orca6.out`、`dihedral_scan_relaxed_gaussian16.log`、`zmatrix_scan_rigid_orca5.out` | 打开；☰ 面板 | 势能面扫描点：二面角或参数值，相对最低点的 ΔE |
| `4-vibrations` | `divinylbenzene_freq_gaussian16.log`、`divinylbenzene_freq_psi4.out`、文件夹 `xtb_divinylbenzene_freq`（`dvb_ir.out`） | 光谱 → “振动和红外” | 频率和红外光谱、动画、（双向）箭头、“GIF…”、“XYZ 帧…”、“位移 +/−” |
| `5-uv-vis-nmr` | `divinylbenzene_tddft_orca6.out`、`divinylbenzene_tddft_gaussian16.log`、`divinylbenzene_nmr_orca6.out`、`divinylbenzene_nmr_gaussian16.log` | 光谱 → “UV-Vis”和“NMR”选项卡 | 带包络线和跃迁表的吸收光谱；屏蔽常数和化学位移、等价原子 |
| `6-orbitals` | `water_mp2_gaussian16.fchk`、`water_gamess.molden`、`divinylbenzene_orbitals_orca6.out`、`MoOCl4_ecp_gaussian16.fchk` | 打开；“轨道”窗口（ORCA 输出用“轨道…”按钮） | 能级图、HOMO/LUMO、无需 CUBE 文件的轨道或密度等值面 |
| `7-programs` | `water_ccsdt_gaussian16.log`、`water_ccsdt_psi4.out`、文件夹 `xtb_divinylbenzene_sp`（`dvb_sp.out`） | 依次打开 | 同一个水分子计算在 Gaussian 和 Psi4 中的结果（CCSD(T) 最终能量）；xtb 电荷和 Wiberg 键级 |
| `8-compare` | `ethanol.xyz` 与 `ethanol_other_order.xyz`；`butane_anti.xyz` 与 `butane_gauche.xyz` | 打开第一个文件，然后“比较” → “从文件叠合结构…” → 第二个 | 原子顺序不同时的叠合（RMSD ≈ 0，“编号不同”）、“按文件的顺序重新编号模型”；丁烷两个构象的差别 |
| `9-torsion` | `butane.xyz`、`ethanol.xyz` | 右键单击中间的 C–C 键（或 C–O 键）→“绕此键旋转…” | 精确二面角、鼠标旋转、最近接触、构象扫描到步骤面板或 XYZ |
| `10-crystals` | `NaCl_rock_salt.cif`、`CsCl.cif`、`graphite_P1.cif`、`Si_diamond.cif`、`benzoic_acid.cif` | 打开 → “晶体”窗口 → “构建” | 晶胞（NaCl 含面上原子时为 14 个 Na 和 13 个 Cl）、晶胞块、a、b、c 棱；石墨：没有对称操作的文件（P1）；硅——金刚石晶格 Fd-3m，在原胞和惯用晶胞中做 vc-relax（a ≈ 5.47 Å）；苯甲酸——分子晶体：“接触”中的 O–H···O 氢键和 R²₂(8) 二聚体、位移椭球、二聚体计算 |
| `11-fragments` | `example_fragments.json` | 用“文件 → 打开示例…”打开此文件（或“片段”→“导入片段…”） | “我的片段”中的三个片段：—CF₃、叔丁基、乙酰基；可放到原子上或替换氢原子 |

文件夹根目录还有三个可从菜单打开的教学文件：`teaching-demo.out`、`optimization-demo.out`、`vibrations-demo.out`。
显示方案（“视图 → 显示方案”）可以在任意文件上尝试。

`0-molecules`（2026-11-14，根据第一份测试报告）：几何结构由程序按实验键长和键角（CRC Handbook，气相）构建：水 r(OH) 0.9572 Å，∠HOH 104.52°；甲烷 r(CH) 1.087 Å，正四面体；氨 r(NH) 1.012 Å，∠HNH 106.7°；苯 r(CC) 1.397 Å，r(CH) 1.084 Å——对称性是精确的。

`10-crystals/benzoic_acid.cif` 为 COD 条目 7133168（Crystallography Open Database，公有领域）：苯甲酸，P2₁/n，296 K；
Sun、Li、Chen 等，Chem. Commun. 60 (2024) 7224，doi:10.1039/d4cc01751j。仅删除了内嵌的 `_shelx_res_file` 和 `_shelx_hkl_file` 块（SHELXL 输入文件和衍射点）。

`10-crystals/Si_diamond.cif` 为 COD 条目 9008565（来自 American Mineralogist Crystal Structure Database）：硅，Fd-3m，a = 5.4307 Å，300 K；Wyckoff R. W. G.，Crystal Structures 1 (1963) 7–83。文件未作改动（2026-11-21，根据第一份测试报告）。
