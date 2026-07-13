import { useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Check, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
import type { Scene, SceneVersion } from "../../types/entities";
import { label, SOURCE_TYPE_LABELS } from "../../utils/enumLabels";

interface Props {
  scene: Scene | null;
  versions: SceneVersion[];
  modelProfileId?: string;
}

function approvalFailureReason(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) return undefined;
  return (error.response?.data as { details?: { reason?: string } })?.details
    ?.reason;
}

function approvalFailureMessage(reason: string | undefined): string {
  if (reason === "VERSION_REVIEW_REQUIRED") {
    return "该版本尚未完成审查，请先执行审查。";
  }
  if (reason === "EMPTY_VERSION_CONTENT") {
    return "正文为空，不能批准为正式稿。";
  }
  if (reason === "HISTORICAL_REPLACEMENT_NOT_READY") {
    return "历史正式稿替换尚未开放，请保留当前正式稿。";
  }
  return "批准失败，请刷新后重试。";
}

export function SceneApprovalPanel({
  scene,
  versions,
  modelProfileId = "",
}: Props) {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");

  const approveVersion = useMutation({
    mutationFn: ({
      versionId,
      overrideReason,
    }: {
      versionId: string;
      overrideReason?: string;
    }) => apiClient.approveVersion(scene?.id ?? "", versionId, overrideReason),
    onSuccess: () => {
      setMessage("");
      queryClient.invalidateQueries({ queryKey: ["scene", scene?.id] });
      queryClient.invalidateQueries({
        queryKey: ["scene-versions", scene?.id],
      });
      queryClient.invalidateQueries({ queryKey: ["scenes"] });
      queryClient.invalidateQueries({ queryKey: ["impact-reports"] });
    },
  });

  const reviewForApproval = useMutation({
    mutationFn: (versionId: string) =>
      modelProfileId
        ? apiClient.runReview(versionId, modelProfileId)
        : apiClient.runReview(versionId),
    onSuccess: (result) => {
      setMessage("审查已完成，请确认审查问题后再次批准。");
      queryClient.setQueryData(["review-run", result.run.id], result);
      queryClient.invalidateQueries({
        queryKey: ["review-runs", result.run.scene_version_id],
      });
      queryClient.invalidateQueries({
        queryKey: ["scene-versions", scene?.id],
      });
    },
    onError: () => setMessage("审查失败，请稍后重试。"),
  });

  async function requestApproval(version: SceneVersion) {
    setMessage("");
    if (version.review_status !== "completed") {
      if (!window.confirm("该版本尚未完成审查，是否现在执行审查？")) return;
      await reviewForApproval.mutateAsync(version.id).catch(() => undefined);
      return;
    }

    if (
      scene?.approved_version_id &&
      scene.approved_version_id !== version.id &&
      !window.confirm(
        "替换正式稿会使后续场景标记为“需复查”，并使旧版本产生的记忆失效。确认继续吗？",
      )
    ) {
      return;
    }

    try {
      await approveVersion.mutateAsync({ versionId: version.id });
    } catch (error) {
      const reason = approvalFailureReason(error);
      if (reason !== "BLOCKING_REVIEW_ISSUES") {
        setMessage(approvalFailureMessage(reason));
        return;
      }
      if (!window.confirm("存在阻断问题。是否填写理由并强制批准？")) return;
      const overrideReason = window.prompt("请输入强制批准理由：", "")?.trim();
      if (!overrideReason) {
        setMessage("强制批准必须填写理由。");
        return;
      }
      try {
        await approveVersion.mutateAsync({
          versionId: version.id,
          overrideReason,
        });
      } catch (overrideError) {
        setMessage(
          approvalFailureMessage(approvalFailureReason(overrideError)),
        );
      }
    }
  }

  if (!scene || versions.length === 0) return null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-4 text-xs shadow-panel">
      <div className="flex items-center gap-2">
        <ShieldCheck size={15} className="text-brand-700" />
        <div>
          <h2 className="text-sm font-semibold text-stone-900">版本审批</h2>
          <p className="mt-0.5 text-stone-500">
            仅在这里将审查完成的版本批准为正式稿。
          </p>
        </div>
      </div>
      <div className="mt-3 divide-y divide-stone-100 border-t border-stone-100">
        {[...versions]
          .sort((a, b) => b.version_no - a.version_no)
          .map((version) => (
            <div
              key={version.id}
              className="flex items-center justify-between gap-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="font-medium text-stone-800">
                  v{version.version_no}
                </p>
                <p className="truncate text-stone-500">
                  {version.summary ||
                    `${label(SOURCE_TYPE_LABELS, version.source_type)}正文`}
                </p>
              </div>
              <IconButton
                icon={<Check size={15} />}
                label={
                  version.review_status === "completed" ? "批准" : "先审查"
                }
                disabled={
                  scene.approved_version_id === version.id ||
                  approveVersion.isPending ||
                  reviewForApproval.isPending
                }
                onClick={() => void requestApproval(version)}
              />
            </div>
          ))}
      </div>
      {message ? (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 leading-5 text-amber-800">
          {message}
        </p>
      ) : null}
    </section>
  );
}
