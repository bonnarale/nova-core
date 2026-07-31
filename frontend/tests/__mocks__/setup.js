// Jest setup file - mock modules for frontend tests

jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
}));

jest.mock("next/link", () => {
  const React = require("react");
  return {
    __esModule: true,
    default: React.forwardRef(function LinkMock(props, ref) {
      return React.createElement("a", { ref, href: props.href, ...props }, props.children);
    }),
  };
});

// Mock WebSocket globally
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  readyState = 1;
  url;
  onopen = null;
  onclose = null;
  onmessage = null;
  onerror = null;
  constructor(url) {
    this.url = url;
    setTimeout(() => this.onopen && this.onopen(new Event("open")), 0);
  }
  send = jest.fn();
  close = jest.fn();
}
global.WebSocket = MockWebSocket;

// Mock EventSource globally
class MockEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  readyState = 1;
  url;
  onopen = null;
  onmessage = null;
  onerror = null;
  constructor(url) {
    this.url = url;
    setTimeout(() => this.onopen && this.onopen(new Event("open")), 0);
  }
  close = jest.fn();
}
global.EventSource = MockEventSource;

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => { store[key] = value; }),
    removeItem: jest.fn((key) => { delete store[key]; }),
    clear: jest.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: jest.fn((i) => Object.keys(store)[i] || null),
  };
})();
Object.defineProperty(global, "localStorage", { value: localStorageMock });

// Mock crypto.randomUUID
Object.defineProperty(global, "crypto", {
  value: { randomUUID: () => Math.random().toString(36).substring(2, 15) },
});

// Mock fetch globally
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(""),
    status: 200,
    headers: new Headers(),
  })
);
