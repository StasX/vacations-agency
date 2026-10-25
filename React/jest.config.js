module.exports = {
    roots: ['<rootDir>/src', '<rootDir>/tests'],
    testMatch: ['<rootDir>/tests/unit/**/*.test.ts', '<rootDir>/tests/integration/**/*.test.{ts,tsx}'],
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/tests/setupTests.ts'],
    transform: { '^.+\\.(js|jsx|mjs|cjs|ts|tsx)$': 'babel-jest' },
    moduleNameMapper: {
        '^.+\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
        '^.+\\.css$': '<rootDir>/tests/styleMock.js',
        '^.+\\.(png|jpg|jpeg|gif|svg|ico)(\\?url)?$': '<rootDir>/tests/fileMock.js',
    },
    resetMocks: true,
    collectCoverageFrom: [
        'src/**/*.{ts,tsx}',
        '!src/**/*.d.ts',
        '!src/index.tsx',
        '!src/reportWebVitals.ts',
    ],
};

