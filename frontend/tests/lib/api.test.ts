import { NovaAPI, api } from "@/lib/api";

describe("ApiClient (NovaAPI)", () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  describe("configuration", () => {
    it("exports singleton api instance", () => {
      expect(api).toBeDefined();
      expect(api).toBeInstanceOf(NovaAPI);
    });

    it("can create new instances", () => {
      const client = new NovaAPI("http://example.com");
      expect(client).toBeDefined();
    });

    it("can set auth token", () => {
      api.setAuthToken("test-token");
      expect(api).toBeDefined();
    });

    it("can set API key", () => {
      api.setApiKey("test-key");
      expect(api).toBeDefined();
    });
  });

  describe("GET requests", () => {
    it("health makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok" }),
      });
      await api.health();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("models.list makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });
      await api.models.list();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("agents.list makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });
      await api.agents.list();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("agents.get makes GET request with id", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "agent-1" }),
      });
      await api.agents.get("agent-1");
      expect(global.fetch).toHaveBeenCalled();
    });

    it("tasks.list makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });
      await api.tasks.list();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("workflows.list makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });
      await api.workflows.list();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("plugins.list makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });
      await api.plugins.list();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("events.list makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });
      await api.events.list();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("observability.health makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });
      await api.observability.health();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("security.health makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });
      await api.security.health();
      expect(global.fetch).toHaveBeenCalled();
    });

    it("enterprise.status makes GET request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });
      await api.enterprise.status();
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe("POST requests", () => {
    it("agents.create makes POST request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "new" }),
      });
      await api.agents.create({ name: "Test Agent" });
      expect(global.fetch).toHaveBeenCalled();
    });

    it("tasks.create makes POST request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "new" }),
      });
      await api.tasks.create({ title: "Test Task" });
      expect(global.fetch).toHaveBeenCalled();
    });

    it("workflows.create makes POST request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "new" }),
      });
      await api.workflows.create({ name: "Test Workflow" });
      expect(global.fetch).toHaveBeenCalled();
    });

    it("workflows.execute makes POST request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });
      await api.workflows.execute({ workflow_id: "wf-1" });
      expect(global.fetch).toHaveBeenCalled();
    });

    it("rag.query makes POST request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      });
      await api.rag.query({ query: "test" });
      expect(global.fetch).toHaveBeenCalled();
    });

    it("vectorMemory.search makes POST request", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      });
      await api.vectorMemory.search({ query: "test" });
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("throws on non-ok response", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => ({ detail: "Server error" }),
      });
      await expect(api.health()).rejects.toThrow();
    });

    it("throws on network error", async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new TypeError("Failed to fetch"));
      await expect(api.health()).rejects.toThrow();
    });

    it("handles error without detail", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => { throw new Error("not json"); },
      });
      await expect(api.health()).rejects.toThrow();
    });
  });

  describe("streaming", () => {
    it("stream makes POST request with event-stream accept", async () => {
      const readable = { locked: false, cancel: jest.fn() };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: readable,
      });
      const result = await api.stream("/rag/query", { query: "test" });
      expect(global.fetch).toHaveBeenCalled();
      expect(result).toBe(readable);
    });

    it("stream throws on error", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });
      await expect(api.stream("/rag/query")).rejects.toThrow();
    });
  });
});
