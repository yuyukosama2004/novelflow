import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { QuickCreationPage } from "./QuickCreationPage";

describe("QuickCreationPage", () => {
  it("keeps advanced writing settings folded until the user needs them", () => {
    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: {
              queries: { retry: false },
              mutations: { retry: false },
            },
          })
        }
      >
        <MemoryRouter>
          <QuickCreationPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const advancedSettings = screen
      .getByText("高级写作设置")
      .closest("details");
    expect(advancedSettings).not.toHaveAttribute("open");

    fireEvent.click(screen.getByText("高级写作设置"));

    expect(advancedSettings).toHaveAttribute("open");
    expect(screen.getByLabelText("叙述视角")).toHaveValue(
      "third_person_limited",
    );
    expect(screen.getByLabelText("单次目标字数")).toHaveValue("1000");
  });
});
