# Unit 7: 训练流程 — 从损失函数到参数更新

## 通俗理解

想象你在教一个雕塑工厂的整条流水线。推理时，流水线独立运转；但训练时：
1. 给流水线看真实雕像（标签），在上面撒不同程度的灰尘（加噪）
2. 让流水线把灰尘擦掉（去噪），然后和原作对比打分（损失函数）
3. 流水线上的每个工人都根据分数调整手法（梯度更新）

关键：不只是最后一道工序（去噪网络）在学习，整条流水线——
从原材料加工（InputEmbedder）到精炼（Pairformer）到成型（Denoiser）——
所有环节的参数都在被优化。梯度从损失一路回传到最前面的嵌入层。

另外，有些雕像是对称的（比如花瓶），从左边看和从右边看一样。
所以在打分之前，先让流水线快速画个草图（mini-rollout），
把标签旋转到和草图最接近的角度（标签置换），这样打分才公平。

## 背景知识

- **端到端训练**：梯度流过整个模型（Embedder → Pairformer → Denoiser），所有参数联合优化
- **扩散模型的训练**：不是跑完整个去噪链，而是随机采样一个噪声水平，加噪后让网络一步去噪
- **对数正态分布**：训练时噪声水平从 `exp(N(μ, σ²))` 采样，覆盖从极小到极大的范围
- **EMA（指数移动平均）**：维护模型参数的"平滑版本"，推理时使用 EMA 权重更稳定
- **对称性问题**：蛋白质中存在对称结构（如同源二聚体、芳香环），同一结构有多种等价标注方式

## 关键术语

- **ProtenixTrainModel**: 包含所有子模块的完整训练模型
- **SmoothLDDTLoss (Algorithm 27)**: 平滑版局部距离差异测试损失，核心训练损失
- **TrainingNoiseSampler**: 训练时的噪声采样器，使用对数正态分布
- **Mini-Rollout**: 训练中的快速预测（1个样本，少量去噪步），用于标签对齐，在 `no_grad` 下运行
- **Label Permutation (标签置换)**: 将标签旋转/重排到与预测最匹配的等价形式
- **EMA (Exponential Moving Average)**: 参数的指数移动平均，`shadow = decay × shadow + (1-decay) × current`
- **alpha_diffusion / alpha_distogram**: 各损失项的权重系数
- **BondLoss**: 惩罚不正确的化学键长度
- **DistogramLoss**: token 间距离分布的交叉熵损失，梯度通过 z 流回 Pairformer

## 本单元做什么

本单元构建了一个包含完整前向路径的训练模型（`ProtenixTrainModel`），演示：

1. **完整前向路径**：InputEmbedder → Pairformer → Denoiser，梯度流过所有模块
2. **训练噪声采样**：对数正态分布 vs 推理时的确定性调度
3. **加噪 + 单步去噪**：训练时只做一步，不跑完整去噪链
4. **Mini-rollout + 标签置换**：在 `no_grad` 下快速预测，对齐对称标签
5. **多项损失计算**：SmoothLDDT + MSE + Bond + Distogram
6. **梯度验证**：打印每个模块的梯度大小，确认端到端训练
7. **EMA 参数更新**

## 关键代码走读

### 完整梯度流向

```
restype_onehot
     ↓
[InputEmbedder] → s_inputs, z_init     ← 梯度到达
     ↓
[Pairformer × N_cycle] → s, z          ← 梯度到达
     ↓                    ↓
[Denoiser]          [DistogramHead]     ← 梯度到达
(条件: s)           (输入: z)
     ↓                    ↓
x_pred               dist_logits
     ↓                    ↓
LDDT+MSE+Bond        Distogram Loss
     ↓                    ↓
     └────── total_loss ──┘
                ↓
          反向传播 → 更新所有参数
```

Denoiser 通过 `s`（Pairformer 的输出）接收条件信息。因为 `s` 带着梯度，
损失会从 Denoiser 反传到 Pairformer 再到 Embedder。DistogramHead 通过 `z` 提供另一条梯度路径。

### 训练 vs 推理的核心区别

| 方面 | 训练 | 推理 |
|------|------|------|
| 参与模块 | 全模型（Embedder+Pairformer+Denoiser） | 全模型（但无梯度） |
| 噪声采样 | 对数正态（随机） | 确定性调度（Karras） |
| 去噪步数 | 1步（单噪声水平） | 200步（完整去噪链） |
| Mini-rollout | 有（no_grad，用于标签对齐） | 无 |
| 标签置换 | 有（处理对称性） | 无 |
| 梯度 | 全模型反向传播 | 关闭 |
| 参数 | 当前参数 | EMA 参数 |

### 训练噪声采样 (`main.py:TrainingNoiseSampler`)

```python
sigma = exp(N(p_mean=-1.2, p_std=1.5)) * sigma_data
```

对数正态分布的好处：自然覆盖从 ~0.001 到 ~160 的范围，中等噪声水平被采样最多。

### SmoothLDDTLoss (`main.py:SmoothLDDTLoss`)

对每对原子 (l, m)：
1. 计算预测距离和真实距离的差：`diff = |d_pred - d_true|`
2. 在 4 个阈值 [0.5, 1, 2, 4]Å 上用 sigmoid 平滑：`score += 0.25 * sigmoid(threshold - diff)`
3. 损失 = 1 - mean(score)

### Mini-Rollout + 标签置换

1. 在 `no_grad` 下用当前模型（完整路径）快速生成 1 个预测（5步去噪）
2. 计算预测与标签所有等价排列的 RMSD
3. 选择 RMSD 最小的排列作为训练标签

### 梯度验证

每个训练步会打印各模块的平均梯度大小：
```
[梯度分布] embedder=0.0101  pairformer_blocks=0.0026  denoiser=0.0294  distogram_head=0.0001
```
所有模块都有非零梯度，确认端到端训练正常工作。

## 运行方式

```bash
python unit-7-training/main.py
```

## 预期输出

```
🧬 Protenix 训练流程 — 完整前向路径 + 损失 + 反向传播

构建完整模型:
  embedder            :    4,224 参数
  pairformer          :   61,184 参数
  denoiser            :   21,443 参数
  ...

训练步 1/5:
  [Mini-Rollout] 标签置换 RMSD: 23.63Å
  [Trunk] s: [16, 64], z: [16, 16, 32] (梯度已连接)
  [Diffusion] σ: [0.42, 9.85], x_pred: [4, 48, 3]
  [损失] lddt=0.9645, mse=420.95, bond=4.60, dist=4.20
  [梯度分布] embedder=0.0101  pairformer=0.0026  denoiser=0.0294
```

## 练习

1. 冻结 Pairformer 参数（`requires_grad=False`），只训练 Denoiser，对比损失下降速度和最终质量
2. 将 `p_mean` 从 -1.2 改为 0.0，观察噪声水平分布的变化
3. 去掉 mini-rollout 和标签置换，直接用原始标签计算损失，观察损失值的变化
4. 【费曼练习】用自己的话解释：为什么 Denoiser 需要接收 Pairformer 的输出 `s` 作为条件？如果 Denoiser 只看带噪坐标不看 `s`，会怎样？

## 调试指南

- **观察点**: 打印每个模块的梯度大小（代码已内置），确认梯度流过完整路径
- **常见问题**:
  - 某个模块梯度为零：检查前向路径中是否有 `detach()` 或 `no_grad` 断开了梯度
  - 损失爆炸：检查噪声水平是否过大，导致去噪目标不合理
  - 损失不下降：检查学习率、梯度裁剪、EMA decay 是否合适
  - NaN：检查 SmoothLDDT 中的 sigmoid 输入范围，以及距离计算中的除零
- **状态检查**: 打印 `sigma` 分布的直方图，确认覆盖了合理范围
- **隔离测试**: 冻结部分模块，验证剩余模块是否仍能正常训练
