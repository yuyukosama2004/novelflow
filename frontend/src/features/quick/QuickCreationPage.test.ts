import { describe, expect, it } from "vitest";

import { buildQuickBrief } from "./quickBrief";

describe("buildQuickBrief", () => {
  it("turns one idea into the five-field quick brief", () => {
    const brief = buildQuickBrief("失忆侦探追查自己的过去", "3000 字短篇");

    expect(brief.conflict).toBe("失忆侦探追查自己的过去");
    expect(brief.targetLength).toBe("3000 字短篇");
    expect(Object.keys(brief)).toHaveLength(5);
  });
});
