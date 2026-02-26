"""
Unit 3: 输入嵌入 — 从特征到表示

演示 InputFeatureEmbedder 和 RelativePositionEncoding 如何将原始特征转换为模型内部表示。

核心流程：
  原始特征 (氨基酸类型, 原子坐标, 元素类型, ...)
      → AtomAttentionEncoder (原子级注意力 + 聚合)
      → 特征拼接 → s_inputs [N_token, 449]
      → RelativePositionEncoding → z [N_token, N_token, c_z]
      → 线性投影 → s [N_token, 384], z [N_token, N_token, 128]
      → 传入 Pairformer (Unit 4)

真实源码参考: Protenix/protenix/model/modules/embedders.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# === 配置 ===
N_tokens = 16           # token（残基）数量
atoms_per_token = 3     # 每个token包含的原子数（简化，真实中每个残基原子数不同）
N_atoms = N_tokens * atoms_per_token  # 总原子数
c_atom = 128            # 原子嵌入维度
c_atompair = 16         # 原子对嵌入维度
c_s_inputs = 449        # 输入嵌入总维度（32 + 128 + 289）
c_s = 384               # single representation 维度（Pairformer 使用）
c_z = 128               # pair representation 维度
NUM_RESTYPES = 32       # 残基类型数（20标准 + 12特殊）


# === 组件 1: AtomAttentionEncoder ===
class AtomAttentionEncoder(nn.Module):
    """
    模拟 Algorithm 5: 在原子级别做局部注意力，然后聚合到token级别。

    类比：每个残基是一个"小组"，组内的原子先开会讨论（注意力），
    然后选出一个代表（聚合）去参加全体大会（token级别处理）。

    为什么需要原子级注意力？
    - 一个残基内的不同原子扮演不同角色（骨架原子提供结构，侧链原子决定化学性质）
    - 原子之间的相互作用（如氢键、范德华力）需要在原子级别捕捉
    - 直接平均原子特征会丢失原子间的交互信息

    输入:
        ref_pos:            [N_atoms, 3]     原子参考坐标
        ref_element:        [N_atoms, 128]   原子元素类型 one-hot
        atom_to_token_idx:  [N_atoms]        每个原子所属的token索引
        N_tokens:           int              token总数

    输出:
        token_features:     [N_tokens, c_out] 聚合后的token级特征
    """

    def __init__(self, c_atom, c_atompair, c_out):
        super().__init__()
        # LEARN: 原子特征投影——把原始原子特征（坐标+元素类型）映射到统一的嵌入空间
        self.atom_proj = nn.Linear(3 + 128, c_atom)  # ref_pos(3) + ref_element(128) → c_atom

        # LEARN: 简化的注意力层——让原子之间交换信息
        # 真实实现中使用局部注意力窗口（只在同一token的原子间计算），这里简化为全局注意力
        self.attention = nn.MultiheadAttention(c_atom, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(c_atom)

        # LEARN: 聚合投影——将原子级特征投影到token级输出维度
        self.aggregate = nn.Linear(c_atom, c_out)

    def forward(self, ref_pos, ref_element, atom_to_token_idx, N_tokens):
        """前向传播：原子特征 → 注意力 → 聚合到token级别"""
        print("  [AtomAttentionEncoder]")

        # LEARN: 步骤1 — 拼接原子特征并投影
        # 每个原子的特征 = 三维坐标(3) + 元素类型one-hot(128)
        atom_features = torch.cat([ref_pos, ref_element], dim=-1)  # [N_atoms, 131]
        atom_embed = self.atom_proj(atom_features)  # [N_atoms, c_atom]
        print(f"    原子嵌入: {atom_embed.shape}")

        # LEARN: 步骤2 — 原子间注意力计算
        # 让每个原子"看到"其他原子，学习原子间的交互模式
        # 真实实现中，注意力只在每个token的原子组内计算（局部注意力），大大降低计算量
        atom_embed_3d = atom_embed.unsqueeze(0)  # [1, N_atoms, c_atom] — 添加batch维度
        attn_out, _ = self.attention(atom_embed_3d, atom_embed_3d, atom_embed_3d)
        atom_embed = self.norm(attn_out.squeeze(0) + atom_embed)  # 残差连接 + 层归一化
        print(f"    注意力后: {atom_embed.shape}")

        # LEARN: 步骤3 — 按token聚合
        # 每个token收集其所属原子的特征，取平均值作为该token的原子级表示
        # 这一步将 [N_atoms, c_atom] 压缩为 [N_tokens, c_atom]
        token_features = torch.zeros(N_tokens, atom_embed.shape[-1])
        counts = torch.zeros(N_tokens, 1)
        for i in range(len(atom_to_token_idx)):
            tid = atom_to_token_idx[i]
            token_features[tid] += atom_embed[i]
            counts[tid] += 1
        token_features = token_features / counts.clamp(min=1)  # 防止除以零

        # LEARN: 投影到输出维度
        output = self.aggregate(token_features)  # [N_tokens, c_out]
        print(f"    聚合到token级别: {output.shape}")
        return output


# === 组件 2: RelativePositionEncoding ===
class RelativePositionEncoding(nn.Module):
    """
    模拟 Algorithm 3: 编码token之间的相对位置。

    类比：不是记录"你在第几排"（绝对位置），而是记录"你离我几排"（相对位置）。
    蛋白质中，相邻残基的关系比远处残基更重要，相对位置编码天然地捕捉了这种距离信息。

    为什么用相对位置而非绝对位置？
    - 蛋白质长度不固定，绝对位置编码难以泛化到不同长度
    - 残基间的相互作用主要取决于它们的相对距离，而非绝对位置
    - 相对位置编码对序列平移具有不变性

    输入:
        N_tokens: int  token数量

    输出:
        z: [N_tokens, N_tokens, c_z]  pair嵌入矩阵
    """

    def __init__(self, c_z, max_rel_pos=32):
        super().__init__()
        self.max_rel_pos = max_rel_pos
        # LEARN: 将相对位置的one-hot编码投影到pair嵌入空间
        # one-hot维度 = 2 * max_rel_pos + 1（从 -max 到 +max，包含0）
        self.proj = nn.Linear(2 * max_rel_pos + 1, c_z)

    def forward(self, N_tokens):
        """前向传播：token位置 → 相对位置矩阵 → pair嵌入"""
        print("  [RelativePositionEncoding]")

        # LEARN: 步骤1 — 计算所有token对之间的相对位置
        # rel_pos[i][j] = i - j，表示token i 相对于 token j 的位置偏移
        pos = torch.arange(N_tokens)
        rel_pos = pos.unsqueeze(0) - pos.unsqueeze(1)  # [N, N]
        # 裁剪到 [-max_rel_pos, max_rel_pos]，超出范围的视为"很远"
        rel_pos = rel_pos.clamp(-self.max_rel_pos, self.max_rel_pos)

        # LEARN: 步骤2 — one-hot编码相对位置
        # 先平移到非负范围 [0, 2*max_rel_pos]，然后做one-hot
        rel_pos_shifted = rel_pos + self.max_rel_pos
        rel_pos_onehot = F.one_hot(rel_pos_shifted, 2 * self.max_rel_pos + 1).float()
        print(f"    相对位置矩阵: {rel_pos.shape}")
        print(f"    one-hot编码: {rel_pos_onehot.shape}")

        # LEARN: 步骤3 — 线性投影到 c_z 维度
        # 将离散的相对位置信息转换为连续的pair嵌入
        z = self.proj(rel_pos_onehot)  # [N, N, c_z]
        print(f"    pair嵌入 z: {z.shape}")
        return z


# === 组件 3: InputFeatureEmbedder (主模块) ===
class InputFeatureEmbedder(nn.Module):
    """
    模拟 Algorithm 2: 将所有输入特征组合成 s_inputs 和 z。

    这是输入嵌入的主模块，协调 AtomAttentionEncoder 和 RelativePositionEncoding，
    将原始特征转换为模型内部使用的 single 和 pair 表示。

    流程:
        1. AtomAttentionEncoder 处理原子级特征 → [N_token, 128]
        2. 拼接: restype(32) + atom_enc(128) + others(289) → [N_token, 449]
        3. RelativePositionEncoding → z [N_token, N_token, c_z]

    输出:
        s_inputs: [N_token, c_s_inputs=449]  token级输入嵌入
        z:        [N_token, N_token, c_z]    pair级位置嵌入
    """

    def __init__(self):
        super().__init__()
        self.atom_encoder = AtomAttentionEncoder(c_atom, c_atompair, c_out=128)
        self.rel_pos_enc = RelativePositionEncoding(c_z)

        # LEARN: 最终投影到 c_s_inputs 维度
        # 449 = 32(restype one-hot) + 128(AtomAttentionEncoder输出) + 289(其他特征)
        # 其他特征包括: profile特征、模板特征、MSA统计量等（这里用随机值模拟）
        self.final_proj = nn.Linear(32 + 128 + 289, c_s_inputs)

    def forward(self, features):
        """
        前向传播：原始特征 → s_inputs + z

        参数:
            features: 字典，包含:
                - restype:           [N_token, 32]   残基类型one-hot
                - ref_pos:           [N_atoms, 3]    原子参考坐标
                - ref_element:       [N_atoms, 128]  原子元素类型one-hot
                - atom_to_token_idx: [N_atoms]       原子→token映射
        """
        print("=" * 60)
        print("InputFeatureEmbedder: 特征 → 嵌入")
        print("=" * 60)

        # LEARN: 步骤1 — AtomAttentionEncoder 处理原子级特征
        # 原子坐标和元素类型 → 原子级注意力 → 聚合到token级别
        atom_enc_out = self.atom_encoder(
            features["ref_pos"], features["ref_element"],
            features["atom_to_token_idx"], N_tokens
        )

        # LEARN: 步骤2 — 拼接所有token级特征
        # 真实实现中，这里会拼接很多种特征（profile、模板、MSA等）
        # 我们用随机值模拟那些额外特征
        restype = features["restype"]  # [N_token, 32]
        other_features = torch.randn(N_tokens, 289)  # 模拟其他特征（profile等）

        combined = torch.cat([restype, atom_enc_out, other_features], dim=-1)
        print(f"\n  拼接特征: {combined.shape} = 32 + 128 + 289")

        s_inputs = self.final_proj(combined)
        print(f"  s_inputs: {s_inputs.shape}")

        # LEARN: 步骤3 — RelativePositionEncoding 生成 pair 嵌入
        # 编码token之间的相对位置关系，为后续的pair推理提供位置信息
        print()
        z = self.rel_pos_enc(N_tokens)

        return s_inputs, z


# === 主流程 ===
def main():
    """
    主函数：演示完整的输入嵌入流程。

    流程:
        1. 准备输入特征（模拟 Unit 2 的输出）
        2. 运行 InputFeatureEmbedder 生成 s_inputs 和 z
        3. 将 s_inputs 投影到 Pairformer 维度 s
        4. 输出统计信息
    """
    print("🧬 Protenix 输入嵌入 — 从特征到表示\n")

    # === 准备输入特征 ===
    # 这些特征在真实流程中来自 Unit 2（数据预处理）的输出
    print("准备输入特征（模拟 Unit 2 的输出）...")
    features = {
        # 残基类型 one-hot 编码：20种标准氨基酸 + 12种特殊token = 32维
        "restype": F.one_hot(
            torch.randint(0, 20, (N_tokens,)), NUM_RESTYPES
        ).float(),

        # 原子参考坐标：每个原子的三维空间位置
        "ref_pos": torch.randn(N_atoms, 3),

        # 原子元素类型 one-hot：标识每个原子是什么元素（C, N, O, S, ...）
        # 这里简化为128维one-hot（真实中维度可能不同）
        "ref_element": F.one_hot(
            torch.randint(0, 10, (N_atoms,)), 128
        ).float(),

        # 原子到token的映射：告诉模型每个原子属于哪个残基
        # 例如 [0,0,0, 1,1,1, ...] 表示每3个原子属于一个token
        "atom_to_token_idx": torch.arange(N_tokens).repeat_interleave(atoms_per_token),
    }

    for k, v in features.items():
        print(f"  {k}: {v.shape}")
    print()

    # === 运行 InputFeatureEmbedder ===
    embedder = InputFeatureEmbedder()
    with torch.no_grad():
        s_inputs, z = embedder(features)

    # === 投影到 Pairformer 维度 ===
    # s_inputs [N_token, 449] → s [N_token, 384]
    # 这一步在真实代码中是 Pairformer 输入前的线性投影
    print(f"\n{'=' * 60}")
    print("投影到 Pairformer 维度")
    print("=" * 60)
    s_proj = nn.Linear(c_s_inputs, c_s, bias=False)
    with torch.no_grad():
        s = s_proj(s_inputs)
    print(f"  s_inputs {s_inputs.shape} → s {s.shape}")
    print(f"  z: {z.shape}")

    # === 输出统计信息 ===
    print(f"\n  ✓ 嵌入完成！s 和 z 将传入 Pairformer (→ Unit 4)")
    print(f"  s 统计: mean={s.mean():.4f}, std={s.std():.4f}")
    print(f"  z 统计: mean={z.mean():.4f}, std={z.std():.4f}")


if __name__ == "__main__":
    torch.manual_seed(42)
    main()
