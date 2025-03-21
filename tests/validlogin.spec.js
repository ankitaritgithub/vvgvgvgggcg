const { test, expect } = require('@playwright/test');

test('valid login test', async ({ page }) => {
  await page.goto('https://dev.typ.delivery/en/auth/login');
  await page.getByPlaceholder('Email').click();
  await page.getByPlaceholder('Email').fill('platformops@lifedata.ai');
  await page.getByPlaceholder('Password').click();
  await page.getByPlaceholder('Password').fill('Lifedata@124');
  await page.getByRole('button', { name: 'Sign in' }).click();
  
  // Add a simple assertion
  await expect(page).toHaveURL(/.*dashboard/);
});