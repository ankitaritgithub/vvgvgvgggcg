import fs from 'fs';
import path from 'path';
import { test, expect } from '@playwright/test';
import { parse } from 'csv-parse/sync';

// Helper function to get all CSV files from the "testdata" directory dynamically
const getCsvFiles = (dirPath) => {
  return fs.readdirSync(dirPath).filter((file) => file.endsWith('.csv'));
};

// Test setup: Iterate through all CSV files and dynamically create tests
const directoryPath = path.join(__dirname, '..', 'testdata');

const csvFiles = getCsvFiles(directoryPath);

csvFiles.forEach((csvFile) => {
  test.describe(`Login tests from ${csvFile}`, () => {
    const records = parse(fs.readFileSync(path.join(directoryPath, csvFile)), {
      columns: true,
      skip_empty_lines: true
    });

    for (const record of records) {
      test(`Login with ${record.email}`, async ({ page }) => {
        await page.goto('https://dev.typ.delivery/en/auth/login');
        await page.locator('input[placeholder="Email"]').click();
        await page.locator('input[placeholder="Email"]').fill(record.email);
        await page.locator('input[placeholder="Password"]').click();
        await page.locator('input[placeholder="Password"]').fill(record.password);
        await page.locator('button:has-text("Sign in")').click();
      });
    }
  });
});
