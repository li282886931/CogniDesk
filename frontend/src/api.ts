export type Session = {
  session_id: string;
  customer_id: string;
  customer_name: string;
  channel: string;
  status: string;
  assignee_name?: string | null;
  transfer_reason?: string | null;
  created_at: string;
  updated_at: string;
  messages?: Message[];
  tickets?: Ticket[];
};

export type Message = {
  message_id: string;
  sender_type: "customer" | "robot" | "agent" | "system";
  content: string;
  created_at: string;
  evidence?: KnowledgeEvidence[];
};

export type Ticket = {
  ticket_id: string;
  title: string;
  category: string;
  priority: string;
  status: string;
  sla_due_at: string;
};

export type KnowledgeVersion = {
  version_id: string;
  knowledge_id: string;
  version: number;
  content: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  source_note?: string | null;
  effective_from?: string | null;
  effective_until?: string | null;
  created_by: string;
  created_at: string;
};

export type Knowledge = {
  knowledge_id: string;
  title: string;
  category: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  current_version: number;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  versions?: KnowledgeVersion[];
};

export type KnowledgeEvidence = {
  evidence_id: string;
  message_id: string;
  knowledge_id: string;
  version: number;
  chunk_text: string;
  score: number;
  title: string;
  source_note?: string | null;
};

export type MessageSendResult = {
  message_id: string;
  session_id: string;
  handler: "agent" | "robot" | "human" | "idempotent";
  reply?: string | null;
  reply_message_id?: string | null;
  evidence: KnowledgeEvidence[];
  confidence?: number | null;
  handoff_required: boolean;
  session: Session;
};

type Envelope<T> = { code: number; data: T };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options
  });
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return (await response.json() as Envelope<T>).data;
}

export const api = {
  listSessions: (status?: string) => request<Session[]>(`/sessions${status ? `?status=${status}` : ""}`),
  getSession: (sessionId: string) => request<Session>(`/sessions/${sessionId}`),
  createSession: (customerName: string) => request<Session>("/sessions", { method: "POST", body: JSON.stringify({ customer_name: customerName, channel: "web" }) }),
  sendMessage: (sessionId: string, content: string) =>
    request<MessageSendResult>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ client_msg_id: `web_${crypto.randomUUID()}`, sender_type: "agent", content, msg_type: "text" })
    }),
  transfer: (sessionId: string) => request<Session>(`/sessions/${sessionId}/transfer`, { method: "POST", body: JSON.stringify({ reason: "user_request" }) }),
  createTicket: (sessionId: string) =>
    request<Ticket>("/tickets", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, title: "需要人工复核", category: "售后-退款", priority: "P1", summary: "由客服工作台创建，等待业务团队跟进。" })
    }),
  listKnowledge: (status?: string) => request<Knowledge[]>(`/knowledge${status ? `?status=${status}` : ""}`),
  getKnowledge: (knowledgeId: string) => request<Knowledge>(`/knowledge/${knowledgeId}`),
  createKnowledge: (payload: { title: string; category: string; content: string; source_note?: string }) =>
    request<Knowledge>("/knowledge", { method: "POST", body: JSON.stringify(payload) }),
  createKnowledgeVersion: (knowledgeId: string, payload: { content: string; source_note?: string }) =>
    request<KnowledgeVersion>(`/knowledge/${knowledgeId}/versions`, { method: "POST", body: JSON.stringify(payload) }),
  publishKnowledge: (knowledgeId: string, version: number) =>
    request<Knowledge>(`/knowledge/${knowledgeId}/publish`, { method: "POST", body: JSON.stringify({ version }) }),
  archiveKnowledge: (knowledgeId: string) =>
    request<Knowledge>(`/knowledge/${knowledgeId}/archive`, { method: "POST" }),
  getKnowledgeEvidence: (knowledgeId: string) =>
    request<KnowledgeEvidence[]>(`/knowledge/${knowledgeId}/evidence`),
  dashboard: () => request<{ active_sessions: number; waiting_for_agent: number; open_tickets: number; ai_resolution_rate: number; csat: number }>("/dashboard")
};
