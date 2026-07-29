import React from "react";
import { render, screen } from "@testing-library/react";
import { BarChart, LineChart, PieChart } from "@/components/charts";
import { MessageBubble, TypingIndicator } from "@/components/chat";
import { WorkflowCanvas, WorkflowToolbar } from "@/components/workflow";
import { PageContainer, Section, LoadingScreen, ErrorBoundary, ConfirmDialog, ToastProvider } from "@/components/common";

describe("Chart Components", () => {
  describe("BarChart", () => {
    it("renders with data", () => {
      const data = [{ label: "A", value: 10 }, { label: "B", value: 20 }];
      render(<BarChart data={data} title="Test Chart" />);
      expect(screen.getByText("Test Chart")).toBeTruthy();
      expect(screen.getByText("A")).toBeTruthy();
      expect(screen.getByText("B")).toBeTruthy();
    });
  });

  describe("LineChart", () => {
    it("renders", () => {
      const { container } = render(<LineChart data={[1, 2, 3]} title="Line" />);
      expect(screen.getByText("Line")).toBeTruthy();
      expect(container.querySelector("svg")).toBeTruthy();
    });
  });

  describe("PieChart", () => {
    it("renders with data", () => {
      const data = [
        { label: "A", value: 50, color: "#FF0000" },
        { label: "B", value: 50, color: "#00FF00" },
      ];
      render(<PieChart data={data} title="Pie" />);
      expect(screen.getByText("A")).toBeTruthy();
      expect(screen.getByText("B")).toBeTruthy();
    });
  });
});

describe("Chat Components", () => {
  describe("MessageBubble", () => {
    it("renders user message", () => {
      render(<MessageBubble role="user" content="Hello" timestamp="2024-01-01T00:00:00Z" />);
      expect(screen.getByText("Hello")).toBeTruthy();
    });

    it("renders assistant message with agent name", () => {
      render(<MessageBubble role="assistant" content="Hi there" timestamp="2024-01-01T00:00:00Z" agentName="Nova" />);
      expect(screen.getByText("Hi there")).toBeTruthy();
      expect(screen.getByText("Nova")).toBeTruthy();
    });
  });

  describe("TypingIndicator", () => {
    it("renders", () => {
      render(<TypingIndicator agentName="Nova" />);
      expect(screen.getByText(/Nova is thinking/)).toBeTruthy();
    });
  });
});

describe("Workflow Components", () => {
  describe("WorkflowCanvas", () => {
    it("renders nodes", () => {
      const nodes = [{ id: "1", type: "trigger", label: "Start", x: 50, y: 50 }];
      const { container } = render(<WorkflowCanvas nodes={nodes} edges={[]} />);
      expect(screen.getByText("Start")).toBeTruthy();
      expect(container.querySelector("svg")).toBeTruthy();
    });

    it("renders edges", () => {
      const nodes = [
        { id: "1", type: "trigger", label: "Start", x: 0, y: 0 },
        { id: "2", type: "action", label: "End", x: 200, y: 0 },
      ];
      const edges = [{ from: "1", to: "2" }];
      const { container } = render(<WorkflowCanvas nodes={nodes} edges={edges} />);
      expect(container.querySelector("line")).toBeTruthy();
    });
  });

  describe("WorkflowToolbar", () => {
    it("renders node type buttons", () => {
      render(<WorkflowToolbar onAddNode={() => {}} onSave={() => {}} onRun={() => {}} />);
      expect(screen.getByText("Trigger")).toBeTruthy();
      expect(screen.getByText("Action")).toBeTruthy();
      expect(screen.getByText("LLM Call")).toBeTruthy();
      expect(screen.getByText("Save")).toBeTruthy();
      expect(screen.getByText("Run")).toBeTruthy();
    });
  });
});

describe("Common Components", () => {
  describe("PageContainer", () => {
    it("renders children", () => {
      render(<PageContainer><div>Content</div></PageContainer>);
      expect(screen.getByText("Content")).toBeTruthy();
    });
  });

  describe("Section", () => {
    it("renders title and children", () => {
      render(<Section title="My Section"><div>Body</div></Section>);
      expect(screen.getByText("My Section")).toBeTruthy();
      expect(screen.getByText("Body")).toBeTruthy();
    });
  });

  describe("LoadingScreen", () => {
    it("renders", () => {
      render(<LoadingScreen />);
      expect(screen.getByText("NOVA CORE")).toBeTruthy();
      expect(screen.getByText("Loading...")).toBeTruthy();
    });
  });

  describe("ErrorBoundary", () => {
    it("renders children when no error", () => {
      render(
        <ErrorBoundary>
          <div>Child content</div>
        </ErrorBoundary>
      );
      expect(screen.getByText("Child content")).toBeTruthy();
    });

    it("renders fallback UI when child throws", () => {
      const ThrowingChild = () => {
        throw new Error("Test crash");
      };
      // Suppress console.error for this test
      const spy = jest.spyOn(console, "error").mockImplementation();
      render(
        <ErrorBoundary>
          <ThrowingChild />
        </ErrorBoundary>
      );
      expect(screen.getByText("Something went wrong")).toBeTruthy();
      expect(screen.getByText("Test crash")).toBeTruthy();
      expect(screen.getByText("Try again")).toBeTruthy();
      spy.mockRestore();
    });
  });

  describe("ConfirmDialog", () => {
    it("renders when open", () => {
      render(<ConfirmDialog open={true} title="Confirm?" message="Are you sure?" onConfirm={() => {}} onCancel={() => {}} />);
      expect(screen.getByText("Confirm?")).toBeTruthy();
      expect(screen.getByText("Are you sure?")).toBeTruthy();
    });

    it("does not render when closed", () => {
      render(<ConfirmDialog open={false} title="Hidden" message="Gone" onConfirm={() => {}} onCancel={() => {}} />);
      expect(screen.queryByText("Hidden")).toBeNull();
    });
  });

  describe("ToastProvider", () => {
    it("renders children", () => {
      render(
        <ToastProvider>
          <div>App content</div>
        </ToastProvider>
      );
      expect(screen.getByText("App content")).toBeTruthy();
    });
  });
});
