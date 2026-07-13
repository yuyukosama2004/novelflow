import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Panel, Group, Separator, type Layout } from "react-resizable-panels";
import { PanelLeft, PanelRight, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { cn } from "../../utils/cn";

const DESKTOP_QUERY = "(min-width: 1280px)";
const LAYOUT_STORAGE_KEY = "novelflow:workspace-panel-layout";

interface WorkspaceShellProps {
  focusMode: boolean;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}

function getStoredLayout(): Layout | undefined {
  try {
    const value = window.localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!value) return undefined;

    const layout = JSON.parse(value) as Layout;
    return ["outline", "editor", "assistant"].every(
      (key) => typeof layout[key] === "number",
    )
      ? layout
      : undefined;
  } catch {
    return undefined;
  }
}

function useDesktopLayout() {
  const [isDesktop, setIsDesktop] = useState(
    () => window.matchMedia(DESKTOP_QUERY).matches,
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(DESKTOP_QUERY);
    const update = () => setIsDesktop(mediaQuery.matches);
    update();
    mediaQuery.addEventListener("change", update);
    return () => mediaQuery.removeEventListener("change", update);
  }, []);

  return isDesktop;
}

function WorkspaceDrawer({
  open,
  onOpenChange,
  title,
  side,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  side: "left" | "right";
  children: ReactNode;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-stone-950/35 backdrop-blur-[1px]" />
        <DialogPrimitive.Content
          className={cn(
            "fixed inset-y-0 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col bg-stone-50 shadow-dialog outline-none",
            side === "left"
              ? "left-0 border-r border-stone-200"
              : "right-0 border-l border-stone-200",
          )}
        >
          <div className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3">
            <DialogPrimitive.Title className="text-sm font-semibold text-stone-900">
              {title}
            </DialogPrimitive.Title>
            <DialogPrimitive.Close
              className="rounded-md p-1.5 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              aria-label={`关闭${title}`}
            >
              <X size={17} />
            </DialogPrimitive.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-4">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function ResizeHandle({ label }: { label: string }) {
  return (
    <Separator
      aria-label={label}
      className="group relative w-3 shrink-0 bg-transparent outline-none before:absolute before:inset-y-0 before:left-1/2 before:w-px before:-translate-x-1/2 before:bg-stone-200 hover:before:bg-brand-400 focus-visible:before:bg-brand-500"
    >
      <span className="absolute left-1/2 top-1/2 h-8 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-stone-300 opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100" />
    </Separator>
  );
}

export function WorkspaceShell({
  focusMode,
  left,
  center,
  right,
}: WorkspaceShellProps) {
  const isDesktop = useDesktopLayout();
  const [outlineOpen, setOutlineOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);

  if (focusMode) {
    return (
      <div className="mx-auto max-w-[1200px] px-4 py-5 sm:px-6">{center}</div>
    );
  }

  if (!isDesktop) {
    return (
      <div className="px-4 py-4 sm:px-6">
        <div className="mb-3 flex items-center justify-between rounded-xl border border-stone-200 bg-white p-2 shadow-panel">
          <button
            type="button"
            onClick={() => setOutlineOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <PanelLeft size={16} />
            大纲与设定
          </button>
          <button
            type="button"
            onClick={() => setAssistantOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-50 px-3 py-2 text-sm font-medium text-brand-700 transition hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <PanelRight size={16} />
            创作辅助
          </button>
        </div>
        {center}
        <WorkspaceDrawer
          open={outlineOpen}
          onOpenChange={setOutlineOpen}
          title="大纲与设定"
          side="left"
        >
          {left}
        </WorkspaceDrawer>
        <WorkspaceDrawer
          open={assistantOpen}
          onOpenChange={setAssistantOpen}
          title="创作辅助"
          side="right"
        >
          {right}
        </WorkspaceDrawer>
      </div>
    );
  }

  return (
    <Group
      id="writing-workspace"
      orientation="horizontal"
      defaultLayout={getStoredLayout()}
      onLayoutChanged={(layout, meta) => {
        if (meta.isUserInteraction) {
          window.localStorage.setItem(
            LAYOUT_STORAGE_KEY,
            JSON.stringify(layout),
          );
        }
      }}
      resizeTargetMinimumSize={{ coarse: 28, fine: 12 }}
      className="mx-auto min-h-[calc(100vh-9rem)] max-w-[1800px] px-5 py-5"
    >
      <Panel id="outline" defaultSize="280px" minSize="220px" maxSize="380px">
        <aside className="h-full overflow-y-auto pr-1">{left}</aside>
      </Panel>
      <ResizeHandle label="调整大纲栏宽度" />
      <Panel id="editor" minSize="420px">
        <main className="h-full min-w-0 overflow-y-auto px-3">{center}</main>
      </Panel>
      <ResizeHandle label="调整创作辅助栏宽度" />
      <Panel id="assistant" defaultSize="370px" minSize="300px" maxSize="520px">
        <aside className="h-full overflow-y-auto pl-1">{right}</aside>
      </Panel>
    </Group>
  );
}
