// test_template.spec.js
import { test, expect } from '@playwright/test';

const credentials = {
  email: 'your-email@example.com', 
  password: 'your-secure-password'
};

test('login test', async ({ page }) => {
    await page.goto('https://dev.typ.delivery/en/auth/login');
    await page.getByPlaceholder('Email').fill(credentials.email);
    await page.getByPlaceholder('Password').fill(credentials.password);
    await page.getByRole('button', { name: 'Sign in' }).click();
});
