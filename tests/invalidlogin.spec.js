import { test, expect } from '@playwright/test';
 
 
test('Sign in with invalid email', async ({ page }) => {
    await page.goto('https://dev.typ.delivery/en/auth/login',{ waitUntil: 'networkidle', timeout: 60000 });
    await page.getByPlaceholder('Email').click();
    await page.getByPlaceholder('Email').fill('invalidemail@domain.com');
    await page.getByPlaceholder('Password').click();
    await page.getByPlaceholder('Password').fill('Lifedata@124');
    await page.getByRole('button', { name: 'Sign in' }).click();
    const errorMessage = page.locator('text=Warning!user not found for given credential');
    await expect(errorMessage).toHaveText('Warning!user not found for given credential');
 
  });