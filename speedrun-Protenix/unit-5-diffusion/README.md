# Unit 5: 扩散模块 — 从噪声到三维结构

## 通俗理解

想象一位雕塑家面对一块粗糙的随机石块（高斯噪声），他需要一刀一刀地凿出最终的雕像（蛋白质三维结构）。

- **前向过程（加噪）**：把一座完美的雕像逐渐打碎成碎石——这是训练时做的事，给真实坐标加噪声。
- **反向过程（去噪）**：从碎石中一步步恢复雕像——这是推理时做的事，从纯噪声出发，迭代去噪。
- **噪声调度**：就是"工序表"——先用大锤粗凿大轮廓（高噪声阶段，σ=160），再用小刀细雕细节（低噪声阶段，σ→0.0004）。参数 ρ=7 控制了"先快后慢"的节奏。
- **去噪网络**：就是雕塑家本人——它接收当前的"半成品"和"现在是第几刀"的信息，输出"下一刀往哪凿"。

为什么不直接让网络回归坐标？因为同一条蛋白质序列可能折叠成多种构象（多模态分布），直接回归会输出一个"平均"结构，哪种都不像。扩散模型天然支持多模态采样——每次从不同的随机噪声出发，就能得到不同的合理构象。

## 背景知识

### 扩散模型基本原理
扩散模型（Diffusion Model）的核心思想非常简单：
1. **前向过程**：给数据逐步加高斯噪声，直到数据变成纯噪声
2. **反向过程**：训练一个神经网络，学习如何从噪声中恢复数据

这与图像生成领域的 DALL-E、Stable Diffusion 是同一类方法。区别在于：
- 图像扩散在 2D 像素空间操作
- Protenix 的扩散在 3D 原子坐标空间操作
- 蛋白质坐标需要考虑旋转/平移不变性

### 为什么用扩散而不是直接回归坐标
- **多模态分布**：同一序列可能有多种合理构象，直接回归只能输出均值
- **不确定性建模**：扩散模型自然地表达预测的不确定性
- **采样多样性**：每次从不同噪声出发，可以生成多个候选结构

### Euler 方法
最简单的常微分方程（ODE）求解器。去噪过程可以看作沿着一条 ODE 轨迹从噪声走向数据：
```
x_{i+1} = x_i + (σ_{i+1} - σ_i) * d_i
```
其中 `d_i = (x_i - x_denoised) / σ_i` 是去噪方向。

### EDM 框架（Karras et al. 2022）
Protenix 采用 EDM（Elucidating Diffusion Models）框架，核心是三个缩放因子：
- `c_in = 1 / sqrt(σ² + σ_data²)` — 输入缩放，保证网络输入方差稳定
- `c_skip = σ_data² / (σ² + σ_data²)` — skip connection 权重
- `c_out = σ * σ_data / sqrt(σ² + σ_data²)` — 输出缩放

## 关键术语

| 术语 | 含义 |
|------|------|
| **σ (sigma)** | 噪声水平，从大到小递减 |
| **σ_data** | 数据标准差（=16），用于缩放因子的计算 |
| **s_max / s_min** | 噪声调度的上下界（160 / 0.0004） |
| **ρ (rho)** | 噪声调度的形状参数（=7），控制"先快后慢"的节奏 |
| **N_step** | 去噪总步数（默认200，演示中用20） |
| **DiffusionConditioning** | Algorithm 21：将噪声水平信息注入到 trunk 嵌入（s, z）中 |
| **DiffusionTransformer** | Algorithm 23：去噪网络的核心，使用 AttentionPairBias |
| **AtomAttentionEncoder** | 将原子级坐标聚合到 token 级特征 |
| **AtomAttentionDecoder** | 将 token 级特征展开回原子级坐标预测 |
| **Fourier Embedding** | 将标量噪声水平编码为高维向量（类似位置编码） |
| **Predictor-Corrector** | 先预测（Euler 步）再校正的采样策略 |
| **c_in / c_skip / c_out** | EDM 框架的三个缩放因子，保证数值稳定性 |

## 本单元做什么

本单元演示扩散去噪的完整推理流程：

1. **噪声调度器**：生成从 σ_max=160 到 σ_min=0.0004 的噪声水平序列
2. **Fourier Embedding**：将标量噪声水平编码为高维向量
3. **DiffusionConditioning**：将噪声水平信息注入到 Pairformer 输出的 s 和 z 中
4. **去噪网络**：接收带噪坐标 + 条件信息，预测"干净"坐标
5. **Euler 采样**：从纯噪声出发，逐步去噪，生成最终三维坐标

数据流：
```
纯高斯噪声 x ~ N(0, σ_max²)
    │
    ▼ (重复 N_step 次)
┌─────────────────────────────────┐
│  σ_i → Fourier Embedding       │
│  s, z + 噪声条件 → s', z'      │  ← DiffusionConditioning
│  x_noisy → AtomAttentionEncoder │
│  Transformer(s', z') 处理       │  ← DiffusionTransformer
│  AtomAttentionDecoder → x_pred  │
│  Euler 步: x ← x + d*(σ_{i+1}-σ_i) │
└─────────────────────────────────┘
    │
    ▼
最终三维坐标 x_final [N_atoms, 3]
```

## 关键代码走读

### 噪声调度公式
```python
# 来自 protenix/model/generator.py
# σ_i = σ_data * (s_max^(1/ρ) + i/N * (s_min^(1/ρ) - s_max^(1/ρ)))^ρ
steps = torch.arange(N_step + 1) / N_step
sigmas = sigma_data * (
    s_max ** (1/rho) + steps * (s_min ** (1/rho) - s_max ** (1/rho))
) ** rho
```
这个公式产生一个"先快后慢"的递减序列。ρ=7 使得前期噪声下降很快（粗凿阶段），后期下降很慢（细雕阶段）。

### EDM 缩放因子
```python
# 来自 protenix/model/modules/diffusion.py
c_in = 1.0 / (sigma**2 + sigma_data**2).sqrt()
c_skip = sigma_data**2 / (sigma**2 + sigma_data**2)
c_out = sigma * sigma_data / (sigma**2 + sigma_data**2).sqrt()
```

### Euler 去噪步
```python
# 去噪方向
d = (x - x_denoised) / sigma_curr
# Euler 更新
x = x + d * (sigma_next - sigma_curr)
```

### 真实源码位置
- 扩散模块核心：`protenix/model/modules/diffusion.py`
  - `DiffusionConditioning` — Algorithm 21
  - `DiffusionTransformer` — Algorithm 23
  - `AtomAttentionEncoder` / `AtomAttentionDecoder`
- 采样器：`protenix/model/generator.py`
  - `InferenceNoiseScheduler` — 噪声调度
  - Predictor-Corrector 采样循环

## 运行方式

```bash
cd speedrun-Protenix/unit-5-diffusion
python main.py
```

## 预期输出

```
🧬 Protenix 扩散模块 — 从噪声到三维结构
   配置: N_atoms=48, N_step=20
   噪声调度: σ_max=160.0, σ_min=0.0004, ρ=7.0, σ_data=16.0

============================================================
噪声调度
============================================================
  σ序列(前5): ['2560.00', '1528.15', '879.40', '483.56', ...]
  σ序列(后5): [..., '0.02', '0.01', '0.01', '0.01', '0.01']
  总步数: 20

============================================================
扩散去噪采样
============================================================
  初始噪声: x range=[-xxxx.x, xxxx.x], σ=2560.00
  Step   1/20: σ=2560.0000 → 1528.1467, x range=[...], x std=...
  ...（每5步打印一次）
  Step  20/20: σ=... → ..., x range=[...], x std=...

============================================================
生成结果分析
============================================================
  最终坐标: torch.Size([48, 3])
  坐标范围: x=[...], y=[...], z=[...]
  相邻原子距离: mean=...Å, std=...Å

  ✓ 扩散采样完成！坐标将传入 ConfidenceHead (→ Unit 6)
```

注意：由于网络未经训练（随机权重），生成的坐标不会是真实的蛋白质结构。重点是理解扩散去噪的流程和各组件的作用。

## 练习

1. **调整去噪步数**：将 `N_step` 从 20 改为 5，观察最终坐标质量（std、距离分布）的变化。步数越少，去噪越粗糙。
2. **线性噪声调度**：将噪声调度改为线性递减（`sigmas = torch.linspace(s_max, s_min, N_step+1) * sigma_data`），比较与指数调度的去噪过程差异。
3. **【费曼练习】** 向一个不懂机器学习的朋友解释：为什么扩散模型比直接回归坐标更适合蛋白质结构预测？提示：想想同一序列可能折叠成多种构象——直接回归会输出"平均"结构，而扩散模型每次采样都能给出不同的合理构象。

## 调试指南

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| 坐标值爆炸（NaN 或极大值） | 缩放因子计算错误 | 检查 c_in, c_skip, c_out 公式是否正确 |
| 所有坐标收敛到同一点 | 去噪网络输出常数 | 检查网络是否正确接收了条件信息 |
| 噪声调度全为 0 | rho 参数错误 | 确认 rho=7，s_max=160，s_min=4e-4 |
| 去噪过程不收敛 | 步长过大 | 增加 N_step（如 50 或 200） |
| 相邻原子距离不合理 | 网络未训练 | 正常现象，随机权重无法产生真实结构 |
| GPU 内存不足 | N_atoms 或 c_s 过大 | 减小配置参数，或使用 CPU 运行 |
