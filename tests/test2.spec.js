
import { test, expect } from '@playwright/test';

test('login test', async ({ page }) => {
    await page.goto('https://dev.typ.delivery/en/auth/login');
    await page.getByPlaceholder('Email').fill('demo@13.com');
    await page.getByPlaceholder('Password').fill('data@123');
    await page.getByRole('button', { name: 'Sign in' }).click();
});
