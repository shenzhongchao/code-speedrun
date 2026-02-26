"""
Unit 5: 扩散模块 — 从噪声到三维结构
演示扩散去噪过程如何从随机噪声生成蛋白质三维坐标。

核心思想：
  - 前向过程：给真实坐标加噪声（训练时）
  - 反向过程：从纯噪声出发，迭代去噪，恢复三维坐标（推理时）
  - 噪声调度：先粗凿（高噪声）再细雕（低噪声）

对应真实源码：
  - protenix/model/modules/diffusion.py (DiffusionConditioning, DiffusionTransformer)
  - protenix/model/generator.py (InferenceNoiseScheduler, 采样循环)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# === 配置 ===
N_tokens = 16           # token 数量（残基数）
atoms_per_token = 3     # 每个 token 的原子数
N_atoms = N_tokens * atoms_per_token  # 总原子数 = 48
c_s = 384               # single representation 维度
c_z = 128               # pair representation 维度
N_step = 20             # 去噪步数（真实值200，这里缩小以便快速演示）
sigma_data = 16.0       # 数据标准差，EDM 框架的核心常数
s_max = 160.0           # 最大噪声水平
s_min = 4e-4            # 最小噪声水平
rho = 7.0               # 调度形状参数，控制"先快后慢"的节奏


# ============================================================
# 组件 1: 噪声调度器
# ============================================================
class InferenceNoiseScheduler:
    """
    生成从大到小的噪声水平序列。
    类比：雕塑的工序表——先用大锤粗凿(高噪声)，再用小刀细雕(低噪声)。

    噪声调度公式：
      σ_i = σ_data * (s_max^(1/ρ) + i/N * (s_min^(1/ρ) - s_max^(1/ρ)))^ρ

    ρ=7 使得前期噪声下降很快（粗凿），后期下降很慢（细雕）。
    对应源码: protenix/model/generator.py — InferenceNoiseScheduler
    """

    def __init__(self, N_step, s_max, s_min, rho, sigma_data):
        self.N_step = N_step
        self.sigma_data = sigma_data

        # LEARN: 噪声调度公式 — 指数衰减，前期下降快(粗凿)，后期下降慢(细雕)
        # steps 从 0 到 1 均匀分布，共 N_step+1 个点
        steps = torch.arange(N_step + 1, dtype=torch.float64) / N_step
        sigmas = sigma_data * (
            s_max ** (1 / rho) + steps * (s_min ** (1 / rho) - s_max ** (1 / rho))
        ) ** rho
        self.sigmas = sigmas.float()

    def get_schedule(self):
        """返回噪声水平序列，长度为 N_step+1"""
        return self.sigmas


# ============================================================
# 组件 2: Fourier Embedding
# ============================================================
class FourierEmbedding(nn.Module):
    """
    将标量噪声水平编码为高维向量。
    类比：把一个数字"展开"成一组正弦/余弦波，让网络更容易理解噪声水平。

    原理与 Transformer 的位置编码相同：
      用不同频率的 sin/cos 将一个标量映射到高维空间，
      使得相近的噪声水平在嵌入空间中也相近。

    对应源码: protenix/model/modules/diffusion.py — FourierEmbedding
    """

    def __init__(self, dim=256):
        super().__init__()
        self.dim = dim
        self.proj = nn.Linear(dim, dim)

    def forward(self, sigma):
        """
        sigma: [B] — 噪声水平标量（可以是 batch）
        返回: [B, dim] — 高维嵌入
        """
        # LEARN: 类似 Transformer 的位置编码，用不同频率的正弦波编码标量
        half_dim = self.dim // 2
        freqs = torch.exp(
            -math.log(1000) * torch.arange(half_dim, device=sigma.device) / half_dim
        )
        # sigma: [B] -> [B, 1], freqs: [half_dim] -> [1, half_dim]
        x = sigma.unsqueeze(-1) * freqs.unsqueeze(0)
        # 拼接 cos 和 sin，得到 [B, dim]
        embedding = torch.cat([x.cos(), x.sin()], dim=-1)
        return self.proj(embedding)


# ============================================================
# 组件 3: DiffusionConditioning (Algorithm 21)
# ============================================================
class DiffusionConditioning(nn.Module):
    """
    Algorithm 21: 将噪声水平信息注入到 trunk 嵌入中。
    类比：告诉雕塑家"现在是粗凿阶段还是细雕阶段"，让他调整力度。

    输入：
      - s: [N_token, c_s] — 来自 Pairformer 的 single representation
      - z: [N_token, N_token, c_z] — 来自 Pairformer 的 pair representation
      - sigma: [1] — 当前噪声水平

    输出：
      - s_cond, z_cond: 注入了噪声水平信息的条件化表示

    对应源码: protenix/model/modules/diffusion.py — DiffusionConditioning
    """

    def __init__(self, c_s, c_z):
        super().__init__()
        self.fourier = FourierEmbedding(256)
        self.noise_to_s = nn.Linear(256, c_s)   # 噪声嵌入 → single 维度
        self.noise_to_z = nn.Linear(256, c_z)   # 噪声嵌入 → pair 维度
        self.norm_s = nn.LayerNorm(c_s)
        self.norm_z = nn.LayerNorm(c_z)

    def forward(self, s, z, sigma):
        """
        s: [N_token, c_s] — single representation（来自 Pairformer）
        z: [N_token, N_token, c_z] — pair representation
        sigma: [1] — 当前噪声水平
        """
        # LEARN: 步骤1 — 将噪声水平编码为高维向量
        noise_embed = self.fourier(sigma)  # [1, 256]

        # LEARN: 步骤2 — 投影到 s 和 z 的维度，然后加到归一化后的表示上
        # 这样网络就知道"现在是什么噪声水平"，从而调整去噪策略
        s_cond = self.norm_s(s) + self.noise_to_s(noise_embed)  # 广播加法
        z_cond = self.norm_z(z) + self.noise_to_z(noise_embed)  # 广播加法

        return s_cond, z_cond


# ============================================================
# 组件 4: 简化的去噪网络
# ============================================================
class SimpleDenoisingNetwork(nn.Module):
    """
    简化版 DiffusionTransformer + AtomAttentionEncoder/Decoder。

    真实系统中，这是一个完整的 Transformer，包含：
      - AtomAttentionEncoder: 将原子坐标聚合到 token 级特征
      - DiffusionTransformer: 多层注意力 + AttentionPairBias
      - AtomAttentionDecoder: 将 token 级特征展开回原子级坐标

    这里用简化的 MLP + 单层注意力模拟核心逻辑，
    重点展示数据流而非完整架构。

    对应源码:
      - protenix/model/modules/diffusion.py — DiffusionTransformer (Algorithm 23)
      - protenix/model/modules/diffusion.py — AtomAttentionEncoder / Decoder
    """

    def __init__(self, c_s, c_z, N_atoms):
        super().__init__()
        self.conditioning = DiffusionConditioning(c_s, c_z)

        # LEARN: 去噪网络接收带噪坐标和条件信息，输出"干净"坐标的预测
        self.coord_embed = nn.Linear(3, c_s)       # 坐标 → 特征空间
        self.atom_to_token_proj = nn.Linear(c_s, c_s)

        # 简化的 Transformer 层（真实系统有多层 + AttentionPairBias）
        self.attn = nn.MultiheadAttention(c_s, num_heads=4, batch_first=True)
        self.ffn = nn.Sequential(
            nn.LayerNorm(c_s),
            nn.Linear(c_s, c_s * 4),
            nn.SiLU(),                              # SiLU = Swish 激活函数
            nn.Linear(c_s * 4, c_s),
        )
        self.coord_out = nn.Linear(c_s, 3)         # 特征空间 → 坐标

    def forward(self, x_noisy, s, z, sigma, atom_to_token_idx):
        """
        x_noisy: [N_atoms, 3] — 带噪声的原子坐标
        s: [N_token, c_s] — single representation
        z: [N_token, N_token, c_z] — pair representation
        sigma: [1] — 当前噪声水平
        atom_to_token_idx: [N_atoms] — 每个原子属于哪个 token

        返回: [N_atoms, 3] — 预测的"干净"坐标
        """
        # LEARN: 步骤1 — 条件注入：告诉网络当前噪声水平
        s_cond, z_cond = self.conditioning(s, z, sigma)

        # LEARN: 步骤2 — 将坐标嵌入到特征空间（AtomAttentionEncoder 的简化版）
        coord_feat = self.coord_embed(x_noisy)  # [N_atoms, c_s]

        # LEARN: 步骤3 — 聚合到 token 级别（简化版 AtomAttentionEncoder）
        # 真实系统中用局部注意力聚合，这里用均值池化模拟
        n_tokens = s_cond.shape[0]
        token_feat = torch.zeros(n_tokens, c_s, device=x_noisy.device)
        counts = torch.zeros(n_tokens, 1, device=x_noisy.device)
        for i in range(len(atom_to_token_idx)):
            tid = atom_to_token_idx[i]
            token_feat[tid] += coord_feat[i]
            counts[tid] += 1
        token_feat = token_feat / counts.clamp(min=1)

        # LEARN: 步骤4 — 加入条件信息并做注意力（DiffusionTransformer 的简化版）
        token_feat = token_feat + s_cond
        token_feat = token_feat.unsqueeze(0)  # [1, N_token, c_s] — 加 batch 维
        attn_out, _ = self.attn(token_feat, token_feat, token_feat)
        token_feat = (token_feat + attn_out).squeeze(0)  # 残差连接
        token_feat = token_feat + self.ffn(token_feat)    # FFN + 残差

        # LEARN: 步骤5 — 展开回原子级别（简化版 AtomAttentionDecoder）
        # 每个原子从其所属 token 获取特征
        atom_feat = token_feat[atom_to_token_idx]  # [N_atoms, c_s]
        x_pred = self.coord_out(atom_feat)          # [N_atoms, 3]

        return x_pred


# ============================================================
# 组件 5: 扩散采样器
# ============================================================
def diffusion_sample(denoiser, s, z, N_atoms, atom_to_token_idx, scheduler):
    """
    Algorithm 18: 从纯噪声中采样三维坐标。
    使用 Euler 方法进行迭代去噪。

    流程：
      1. 从高斯噪声 x ~ N(0, σ_max²) 出发
      2. 对每一步 i:
         a. 计算 EDM 缩放因子 c_in, c_skip, c_out
         b. 网络预测去噪后的坐标
         c. Euler 步更新坐标
      3. 返回最终坐标

    对应源码: protenix/model/generator.py — 采样循环
    """
    sigmas = scheduler.get_schedule()

    # LEARN: 从纯高斯噪声开始，缩放到最大噪声水平
    x = torch.randn(N_atoms, 3) * sigmas[0]

    print(f"  初始噪声: x range=[{x.min():.1f}, {x.max():.1f}], "
          f"sigma={sigmas[0]:.2f}")

    for i in range(len(sigmas) - 1):
        sigma_curr = sigmas[i]
        sigma_next = sigmas[i + 1]

        # LEARN: EDM 缩放因子（Karras et al. 2022）
        # 这三个因子保证了不同噪声水平下网络的数值稳定性
        # c_in: 缩放输入，使网络输入方差接近 1
        c_in = 1.0 / (sigma_curr**2 + sigma_data**2).sqrt()
        # c_skip: skip connection 权重，高噪声时更依赖网络输出
        c_skip = sigma_data**2 / (sigma_curr**2 + sigma_data**2)
        # c_out: 缩放网络输出
        c_out = sigma_curr * sigma_data / (sigma_curr**2 + sigma_data**2).sqrt()

        # LEARN: 网络预测 + 缩放
        x_scaled = x * c_in  # 缩放输入
        sigma_tensor = sigma_curr.unsqueeze(0)
        with torch.no_grad():
            x_denoised = denoiser(x_scaled, s, z, sigma_tensor, atom_to_token_idx)

        # LEARN: 应用 skip connection 和输出缩放
        # x_denoised = c_skip * x + c_out * F_theta(c_in * x, sigma)
        x_denoised = c_skip * x + c_out * x_denoised

        # LEARN: Euler 步 — 沿去噪方向前进
        # d = (x - x_denoised) / sigma 是"去噪方向"（指向数据的方向）
        # 然后沿这个方向走一步：x_new = x + d * (sigma_next - sigma_curr)
        # 注意 sigma_next < sigma_curr，所以实际上是在减小噪声
        d = (x - x_denoised) / sigma_curr
        x = x + d * (sigma_next - sigma_curr)  # Euler 更新

        if i % 5 == 0 or i == len(sigmas) - 2:
            print(f"  Step {i + 1:3d}/{len(sigmas) - 1}: "
                  f"sigma={sigma_curr:.4f} -> {sigma_next:.4f}, "
                  f"x range=[{x.min():.2f}, {x.max():.2f}], "
                  f"x std={x.std():.2f}")

    return x


# ============================================================
# 主流程
# ============================================================
def main():
    print("Protenix 扩散模块 -- 从噪声到三维结构")
    print(f"   配置: N_atoms={N_atoms}, N_step={N_step}")
    print(f"   噪声调度: sigma_max={s_max}, sigma_min={s_min}, "
          f"rho={rho}, sigma_data={sigma_data}\n")

    # --- 模拟 Pairformer 输出（来自 Unit 4）---
    s = torch.randn(N_tokens, c_s) * 0.02   # single representation
    z = torch.randn(N_tokens, N_tokens, c_z) * 0.02  # pair representation
    # 每个 token 对应 atoms_per_token 个原子
    atom_to_token_idx = torch.arange(N_tokens).repeat_interleave(atoms_per_token)

    # --- 噪声调度 ---
    print("=" * 60)
    print("噪声调度")
    print("=" * 60)
    scheduler = InferenceNoiseScheduler(N_step, s_max, s_min, rho, sigma_data)
    sigmas = scheduler.get_schedule()
    print(f"  sigma 序列(前5): {[f'{v:.2f}' for v in sigmas[:5].tolist()]}")
    print(f"  sigma 序列(后5): {[f'{v:.4f}' for v in sigmas[-5:].tolist()]}")
    print(f"  总步数: {len(sigmas) - 1}")
    print(f"  最大噪声: {sigmas[0]:.2f}, 最小噪声: {sigmas[-1]:.6f}")

    # --- 构建去噪网络 ---
    denoiser = SimpleDenoisingNetwork(c_s, c_z, N_atoms)
    total_params = sum(p.numel() for p in denoiser.parameters())
    print(f"\n  去噪网络参数量: {total_params:,}")

    # --- 扩散采样 ---
    print(f"\n{'=' * 60}")
    print("扩散去噪采样")
    print("=" * 60)
    coords = diffusion_sample(denoiser, s, z, N_atoms, atom_to_token_idx, scheduler)

    # --- 结果分析 ---
    print(f"\n{'=' * 60}")
    print("生成结果分析")
    print("=" * 60)
    print(f"  最终坐标形状: {coords.shape}")
    print(f"  坐标范围: x=[{coords[:, 0].min():.2f}, {coords[:, 0].max():.2f}]")
    print(f"            y=[{coords[:, 1].min():.2f}, {coords[:, 1].max():.2f}]")
    print(f"            z=[{coords[:, 2].min():.2f}, {coords[:, 2].max():.2f}]")

    # 计算相邻原子距离（真实蛋白质中键长约 1.5 Angstrom）
    dists = (coords[1:] - coords[:-1]).norm(dim=-1)
    print(f"  相邻原子距离: mean={dists.mean():.2f}A, std={dists.std():.2f}A")

    # --- 训练过程简述 ---
    print(f"\n{'=' * 60}")
    print("训练过程简述（本演示不执行训练，仅说明流程）")
    print("=" * 60)
    print("  1. 从训练集取真实坐标 x_true")
    print("  2. 随机采样噪声水平 sigma ~ p(sigma)")
    print("  3. 加噪: x_noisy = x_true + sigma * epsilon, epsilon ~ N(0, I)")
    print("  4. 网络预测: x_pred = F_theta(c_in * x_noisy, sigma)")
    print("  5. 损失: L = ||x_pred - x_true||^2 (加权)")
    print("  6. 反向传播更新网络参数")

    print(f"\n  [完成] 扩散采样完成。坐标将传入 ConfidenceHead (-> Unit 6)")
    print(f"  在真实系统中，会生成多个样本(N_sample=5)并用置信度排序。")


if __name__ == "__main__":
    torch.manual_seed(42)
    main()
