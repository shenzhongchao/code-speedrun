# Unit 1: 端到端总览 — Protenix 蛋白质结构预测

## 通俗理解

把 Protenix 想象成一条**工厂流水线**：

1. **原材料进场**（输入嵌入）：氨基酸序列就像一串字母密码，先被翻译成机器能理解的数字向量——就像把零散的原材料加工成标准化的零件。
2. **反复打磨**（Pairformer 迭代精炼）：零件在流水线上被反复检查和打磨。每一轮循环中，模型同时考虑"每个氨基酸自身的特征"和"任意两个氨基酸之间的关系"，让信息越来越精确。
3. **从噪声中雕刻**（扩散模块）：想象一位雕塑家面对一块随机的石头（纯噪声坐标），一刀一刀地凿去多余的部分，最终凿出精美的雕像（三维蛋白质结构）。
4. **质量检验**（置信度评估）：成品出厂前要经过质检。模型给自己的每个预测打分——哪些部分预测得准，哪些部分不太确定。

整条流水线的输入是**氨基酸序列**（一维字符串），输出是**三维原子坐标 + 置信度分数**。

## 背景知识

### 蛋白质折叠问题

蛋白质是生命的"工作机器"。一条氨基酸序列（一维）会自发折叠成特定的三维结构，而结构决定了蛋白质的功能。预测"序列→结构"的映射关系，就是蛋白质折叠问题——这是结构生物学中长达 50 年的核心挑战。

### Transformer 注意力机制在生物序列中的应用

Transformer 最初为自然语言处理设计，其核心是**注意力机制**——让序列中的每个位置都能"看到"其他所有位置。蛋白质序列天然适合这种处理方式：远距离的氨基酸在三维空间中可能非常接近，注意力机制能捕捉这种长程依赖关系。

### 扩散模型

扩散模型是一类生成模型，其核心思想是：
- **正向过程**：逐步向数据添加噪声，直到变成纯随机噪声
- **反向过程**：学习从噪声中逐步去噪，恢复出原始数据

类比：雕塑家从一块粗糙的石头开始，每一步都去掉一点多余的材料，最终得到精美的雕像。在 Protenix 中，"石头"是随机的三维坐标，"雕像"是蛋白质的真实结构。

### AlphaFold 系列的演进

| 版本 | 关键创新 | 局限 |
|------|---------|------|
| **AF1** (2018) | 距离预测 + 梯度下降 | 精度有限 |
| **AF2** (2020) | Evoformer + Structure Module，端到端预测 | 仅支持单链蛋白质 |
| **AF3** (2024) | Pairformer + 扩散模块，支持复合物 | 闭源 |
| **Protenix** | AF3 的开源复现，字节跳动出品 | 本课程的学习对象 |

Protenix 是 AlphaFold3 架构的开源实现，用 PyTorch 编写，支持蛋白质、核酸、配体等多种分子类型的结构预测。

## 关键术语

- **Token**: 蛋白质中的一个残基（氨基酸）或核酸中的一个碱基，是模型处理的基本单位
- **Pair Representation (z)**: 描述任意两个 token 之间关系的矩阵，形状为 `[N_token, N_token, c_z]`。可以理解为一张"关系表"——`z[i][j]` 编码了第 i 个和第 j 个 token 之间的相互作用信息
- **Single Representation (s)**: 描述每个 token 自身特征的向量，形状为 `[N_token, c_s]`。编码了每个氨基酸的局部环境和进化信息
- **MSA (Multiple Sequence Alignment)**: 多序列比对。通过比较同源蛋白质的序列，推断哪些位置在进化中共同变化（共进化），从而推断结构约束
- **pLDDT (predicted Local Distance Difference Test)**: 每个原子的预测置信度分数（0-100）。分数越高，模型对该原子位置的预测越有信心。通常 >90 表示高置信度，<50 表示可能无序
- **PAE (Predicted Aligned Error)**: 预测的对齐误差。`PAE[i][j]` 表示：如果以残基 i 所在的域为参考对齐结构，残基 j 的位置误差预计是多少埃。对判断域间相对位置特别有用
- **PTM (predicted TM-score)**: 预测的模板匹配分数，衡量整体结构的全局质量（0-1）
- **iPTM (interface predicted TM-score)**: 界面预测模板匹配分数，衡量复合物中不同链之间界面的预测质量
- **Diffusion / 去噪扩散**: 从随机噪声逐步去噪生成目标结构的生成模型方法
- **N_cycle**: Pairformer 循环迭代次数（默认 10），每次循环都让 single 和 pair representation 更加精确
- **N_step**: 扩散去噪步数（默认 200），步数越多生成质量越高但速度越慢

## 本单元做什么

本单元用**桩函数（stub functions）**模拟了 Protenix 完整的预测流程。每个子系统都用简化版本替代——不包含真实的神经网络权重和复杂计算，而是用随机张量和简单运算来模拟数据流。

这样做的目的是让学习者**先看到全貌**：
- 数据如何从一个阶段流向下一个阶段
- 每个阶段的输入和输出张量的形状（shape）是什么
- 各个超参数（N_tokens, c_s, c_z 等）如何影响张量维度

后续单元会逐一深入每个子系统的真实实现。本单元是"地图"，后续单元是"实地探索"。

## 关键代码走读

`main.py` 中的流程对应 Protenix 的四大阶段：

1. **`input_embedding()`**（约第 20-38 行）：模拟 `InputFeatureEmbedder` 和 `RelativePositionEncoding`。将序列信息转换为 `s_inputs [N_tokens, c_s_inputs]` 和 `z [N_tokens, N_tokens, c_z]`，同时建立 `atom_to_token` 的映射关系。

2. **`pairformer()`**（约第 40-58 行）：模拟 `PairformerStack`。将 `s_inputs` 投影到 `c_s` 维度后，进行 `N_cycle` 次迭代。每次迭代中 `s` 和 `z` 互相交换信息（真实系统中通过三角注意力和三角乘法更新实现）。

3. **`diffusion_sampling()`**（约第 60-85 行）：模拟 `DiffusionModule`。对每个样本，从纯噪声 `x ~ N(0, sigma_max)` 开始，经过 `N_step` 步去噪，生成 `[N_atoms, 3]` 的三维坐标。

4. **`confidence_head()`**（约第 87-115 行）：模拟 `ConfidenceHead`。计算 pLDDT、PAE、PTM、iPTM 等置信度指标，并用 `0.8 * iPTM + 0.2 * PTM` 作为排序分数选出最佳候选。

5. **`main()`**（约第 117 行起）：串联以上四个阶段，打印最终结果。

## 运行方式

```bash
cd /root/key_projects/learn-codebase/speedrun-Protenix
python unit-1-overall/main.py
```

确保已安装 PyTorch：
```bash
pip install torch
```

## 预期输出

```
🧬 Protenix 蛋白质结构预测 — 端到端总览
   配置: N_tokens=32, N_atoms=96, c_s=384, c_z=128
   循环: N_cycle=3, 扩散步数: N_step=10, 采样数: N_sample=2

============================================================
阶段 1: 输入嵌入 (InputFeatureEmbedder)
============================================================
  s_inputs (token嵌入):  torch.Size([32, 449])
  z (pair嵌入):          torch.Size([32, 32, 128])
  atom_to_token 映射:    torch.Size([96])

============================================================
阶段 2: Pairformer 迭代精炼 (N_cycle=3)
============================================================
  Cycle 1/3: s torch.Size([32, 384]), z torch.Size([32, 32, 128]), s_mean=..., z_mean=...
  Cycle 2/3: s torch.Size([32, 384]), z torch.Size([32, 32, 128]), s_mean=..., z_mean=...
  Cycle 3/3: s torch.Size([32, 384]), z torch.Size([32, 32, 128]), s_mean=..., z_mean=...

============================================================
阶段 3: 扩散去噪采样 (N_step=10, N_sample=2)
============================================================
  Sample 1: coords torch.Size([96, 3]), coord_range=[..., ...]
  Sample 2: coords torch.Size([96, 3]), coord_range=[..., ...]
  最终坐标: torch.Size([2, 96, 3])

============================================================
阶段 4: 置信度评估 (ConfidenceHead)
============================================================
  pLDDT:    torch.Size([2, 96]), mean=...
  PAE:      torch.Size([2, 32, 32]), mean=...
  Sample 1: PTM=..., iPTM=..., ranking=...
  Sample 2: PTM=..., iPTM=..., ranking=...

============================================================
预测完成!
============================================================
  生成了 2 个候选结构
  每个结构包含 96 个原子的三维坐标
  最佳候选: Sample X (ranking=...)

  在真实系统中，这些坐标会被保存为 CIF 格式的结构文件，
  可以用 PyMOL 或 ChimeraX 等工具可视化。
```

（注：由于使用了随机数，具体数值每次运行会有所不同，但张量形状是固定的。）

## 练习

1. **修改序列长度**：将 `N_tokens` 从 32 改为 50，重新运行。观察各阶段张量 shape 的变化，特别注意 `N_atoms` 和 pair representation `z` 的维度变化。思考：为什么 `z` 的大小是 `N_tokens` 的平方级别？这对长序列意味着什么？

2. **减少迭代次数**：将 `N_cycle` 从 3 改为 1，观察 Pairformer 阶段的输出差异。思考：在真实系统中，更多的循环次数为什么能提升预测质量？

3. **【费曼练习】** 用自己的话解释：为什么蛋白质结构预测需要 pair representation？单独的 single representation 为什么不够？

   提示：想想蛋白质折叠的本质——远距离的氨基酸可能在三维空间中非常接近。single representation 只描述"每个氨基酸是什么"，而 pair representation 描述"两个氨基酸之间的关系"。没有 pair representation，模型就无法直接建模残基间的距离和角度约束。

## 调试指南

### 观察点

在每个阶段后打印张量的 shape 和统计量，这是理解数据流的最佳方式：

```python
print(f"shape: {tensor.shape}")
print(f"mean: {tensor.mean():.4f}, std: {tensor.std():.4f}")
print(f"min: {tensor.min():.4f}, max: {tensor.max():.4f}")
```

### 常见问题

- **维度不匹配**：注意区分 `N_tokens`（残基数）和 `N_atoms`（原子数）。在真实系统中，每个残基包含不同数量的原子（甘氨酸 4 个，色氨酸 14 个），`atom_to_token` 映射负责在两者之间转换。
- **内存不足**：pair representation 的大小是 `O(N_tokens^2)`，对于长序列会消耗大量内存。这也是为什么真实系统需要 crop（裁剪）策略。

### 数值稳定性检查

```python
# 检查是否有 NaN 或 Inf
assert not torch.isnan(tensor).any(), "发现 NaN!"
assert not torch.isinf(tensor).any(), "发现 Inf!"

# 检查数值范围是否合理
print(f"数值范围: [{tensor.min():.4f}, {tensor.max():.4f}]")
```
