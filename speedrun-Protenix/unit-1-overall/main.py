"""
Unit 1: Protenix 端到端总览
============================
用桩函数模拟完整的蛋白质结构预测流程。

每个阶段都用简化的张量运算替代真实的神经网络计算，
目的是让学习者看到数据如何从头到尾流过整个系统。

真实 Protenix 流程:
  序列 → InputFeatureEmbedder → PairformerStack → DiffusionModule → ConfidenceHead → 结构+置信度

本脚本对应关系:
  input_embedding()  → 阶段 1: 输入嵌入
  pairformer()       → 阶段 2: 迭代精炼
  diffusion_sampling() → 阶段 3: 扩散去噪
  confidence_head()  → 阶段 4: 置信度评估
"""

import torch
import torch.nn as nn


# === 配置 ===
# LEARN: 这些超参数控制了整个系统的张量维度，理解它们是读懂代码的第一步
N_tokens = 32       # token 数量（残基数），真实蛋白质通常几百到几千个残基
N_atoms = 32 * 3    # 原子数量（每个残基约3个主链原子 N/CA/C，简化处理）
c_s = 384           # single representation 维度（真实系统中也是 384）
c_z = 128           # pair representation 维度（真实系统中也是 128）
c_s_inputs = 449    # 输入嵌入维度（由各种输入特征拼接决定）
N_cycle = 3         # Pairformer 循环次数（真实系统默认 10）
N_step = 10         # 扩散去噪步数（真实系统默认 200，这里简化加速）
N_sample = 2        # 采样数量（生成多个候选结构，取最优）


# =============================================================================
# 阶段 1: 输入嵌入
# =============================================================================
# LEARN: 类比——把原材料(氨基酸序列)加工成标准化的零件(嵌入向量)
# 真实系统中 InputFeatureEmbedder 将 one-hot 编码、原子特征等压缩为固定维度的嵌入
def input_embedding(N_tokens, N_atoms, c_s_inputs, c_z):
    """
    模拟 InputFeatureEmbedder + RelativePositionEncoding。

    在真实 Protenix 中，这一步做了以下事情：
    1. 将氨基酸类型、原子类型等离散特征转为 one-hot 编码
    2. 通过线性层将高维稀疏特征压缩为稠密的 s_inputs
    3. 用相对位置编码初始化 pair representation z
    4. 建立 atom_to_token 映射（每个原子属于哪个残基）

    返回:
        s_inputs: [N_tokens, c_s_inputs] — 每个 token 的初始特征
        z:        [N_tokens, N_tokens, c_z] — token 对之间的初始关系
        atom_to_token: [N_atoms] — 原子到 token 的映射索引
    """
    print("=" * 60)
    print("阶段 1: 输入嵌入 (InputFeatureEmbedder)")
    print("=" * 60)

    # LEARN: s_inputs 是每个 token 的初始特征向量
    # 真实系统中由氨基酸类型(20维 one-hot)、原子特征、MSA 特征等拼接而成
    # → Unit 3 深入讲解嵌入的具体实现
    s_inputs = torch.randn(N_tokens, c_s_inputs)
    print(f"  s_inputs (token嵌入):  {s_inputs.shape}")

    # LEARN: z 是 pair representation，描述任意两个 token 之间的关系
    # 类比——z[i][j] 就像一张"关系表"，记录第i个和第j个氨基酸之间的"亲密程度"
    # 注意 z 的大小是 N_tokens 的平方，这是内存瓶颈所在
    z = torch.randn(N_tokens, N_tokens, c_z)
    print(f"  z (pair嵌入):          {z.shape}")

    # LEARN: atom_to_token 映射原子到所属的 token（残基）
    # 例如：残基0的3个原子(N,CA,C)的 atom_to_token 都是 0
    # 真实系统中每个残基的原子数不同，这里简化为每个残基固定3个原子
    atom_to_token = torch.arange(N_tokens).repeat_interleave(N_atoms // N_tokens)
    print(f"  atom_to_token 映射:    {atom_to_token.shape}")
    print(f"  (前12个值: {atom_to_token[:12].tolist()})")

    return s_inputs, z, atom_to_token


# =============================================================================
# 阶段 2: Pairformer 迭代精炼
# =============================================================================
# LEARN: 类比——反复打磨零件，每次循环都让 s 和 z 更精确
# 真实系统中使用三角注意力(Triangle Attention)和三角乘法更新(Triangle Multiplication)，
# 利用蛋白质距离矩阵的三角不等式约束：d(i,k) <= d(i,j) + d(j,k)
def pairformer(s_inputs, z, c_s, N_cycle):
    """
    模拟 PairformerStack 的 N_cycle 次迭代。

    在真实 Protenix 中，每次循环包含：
    1. Triangle Multiplication (Outgoing/Incoming) — 利用三角不等式更新 z
    2. Triangle Attention (Starting/Ending) — 在 pair 维度上做注意力
    3. Pair Transition — pair representation 的前馈网络
    4. Single Attention with Pair Bias — 用 z 作为偏置更新 s
    5. Single Transition — single representation 的前馈网络

    参数:
        s_inputs: [N_tokens, c_s_inputs] — 输入嵌入
        z: [N_tokens, N_tokens, c_z] — pair representation
        c_s: int — single representation 的目标维度
        N_cycle: int — 迭代次数

    返回:
        s: [N_tokens, c_s] — 精炼后的 single representation
        z: [N_tokens, N_tokens, c_z] — 精炼后的 pair representation
    """
    print(f"\n{'=' * 60}")
    print(f"阶段 2: Pairformer 迭代精炼 (N_cycle={N_cycle})")
    print("=" * 60)

    # LEARN: s 从 s_inputs 投影到 c_s 维度
    # 这一步对应真实系统中的 linear_s_init 层
    s = nn.Linear(s_inputs.shape[-1], c_s, bias=False)(s_inputs)
    print(f"  初始投影: s_inputs {s_inputs.shape} → s {s.shape}")

    for cycle in range(N_cycle):
        # LEARN: 每次循环中，s 和 z 互相交换信息
        # s 从 z 中获取残基间的关系信息（通过 attention with pair bias）
        # z 从 s 中获取残基自身的特征信息（通过 outer product mean）
        # → Unit 4 深入讲解三角注意力机制

        # 模拟 s 的更新（真实系统中是多头注意力 + 前馈网络）
        s = s + torch.randn_like(s) * 0.01

        # 模拟 z 的更新（真实系统中是三角乘法 + 三角注意力 + 前馈网络）
        z = z + torch.randn_like(z) * 0.01

        print(f"  Cycle {cycle + 1}/{N_cycle}: "
              f"s {s.shape}, z {z.shape}, "
              f"s_mean={s.mean():.4f}, z_mean={z.mean():.4f}")

    return s, z


# =============================================================================
# 阶段 3: 扩散模块 — 从噪声生成三维坐标
# =============================================================================
# LEARN: 类比——雕塑家从一块随机的石头(噪声)开始，一刀一刀凿出雕像(蛋白质结构)
# 每一步去噪都让坐标更接近真实结构
# 扩散模型的关键优势：可以生成多个不同的候选结构（多样性采样）
def diffusion_sampling(s, z, atom_to_token, N_atoms, N_step, N_sample):
    """
    模拟 DiffusionModule 的去噪采样过程。

    在真实 Protenix 中，扩散模块：
    1. 从高斯噪声 x ~ N(0, sigma_max^2 * I) 开始
    2. 使用训练好的去噪网络 (AtomDiffusion) 预测噪声
    3. 按照噪声调度表 (sigma schedule) 逐步去噪
    4. 去噪网络以 s, z 为条件，确保生成的结构与序列一致

    参数:
        s: [N_tokens, c_s] — single representation（作为去噪条件）
        z: [N_tokens, N_tokens, c_z] — pair representation（作为去噪条件）
        atom_to_token: [N_atoms] — 原子到 token 的映射
        N_atoms: int — 原子总数
        N_step: int — 去噪步数
        N_sample: int — 生成的候选结构数量

    返回:
        coords: [N_sample, N_atoms, 3] — 生成的三维坐标
    """
    print(f"\n{'=' * 60}")
    print(f"阶段 3: 扩散去噪采样 (N_step={N_step}, N_sample={N_sample})")
    print("=" * 60)

    # LEARN: sigma_data 是训练数据中坐标的标准差，用于归一化
    sigma_data = 16.0

    all_coords = []
    for sample_idx in range(N_sample):
        # LEARN: 从纯噪声开始
        # 初始坐标是随机的，sigma 从大到小逐步去噪
        # → Unit 5 深入讲解扩散过程和噪声调度
        x = torch.randn(N_atoms, 3) * sigma_data
        print(f"  Sample {sample_idx + 1} 初始噪声: "
              f"mean={x.mean():.2f}, std={x.std():.2f}")

        for step in range(N_step):
            # LEARN: sigma 从大到小递减，控制每步去噪的幅度
            # 真实系统使用更复杂的噪声调度（如 Karras 调度）
            sigma = sigma_data * (1 - step / N_step)

            # LEARN: 去噪网络预测当前噪声，然后从 x 中减去
            # 真实系统中这里是一个完整的 Transformer 网络
            noise_pred = torch.randn_like(x) * 0.1

            # LEARN: 简化的 Euler 采样步
            # 真实系统使用更精确的 ODE 求解器
            x = x - noise_pred * sigma * 0.01

        all_coords.append(x)
        print(f"  Sample {sample_idx + 1} 去噪完成: "
              f"coords {x.shape}, "
              f"coord_range=[{x.min():.2f}, {x.max():.2f}]")

    # LEARN: 将所有样本堆叠成一个张量
    coords = torch.stack(all_coords)  # [N_sample, N_atoms, 3]
    print(f"  最终坐标: {coords.shape}")
    return coords


# =============================================================================
# 阶段 4: 置信度评估
# =============================================================================
# LEARN: 类比——质检环节，模型给自己的预测打分
# 这些分数帮助用户判断预测结果的可靠性
def confidence_head(s, z, coords, N_tokens, N_atoms):
    """
    模拟 ConfidenceHead 的置信度预测。

    在真实 Protenix 中，ConfidenceHead 基于 s, z 和预测坐标计算：
    1. pLDDT: 每个原子的局部置信度（0-100）
    2. PAE: 任意两个残基之间的预测对齐误差
    3. PTM: 全局结构质量分数（0-1）
    4. iPTM: 界面质量分数（0-1），用于评估复合物预测

    最终用 ranking_score = 0.8 * iPTM + 0.2 * PTM 对候选结构排序。

    参数:
        s: [N_tokens, c_s] — single representation
        z: [N_tokens, N_tokens, c_z] — pair representation
        coords: [N_sample, N_atoms, 3] — 预测的三维坐标
        N_tokens: int — token 数量
        N_atoms: int — 原子数量

    返回:
        plddt: [N_sample, N_atoms] — 每个原子的 pLDDT 分数
        pae: [N_sample, N_tokens, N_tokens] — 预测对齐误差
        ptm: [N_sample] — 全局 PTM 分数
        iptm: [N_sample] — 界面 iPTM 分数
    """
    print(f"\n{'=' * 60}")
    print("阶段 4: 置信度评估 (ConfidenceHead)")
    print("=" * 60)

    N_sample = coords.shape[0]

    # LEARN: pLDDT — 每个原子的局部距离差异测试分数
    # 真实系统中通过对 s 做线性变换 + softmax 得到离散化的置信度分布
    # → Unit 6 深入讲解置信度计算
    plddt = torch.sigmoid(torch.randn(N_sample, N_atoms)) * 100
    print(f"  pLDDT:    {plddt.shape}, mean={plddt.mean():.1f}")

    # LEARN: PAE — 预测的对齐误差，衡量两个残基相对位置的准确性
    # PAE[i][j] 的含义：以残基 i 为参考对齐后，残基 j 的预测位置误差（单位：埃）
    pae = torch.abs(torch.randn(N_sample, N_tokens, N_tokens)) * 10
    print(f"  PAE:      {pae.shape}, mean={pae.mean():.1f}")

    # LEARN: PTM/iPTM — 全局结构质量分数
    # PTM 衡量整体折叠质量，iPTM 衡量链间界面质量
    # 对于单链蛋白质，PTM 和 iPTM 通常接近
    ptm = torch.sigmoid(torch.randn(N_sample)) * 0.3 + 0.5
    iptm = torch.sigmoid(torch.randn(N_sample)) * 0.3 + 0.5

    for i in range(N_sample):
        # LEARN: ranking_score 用于在多个候选结构中选出最优
        # 权重 0.8/0.2 反映了界面质量在复合物预测中的重要性
        ranking = 0.8 * iptm[i] + 0.2 * ptm[i]
        print(f"  Sample {i + 1}: PTM={ptm[i]:.3f}, iPTM={iptm[i]:.3f}, "
              f"ranking={ranking:.3f}")

    return plddt, pae, ptm, iptm


# =============================================================================
# 主流程
# =============================================================================
def main():
    """
    串联四个阶段，模拟 Protenix 的完整预测流程。

    数据流:
      序列 → [输入嵌入] → s_inputs, z
           → [Pairformer] → s, z (精炼后)
           → [扩散采样] → coords (三维坐标)
           → [置信度] → pLDDT, PAE, PTM, iPTM
    """
    print("🧬 Protenix 蛋白质结构预测 — 端到端总览")
    print(f"   配置: N_tokens={N_tokens}, N_atoms={N_atoms}, "
          f"c_s={c_s}, c_z={c_z}")
    print(f"   循环: N_cycle={N_cycle}, 扩散步数: N_step={N_step}, "
          f"采样数: N_sample={N_sample}\n")

    # 阶段 1: 输入嵌入
    # LEARN: 这是流水线的起点，将原始序列信息转换为模型可处理的张量
    s_inputs, z, atom_to_token = input_embedding(
        N_tokens, N_atoms, c_s_inputs, c_z
    )

    # 阶段 2: Pairformer 迭代精炼
    # LEARN: 这是模型的核心，通过多轮迭代让 s 和 z 编码越来越丰富的结构信息
    s, z = pairformer(s_inputs, z, c_s, N_cycle)

    # 阶段 3: 扩散去噪采样
    # LEARN: 这是 AF3/Protenix 相比 AF2 的最大创新——用扩散模型生成坐标
    coords = diffusion_sampling(s, z, atom_to_token, N_atoms, N_step, N_sample)

    # 阶段 4: 置信度评估
    # LEARN: 模型的"自我评估"，帮助用户判断哪些预测可信
    plddt, pae, ptm, iptm = confidence_head(s, z, coords, N_tokens, N_atoms)

    # === 总结 ===
    print(f"\n{'=' * 60}")
    print("预测完成!")
    print("=" * 60)
    print(f"  生成了 {N_sample} 个候选结构")
    print(f"  每个结构包含 {N_atoms} 个原子的三维坐标")

    # LEARN: 用 ranking_score 选出最佳候选
    ranking_scores = 0.8 * iptm + 0.2 * ptm
    best = ranking_scores.argmax()
    print(f"  最佳候选: Sample {best + 1} "
          f"(ranking={ranking_scores[best]:.3f})")

    print(f"\n  在真实系统中，这些坐标会被保存为 CIF 格式的结构文件，")
    print(f"  可以用 PyMOL 或 ChimeraX 等工具可视化。")


if __name__ == "__main__":
    # LEARN: 固定随机种子以确保结果可复现
    torch.manual_seed(42)
    main()
