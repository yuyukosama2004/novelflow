import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkspacePanelTabs } from "./WorkspacePanelTabs";

describe("WorkspacePanelTabs", () => {
  it("uses Chinese labels and changes the active panel", () => {
    const onChange = vi.fn();
    render(<WorkspacePanelTabs value="ai" onChange={onChange} />);

    expect(screen.getByLabelText("创作")).toBeInTheDocument();
    expect(screen.getByLabelText("检查")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AI 续写" })).toHaveClass(
      "text-brand-700",
    );
    fireEvent.click(screen.getByRole("button", { name: "一致性审查" }));

    expect(onChange).toHaveBeenCalledWith("review");
  });
});
