import { describe, expect, it } from "vitest";

import { buildQuickBrief } from "./quickBrief";

describe("buildQuickBrief", () => {
  it("keeps a usable editable fallback when AI planning is unavailable", () => {
    const brief = buildQuickBrief("失忆侦探追查自己的过去", "3000 字短篇");

    expect(brief.conflict).toBe("失忆侦探追查自己的过去");
    expect(brief.targetLength).toBe("3000 字短篇");
    expect(brief.titleCandidates).toEqual(["未命名故事"]);
    expect(brief.goal).toContain("核心麻烦");
    expect(brief.sceneTitle).toBe("开篇场景");
  });
});
