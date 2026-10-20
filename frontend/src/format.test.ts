import { describe, expect, it } from "vitest";

import { formatStatus } from "./format";

describe("formatStatus", () => {
  it("renders session state in service language", () => {
    expect(formatStatus("HUMAN_HANDLING")).toBe("人工处理中");
  });

  it("keeps unknown states visible for investigation", () => {
    expect(formatStatus("UNKNOWN_STATE")).toBe("UNKNOWN_STATE");
  });
});
