# start chrome --remote-debugging-port=9222
import asyncio
from playwright.async_api import async_playwright

# CSS selector for all elements with ID starting with "unit"
UNIT_SELECTOR = "div.join.join-vertical > div"
LESSON_SELECTOR = "ol > li > a"
BASE_URL = 'https://www.guitarclub.io'
VIDEO_SELECTOR = "body > main > div > div > div.w-full.max-w-7xl.gap-4.m-auto.py-8.md\:py-16.px-4.md\:px-4.xl\:px-0 > div > div.md\:\[grid-area\:header\].md\:col-span-3 > div.md\:sticky.top-16.z-10 > div:nth-child(1) > div > div > div:nth-child(1) > video"

async def main():
    async with async_playwright() as playwright:
        # Connect to an existing instance of Chrome using the connect_over_cdp method.
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        current_context = browser.contexts[0]
        new_page = await current_context.new_page()
        await new_page.goto("https://www.guitarclub.io/courses/acoustic-beginners-level-1")
        
        # Wait for page to load
        await new_page.wait_for_load_state("domcontentloaded")
        # Find all elements with IDs that start with "unit"
        unit_elements = await new_page.query_selector_all(UNIT_SELECTOR)
        
        # Create a list to track seen IDs to avoid duplicates
        seen_ids = []
        unique_unit_elements = []
        
        for element in unit_elements:
            element_id = await element.get_attribute("id")
            if element_id and element_id not in seen_ids:
                seen_ids.append(element_id)
                unique_unit_elements.append(element)
        
        print(f"Found {len(unique_unit_elements)} unit elements")
        print([{await unique_unit_ele.get_attribute("id"): unique_unit_ele.inner_text()} for unique_unit_ele in unique_unit_elements])
        
        # Print details about each unit element
        for unit_element in (unique_unit_elements):
            unit_id = await unit_element.get_attribute("id")
            unit_name_element = await unit_element.query_selector("div.flex.flex-col.grow > p:nth-child(2)")
            unit_name = await unit_name_element.inner_text() if unit_name_element else "Unknown"
            lesson_elements = await unit_element.query_selector_all(LESSON_SELECTOR)
            for lesson_ele in lesson_elements:
                lesson_url = BASE_URL + (await lesson_ele.get_attribute('href'))
                new_page_2 = await current_context.new_page()
                await new_page_2.goto(lesson_url)
                await new_page_2.wait_for_load_state("domcontentloaded")
                
                video_element = await new_page_2.query_selector(VIDEO_SELECTOR)
                print(await video_element.get_attribute("src"))
                
            print(f"ID = {unit_id} - {unit_name}")

# Run the async function with asyncio
asyncio.run(main())


def sanitize_filename(name):
    """Convert a string to a valid filename"""
    # Remove invalid characters
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Limit length
    return name[:100]