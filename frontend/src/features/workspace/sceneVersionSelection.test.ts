import { describe, expect, it } from "vitest";

import {
  getDefaultSceneVersionId,
  resolveSceneVersionSelection,
} from "./sceneVersionSelection";

const versions = [
  { id: "v1", version_no: 1 },
  { id: "v2", version_no: 2 },
  { id: "v3", version_no: 3 },
];

describe("sceneVersionSelection", () => {
  it("prefers the approved version over the newest version", () => {
    expect(getDefaultSceneVersionId(versions, "v2")).toBe("v2");
  });

  it("uses the newest version when there is no approved version match", () => {
    expect(getDefaultSceneVersionId(versions, null)).toBe("v3");
    expect(getDefaultSceneVersionId(versions, "missing")).toBe("v3");
  });

  it("updates an automatic selection when the default version changes", () => {
    expect(
      resolveSceneVersionSelection({
        versions,
        defaultVersionId: "v2",
        selectedVersionId: "v3",
        pendingVersionId: "",
        hasExplicitSelection: false,
      }),
    ).toEqual({
      selectedVersionId: "v2",
      pendingVersionId: "",
      hasExplicitSelection: false,
    });
  });

  it("preserves a valid explicit selection when the default version changes", () => {
    expect(
      resolveSceneVersionSelection({
        versions,
        defaultVersionId: "v2",
        selectedVersionId: "v3",
        pendingVersionId: "",
        hasExplicitSelection: true,
      }),
    ).toEqual({
      selectedVersionId: "v3",
      pendingVersionId: "",
      hasExplicitSelection: true,
    });
  });

  it("selects a pending created version once it appears", () => {
    expect(
      resolveSceneVersionSelection({
        versions,
        defaultVersionId: "v2",
        selectedVersionId: "v2",
        pendingVersionId: "v3",
        hasExplicitSelection: false,
      }),
    ).toEqual({
      selectedVersionId: "v3",
      pendingVersionId: "",
      hasExplicitSelection: true,
    });
  });

  it("repairs a missing explicit selection back to the default", () => {
    expect(
      resolveSceneVersionSelection({
        versions,
        defaultVersionId: "v2",
        selectedVersionId: "missing",
        pendingVersionId: "",
        hasExplicitSelection: true,
      }),
    ).toEqual({
      selectedVersionId: "v2",
      pendingVersionId: "",
      hasExplicitSelection: false,
    });
  });
});
