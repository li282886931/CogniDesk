import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { api, type KnowledgeEvidence } from "./api";
import { EvidencePanel } from "./main";

describe("knowledge API", () => {
  it("lists knowledge with an optional status filter", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: 0, data: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.listKnowledge("PUBLISHED");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/knowledge?status=PUBLISHED",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
  });

  it("publishes a selected knowledge version", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: 0, data: { status: "PUBLISHED" } }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.publishKnowledge("kn_1", 2);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/knowledge/kn_1/publish",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ version: 2 }),
      }),
    );
  });

  it("renders real evidence in the source panel", () => {
    const evidence: KnowledgeEvidence[] = [
      {
        evidence_id: "ev_1",
        message_id: "msg_1",
        knowledge_id: "kn_1",
        version: 2,
        chunk_text: "物流状态会在承诺时效内更新。",
        score: 0.93,
        title: "订单物流服务规范",
        source_note: "客服运营部",
      },
    ];

    render(<EvidencePanel evidence={evidence} />);

    expect(screen.getByText("订单物流服务规范")).toBeTruthy();
    expect(screen.getByText(/v2 · 命中 93%/)).toBeTruthy();
    expect(screen.getByText("物流状态会在承诺时效内更新。")).toBeTruthy();
  });
});
