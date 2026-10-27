import { useEffect, useMemo, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive, BarChart3, BookOpen, Bot, CheckCircle2, ChevronDown, ClipboardList,
  FileText, Headphones, LayoutDashboard, MessageSquareMore, Plus, Search, Send,
  ShieldCheck, Sparkles, TicketCheck, Users
} from "lucide-react";
import {
  api,
  type Knowledge,
  type KnowledgeEvidence,
  type Session,
} from "./api";
import { formatStatus } from "./format";
import "./styles.css";
import "./knowledge.css";

type Metrics = {
  active_sessions: number;
  waiting_for_agent: number;
  open_tickets: number;
  ai_resolution_rate: number;
  csat: number;
};

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
    { message_id: "m2", sender_type: "robot", content: "该问题涉及退款申请，已为您转接人工客服，并保留了当前对话与订单问题摘要。", created_at: "2026-10-20T09:20:02Z" },
  ],
  tickets: [],
};

export function App() {
  const [activeView, setActiveView] = useState<"workbench" | "knowledge">("workbench");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState<Session>(demoSession);
  const [message, setMessage] = useState("");
  const [evidence, setEvidence] = useState<KnowledgeEvidence[]>([]);
  const [metrics, setMetrics] = useState<Metrics>({
    active_sessions: 12,
    waiting_for_agent: 4,
    open_tickets: 7,
    ai_resolution_rate: 0.64,
    csat: 0.88,
  });
  const [notice, setNotice] = useState("当前为本地服务预览，连接 API 后数据会实时同步。");
  const [loading, setLoading] = useState(true);

  const queueLabel = useMemo(
    () => `${sessions.filter((item) => item.status === "HUMAN_HANDLING").length || 4} 个待接入`,
    [sessions],
  );

  async function refresh() {
    try {
      const [list, dashboard] = await Promise.all([api.listSessions(), api.dashboard()]);
      setSessions(list);
      setMetrics(dashboard);
      if (list.length) {
        const detail = await api.getSession(list[0].session_id);
        setSelected(detail);
        setEvidence(detail.messages?.flatMap((item) => item.evidence ?? []) ?? []);
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
    try {
      const detail = await api.getSession(session.session_id);
      setSelected(detail);
      setEvidence(detail.messages?.flatMap((item) => item.evidence ?? []) ?? []);
    } catch {
      setNotice("无法加载该会话详情。");
    }
  }

  async function send() {
    const text = message.trim();
    if (!text) return;
    if (selected.session_id === "local-preview") {
      setSelected({
        ...selected,
        messages: [
          ...(selected.messages ?? []),
          { message_id: crypto.randomUUID(), sender_type: "agent", content: text, created_at: new Date().toISOString() },
        ],
      });
      setMessage("");
      setNotice("预览消息已发送。启动 API 后会写入本地数据库。");
      return;
    }
    try {
      const result = await api.sendMessage(selected.session_id, text);
      setEvidence(result.evidence);
      setMessage("");
      await selectSession(selected);
      setEvidence(result.evidence);
      setNotice(result.handoff_required ? "该问题已转人工，并保留了检索证据。" : "消息已发送，回复已关联知识来源。");
    } catch {
      setNotice("消息发送失败，请检查 API 服务。");
    }
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
    } catch {
      setNotice("工单创建失败，请检查 API 服务。");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Headphones size={19} /></div><span>ServiceHub</span></div>
        <nav className="nav" aria-label="主导航">
          <button className={`nav-item ${activeView === "workbench" ? "active" : ""}`} onClick={() => setActiveView("workbench")} aria-current={activeView === "workbench" ? "page" : undefined}>
            <LayoutDashboard size={18} />服务工作台
          </button>
          <button className="nav-item" onClick={() => setActiveView("workbench")}>
            <MessageSquareMore size={18} />会话中心 <span className="count">{queueLabel.split(" ")[0]}</span>
          </button>
          <button className="nav-item"><TicketCheck size={18} />工单管理</button>
          <button className={`nav-item ${activeView === "knowledge" ? "active" : ""}`} onClick={() => setActiveView("knowledge")} aria-current={activeView === "knowledge" ? "page" : undefined}>
            <BookOpen size={18} />知识库
          </button>
          <button className="nav-item"><BarChart3 size={18} />运营数据</button>
        </nav>
        <div className="sidebar-footer">
          <div className="security"><ShieldCheck size={16} /><span>审计记录已启用</span></div>
          <div className="user-mini"><div className="avatar">沈</div><div><strong>沈宁</strong><span>售后技能组</span></div><ChevronDown size={15} /></div>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{activeView === "knowledge" ? "知识库" : "服务工作台"}</h1>
            <p>{activeView === "knowledge" ? "维护已发布知识与回答依据" : "实时处理客户会话与服务风险"}</p>
          </div>
          {activeView === "workbench" && <div className="top-actions"><button className="icon-button" aria-label="搜索"><Search size={18} /></button><button className="primary-button"><Plus size={16} />新建会话</button></div>}
        </header>
        {activeView === "knowledge" ? <KnowledgeView onNotice={setNotice} /> : (
          <>
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
                <div className="risk-strip"><Sparkles size={15} /><span>AI 回复仅基于已发布知识，低置信度问题自动转人工。</span></div>
                <div className="messages">
                  <div className="timestamp">今天 09:20</div>
                  {(selected.messages ?? demoSession.messages ?? []).map((item) => <MessageBubble key={item.message_id} message={item} />)}
                </div>
                <div className="reply-box"><textarea value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }} placeholder="输入回复，Enter 发送，Shift + Enter 换行" /><button className="send-button" onClick={() => void send()} aria-label="发送"><Send size={18} /></button></div>
              </div>
              <aside className="right-rail">
                <EvidencePanel evidence={evidence} />
                <div className="panel profile-panel"><div className="panel-heading"><div><h2>客户画像</h2><p>跨渠道统一身份</p></div></div><dl><div><dt>客户等级</dt><dd>黄金会员</dd></div><div><dt>历史工单</dt><dd>2 个已关闭</dd></div><div><dt>最近订单</dt><dd>SO-104382</dd></div></dl></div>
                <div className="panel ticket-panel"><div className="panel-heading"><div><h2>服务动作</h2><p>操作将写入审计记录</p></div></div><button className="ticket-action" onClick={() => void createTicket()}><TicketCheck size={17} /><span>创建退款复核工单</span><ChevronDown size={16} /></button><button className="outline-button">转接其他技能组</button></div>
              </aside>
            </section>
          </>
        )}
        <div className="notice"><ShieldCheck size={15} />{notice}</div>
      </main>
    </div>
  );
}

function KnowledgeView({ onNotice }: { onNotice: (message: string) => void }) {
  const [items, setItems] = useState<Knowledge[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Knowledge | null>(null);
  const [filter, setFilter] = useState<"" | Knowledge["status"]>("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<"create" | "version" | null>(null);
  const [form, setForm] = useState({ title: "", category: "", content: "", source_note: "" });

  async function refreshList() {
    setLoading(true);
    try {
      const next = await api.listKnowledge(filter || undefined);
      setItems(next);
      if (selectedId && next.some((item) => item.knowledge_id === selectedId)) return;
      if (next[0]) setSelectedId(next[0].knowledge_id);
      else { setSelectedId(null); setDetail(null); }
    } catch {
      onNotice("知识库加载失败，请检查 API 服务。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refreshList(); }, [filter]);

  useEffect(() => {
    if (!selectedId) return;
    void api.getKnowledge(selectedId).then(setDetail).catch(() => onNotice("无法加载知识详情。"));
  }, [selectedId]);

  function beginCreate() {
    setEditing("create");
    setForm({ title: "", category: "", content: "", source_note: "" });
  }

  function beginVersion() {
    setEditing("version");
    setForm({ title: detail?.title ?? "", category: detail?.category ?? "", content: "", source_note: "" });
  }

  async function submitForm() {
    try {
      if (editing === "create") {
        const created = await api.createKnowledge(form);
        setSelectedId(created.knowledge_id);
        onNotice("知识草稿已创建。");
      } else if (editing === "version" && detail) {
        await api.createKnowledgeVersion(detail.knowledge_id, { content: form.content, source_note: form.source_note });
        onNotice("新版本草稿已创建。");
      }
      setEditing(null);
      await refreshList();
      if (selectedId) setDetail(await api.getKnowledge(selectedId));
    } catch {
      onNotice("知识保存失败，请检查字段和 API 服务。");
    }
  }

  async function publish() {
    if (!detail) return;
    const draft = detail.versions?.find((version) => version.status === "DRAFT");
    if (!draft) return;
    try {
      const next = await api.publishKnowledge(detail.knowledge_id, draft.version);
      setDetail(next);
      await refreshList();
      onNotice(`知识 v${draft.version} 已发布并建立向量索引。`);
    } catch {
      onNotice("发布失败，向量索引未完成，知识仍保持草稿。");
    }
  }

  async function archive() {
    if (!detail) return;
    try {
      const next = await api.archiveKnowledge(detail.knowledge_id);
      setDetail(next);
      await refreshList();
      onNotice("知识已停用，不再参与机器人检索。");
    } catch {
      onNotice("停用失败，请检查 API 服务。");
    }
  }

  return (
    <section className="knowledge-view">
      <div className="panel knowledge-list-panel">
        <div className="panel-heading">
          <div><h2>知识条目</h2><p>{items.length} 条 · 仅已发布内容参与回答</p></div>
          <button className="primary-button compact-button" onClick={beginCreate}><Plus size={15} />新建知识</button>
        </div>
        <div className="knowledge-filters">
          {(["", "PUBLISHED", "DRAFT", "ARCHIVED"] as const).map((value) => (
            <button key={value} className={`filter ${filter === value ? "selected" : ""}`} onClick={() => setFilter(value)}>
              {value === "" ? "全部" : value === "PUBLISHED" ? "已发布" : value === "DRAFT" ? "草稿" : "已停用"}
            </button>
          ))}
        </div>
        <div className="knowledge-list">
          {loading && <div className="knowledge-empty">正在加载知识库...</div>}
          {!loading && !items.length && <div className="knowledge-empty"><FileText size={18} /><span>暂无知识条目</span></div>}
          {items.map((item) => (
            <button key={item.knowledge_id} className={`knowledge-row ${item.knowledge_id === selectedId ? "selected" : ""}`} onClick={() => { setSelectedId(item.knowledge_id); setEditing(null); }}>
              <div className="knowledge-row-icon"><BookOpen size={16} /></div>
              <div className="knowledge-row-copy"><strong>{item.title}</strong><span>{item.category} · v{item.current_version}</span></div>
              <StatusBadge status={item.status} />
            </button>
          ))}
        </div>
      </div>
      <div className="panel knowledge-detail-panel">
        {editing ? (
          <div className="knowledge-editor">
            <div className="panel-heading"><div><h2>{editing === "create" ? "新建知识" : "创建新版本"}</h2><p>{editing === "create" ? "保存后默认为草稿，发布前可继续修改。" : `基于 ${detail?.title} 创建不可变新版本。`}</p></div></div>
            <label>标题<input value={form.title} disabled={editing === "version"} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="例如：订单物流服务规范" /></label>
            <label>分类<input value={form.category} disabled={editing === "version"} onChange={(event) => setForm({ ...form, category: event.target.value })} placeholder="例如：物流" /></label>
            <label>知识正文<textarea value={form.content} onChange={(event) => setForm({ ...form, content: event.target.value })} placeholder="填写客服可以引用的事实和处理规则。" /></label>
            <label>来源说明<input value={form.source_note} onChange={(event) => setForm({ ...form, source_note: event.target.value })} placeholder="例如：客服运营部" /></label>
            <div className="editor-actions"><button className="outline-button" onClick={() => setEditing(null)}>取消</button><button className="primary-button" onClick={() => void submitForm()} disabled={!form.content.trim() || (editing === "create" && (!form.title.trim() || !form.category.trim()))}><CheckCircle2 size={15} />保存草稿</button></div>
          </div>
        ) : detail ? (
          <div className="knowledge-detail">
            <div className="knowledge-detail-heading"><div><div className="detail-kicker">知识条目</div><h2>{detail.title}</h2><p>{detail.category} · 更新于 {detail.updated_at.slice(0, 10)}</p></div><StatusBadge status={detail.status} /></div>
            <div className="knowledge-actions"><button className="outline-button" onClick={beginVersion}><Plus size={15} />创建新版本</button>{detail.status === "PUBLISHED" && <button className="danger-button" onClick={() => void archive()}><Archive size={15} />停用</button>}{detail.versions?.some((version) => version.status === "DRAFT") && <button className="primary-button" onClick={() => void publish()}><CheckCircle2 size={15} />发布草稿</button>}</div>
            <div className="version-heading"><h3>版本记录</h3><span>{detail.versions?.length ?? 0} 个版本</span></div>
            <div className="version-list">
              {(detail.versions ?? []).map((version) => (
                <div className="version-row" key={version.version_id}><div><strong>v{version.version}</strong><span>{version.content}</span><small>{version.source_note || "未填写来源"} · {version.created_at.slice(0, 10)}</small></div><StatusBadge status={version.status} /></div>
              ))}
            </div>
            <div className="verification-note"><ShieldCheck size={16} /><div><strong>发布前人工核验</strong><span>机器人只会引用已发布版本，停用后立即停止参与检索。</span></div></div>
          </div>
        ) : <div className="knowledge-empty large-empty"><BookOpen size={20} /><span>选择一条知识查看详情</span></div>}
      </div>
    </section>
  );
}

export function EvidencePanel({ evidence }: { evidence: KnowledgeEvidence[] }) {
  return (
    <div className="panel evidence-panel">
      <div className="panel-heading"><div><h2>AI 处理依据</h2><p>{evidence.length ? "来自已发布知识" : "当前回复暂无可引用来源"}</p></div><span className={`source-badge ${evidence.length ? "" : "muted-badge"}`}>{evidence.length ? "已溯源" : "待核验"}</span></div>
      {evidence.length ? evidence.map((item) => (
        <div className="source-item" key={`${item.knowledge_id}-${item.version}-${item.message_id}`}><BookOpen size={17} /><div><strong>{item.title}</strong><p>v{item.version} · 命中 {Math.round(item.score * 100)}%</p><span>{item.chunk_text}</span></div></div>
      )) : <div className="evidence-empty"><Bot size={17} /><span>无命中时系统会自动建议转人工。</span></div>}
      {evidence.length > 0 && <button className="outline-button">核验知识来源</button>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status === "PUBLISHED" ? "已发布" : status === "DRAFT" ? "草稿" : "已停用"}</span>;
}

function Metric({ icon, label, value, note, alert = false }: { icon: ReactNode; label: string; value: string | number; note: string; alert?: boolean }) {
  return <div className="metric"><div className={`metric-icon ${alert ? "alert" : ""}`}>{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></div>;
}

function MessageBubble({ message }: { message: { sender_type: string; content: string } }) {
  const actor = message.sender_type === "customer" ? "customer" : message.sender_type === "robot" ? "robot" : "agent";
  const label = actor === "customer" ? "林晓" : actor === "robot" ? "智能助手" : "我";
  return <div className={`message-row ${actor}`}><div className="avatar bubble-avatar">{actor === "robot" ? <Bot size={15} /> : label.slice(0, 1)}</div><div><span className="message-author">{label}</span><div className="bubble">{message.content}</div></div></div>;
}

const root = document.getElementById("root");
if (root) createRoot(root).render(<App />);
