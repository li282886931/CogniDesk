import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3, BookOpen, Bot, CheckCircle2, ChevronDown, ClipboardList,
  Headphones, LayoutDashboard, MessageSquareMore, Plus, Search, Send,
  ShieldCheck, Sparkles, TicketCheck, Users
} from "lucide-react";
import { api, type Session } from "./api";
import { formatStatus } from "./format";
import "./styles.css";

type Metrics = { active_sessions: number; waiting_for_agent: number; open_tickets: number; ai_resolution_rate: number; csat: number };

const demoSession: Session = {
  session_id: "local-preview",
  customer_id: "cus-preview",
  customer_name: "林晓",
  channel: "web",
  status: "HUMAN_HANDLING",
  transfer_reason: "sensitive_intent",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  messages: [
    { message_id: "m1", sender_type: "customer", content: "我的订单已经三天没有物流更新，想申请退款。", created_at: "2026-10-20T09:20:00Z" },
    { message_id: "m2", sender_type: "robot", content: "该问题涉及退款申请，已为您转接人工客服，并保留了当前对话与订单问题摘要。", created_at: "2026-10-20T09:20:02Z" }
  ],
  tickets: []
};

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState<Session>(demoSession);
  const [message, setMessage] = useState("");
  const [metrics, setMetrics] = useState<Metrics>({ active_sessions: 12, waiting_for_agent: 4, open_tickets: 7, ai_resolution_rate: 0.64, csat: 0.88 });
  const [notice, setNotice] = useState("当前为本地服务预览，连接 API 后数据会实时同步。");
  const [loading, setLoading] = useState(true);

  const queueLabel = useMemo(() => `${sessions.filter((item) => item.status === "HUMAN_HANDLING").length || 4} 个待接入`, [sessions]);

  async function refresh() {
    try {
      const [list, dashboard] = await Promise.all([api.listSessions(), api.dashboard()]);
      setSessions(list);
      setMetrics(dashboard);
      if (list.length) {
        const detail = await api.getSession(list[0].session_id);
        setSelected(detail);
        setNotice("已同步本地服务数据。");
      }
    } catch {
      setNotice("后端未连接，正在展示可操作的本地预览。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function selectSession(session: Session) {
    if (session.session_id === "local-preview") return;
    try { setSelected(await api.getSession(session.session_id)); } catch { setNotice("无法加载该会话详情。"); }
  }

  async function send() {
    const text = message.trim();
    if (!text) return;
    if (selected.session_id === "local-preview") {
      setSelected({ ...selected, messages: [...(selected.messages ?? []), { message_id: crypto.randomUUID(), sender_type: "agent", content: text, created_at: new Date().toISOString() }] });
      setMessage("");
      setNotice("预览消息已发送。启动 API 后会写入本地数据库。");
      return;
    }
    try {
      await api.sendMessage(selected.session_id, text);
      setMessage("");
      await selectSession(selected);
      setNotice("消息已发送并记录到会话审计。");
    } catch { setNotice("消息发送失败，请检查 API 服务。"); }
  }

  async function createTicket() {
    if (selected.session_id === "local-preview") {
      setNotice("预览状态：工单将以 P1 优先级进入待处理队列。");
      return;
    }
    try {
      await api.createTicket(selected.session_id);
      await refresh();
      setNotice("工单已创建，并按 P1 SLA 进入待处理队列。");
    } catch { setNotice("工单创建失败，请检查 API 服务。"); }
  }

  const messages = selected.messages ?? demoSession.messages ?? [];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Headphones size={19} /></div><span>ServiceHub</span></div>
        <nav className="nav">
          <a className="nav-item active"><LayoutDashboard size={18} />服务工作台</a>
          <a className="nav-item"><MessageSquareMore size={18} />会话中心 <span className="count">{queueLabel.split(" ")[0]}</span></a>
          <a className="nav-item"><TicketCheck size={18} />工单管理</a>
          <a className="nav-item"><BookOpen size={18} />知识库</a>
          <a className="nav-item"><BarChart3 size={18} />运营数据</a>
        </nav>
        <div className="sidebar-footer">
          <div className="security"><ShieldCheck size={16} /><span>审计记录已启用</span></div>
          <div className="user-mini"><div className="avatar">沈</div><div><strong>沈宁</strong><span>售后技能组</span></div><ChevronDown size={15} /></div>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div><h1>服务工作台</h1><p>实时处理客户会话与服务风险</p></div>
          <div className="top-actions"><button className="icon-button" aria-label="搜索"><Search size={18} /></button><button className="primary-button"><Plus size={16} />新建会话</button></div>
        </header>
        <section className="metrics">
          <Metric icon={<Users />} label="进行中会话" value={metrics.active_sessions} note="较昨日 +12%" />
          <Metric icon={<Headphones />} label="待人工接入" value={metrics.waiting_for_agent} note="当前队列" alert />
          <Metric icon={<ClipboardList />} label="待处理工单" value={metrics.open_tickets} note="SLA 运行中" />
          <Metric icon={<Bot />} label="AI 独立解决率" value={`${Math.round(metrics.ai_resolution_rate * 100)}%`} note="本周目标 60%" />
          <Metric icon={<CheckCircle2 />} label="客户满意度" value={`${Math.round(metrics.csat * 100)}%`} note="目标 85%" />
        </section>
        <section className="work-grid">
          <div className="panel queue-panel">
            <div className="panel-heading"><div><h2>人工接入队列</h2><p>{queueLabel} · 按风险优先级排序</p></div><button className="text-button">查看全部</button></div>
            <div className="filters"><button className="filter selected">待接入</button><button className="filter">处理中</button><button className="filter">需关注</button></div>
            <div className="conversation-list">
              {(sessions.length ? sessions : [demoSession]).map((session) => (
                <button key={session.session_id} className={`conversation-row ${selected.session_id === session.session_id ? "selected" : ""}`} onClick={() => void selectSession(session)}>
                  <div className="avatar customer-avatar">{session.customer_name.slice(0, 1)}</div>
                  <div className="conversation-summary"><div><strong>{session.customer_name}</strong><span className="channel">网页</span></div><p>{session.transfer_reason === "sensitive_intent" ? "退款申请，需要人工复核" : "等待客服处理"}</p></div>
                  <div className="conversation-meta"><span className="priority high">P1</span><time>刚刚</time></div>
                </button>
              ))}
              {!loading && sessions.length === 0 && <div className="empty-queue">暂无真实会话，下面展示预览会话。</div>}
            </div>
          </div>
          <div className="panel chat-panel">
            <div className="chat-header"><div className="avatar customer-avatar">林</div><div><h2>{selected.customer_name}</h2><p><span className="online-dot" />在线 · {formatStatus(selected.status)}</p></div><button className="text-button">查看档案</button></div>
            <div className="risk-strip"><Sparkles size={15} /><span>AI 已识别：退款类敏感业务，建议保留人工复核与处理凭证。</span></div>
            <div className="messages">
              <div className="timestamp">今天 09:20</div>
              {messages.map((item) => <MessageBubble key={item.message_id} message={item} />)}
            </div>
            <div className="reply-box"><textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} placeholder="输入回复，Enter 发送，Shift + Enter 换行" /><button className="send-button" onClick={() => void send()} aria-label="发送"><Send size={18} /></button></div>
          </div>
          <aside className="right-rail">
            <div className="panel evidence-panel"><div className="panel-heading"><div><h2>AI 处理依据</h2><p>待人工核验</p></div><span className="source-badge">已溯源</span></div><div className="confidence"><span>转人工判定</span><strong>敏感业务</strong></div><div className="source-item"><BookOpen size={17} /><div><strong>退款申请服务规范</strong><p>v2.4 · 已发布 · 命中 92%</p></div></div><div className="source-item"><Bot size={17} /><div><strong>会话摘要</strong><p>客户订单物流停滞 3 天，要求退款。</p></div></div><button className="outline-button">核验知识来源</button></div>
            <div className="panel profile-panel"><div className="panel-heading"><div><h2>客户画像</h2><p>跨渠道统一身份</p></div></div><dl><div><dt>客户等级</dt><dd>黄金会员</dd></div><div><dt>历史工单</dt><dd>2 个已关闭</dd></div><div><dt>最近订单</dt><dd>SO-104382</dd></div></dl></div>
            <div className="panel ticket-panel"><div className="panel-heading"><div><h2>服务动作</h2><p>操作将写入审计记录</p></div></div><button className="ticket-action" onClick={() => void createTicket()}><TicketCheck size={17} /><span>创建退款复核工单</span><ChevronDown size={16} /></button><button className="outline-button">转接其他技能组</button></div>
          </aside>
        </section>
        <div className="notice"><ShieldCheck size={15} />{notice}</div>
      </main>
    </div>
  );
}

function Metric({ icon, label, value, note, alert = false }: { icon: React.ReactNode; label: string; value: string | number; note: string; alert?: boolean }) {
  return <div className="metric"><div className={`metric-icon ${alert ? "alert" : ""}`}>{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></div>;
}

function MessageBubble({ message }: { message: { sender_type: string; content: string } }) {
  const actor = message.sender_type === "customer" ? "customer" : message.sender_type === "robot" ? "robot" : "agent";
  const label = actor === "customer" ? "林晓" : actor === "robot" ? "智能助手" : "我";
  return <div className={`message-row ${actor}`}><div className="avatar bubble-avatar">{actor === "robot" ? <Bot size={15} /> : label.slice(0, 1)}</div><div><span className="message-author">{label}</span><div className="bubble">{message.content}</div></div></div>;
}

createRoot(document.getElementById("root")!).render(<App />);
