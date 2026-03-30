const { test, expect } = require('@playwright/test');

test('Homer contabulate loads and returns results for a Greek query', async ({ page }) => {
  await page.goto('/docs/');
  await page.waitForFunction(() => window.__contabulateReady === true);

  await expect(page).toHaveTitle(/Homer/);
  await expect(page.locator('h1')).toContainText('Iliad');
  await expect(page.locator('#gran')).toHaveValue('act');

  await page.locator('#q').fill('μῆνιν');
  await page.locator('#addColumnBtn').click();

  await expect(page.locator('#results thead')).toContainText('Work');
  await expect(page.locator('#results thead')).toContainText('Book');
  expect(await page.locator('#results tbody tr').count()).toBeGreaterThan(0);
  await expect(page.locator('#results tbody tr').first()).toContainText('Iliad');
});
