module.exports = {
  testEnvironment: "jsdom",
  setupFiles: ["<rootDir>/tests/__mocks__/setup.js"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "\\.(css|less|scss)$": "identity-obj-proxy",
  },
  transform: {
    "^.+\\.(ts|tsx)$": ["ts-jest", {
      tsconfig: {
        jsx: "react-jsx",
        esModuleInterop: true,
        module: "commonjs",
        moduleResolution: "node",
        target: "ES2022",
        strict: false,
        skipLibCheck: true,
      },
    }],
  },
  transformIgnorePatterns: ["/node_modules/"],
  testMatch: ["**/tests/**/*.test.(ts|tsx|js)", "**/__tests__/**/*.(ts|tsx|js)"],
};
