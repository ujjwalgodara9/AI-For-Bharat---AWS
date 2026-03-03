// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,  // Run tests sequentially — each test is a full conversation
  forbidOnly: false,
  retries: 1,
  workers: 1,
  timeout: 120000,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/playwright-report', open: 'never' }],
    ['json', { outputFile: 'tests/playwright-results.json' }],
  ],
  use: {
    baseURL: 'https://d2mtfau3fvs243.cloudfront.net',
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    // Browser permissions
    permissions: ['geolocation', 'microphone'],
    geolocation: { latitude: 28.6139, longitude: 77.2090 },  // Delhi (user live location)
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: true,  // Headless for CI
      },
    },
  ],
  outputDir: 'tests/test-results',
});
