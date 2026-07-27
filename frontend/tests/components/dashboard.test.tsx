import React from "react";
import { render, screen } from "@testing-library/react";
import { MetricCard, DataTable, StatBar, PageHeader, HealthGrid } from "@/components/dashboard";

describe("Dashboard Components", () => {
  describe("MetricCard", () => {
    it("renders title and value", () => {
      render(<MetricCard title="Active Agents" value={5} />);
      expect(screen.getByText("Active Agents")).toBeTruthy();
      expect(screen.getByText("5")).toBeTruthy();
    });

    it("renders string value", () => {
      render(<MetricCard title="Status" value="Healthy" />);
      expect(screen.getByText("Healthy")).toBeTruthy();
    });

    it("renders positive change", () => {
      render(<MetricCard title="Tasks" value={10} change={12.5} />);
      expect(screen.getByText("+12.5% from last period")).toBeTruthy();
    });

    it("renders negative change", () => {
      render(<MetricCard title="Errors" value={3} change={-5} />);
      expect(screen.getByText("-5% from last period")).toBeTruthy();
    });
  });

  describe("DataTable", () => {
    it("renders headers", () => {
      const columns = [{ key: "name", label: "Name" }, { key: "status", label: "Status" }];
      render(<DataTable columns={columns} data={[]} />);
      expect(screen.getByText("Name")).toBeTruthy();
      expect(screen.getByText("Status")).toBeTruthy();
    });

    it("renders data rows", () => {
      const columns = [{ key: "name", label: "Name" }];
      const data = [{ name: "Agent 1" }, { name: "Agent 2" }];
      render(<DataTable columns={columns} data={data} />);
      expect(screen.getByText("Agent 1")).toBeTruthy();
      expect(screen.getByText("Agent 2")).toBeTruthy();
    });

    it("shows empty message when no data", () => {
      render(<DataTable columns={[{ key: "x", label: "X" }]} data={[]} />);
      expect(screen.getByText("No data available")).toBeTruthy();
    });
  });

  describe("StatBar", () => {
    it("renders label and value", () => {
      render(<StatBar label="CPU" value={75} />);
      expect(screen.getByText("CPU")).toBeTruthy();
      expect(screen.getByText("75")).toBeTruthy();
    });
  });

  describe("PageHeader", () => {
    it("renders title", () => {
      render(<PageHeader title="Dashboard" />);
      expect(screen.getByText("Dashboard")).toBeTruthy();
    });

    it("renders description", () => {
      render(<PageHeader title="Dash" description="Overview" />);
      expect(screen.getByText("Overview")).toBeTruthy();
    });
  });

  describe("HealthGrid", () => {
    it("renders service items", () => {
      const items = [
        { name: "Database", status: "healthy", detail: "2ms" },
        { name: "Redis", status: "degraded" },
      ];
      render(<HealthGrid items={items} />);
      expect(screen.getByText("Database")).toBeTruthy();
      expect(screen.getByText("Redis")).toBeTruthy();
      expect(screen.getByText("2ms")).toBeTruthy();
    });
  });
});
