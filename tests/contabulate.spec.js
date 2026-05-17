const { test, expect } = require('@playwright/test');

test('Homer contabulate loads and returns results for a Greek query', async ({ page }) => {
  await page.goto('/docs/');
  await page.waitForFunction(() => window.__contabulateReady === true);

  await expect(page).toHaveTitle(/Homer/);
  await expect(page.locator('h1')).toContainText('Iliad');
  await page.locator('#gran').selectOption('act');

  await page.locator('#q').fill('μῆνιν');
  await page.locator('#addColumnBtn').click();

  await expect(page.locator('#results thead')).toContainText('Work');
  await expect(page.locator('#results thead')).toContainText('Book');
  expect(await page.locator('#results tbody tr').count()).toBeGreaterThan(0);
  await expect(page.locator('#results tbody tr').first()).toContainText('Iliad');
});

test('Homer line rows show text even without search terms', async ({ page }) => {
  await page.goto('/docs/');
  await page.waitForFunction(() => window.__contabulateReady === true);

  await expect(page.locator('#gran option[value="line"]')).toHaveText('Lines');
  await page.locator('#gran').selectOption('line');
  await page.locator('#q').fill('');
  await page.locator('#addColumnBtn').click();

  await expect(page.locator('#results thead')).toContainText('Lines');
  await expect(page.locator('#results tbody tr').first()).toContainText('μῆνιν ἄειδε');
});

test('Homer Lines tab can show all lines with an empty query', async ({ page }) => {
  await page.goto('/docs/');
  await page.waitForFunction(() => window.__contabulateReady === true);

  await page.evaluate(() => document.querySelector('.tab-btn[data-tab="lines"]').click());
  await page.locator('#linesQuery').fill('');

  await expect(page.locator('#linesResults thead')).toContainText('Lines');
  await expect(page.locator('#linesResults tbody tr').first()).toContainText('μῆνιν ἄειδε');
  await expect(page.locator('#linesTotalInfo')).toContainText('total lines');
});
