import { render, screen } from "@testing-library/react";
import React from "react";
import { Button, Card, Badge, Input, Spinner, StatusBadge, EmptyState, Modal } from "@/components/ui";

describe("UI Components", () => {
  describe("Button", () => {
    it("renders with text", () => {
      render(<Button>Click me</Button>);
      expect(screen.getByText("Click me")).toBeTruthy();
    });

    it("renders primary variant", () => {
      const { container } = render(<Button variant="primary">Primary</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-indigo-600");
    });

    it("renders secondary variant", () => {
      const { container } = render(<Button variant="secondary">Secondary</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-gray-700");
    });

    it("renders ghost variant", () => {
      const { container } = render(<Button variant="ghost">Ghost</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-transparent");
    });

    it("renders danger variant", () => {
      const { container } = render(<Button variant="danger">Danger</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("bg-red-600");
    });

    it("renders small size", () => {
      const { container } = render(<Button size="sm">Small</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("px-3");
    });

    it("renders large size", () => {
      const { container } = render(<Button size="lg">Large</Button>);
      const btn = container.querySelector("button");
      expect(btn?.className).toContain("px-6");
    });

    it("is disabled when loading", () => {
      render(<Button loading>Loading</Button>);
      const btn = screen.getByRole("button");
      expect(btn.disabled).toBe(true);
    });

    it("is disabled when disabled prop set", () => {
      render(<button disabled>Disabled</button>);
      expect(screen.getByRole("button").disabled).toBe(true);
    });
  });

  describe("Card", () => {
    it("renders children", () => {
      render(<Card><div>Content</div></Card>);
      expect(screen.getByText("Content")).toBeTruthy();
    });

    it("renders title", () => {
      render(<Card title="My Title"><div /></Card>);
      expect(screen.getByText("My Title")).toBeTruthy();
    });
  });

  describe("Badge", () => {
    it("renders with default variant", () => {
      const { container } = render(<Badge>Badge</Badge>);
      expect(container.textContent).toBe("Badge");
    });

    it("renders success variant", () => {
      const { container } = render(<Badge variant="success">OK</Badge>);
      const span = container.querySelector("span");
      expect(span?.className).toContain("text-green-400");
    });

    it("renders error variant", () => {
      const { container } = render(<Badge variant="error">Err</Badge>);
      const span = container.querySelector("span");
      expect(span?.className).toContain("text-red-400");
    });
  });

  describe("Input", () => {
    it("renders with label", () => {
      render(<Input label="Email" />);
      expect(screen.getByText("Email")).toBeTruthy();
    });

    it("renders error message", () => {
      render(<Input error="Required field" />);
      expect(screen.getByText("Required field")).toBeTruthy();
    });
  });

  describe("Spinner", () => {
    it("renders", () => {
      const { container } = render(<Spinner />);
      expect(container.firstChild).toBeTruthy();
    });
  });

  describe("StatusBadge", () => {
    it("renders healthy status", () => {
      render(<StatusBadge status="healthy" />);
      expect(screen.getByText("Healthy")).toBeTruthy();
    });

    it("renders error status", () => {
      render(<StatusBadge status="error" />);
      expect(screen.getByText("Error")).toBeTruthy();
    });

    it("renders unknown status as-is", () => {
      render(<StatusBadge status="custom" />);
      expect(screen.getByText("custom")).toBeTruthy();
    });
  });

  describe("EmptyState", () => {
    it("renders title", () => {
      render(<EmptyState title="No items found" />);
      expect(screen.getByText("No items found")).toBeTruthy();
    });

    it("renders description", () => {
      render(<EmptyState title="Empty" description="Nothing here" />);
      expect(screen.getByText("Nothing here")).toBeTruthy();
    });
  });

  describe("Modal", () => {
    it("renders when open", () => {
      render(<Modal open={true} onClose={() => {}} title="Modal Title"><div>Body</div></Modal>);
      expect(screen.getByText("Modal Title")).toBeTruthy();
      expect(screen.getByText("Body")).toBeTruthy();
    });

    it("does not render when closed", () => {
      render(<Modal open={false} onClose={() => {}} title="Hidden"><div /></Modal>);
      expect(screen.queryByText("Hidden")).toBeNull();
    });
  });
});
