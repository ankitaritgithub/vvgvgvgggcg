// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// import dotenv from 'dotenv';
// import path from 'path';
// dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  // reporter: 'html',
  reporter : [['json', { outputFile: 'results.json' }]],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    video: 'on',
    /* Base URL to use in actions like `await page.goto('/')`. */
    // baseURL: 'http://127.0.0.1:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    baseURL: 'https://dev.typ.delivery/en/auth/login',
    headless: false, // Set to `false` to see the browser in action
    viewport: { width: 1280, height: 720 }, // Set default viewport size
    actionTimeout: 5000,
    
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'] },
    // },

    // /* Test against mobile viewports. */
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },

    /* Test against branded browsers. */
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'], channel: 'msedge' },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    // },
  ],

  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://127.0.0.1:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});

function extractVideosFromTestResults(directory) {
    const fs = require('fs');
    const path = require('path');

    let videoData = {};

    // Read the test-results directory
    fs.readdirSync(directory).forEach(section => {
        const sectionPath = path.join(directory, section);
        if (fs.statSync(sectionPath).isDirectory()) {
            videoData[section] = [];
            // Read files in the section
            fs.readdirSync(sectionPath).forEach(file => {
                if (file.endsWith('.mp4') || file.endsWith('.avi')) { // Assuming video formats
                    videoData[section].push(path.join(sectionPath, file));
                }
            });
        }
    });

    return videoData;
}

// Example usage:
// const videos = extractVideosFromTestResults('./test-results');
// console.log(videos);
