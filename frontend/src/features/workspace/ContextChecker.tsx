import { useQuery } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

interface Props {
  sceneId: string;
}

interface ContextData {
  previous_scene: {
    scene_id: string;
    title: string;
    version_no: number;
    content_preview: string;
  } | null;
  characters: {
    id: string;
    name: string;
    role: string;
    public_identity: string;
    speech_style: string;
    decision_pattern: string;
    core_desire: string;
    core_fear: string;
    forbidden_behaviors: string[];
    current_state: Record<string, unknown> | null;
    knowledge_known: string[];
    knowledge_unknown: string[];
  }[];
  world_facts: {
    id: string;
    name: string;
    entry_type: string;
    summary: string;
    content: string;
  }[];
  manifest: Record<string, unknown>;
}

export default function ContextChecker({ sceneId }: Props) {
  const [open, setOpen] = useState(false);

  const ctx = useQuery({
    queryKey: ["context", sceneId],
    queryFn: async () => {
      // Using raw fetch since apiClient doesn't have this endpoint yet
      const baseUrl =
        import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
      const res = await fetch(`${baseUrl}/scenes/${sceneId}/context`);
      const json = await res.json();
      return json.data as ContextData;
    },
    enabled: open,
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
      >
        <Eye size={14} />
        View Context
      </button>
    );
  }

  const data = ctx.data;

  return (
    <div className="rounded-md border border-indigo-200 bg-white p-3 text-xs">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-indigo-900">
          Generation Context
          {data?.manifest && (
            <span className="ml-2 font-normal text-gray-500">
              ~{data.manifest.token_estimate as number} tokens
            </span>
          )}
        </h4>
        <button
          onClick={() => setOpen(false)}
          className="text-gray-400 hover:text-gray-600"
        >
          <EyeOff size={14} />
        </button>
      </div>

      {ctx.isLoading && <p className="text-gray-400">Loading context...</p>}
      {ctx.isError && <p className="text-red-500">Failed to load context</p>}

      {data?.previous_scene && (
        <div className="mb-2">
          <p className="font-medium text-gray-700">
            Previous Scene: {data.previous_scene.title}
          </p>
          <p className="text-gray-500 mt-0.5 line-clamp-3">
            {data.previous_scene.content_preview}
          </p>
        </div>
      )}

      {data?.characters && data.characters.length > 0 && (
        <div className="mb-2">
          <p className="font-medium text-gray-700 mb-1">
            Characters ({data.characters.length})
          </p>
          {data.characters.map((ch) => (
            <details key={ch.id} className="mb-1">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                {ch.name} ({ch.role})
              </summary>
              <div className="ml-3 mt-0.5 text-gray-500 space-y-0.5">
                <p>Wants: {ch.core_desire || "n/a"}</p>
                <p>Fears: {ch.core_fear || "n/a"}</p>
                <p>Speech: {ch.speech_style || "n/a"}</p>
                {ch.knowledge_known.length > 0 && (
                  <p>
                    Knows: {ch.knowledge_known.join(", ")}
                  </p>
                )}
                {ch.knowledge_unknown.length > 0 && (
                  <p className="text-red-500">
                    Must NOT know: {ch.knowledge_unknown.join(", ")}
                  </p>
                )}
                {ch.forbidden_behaviors.length > 0 && (
                  <p className="text-orange-600">
                    Forbidden: {ch.forbidden_behaviors.join(", ")}
                  </p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      {data?.world_facts && data.world_facts.length > 0 && (
        <div className="mb-2">
          <p className="font-medium text-gray-700 mb-1">
            World Facts ({data.world_facts.length})
          </p>
          {data.world_facts.map((wf) => (
            <div key={wf.id} className="ml-2 text-gray-500">
              [{wf.entry_type}] {wf.name}: {wf.summary}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
