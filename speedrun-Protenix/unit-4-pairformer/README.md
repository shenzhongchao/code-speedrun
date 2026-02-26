# Unit 4: Pairformer — 三角注意力迭代精炼

## 通俗理解

想象一个社交网络：每个残基是一个人，pair representation `z[i][j]` 记录了 i 和 j 之间的"关系强度"。

三角更新的核心逻辑是：**如果 A 认识 B，B 认识 C，那么 A 和 C 之间也应该建立联系。**

这就是三角不等式在蛋白质结构中的体现——如果残基 i 离 k 近，k 离 j 近，那 i 离 j 也不会太远。Pairformer 就是通过反复执行这种"朋友的朋友也是朋友"的逻辑，让 pair representation 逐渐收敛到一个满足三维几何约束的状态。

## 背景知识

- **三角不等式**：三维空间中距离的基本约束 `d(i,j) <= d(i,k) + d(k,j)`。任何合理的蛋白质结构都必须满足这个约束。
- **为什么蛋白质需要这个**：蛋白质是三维物体，残基之间的距离必须满足几何约束。如果模型预测 i-k 距离为 3A，k-j 距离为 4A，但 i-j 距离为 100A，那显然不合理。三角更新就是在隐式地强制这种一致性。
- **Attention 机制回顾**：`Q * K^T / sqrt(d)` -> `softmax` -> `* V`。本单元中三角注意力沿 pair 矩阵的行或列执行标准注意力。
- **残差连接和 LayerNorm 的作用**：每个子模块都使用 `x + f(LayerNorm(x))` 的模式，确保梯度流动和训练稳定性。

## 关键术语

- **PairformerStack**: 包含多个 PairformerBlock 的堆叠，执行 `N_cycle` 次迭代。每次迭代将上一轮的输出作为输入，逐步精炼表示。
- **PairformerBlock**: 一个完整的更新块，包含三角更新 + 注意力 + 前馈网络。
- **TriangleMultiplication（三角乘法更新）**: 利用第三方残基 k 传播信息。
  - **Outgoing（出方向，Algorithm 11）**: `z_ij <- f(z_ik, z_jk)` — "从 i 和 j 出发到 k"。想象 i 和 j 各自伸出手去够 k，如果都够到了，说明 i 和 j 之间也有关系。
  - **Incoming（入方向，Algorithm 12）**: `z_ij <- f(z_ki, z_kj)` — "从 k 到达 i 和 j"。想象 k 同时指向 i 和 j，如果 k 和两者都有关系，那 i 和 j 之间也应该有关系。
- **TriangleAttention（三角注意力）**: 沿 pair 矩阵的行或列做注意力。
  - **StartingNode（Algorithm 13）**: 固定起始节点 i，让所有终止节点 j 之间互相交流信息。
  - **EndingNode（Algorithm 14）**: 固定终止节点 j，让所有起始节点 i 之间互相交流信息。
- **AttentionPairBias（Algorithm 24）**: 对 single representation `s` 做注意力，用 pair representation `z` 作为注意力偏置。这是 pair 信息"流入" single 表示的关键通道。
- **Transition**: 简单的两层前馈网络（expand -> SiLU -> contract），用于增加非线性表达能力。

## 本单元做什么

本单元实现了简化版的 PairformerBlock 和 PairformerStack，展示三角更新如何传播几何约束信息。

具体来说：
1. 实现 `TriangleMultiplicationOutgoing` 和 `TriangleMultiplicationIncoming`，展示两个方向的三角乘法更新
2. 实现 `TriangleAttention`，展示沿行和列的注意力机制
3. 实现 `AttentionPairBias`，展示 pair 信息如何影响 single 表示的更新
4. 将所有组件组装成 `PairformerBlock`，再堆叠成 `PairformerStack`
5. 运行 `N_cycle` 次迭代，观察 `s` 和 `z` 的统计量变化

## 关键代码走读

### TriangleMultiplicationOutgoing（出方向三角乘法）

核心操作是一个 einsum：

```python
# a[i,k,c] 和 b[j,k,c] 对 k 求和
update = torch.einsum("ikc,jkc->ijc", a, b)
```

这行代码的含义：对于每一对 (i, j)，遍历所有中间节点 k，将 i->k 的信息和 j->k 的信息逐通道相乘后求和。这就是"出方向"——i 和 j 都"出发"去找 k。

### TriangleMultiplicationIncoming（入方向三角乘法）

```python
# a[k,i,c] 和 b[k,j,c] 对 k 求和
update = torch.einsum("kic,kjc->ijc", a, b)
```

区别在于下标的位置：这里是 k->i 和 k->j，即 k "到达" i 和 j。两个方向的三角乘法互补，确保信息从所有可能的三角关系中传播。

### TriangleAttention

三角注意力的巧妙之处在于：它沿 pair 矩阵的一个维度做标准注意力。

- **StartingNode**: 固定 i，对 `z[i, :]`（第 i 行）做注意力。让所有 `z[i,j]` 之间互相交流。
- **EndingNode**: 固定 j，对 `z[:, j]`（第 j 列）做注意力。实现上通过转置矩阵复用同一套代码。

### AttentionPairBias

```python
# 用 z 作为注意力偏置
bias = self.bias_proj(self.norm_z(z))  # [N, N, n_heads]
attn = attn + bias  # pair 信息直接影响注意力权重
```

这是 pair 信息流入 single 表示的关键机制：`z[i,j]` 的值直接影响 token i 对 token j 的注意力权重。

### PairformerBlock 的执行顺序

```
z -> TriMulOut -> TriMulIn -> TriAttnStart -> TriAttnEnd -> Transition_z
s -> AttentionPairBias(s, z) -> Transition_s
```

先更新 z（传播几何约束），再用更新后的 z 来更新 s。这个顺序很重要。

## 运行方式

```bash
cd /root/key_projects/learn-codebase/speedrun-Protenix
python unit-4-pairformer/main.py
```

## 预期输出

程序会展示 `N_cycle` 次迭代中 `s` 和 `z` 的统计量变化：

```
初始状态:
  s: torch.Size([16, 384]), mean=..., std=...
  z: torch.Size([16, 16, 128]), mean=..., std=...

============================================================
Cycle 1/3
============================================================
  s: mean=..., std=...
  z: mean=..., std=...
  z 不对称度: ... (越小越好)

...（Cycle 2, 3 类似）

Pairformer 精炼完成!
  s: torch.Size([16, 384]) -> 传入 DiffusionModule
  z: torch.Size([16, 16, 128]) -> 传入 DiffusionModule 和 ConfidenceHead
```

观察要点：
- `z` 的不对称度是否随迭代降低（好的 pair representation 应该接近对称）
- `s` 和 `z` 的标准差是否保持在合理范围（不爆炸、不消失）

## 练习

1. **去掉三角注意力**：只保留 `TriangleMultiplication`，注释掉 `TriangleAttention`，观察 `z` 的变化模式有什么不同。三角乘法是局部传播，三角注意力是全局交流——缺少哪个影响更大？

2. **增加迭代次数**：将 `N_cycle` 从 3 改为 10，观察 `s` 和 `z` 是否收敛。如果标准差持续增长，说明什么问题？

3. **费曼练习**：用自己的话解释——`TriangleMultiplicationOutgoing` 和 `Incoming` 的区别是什么？为什么需要两个方向？（提示：想想有向图中"出边"和"入边"的区别）

4. **对称性实验**：在初始化时让 `z = (z + z.transpose(0,1)) / 2` 使其对称，观察迭代后对称性是否更好地保持。

## 调试指南

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| `z` 的值爆炸（std 持续增大） | 残差连接累积、门控初始化不当 | 检查 gate 的初始偏置，减小初始化标准差 |
| `z` 不对称度不降反升 | Outgoing 和 Incoming 没有对称化 | 这是正常的——模型不强制对称，但训练后会趋向对称 |
| 内存不足 | `N_tokens` 太大，三角注意力是 O(N^3) | 减小 `N_tokens`，或使用 chunked attention |
| 输出全为零 | gate 初始化为负值导致 sigmoid 接近 0 | 检查 gate 层的权重初始化 |

## 源码对照

本单元简化实现对应的 Protenix 源码：
- `protenix/model/modules/pairformer.py` — PairformerStack 和 PairformerBlock
- `protenix/model/triangular/triangular.py` — TriangleMultiplication 和 TriangleAttention 的完整实现

主要简化：
- 去掉了 chunked attention（用于处理长序列的内存优化）
- 去掉了 dropout（训练时的正则化）
- 简化了门控机制（原版有更复杂的 gating）
- 去掉了 batch 维度（原版支持 batch 处理）
