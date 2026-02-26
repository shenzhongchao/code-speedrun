# 简化清单 — 速通版 vs 原版 Protenix

本文档列出速通版相对于原版的所有简化点。每一项都是一个可以独立扩展的方向。

> **提示**: 你可以借助 AI 编程工具（如 Claude Code、Cursor、Copilot 等），在速通版代码的基础上逐项向原版靠拢。推荐方式：选择下方某一项，把对应的速通版文件和原版文件一起提供给 AI，要求它"在速通版基础上补充 XXX 的完整实现"。这样你既能看到差异，又能逐步理解原版的工程决策。

---

## 模型架构

| 简化点 | 速通版 | 原版 | 涉及单元 | 原版文件 |
|--------|--------|------|----------|----------|
| AtomAttentionEncoder | 全局注意力 + 平均聚合 | 局部注意力窗口 + dense trunk rearrangement | Unit 3 | `protenix/model/modules/transformer.py` |
| 三角乘法更新 | 朴素 einsum | 3种后端: PyTorch / Cuequivariance / 自定义CUDA kernel | Unit 4 | `protenix/model/triangular/triangular.py` |
| 三角注意力 | 简化的多头注意力 | 带 gating 的完整实现 + kernel fusion | Unit 4 | `protenix/model/triangular/triangular.py` |
| DiffusionTransformer | 单层 MHA + MLP | 多层 DiffusionTransformerBlock + AdaLN (Algorithm 26) | Unit 5 | `protenix/model/modules/diffusion.py` |
| ConfidenceHead | 单层 pair/single 更新 | 4层 PairformerStack + 多个预测头 | Unit 6 | `protenix/model/modules/confidence.py` |
| MSAModule | 未实现 | 完整的 MSA 注意力 + pair-weighted averaging | Unit 4 | `protenix/model/modules/pairformer.py` |
| TemplateEmbedder | 未实现 | 模板距离图 + 单位向量嵌入 | Unit 3 | `protenix/model/modules/pairformer.py` |
| ConstraintEmbedder | 未实现 | 用户自定义约束注入 pair representation | — | `protenix/model/modules/embedders.py` |
| ESM 嵌入 | 未实现 | ESM-2 蛋白质语言模型特征拼接 | — | `protenix/data/esm/` |

## 数据管线

| 简化点 | 速通版 | 原版 | 涉及单元 | 原版文件 |
|--------|--------|------|----------|----------|
| 输入格式 | 纯氨基酸字符串 | JSON (多链/配体/核酸/修饰残基/共价键) | Unit 2 | `protenix/data/inference/json_parser.py` |
| 原子表示 | 每残基固定3个主链原子 | 全原子 (最多14个侧链原子 + 配体原子) | Unit 2 | `protenix/data/tokenizer.py` |
| MSA 生成 | 随机突变模拟 | hmmsearch / ColabFold 数据库搜索 | Unit 2 | `protenix/data/msa/` |
| 模板特征 | 随机张量 | HHR/A3M 解析 + 结构比对 | Unit 2 | `protenix/data/template/` |
| mmCIF 解析 | 未实现 | 完整的 MMCIFParser + 生物组装体处理 | — | `protenix/data/core/parser.py` |
| 数据过滤 | 无 | 分辨率/链长/clash 等多维过滤 | — | `protenix/data/core/filter.py` |
| 裁剪 (Cropping) | 无 | 空间/连续裁剪到 train_crop_size | — | `protenix/utils/cropping.py` |

## 训练流程

| 简化点 | 速通版 | 原版 | 涉及单元 | 原版文件 |
|--------|--------|------|----------|----------|
| 标签置换 | 坐标翻转 + RMSD 比较 | 链置换 + 原子置换 + pocket-based 启发式 | Unit 7 | `protenix/utils/permutation/` |
| 置信度损失 | 未实现 | pLDDT + PAE + PDE + Resolved (4项) | Unit 7 | `protenix/model/loss.py` |
| 分布式训练 | 单进程 | DeepSpeed ZeRO + 多GPU + 梯度累积 | Unit 7 | `runner/train.py` |
| 学习率调度 | 固定 lr | WarmupCosine / WarmupLinearDecay | — | `protenix/utils/lr_scheduler.py` |
| 实验追踪 | 无 | Weights & Biases (wandb) 集成 | — | `runner/train.py` |

## 工程优化

| 简化点 | 速通版 | 原版 | 原版文件 |
|--------|--------|------|----------|
| 数值精度 | 默认 float32 | 选择性 AMP + skip_amp 配置 | `protenix/model/protenix.py` |
| 内存优化 | 无 | Activation checkpointing + inplace ops | `protenix/model/modules/pairformer.py` |
| 自定义算子 | 无 | Triton LayerNorm + CUDA triangle attention | `protenix/model/layer_norm/`, `protenix/model/tri_attention/` |
| 配置系统 | 硬编码常量 | ConfigManager + 多层配置继承 + CLI覆盖 | `protenix/config/config.py` |
| 输出格式 | 打印到终端 | CIF 文件 + JSON 置信度 + 排序 | `runner/inference.py` |

## 未覆盖的功能模块

| 模块 | 说明 | 原版文件 |
|------|------|----------|
| 多链复合物 | 蛋白质-蛋白质/蛋白质-核酸复合物处理 | `protenix/data/core/featurizer.py` |
| 配体处理 | 小分子配体的 SMILES 解析 + RDKit 构象生成 | `protenix/data/tokenizer.py` |
| RNA MSA | RNA 序列的 nhmmer 搜索 | `scripts/` |
| Web Service | Colab 请求解析 + 结构可视化 | `protenix/web_service/` |
| 评估指标 | LDDT / RMSD / Clash 完整计算 | `protenix/metrics/` |

---

## 推荐扩展路径

从易到难：

1. **配置系统** — 把硬编码常量替换为 ConfigManager，学习原版的配置继承机制
2. **全原子表示** — 从3个主链原子扩展到全原子，理解侧链建模
3. **完整三角更新** — 加入 gating、dropout、LayerNorm，对比性能差异
4. **MSAModule** — 实现 MSA 注意力，理解进化信息如何注入 pair representation
5. **置信度损失** — 补全 pLDDT/PAE/PDE/Resolved 四项损失
6. **标签置换** — 实现链级 + 原子级置换，处理对称蛋白质
7. **混合精度 + Checkpointing** — 加入 AMP 和 activation checkpointing，对比显存占用
8. **分布式训练** — 接入 DeepSpeed，在多 GPU 上训练

每一步都可以用 AI 编程工具辅助：把速通版代码和原版对应文件一起提供，让 AI 帮你桥接差异。
