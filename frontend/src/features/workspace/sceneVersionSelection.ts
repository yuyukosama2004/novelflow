import type { SceneVersion } from "../../types/entities";

type VersionOption = Pick<SceneVersion, "id" | "version_no">;

export interface SceneVersionSelectionState {
  selectedVersionId: string;
  pendingVersionId: string;
  hasExplicitSelection: boolean;
}

interface ResolveSceneVersionSelectionInput extends SceneVersionSelectionState {
  versions: VersionOption[];
  defaultVersionId: string;
}

export function getDefaultSceneVersionId(
  versions: VersionOption[],
  approvedVersionId: string | null | undefined,
): string {
  if (versions.length === 0) {
    return "";
  }
  const approved = approvedVersionId
    ? versions.find((version) => version.id === approvedVersionId)
    : null;
  return (
    approved?.id ??
    [...versions].sort((a, b) => b.version_no - a.version_no)[0].id
  );
}

export function resolveSceneVersionSelection({
  versions,
  defaultVersionId,
  selectedVersionId,
  pendingVersionId,
  hasExplicitSelection,
}: ResolveSceneVersionSelectionInput): SceneVersionSelectionState {
  if (versions.length === 0) {
    return {
      selectedVersionId: "",
      pendingVersionId: "",
      hasExplicitSelection: false,
    };
  }

  const hasVersion = (versionId: string) =>
    Boolean(versionId) && versions.some((version) => version.id === versionId);
  const repairedDefaultVersionId = hasVersion(defaultVersionId)
    ? defaultVersionId
    : getDefaultSceneVersionId(versions, null);

  if (pendingVersionId) {
    if (hasVersion(pendingVersionId)) {
      return {
        selectedVersionId: pendingVersionId,
        pendingVersionId: "",
        hasExplicitSelection: true,
      };
    }
    return {
      selectedVersionId: hasVersion(selectedVersionId)
        ? selectedVersionId
        : repairedDefaultVersionId,
      pendingVersionId,
      hasExplicitSelection:
        hasExplicitSelection && hasVersion(selectedVersionId),
    };
  }

  if (hasExplicitSelection && hasVersion(selectedVersionId)) {
    return {
      selectedVersionId,
      pendingVersionId: "",
      hasExplicitSelection: true,
    };
  }

  return {
    selectedVersionId: repairedDefaultVersionId,
    pendingVersionId: "",
    hasExplicitSelection: false,
  };
}
