"""
Unit 4: Pairformer — 三角注意力迭代精炼

演示 PairformerStack 如何通过三角更新和注意力机制迭代精炼 single (s) 和 pair (z) 表示。

核心思想：蛋白质是三维物体，残基之间的距离必须满足三角不等式。
Pairformer 通过"三角乘法"和"三角注意力"反复传播这种几何约束，
让 pair representation z 逐渐收敛到一个几何上自洽的状态。

对应源码：
  - protenix/model/modules/pairformer.py
  - protenix/model/triangular/triangular.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# === 配置 ===
N_tokens = 16   # 残基数量（简化版，实际蛋白质可能有数百个）
c_s = 384       # single representation 的通道数
c_z = 128       # pair representation 的通道数
N_cycle = 3     # 迭代精炼次数
n_heads = 4     # 注意力头数


# =============================================================================
# 组件 1: TriangleMultiplicationOutgoing (Algorithm 11)
# =============================================================================
class TriangleMultiplicationOutgoing(nn.Module):
    """
    三角乘法更新（出方向）

    类比：如果你(i)和朋友(k)都认识某人(j)，那你和j的关系会被你们共同的朋友k加强。
    数学：z_ij += Σ_k (a_ik ⊙ b_jk)  — i和j分别"出发"到k

    为什么叫"出方向"？因为从 i 和 j 的视角看，信息是"出去"到 k 的：
      i ---> k <--- j
    """

    def __init__(self, c_z):
        super().__init__()
        self.norm = nn.LayerNorm(c_z)
        # 两条投影路径，分别处理"从i出发"和"从j出发"的信息
        self.proj_a = nn.Linear(c_z, c_z)
        self.proj_b = nn.Linear(c_z, c_z)
        # 门控：控制每个通道的信息流量
        self.gate_a = nn.Linear(c_z, c_z)
        self.gate_b = nn.Linear(c_z, c_z)
        # 输出投影和门控
        self.out_proj = nn.Linear(c_z, c_z)
        self.out_gate = nn.Linear(c_z, c_z)

    def forward(self, z):
        """
        输入: z — pair representation, 形状 [N, N, c_z]
        输出: 更新后的 z, 形状 [N, N, c_z]
        """
        # LEARN: 三角乘法的核心——利用"第三方"k来更新i和j的关系
        z_norm = self.norm(z)

        # 门控投影：sigmoid(gate) * projection
        # 门控让模型学会选择性地传播信息
        a = torch.sigmoid(self.gate_a(z_norm)) * self.proj_a(z_norm)  # [N, N, c_z]
        b = torch.sigmoid(self.gate_b(z_norm)) * self.proj_b(z_norm)  # [N, N, c_z]

        # LEARN: 关键操作 — a[i,k] 和 b[j,k] 的外积求和
        # einsum "ikc,jkc->ijc" 意思是：对所有k求和，a的ik和b的jk逐通道相乘
        # 直觉：遍历所有中间节点k，收集 i->k 和 j->k 的信息
        update = torch.einsum("ikc,jkc->ijc", a, b)

        # 输出门控：让模型控制更新幅度
        out_gate = torch.sigmoid(self.out_gate(z_norm))
        return z + out_gate * self.out_proj(update)


# =============================================================================
# 组件 2: TriangleMultiplicationIncoming (Algorithm 12)
# =============================================================================
class TriangleMultiplicationIncoming(nn.Module):
    """
    三角乘法更新（入方向）

    类比：如果某人(k)同时认识你(i)和另一个人(j)，那你和j的关系也会被加强。
    数学：z_ij += Σ_k (a_ki ⊙ b_kj)  — k分别"到达"i和j

    为什么叫"入方向"？因为从 i 和 j 的视角看，信息是从 k "进来"的：
      i <--- k ---> j
    """

    def __init__(self, c_z):
        super().__init__()
        self.norm = nn.LayerNorm(c_z)
        self.proj_a = nn.Linear(c_z, c_z)
        self.proj_b = nn.Linear(c_z, c_z)
        self.gate_a = nn.Linear(c_z, c_z)
        self.gate_b = nn.Linear(c_z, c_z)
        self.out_proj = nn.Linear(c_z, c_z)
        self.out_gate = nn.Linear(c_z, c_z)

    def forward(self, z):
        """
        输入: z — pair representation, 形状 [N, N, c_z]
        输出: 更新后的 z, 形状 [N, N, c_z]
        """
        z_norm = self.norm(z)
        a = torch.sigmoid(self.gate_a(z_norm)) * self.proj_a(z_norm)
        b = torch.sigmoid(self.gate_b(z_norm)) * self.proj_b(z_norm)

        # LEARN: 注意和Outgoing的区别——这里是 a[k,i] 和 b[k,j]
        # einsum "kic,kjc->ijc" 意思是：k"到达"i和j
        # 直觉：遍历所有中间节点k，收集 k->i 和 k->j 的信息
        update = torch.einsum("kic,kjc->ijc", a, b)

        out_gate = torch.sigmoid(self.out_gate(z_norm))
        return z + out_gate * self.out_proj(update)


# =============================================================================
# 组件 3: TriangleAttention (Algorithm 13 / 14)
# =============================================================================
class TriangleAttention(nn.Module):
    """
    三角注意力：沿 pair 矩阵的行(starting)或列(ending)做注意力。

    - StartingNode (Algorithm 13): 固定起始节点 i，让 z[i,:] 中的所有 j 互相交流
    - EndingNode (Algorithm 14): 固定终止节点 j，让 z[:,j] 中的所有 i 互相交流

    与三角乘法的区别：
    - 三角乘法是"局部"的——只看三角关系 (i,j,k)
    - 三角注意力是"全局"的——一行/列中所有元素互相交流
    """

    def __init__(self, c_z, n_heads, mode="starting"):
        """
        参数:
            c_z: pair representation 的通道数
            n_heads: 注意力头数
            mode: "starting" 沿行做注意力, "ending" 沿列做注意力
        """
        super().__init__()
        self.mode = mode
        self.n_heads = n_heads
        self.head_dim = c_z // n_heads
        self.norm = nn.LayerNorm(c_z)
        self.qkv = nn.Linear(c_z, 3 * c_z)
        self.out_proj = nn.Linear(c_z, c_z)
        self.gate = nn.Linear(c_z, c_z)

    def forward(self, z):
        """
        输入: z — pair representation, 形状 [N, N, c_z]
        输出: 更新后的 z, 形状 [N, N, c_z]
        """
        # LEARN: 沿行做注意力 = 固定i，让所有j之间互相交流
        #        沿列做注意力 = 固定j，让所有i之间互相交流
        if self.mode == "ending":
            z = z.transpose(0, 1)  # 转置后沿行做 = 原来沿列做

        z_norm = self.norm(z)
        N = z_norm.shape[0]

        # 计算 Q, K, V
        qkv = self.qkv(z_norm).reshape(N, N, 3, self.n_heads, self.head_dim)
        q, k, v = qkv.unbind(dim=2)  # 每个形状: [N, N, n_heads, head_dim]

        # LEARN: 标准注意力 Q·K^T/√d → softmax → ·V
        # 这里 i 是"行索引"（固定的起始节点），n 是"列索引"（注意力的序列维度）
        # "inhd,jnhd->nijh" 意思是：固定行n，对列维度i和j计算注意力
        attn = torch.einsum("inhd,jnhd->nijh", q, k) / math.sqrt(self.head_dim)
        attn = F.softmax(attn, dim=1)
        out = torch.einsum("nijh,jnhd->inhd", attn, v)
        out = out.reshape(N, N, -1)

        # 门控输出
        gate = torch.sigmoid(self.gate(z_norm))
        result = z + gate * self.out_proj(out)

        if self.mode == "ending":
            result = result.transpose(0, 1)  # 转置回来
        return result


# =============================================================================
# 组件 4: AttentionPairBias (Algorithm 24)
# =============================================================================
class AttentionPairBias(nn.Module):
    """
    带 pair 偏置的注意力：对 single representation s 做注意力，
    用 pair representation z 作为注意力偏置。

    这是 pair 信息"流入" single 表示的关键通道：
    z[i,j] 的值直接影响 token i 对 token j 的注意力权重。

    直觉：z 告诉注意力"哪些残基对之间应该多关注"。
    如果 z[i,j] 很大，说明残基 i 和 j 关系密切，
    那么 s[i] 在更新时就会更多地参考 s[j] 的信息。
    """

    def __init__(self, c_s, c_z, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = c_s // n_heads
        self.norm_s = nn.LayerNorm(c_s)
        self.norm_z = nn.LayerNorm(c_z)
        self.qkv = nn.Linear(c_s, 3 * c_s)
        # 将 z 的 c_z 维投影到 n_heads 维，每个头一个偏置值
        self.bias_proj = nn.Linear(c_z, n_heads)
        self.out_proj = nn.Linear(c_s, c_s)
        self.gate = nn.Linear(c_s, c_s)

    def forward(self, s, z):
        """
        输入:
            s — single representation, 形状 [N, c_s]
            z — pair representation, 形状 [N, N, c_z]
        输出: 更新后的 s, 形状 [N, c_s]
        """
        # LEARN: pair representation z 告诉注意力"哪些token对之间应该多关注"
        s_norm = self.norm_s(s)
        N = s_norm.shape[0]

        # 计算 Q, K, V
        qkv = self.qkv(s_norm).reshape(N, 3, self.n_heads, self.head_dim)
        q, k, v = qkv.unbind(dim=1)  # 每个形状: [N, n_heads, head_dim]

        # 标准注意力分数
        attn = torch.einsum("ihd,jhd->ijh", q, k) / math.sqrt(self.head_dim)

        # LEARN: 关键——用 z 作为注意力偏置
        # 这让 pair 信息直接影响 single representation 的更新
        # bias[i,j,h] 表示"第h个头中，token i 对 token j 的额外关注度"
        bias = self.bias_proj(self.norm_z(z))  # [N, N, n_heads]
        attn = attn + bias

        attn = F.softmax(attn, dim=1)
        out = torch.einsum("ijh,jhd->ihd", attn, v).reshape(N, -1)

        # 门控输出
        gate = torch.sigmoid(self.gate(s_norm))
        return s + gate * self.out_proj(out)


# =============================================================================
# 组件 5: Transition (前馈网络)
# =============================================================================
class Transition(nn.Module):
    """
    简单的两层前馈网络：expand -> SiLU -> contract

    作用：在注意力层之后增加非线性表达能力。
    SiLU (Swish) 激活函数: x * sigmoid(x)，比 ReLU 更平滑。
    """

    def __init__(self, dim, expand_factor=4):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.linear1 = nn.Linear(dim, dim * expand_factor)
        self.linear2 = nn.Linear(dim * expand_factor, dim)

    def forward(self, x):
        """残差连接: x + FFN(LayerNorm(x))"""
        return x + self.linear2(F.silu(self.linear1(self.norm(x))))


# =============================================================================
# 组件 6: PairformerBlock
# =============================================================================
class PairformerBlock(nn.Module):
    """
    一个完整的 Pairformer 块，包含所有子组件。

    执行顺序（很重要！）：
    1. 先更新 z（pair representation）：
       z -> TriMulOut -> TriMulIn -> TriAttnStart -> TriAttnEnd -> Transition_z
    2. 再用更新后的 z 来更新 s（single representation）：
       s -> AttentionPairBias(s, z_updated) -> Transition_s

    为什么先更新 z 再更新 s？
    因为 z 包含残基对之间的关系信息，先让这些关系通过三角更新变得更准确，
    然后再用这些更准确的关系来指导 s 的更新。
    """

    def __init__(self, c_s, c_z, n_heads):
        super().__init__()
        # pair representation z 的更新组件
        self.tri_mul_out = TriangleMultiplicationOutgoing(c_z)
        self.tri_mul_in = TriangleMultiplicationIncoming(c_z)
        self.tri_attn_start = TriangleAttention(c_z, n_heads, "starting")
        self.tri_attn_end = TriangleAttention(c_z, n_heads, "ending")
        self.transition_z = Transition(c_z)
        # single representation s 的更新组件
        self.attn_pair_bias = AttentionPairBias(c_s, c_z, n_heads)
        self.transition_s = Transition(c_s)

    def forward(self, s, z):
        """
        输入:
            s — single representation, 形状 [N, c_s]
            z — pair representation, 形状 [N, N, c_z]
        输出: 更新后的 (s, z)
        """
        # LEARN: pair representation z 的更新顺序很重要
        # 先三角乘法（传播几何约束），再三角注意力（全局信息交换）
        z = self.tri_mul_out(z)    # 出方向三角乘法
        z = self.tri_mul_in(z)     # 入方向三角乘法
        z = self.tri_attn_start(z) # 沿行的三角注意力
        z = self.tri_attn_end(z)   # 沿列的三角注意力
        z = self.transition_z(z)   # 前馈网络

        # LEARN: single representation s 通过 pair-biased attention 更新
        # z 的信息通过注意力偏置"流入" s
        s = self.attn_pair_bias(s, z)
        s = self.transition_s(s)

        return s, z


# =============================================================================
# 组件 7: PairformerStack
# =============================================================================
class PairformerStack(nn.Module):
    """
    N_cycle 次迭代的 PairformerBlock 堆叠。

    每次迭代（cycle）将上一轮的输出 (s, z) 作为输入，
    通过多个 PairformerBlock 进一步精炼表示。

    这就是"迭代精炼"的核心：
    - 第1轮：建立初步的几何约束
    - 第2轮：在第1轮的基础上进一步传播和修正
    - 第3轮：继续精炼，让表示更加自洽
    """

    def __init__(self, c_s, c_z, n_heads, n_blocks=2):
        """
        参数:
            n_blocks: 每次迭代中 PairformerBlock 的数量
        """
        super().__init__()
        self.blocks = nn.ModuleList([
            PairformerBlock(c_s, c_z, n_heads) for _ in range(n_blocks)
        ])

    def forward(self, s, z):
        """依次通过所有 PairformerBlock"""
        for block in self.blocks:
            s, z = block(s, z)
        return s, z


# =============================================================================
# 主流程
# =============================================================================
def main():
    print("=" * 60)
    print("Unit 4: Pairformer — 三角注意力迭代精炼")
    print("=" * 60)
    print(f"  配置: N_tokens={N_tokens}, c_s={c_s}, c_z={c_z}")
    print(f"  N_cycle={N_cycle}, n_heads={n_heads}")
    print()

    # ------------------------------------------------------------------
    # 步骤 1: 初始化输入（模拟来自 Unit 3 InputEmbedder 的输出）
    # ------------------------------------------------------------------
    print("[步骤 1] 初始化输入表示")
    s = torch.randn(N_tokens, c_s) * 0.02       # single representation
    z = torch.randn(N_tokens, N_tokens, c_z) * 0.02  # pair representation
    print(f"  s: 形状={list(s.shape)}, 均值={s.mean():.4f}, 标准差={s.std():.4f}")
    print(f"  z: 形状={list(z.shape)}, 均值={z.mean():.4f}, 标准差={z.std():.4f}")

    # ------------------------------------------------------------------
    # 步骤 2: 构建 PairformerStack
    # ------------------------------------------------------------------
    print(f"\n[步骤 2] 构建 PairformerStack (每个cycle含2个PairformerBlock)")
    stack = PairformerStack(c_s, c_z, n_heads, n_blocks=2)

    # 统计参数量
    n_params = sum(p.numel() for p in stack.parameters())
    print(f"  总参数量: {n_params:,} ({n_params / 1e6:.1f}M)")

    # ------------------------------------------------------------------
    # 步骤 3: N_cycle 次迭代精炼
    # ------------------------------------------------------------------
    print(f"\n[步骤 3] 开始 {N_cycle} 次迭代精炼")

    with torch.no_grad():
        for cycle in range(N_cycle):
            print(f"\n{'─' * 60}")
            print(f"  Cycle {cycle + 1}/{N_cycle}")
            print(f"{'─' * 60}")

            s, z = stack(s, z)

            # LEARN: 观察 z 的对称性——好的 pair representation 应该接近对称
            # 因为 d(i,j) = d(j,i)，所以 z[i,j] 应该和 z[j,i] 接近
            z_asym = (z - z.transpose(0, 1)).abs().mean()

            print(f"  s: 均值={s.mean():.4f}, 标准差={s.std():.4f}")
            print(f"  z: 均值={z.mean():.4f}, 标准差={z.std():.4f}")
            print(f"  z 不对称度: {z_asym:.4f} (越小说明越接近对称)")

    # ------------------------------------------------------------------
    # 步骤 4: 总结输出
    # ------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("Pairformer 精炼完成!")
    print("=" * 60)
    print(f"  s: {list(s.shape)} -> 传入 DiffusionModule (Unit 5)")
    print(f"  z: {list(z.shape)} -> 传入 DiffusionModule 和 ConfidenceHead (Unit 6)")

    # ------------------------------------------------------------------
    # 步骤 5: 可视化 z 的"距离图"特征
    # ------------------------------------------------------------------
    print(f"\n[步骤 5] 可视化 z 的距离图特征（取通道平均，前8x8）")
    z_dist = z.mean(dim=-1)  # [N, N] — 取通道平均作为"伪距离"
    print(f"  （正值表示'更近'，负值表示'更远'，仅供直觉参考）")
    print()

    # 打印表头
    header = "        " + "  ".join([f"  j={j}" for j in range(min(8, N_tokens))])
    print(header)
    for i in range(min(8, N_tokens)):
        row = [f"{z_dist[i, j]:+.2f}" for j in range(min(8, N_tokens))]
        print(f"  i={i}  " + "  ".join(row))

    # ------------------------------------------------------------------
    # 步骤 6: 验证三角更新的效果
    # ------------------------------------------------------------------
    print(f"\n[步骤 6] 验证三角更新效果")
    # 检查对角线——z[i,i] 应该有特殊模式（自身和自身的关系）
    diag_mean = torch.diagonal(z_dist).mean()
    offdiag_mean = (z_dist.sum() - torch.diagonal(z_dist).sum()) / (N_tokens * (N_tokens - 1))
    print(f"  z 对角线均值: {diag_mean:.4f}")
    print(f"  z 非对角线均值: {offdiag_mean:.4f}")
    print(f"  差异: {(diag_mean - offdiag_mean):.4f}")
    print(f"  （如果对角线和非对角线有明显差异，说明模型学会了区分'自身'和'他人'）")

    print(f"\n完成! 下一步: Unit 5 — DiffusionModule（扩散模型生成三维坐标）")


if __name__ == "__main__":
    torch.manual_seed(42)
    main()
