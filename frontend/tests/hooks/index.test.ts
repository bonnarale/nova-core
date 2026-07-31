import { renderHook, act } from "@testing-library/react";
import { useLocalStorage, useDebounce } from "@/hooks";

describe("Hooks", () => {
  describe("useLocalStorage", () => {
    it("returns initial value", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", "default"));
      expect(result.current[0]).toBe("default");
    });

    it("returns setter function", () => {
      const { result } = renderHook(() => useLocalStorage("test-key2", "initial"));
      expect(typeof result.current[1]).toBe("function");
    });

    it("setter updates value", () => {
      const { result } = renderHook(() => useLocalStorage("test-hook-key3", "initial"));
      const [, setValue] = result.current;
      act(() => {
        setValue("updated");
      });
      expect(result.current[0]).toBe("updated");
    });

    it("can store objects", () => {
      const { result } = renderHook(() => useLocalStorage("test-obj", { count: 0 }));
      expect(result.current[0]).toEqual({ count: 0 });
      act(() => {
        result.current[1]({ count: 5 });
      });
      expect(result.current[0]).toEqual({ count: 5 });
    });

    it("can store boolean values", () => {
      const { result } = renderHook(() => useLocalStorage("test-bool", false));
      expect(result.current[0]).toBe(false);
      act(() => {
        result.current[1](true);
      });
      expect(result.current[0]).toBe(true);
    });
  });

  describe("useDebounce", () => {
    it("returns initial value", () => {
      const { result } = renderHook(() => useDebounce("hello", 500));
      expect(result.current).toBe("hello");
    });

    it("updates when value changes", () => {
      const { result, rerender } = renderHook(
        ({ value, delay }) => useDebounce(value, delay),
        { initialProps: { value: "a", delay: 500 } }
      );
      expect(result.current).toBe("a");
      rerender({ value: "b", delay: 500 });
    });

    it("handles numeric values", () => {
      const { result } = renderHook(() => useDebounce(42, 300));
      expect(result.current).toBe(42);
    });

    it("handles null values", () => {
      const { result } = renderHook(() => useDebounce(null, 300));
      expect(result.current).toBeNull();
    });
  });
});
