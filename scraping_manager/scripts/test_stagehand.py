"""Test script to verify Stagehand works"""
import asyncio
from stagehand import Stagehand

async def test_basic_scraping():
    async with Stagehand() as stagehand:
        page = stagehand.page
        await page.goto("https://example.com")
        
        title = await page.extract({
            "instruction": "get the page title",
            "schema": {"title": str}
        })
        
        print(f"Page title: {title}")
        return title

if __name__ == "__main__":
    asyncio.run(test_basic_scraping())