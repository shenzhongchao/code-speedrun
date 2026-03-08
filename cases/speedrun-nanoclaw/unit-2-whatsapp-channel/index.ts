/**
 * Unit 2: WhatsApp 通道 — 消息收发与连接管理
 *
 * 模拟 WhatsApp 通道的核心行为：
 * 连接/断线重连、消息接收分发、消息发送（带前缀）、断线队列
 */
import { fileURLToPath } from "url";
import type { Channel, NewMessage, OnInboundMessage } from "../shared/types.js";

export type { Channel, NewMessage, OnInboundMessage };

// ============================================================
// LEARN: Channel 接口 — 通道抽象层
// 类比：所有快递公司（顺丰、圆通、中通）都必须实现"收件、派件、查询"这几个操作
// NanoClaw 的 Channel 接口让 WhatsApp、Telegram、Slack 都能用同一套逻辑处理
// ============================================================

const DEFAULT_ASSISTANT_NAME = "Andy";
const DEFAULT_HAS_OWN_NUMBER = false;

export interface WhatsAppChannelOpts {
  onMessage: OnInboundMessage;
  assistantName?: string;
  hasOwnNumber?: boolean;
}

export class WhatsAppChannel implements Channel {
  name = "whatsapp";
  private connected = false;
  // LEARN: 断线消息队列 — 断线期间的消息不会丢失，重连后自动发送
  // 类比：快递站关门了，包裹先堆在门口，开门后一起派送
  private outgoingQueue: Array<{ jid: string; text: string }> = [];
  private flushing = false;
  private onMessage: OnInboundMessage;
  private assistantName: string;
  private hasOwnNumber: boolean;

  constructor(opts: WhatsAppChannelOpts) {
    this.onMessage = opts.onMessage;
    this.assistantName = opts.assistantName || DEFAULT_ASSISTANT_NAME;
    this.hasOwnNumber = opts.hasOwnNumber || DEFAULT_HAS_OWN_NUMBER;
  }

  async connect(): Promise<void> {
    // 真实实现：调用 makeWASocket() 创建 WebSocket 连接
    // 然后监听 connection.update 事件处理连接状态变化
    this.connected = true;
  }

  async sendMessage(jid: string, text: string): Promise<void> {
    // LEARN: 消息前缀 — 共用号码时加 "Andy: " 前缀区分人和机器人
    const prefixed = this.hasOwnNumber
      ? text
      : `${this.assistantName}: ${text}`;

    if (!this.connected) {
      this.outgoingQueue.push({ jid, text: prefixed });
      return;
    }

    // 真实实现：await this.sock.sendMessage(jid, { text: prefixed })
    console.log(`[WhatsApp] 发送: ${jid} <- "${prefixed.slice(0, 60)}"`);
  }

  isConnected(): boolean {
    return this.connected;
  }

  // LEARN: ownsJid — 路由的关键
  // WhatsApp 拥有 @g.us（群聊）和 @s.whatsapp.net（私聊）
  ownsJid(jid: string): boolean {
    return jid.endsWith("@g.us") || jid.endsWith("@s.whatsapp.net");
  }

  async disconnect(): Promise<void> {
    this.connected = false;
  }

  async setTyping(jid: string, isTyping: boolean): Promise<void> {
    // 真实实现：await this.sock.sendPresenceUpdate(status, jid)
  }

  // --- 模拟方法（供演示和 Unit 1 组装使用）---

  simulateDisconnect(): void {
    this.connected = false;
  }

  async simulateReconnect(): Promise<void> {
    this.connected = true;
    await this.flushOutgoingQueue();
  }

  simulateIncomingMessage(
    chatJid: string,
    senderName: string,
    content: string,
    fromMe = false
  ): void {
    const isBotMessage = this.hasOwnNumber
      ? fromMe
      : content.startsWith(`${this.assistantName}:`);

    const msg: NewMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      chat_jid: chatJid,
      sender: `${senderName.toLowerCase()}@s.whatsapp.net`,
      sender_name: senderName,
      content,
      timestamp: new Date().toISOString(),
      is_from_me: fromMe,
      is_bot_message: isBotMessage,
    };

    if (!isBotMessage) {
      this.onMessage(chatJid, msg);
    }
  }

  getQueueLength(): number {
    return this.outgoingQueue.length;
  }

  private async flushOutgoingQueue(): Promise<void> {
    if (this.flushing || this.outgoingQueue.length === 0) return;
    this.flushing = true;
    try {
      while (this.outgoingQueue.length > 0) {
        const item = this.outgoingQueue.shift()!;
        console.log(`[WhatsApp] 队列消息已发送: ${item.jid}`);
      }
    } finally {
      this.flushing = false;
    }
  }
}

// ============================================================
// LEARN: 路由函数 — 根据 JID 找到正确的通道
// ============================================================
export function routeOutbound(channels: Channel[], jid: string, text: string): Promise<void> {
  const channel = channels.find((c) => c.ownsJid(jid) && c.isConnected());
  if (!channel) throw new Error(`No channel for JID: ${jid}`);
  return channel.sendMessage(jid, text);
}

export function findChannel(channels: Channel[], jid: string): Channel | undefined {
  return channels.find((c) => c.ownsJid(jid));
}

// ============================================================
// LEARN: 消息格式化 — 把消息数组变成 Claude 能理解的 XML
// ============================================================
export function escapeXml(s: string): string {
  if (!s) return "";
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function formatMessages(messages: NewMessage[]): string {
  const lines = messages.map(
    (m) =>
      `<message sender="${escapeXml(m.sender_name)}" time="${m.timestamp}">${escapeXml(m.content)}</message>`
  );
  return `<messages>\n${lines.join("\n")}\n</messages>`;
}

export function stripInternalTags(text: string): string {
  return text.replace(/<internal>[\s\S]*?<\/internal>/g, "").trim();
}

// ============================================================
// 独立运行时的演示
// ============================================================
async function main(): Promise<void> {
  const wa = new WhatsAppChannel({
    onMessage: (chatJid, msg) => {
      console.log(
        `[回调] 收到消息: ${chatJid}, 发送者: ${msg.sender_name}, 内容: "${msg.content}"`
      );
    },
  });

  await wa.connect();
  console.log("[通道] 已连接");

  console.log(`[通道] ownsJid("chat@g.us") = ${wa.ownsJid("chat@g.us")}`);
  console.log(`[通道] ownsJid("tg:12345") = ${wa.ownsJid("tg:12345")}`);

  console.log("--- 模拟收到群聊消息 ---");
  wa.simulateIncomingMessage("chat-group@g.us", "李四", "@Andy 帮我查一下");

  console.log("--- 模拟收到私聊消息 ---");
  wa.simulateIncomingMessage("user@s.whatsapp.net", "王五", "你好");

  console.log("--- 发送回复 ---");
  await wa.sendMessage("chat-group@g.us", "好的，我来查一下");

  console.log("--- 模拟断线 ---");
  wa.simulateDisconnect();
  console.log("[通道] 断线期间发送消息...");
  await wa.sendMessage("user@s.whatsapp.net", "这条消息会被缓存");
  console.log(`[通道] 队列长度: ${wa.getQueueLength()}`);

  console.log("--- 模拟重连 ---");
  await wa.simulateReconnect();

  console.log("--- 测试多通道路由 ---");
  const channels: Channel[] = [wa];
  await routeOutbound(channels, "chat-group@g.us", "通过路由发送");
  try {
    await routeOutbound(channels, "tg:12345", "这条会失败");
  } catch (e: any) {
    console.log(`[路由] 错误: ${e.message}`);
  }

  console.log("--- 演示结束 ---");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(console.error);
}
