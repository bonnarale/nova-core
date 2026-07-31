import { healthService, agentsService, tasksService, workflowsService, goalsService, memoryService, modelsService, schedulerService, deploymentService } from "@/services";

describe("Services", () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
      text: async () => "[]",
      headers: new Headers({ "content-type": "application/json" }),
    });
  });

  it("healthService.check calls correct endpoint", async () => {
    await healthService.check();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("agentsService.list calls correct endpoint", async () => {
    await agentsService.list();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("tasksService.list calls correct endpoint", async () => {
    await tasksService.list();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("workflowsService.list calls correct endpoint", async () => {
    await workflowsService.list();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("goalsService.list calls correct endpoint", async () => {
    await goalsService.list();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("memoryService.list calls correct endpoint", async () => {
    await memoryService.list();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("modelsService.list calls correct endpoint", async () => {
    await modelsService.list();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("schedulerService.jobs calls correct endpoint", async () => {
    await schedulerService.jobs();
    expect(global.fetch).toHaveBeenCalled();
  });

  it("deploymentService.history calls correct endpoint", async () => {
    await deploymentService.history();
    expect(global.fetch).toHaveBeenCalled();
  });
});
