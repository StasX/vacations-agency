// Reuse CRA's transforms for TypeScript, JSX, CSS, and images while allowing
// tests to live outside src. No application build configuration is changed.
module.exports = {
    roots: ['<rootDir>/src', '<rootDir>/tests'],
    testMatch: ['<rootDir>/tests/unit/**/*.test.ts', '<rootDir>/tests/integration/**/*.test.{ts,tsx}'],
    testEnvironment: 'jsdom',
    setupFiles: [require.resolve('react-app-polyfill/jsdom')],
    setupFilesAfterEnv: ['<rootDir>/tests/setupTests.ts'],
    transform: {
        '^.+\\.(js|jsx|mjs|cjs|ts|tsx)$': require.resolve('react-scripts/config/jest/babelTransform'),
        '^.+\\.css$': require.resolve('react-scripts/config/jest/cssTransform'),
        '^(?!.*\\.(js|jsx|mjs|cjs|ts|tsx|css|json)$)': require.resolve('react-scripts/config/jest/fileTransform'),
    },
    transformIgnorePatterns: [
        '[/\\\\]node_modules[/\\\\].+\\.(js|jsx|mjs|cjs|ts|tsx)$',
        '^.+\\.module\\.(css|sass|scss)$',
    ],
    moduleNameMapper: { '^.+\\.module\\.(css|sass|scss)$': 'identity-obj-proxy' },
    resetMocks: true,
    collectCoverageFrom: [
        'src/**/*.{ts,tsx}',
        '!src/**/*.d.ts',
        '!src/index.tsx',
        '!src/reportWebVitals.ts',
    ],
};
