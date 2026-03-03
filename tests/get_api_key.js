/**
 * MandiMitra — data.gov.in API Key Registration
 * Uses Playwright to register and get an API key from data.gov.in
 */
const { chromium } = require('@playwright/test');

async function getDataGovApiKey() {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('Navigating to data.gov.in registration...');
    await page.goto('https://data.gov.in/user/register', { waitUntil: 'domcontentloaded', timeout: 30000 });

    // Take screenshot to see what we're dealing with
    await page.screenshot({ path: 'tests/screenshots/datagov_register.png', fullPage: true });
    console.log('Screenshot saved: tests/screenshots/datagov_register.png');

    // Try to find form fields
    const fields = await page.$$eval('input', inputs =>
      inputs.map(i => ({ id: i.id, name: i.name, type: i.type, placeholder: i.placeholder }))
    );
    console.log('Form fields found:', JSON.stringify(fields, null, 2));

    // Check if there's already an API key page
    await page.goto('https://data.gov.in/user/me/api-key', { waitUntil: 'domcontentloaded', timeout: 15000 });
    const pageContent = await page.textContent('body');
    console.log('API key page content (first 500 chars):', pageContent.substring(0, 500));

    await page.screenshot({ path: 'tests/screenshots/datagov_apikey.png', fullPage: true });

  } catch (e) {
    console.error('Error:', e.message);
    await page.screenshot({ path: 'tests/screenshots/datagov_error.png', fullPage: true });
  } finally {
    await browser.close();
  }
}

getDataGovApiKey().catch(console.error);
