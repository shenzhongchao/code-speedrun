# Unit 3: 输入嵌入 — 从特征到表示

## 通俗理解

想象你要给一个从没见过蛋白质的人描述一条蛋白质链。你手上有一大堆原始数据：每个氨基酸是什么类型、每个原子的三维坐标、化学键怎么连接、哪些原子属于同一个残基……信息量巨大且杂乱。

**输入嵌入**就是一个"信息压缩器"，它把这堆原始数据压缩成两份紧凑的"摘要"：

- **s（single representation）**：每个残基/token 的"个人档案"——我是什么氨基酸？我的原子长什么样？周围环境如何？
- **z（pair representation）**：任意两个残基之间的"关系档案"——你离我多远？我们在序列上相隔几个位置？

有了 s 和 z，后续的 Pairformer 就可以在这个压缩后的表示空间里高效地推理蛋白质结构了。

## 背景知识

### 嵌入（Embedding）
将离散或高维数据映射到低维连续向量空间。例如，氨基酸类型是离散的（20种 + 特殊类型），通过 one-hot 编码变成 32 维向量，再通过线性层投影到更紧凑的表示。

### 注意力机制在局部原子邻域中的应用
蛋白质中，一个残基可能包含多个原子（甘氨酸 4 个，色氨酸 14 个）。AtomAttentionEncoder 在每个残基的原子"小组"内部做注意力计算，让原子之间交换信息，然后聚合成一个 token 级别的表示。

### 相对位置编码
不是记录"你在序列的第 42 位"（绝对位置），而是记录"你离我 3 个位置"（相对位置）。这样做的好处是：
- 对序列长度更鲁棒
- 直接编码了残基之间的距离关系
- 相邻残基的关系天然比远处残基更重要

## 关键术语

| 术语 | 含义 | 维度 |
|------|------|------|
| **InputFeatureEmbedder** | 主嵌入模块（Algorithm 2），整合所有输入特征 | 输出 s_inputs [N_token, 449] |
| **AtomAttentionEncoder** | 原子级局部注意力 + 聚合到 token 级别（Algorithm 5） | 内部 c_atom=128 |
| **RelativePositionEncoding** | 编码 token 之间的相对位置关系（Algorithm 3） | 输出 z [N_token, N_token, c_z] |
| **c_s_inputs (449)** | 输入嵌入维度，由多种特征拼接而成 | 32 + 128 + 289 |
| **c_s (384)** | Pairformer 使用的 single representation 维度 | s_inputs 经线性投影后 |
| **c_z (128)** | pair representation 维度 | RelativePositionEncoding 输出 |

### 449 维度的来源

```
c_s_inputs = 449
├── restype one-hot:        32  (20种标准氨基酸 + 12种特殊token)
├── AtomAttentionEncoder:  128  (原子级注意力聚合后的输出)
└── 其他特征拼接:          289  (profile特征、模板特征等)
```

## 本单元做什么

本单元演示输入嵌入的完整流程：

```
原始特征 (氨基酸类型, 原子坐标, 元素类型, ...)
    │
    ▼
┌─────────────────────────────┐
│   InputFeatureEmbedder      │
│                             │
│  1. AtomAttentionEncoder    │  ← 原子级注意力 → 聚合到token级
│     - 原子特征投影           │
│     - 局部注意力计算         │
│     - 按token聚合           │
│                             │
│  2. 特征拼接                │  ← restype + atom_enc + others
│     [N_token, 449]          │
│                             │
│  3. RelativePositionEncoding│  ← token间相对位置
│     [N_token, N_token, c_z] │
└─────────────────────────────┘
    │                │
    ▼                ▼
  s_inputs          z_init
 [N, 449]       [N, N, 128]
    │                │
    ▼                │
  线性投影            │
    │                │
    ▼                ▼
    s               z
 [N, 384]       [N, N, 128]
    │                │
    └───────┬────────┘
            ▼
      传入 Pairformer (Unit 4)
```

## 关键代码走读

### 真实源码位置
```
Protenix/protenix/model/modules/embedders.py
```

### AtomAttentionEncoder（Algorithm 5）核心逻辑

```python
# 1. 原子特征投影
atom_features = concat(ref_pos, ref_element, ...)  # 拼接原子级原始特征
atom_embed = linear_proj(atom_features)             # 投影到 c_atom 维度

# 2. 局部注意力（在原子邻域内）
# 真实实现中，只在每个token的原子"小组"内做注意力，而非全局
attn_out = multi_head_attention(atom_embed, atom_embed, atom_embed)
atom_embed = layer_norm(attn_out + atom_embed)      # 残差连接 + 归一化

# 3. 聚合到token级别
# 每个token取其所属原子的平均值（或加权和）
token_features = aggregate_by_token(atom_embed, atom_to_token_idx)
```

### RelativePositionEncoding（Algorithm 3）核心逻辑

```python
# 1. 计算相对位置矩阵
rel_pos[i][j] = position[i] - position[j]  # 范围 [-max, +max]

# 2. one-hot 编码
rel_pos_onehot = one_hot(rel_pos + max_rel_pos)  # [N, N, 2*max+1]

# 3. 线性投影到 c_z
z = linear(rel_pos_onehot)  # [N, N, c_z]
```

### InputFeatureEmbedder（Algorithm 2）核心逻辑

```python
# 1. 原子级处理
atom_enc_out = AtomAttentionEncoder(ref_pos, ref_element, ...)  # [N_token, 128]

# 2. 拼接所有token级特征
s_inputs = concat(restype_onehot, atom_enc_out, other_features)  # [N_token, 449]

# 3. 生成pair嵌入
z = RelativePositionEncoding(positions)  # [N_token, N_token, c_z]
```

## 运行方式

```bash
cd /root/key_projects/learn-codebase/speedrun-Protenix/unit-3-input-embedding
python main.py
```

## 预期输出

```
准备输入特征（模拟 Unit 2 的输出）...
  restype: torch.Size([16, 32])
  ref_pos: torch.Size([48, 3])
  ref_element: torch.Size([48, 128])
  atom_to_token_idx: torch.Size([48])

============================================================
InputFeatureEmbedder: 特征 → 嵌入
============================================================
  [AtomAttentionEncoder]
    原子嵌入: torch.Size([48, 128])
    注意力后: torch.Size([48, 128])
    聚合到token级别: torch.Size([16, 128])

  拼接特征: torch.Size([16, 449]) = 32 + 128 + 289

  s_inputs: torch.Size([16, 449])

  [RelativePositionEncoding]
    相对位置矩阵: torch.Size([16, 16])
    one-hot编码: torch.Size([16, 16, 65])
    pair嵌入 z: torch.Size([16, 16, 128])

============================================================
投影到 Pairformer 维度
============================================================
  s_inputs torch.Size([16, 449]) → s torch.Size([16, 384])
  z: torch.Size([16, 16, 128])
```

## 练习

1. **修改 c_atom 维度**：将 `c_atom` 从 128 改为 64，观察对 `s_inputs` 形状和数值分布的影响。思考：为什么 AtomAttentionEncoder 的内部维度变了，但 s_inputs 的维度不变？

2. **去掉 RelativePositionEncoding**：将 `z` 替换为全零张量，观察输出变化。思考：如果没有位置信息，模型还能区分序列中不同位置的残基吗？

3. **【费曼练习】** 向一个不懂深度学习的朋友解释：为什么需要先在原子级别做注意力再聚合到 token 级别？直接用 token 级别特征不行吗？

   提示：想想一个残基里不同原子的角色——骨架原子（N, CA, C, O）提供结构信息，侧链原子决定化学性质。如果直接平均所有原子特征再处理，会丢失什么信息？

4. **探索 449 的组成**：阅读真实源码 `embedders.py`，找出 449 维度的精确组成。哪些特征来自序列信息？哪些来自结构信息？

## 调试指南

### 常见问题

**Q: `atom_to_token_idx` 是什么？**
A: 一个映射数组，告诉模型每个原子属于哪个 token（残基）。例如 `[0,0,0, 1,1,1, 2,2,2, ...]` 表示前 3 个原子属于 token 0，接下来 3 个属于 token 1，以此类推。

**Q: 为什么 restype 是 32 维而不是 20 维？**
A: 20 种标准氨基酸 + 未知氨基酸 + gap + 各种特殊 token（如 DNA/RNA 碱基等），Protenix 支持多种分子类型。

**Q: 注意力计算的复杂度是多少？**
A: 全局注意力是 O(N_atoms^2)，但 AtomAttentionEncoder 使用局部注意力窗口，只在每个 token 的原子组内计算，复杂度大大降低。

**Q: 维度不匹配报错怎么办？**
A: 检查以下几点：
- `ref_pos` 应该是 [N_atoms, 3]
- `ref_element` 的 one-hot 维度是否正确
- `atom_to_token_idx` 的长度应该等于 N_atoms
- 拼接时各部分维度之和应该等于 `c_s_inputs`

### 与真实代码的差异

| 方面 | 本演示 | 真实 Protenix |
|------|--------|---------------|
| 注意力范围 | 全局注意力（简化） | 局部原子邻域注意力 |
| 特征种类 | 3 种（restype + atom_enc + 随机） | 10+ 种（profile, template, ...） |
| 聚合方式 | 简单平均 | 加权聚合 + 残差连接 |
| 批处理 | 无（单样本） | 支持批处理 + padding |

## 下一步

完成本单元后，你已经理解了：
- 原始特征如何变成 s_inputs [N_token, 449] 和 z [N_token, N_token, 128]
- s_inputs 经过线性投影变成 s [N_token, 384]

接下来在 **Unit 4: Pairformer** 中，s 和 z 将通过多轮迭代的注意力机制相互交流，逐步精炼蛋白质的结构表示。
