# start chrome --remote-debugging-port=9222
import asyncio
import re
import csv
import os
from playwright.async_api import async_playwright
from helper import clean_special_characters, write_to_csv, download_m3u8_with_ffmpeg, is_url_already_downloaded

course_urls = [
"/courses/30-day-beginner-challenge",
"/courses/7th-chords",
"/courses/9th-chords",
"/courses/acoustic-beginners-level-1",
"/courses/acoustic-beginners-level-2",
"/courses/acoustic-fingerstyle-level-1",
"/courses/acoustic-fingerstyle-level-2",
"/courses/acoustic-fingerstyle-level-3",
"/courses/angus-young",
"/courses/b-b-king",
"/courses/barre-chords",
"/courses/beginners-bends",
"/courses/bends-level-2",
"/courses/the-blues-lick-challenge",
"/courses/the-blues-rhythm-challenge",
"/courses/brian-may",
"/courses/carlos-santana",
"/courses/cory-wong",
"/courses/dave-grohl",
"/courses/david-gilmour",
"/courses/dimebag-darrell",
"/courses/diminished-chords",
"/courses/ed-sheeran",
"/courses/eddie-van-halen",
"/courses/electric-blues-essentials-level-1",
"/courses/electric-blues-essentials-level-2",
"/courses/electric-blues-essentials-level-3",
"/courses/electric-beginners-level-1",
"/courses/electric-beginners-level-2",
"/courses/electric-beginners-level-3",
"/courses/electric-intermediates-level-1",
"/courses/electric-intermediates-level-2",
"/courses/eric-clapton",
"/courses/essential-theory",
"/courses/finger-tapping",
"/courses/fingerstyle-arrangement",
"/courses/fingerstyle-percussion-level-1",
"/courses/freddie-king",
"/courses/funk-essentials-level-1",
"/courses/george-benson",
"/courses/harmony",
"/courses/home-studio-guide",
"/courses/how-to-learn-licks",
"/courses/improvisation-level-1",
"/courses/jack-white-and-the-white-stripes",
"/courses/jimi-hendrix",
"/courses/jimmy-page",
"/courses/joe-bonamassa",
"/courses/john-frusciante",
"/courses/john-mayer",
"/courses/john-mayer-acoustic",
"/courses/kurt-cobain-nirvana",
"/courses/lead-guitar-beginners-level-1",
"/courses/lead-guitar-beginners-level-2",
"/courses/lead-guitar-intermediates-level-1",
"/courses/lead-guitar-intermediates-level-2",
"/courses/major-caged-licks",
"/courses/beginner-gym",
"/courses/master-your-fingers",
"/courses/metal-essentials",
"/courses/metal-essentials-level-2",
"/courses/nile-rodgers",
"/courses/noel-gallagher",
"/courses/octaves-challenge",
"/courses/the-open-chords-challenge",
"/courses/pentatonic-mastery",
"/courses/pentatonic-theory",
"/courses/pentatonic-to-diatonic",
"/courses/practical-modes-ionian",
"/courses/beginners-rhythm-challenge",
"/courses/rock-essentials-level-1",
"/courses/rock-legato",
"/courses/rock-licks",
"/courses/scale-harmonisation",
"/courses/slash",
"/courses/beginners-speed-building",
"/courses/speed-building-level-2",
"/courses/steve-lukather",
"/courses/stevie-ray-vaughan",
"/courses/the-12-songs-of-christmas",
"/courses/the-modes",
"/courses/tom-misch",
"/courses/triad-construction",
"/courses/triads",
"/courses/unlocking-major-caged",
"/courses/unlocking-minor-caged",
"/courses/vibrato",
]

# CSS selector for all elements with ID starting with "unit"
UNIT_SELECTOR = "div.join.join-vertical > div"
PLAY_BUTTON_SELECTOR = "body > main > div > div > div > div > div > div > div:nth-child(1) > div > div > div > button:first-child"
TOOLBOX_SELECTOR = "body > button"
NOTE_SELECTOR = "#notes"
LESSON_SELECTOR = "ol > li > a"
BASE_URL = 'https://www.guitarclub.io'
VIDEO_SELECTOR = "body > main > div > div > div.w-full.max-w-7xl.gap-4.m-auto.py-8.md\:py-16.px-4.md\:px-4.xl\:px-0 > div > div.md\:\[grid-area\:header\].md\:col-span-3 > div.md\:sticky.top-16.z-10 > div:nth-child(1) > div > div > div:nth-child(1) > video"
CSV_TRACKING_PATH = "./downloaded_url.csv"
CSV_NOT_DOWNLOADED_TRACKING_PATH = "./not_downloaded.csv"

async def main():
    async with async_playwright() as playwright:
        user = input("Choose (1) for using the current browser instance, other key to sign in: ")
        
        if user == "1":
            # Connect to an existing instance of Chrome using the connect_over_cdp method.
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            
            current_context = browser.contexts[0]
            new_page = await current_context.new_page()
        else:
            browser = await playwright.chromium.launch()
            
            current_context = await browser.new_context()
            new_page = await current_context.new_page()
            print("Please loggin to your account")
            await new_page.goto("https://www.guitarclub.io/login")
            input("Press any key to continue after loggin in: ")
            
        
        for course_link in course_urls:
            await new_page.goto(BASE_URL + course_link)
            
            course_name = clean_special_characters(await new_page.title())
            print(course_name)
            
            os.makedirs(f'./{course_name}', exist_ok=True)
            
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
            
            # Print details about each unit element
            for unit_element in (unique_unit_elements):
                unit_id = await unit_element.get_attribute("id")
                unit_number_element = await unit_element.query_selector("div.flex.flex-col.grow > p:nth-child(1)")
                unit_name_element = await unit_element.query_selector("div.flex.flex-col.grow > p:nth-child(2)")
                unit_name = (await unit_number_element.text_content()) + " - " + (await unit_name_element.text_content() if unit_name_element else "Unknown")
                unit_name = clean_special_characters(unit_name.strip())
                os.makedirs(f"./{course_name}/{unit_name}", exist_ok=True)
                lesson_elements = await unit_element.query_selector_all(LESSON_SELECTOR)
                print(unit_id + " - " + unit_name)
                for lesson_ele in lesson_elements:
                    lesson_name = clean_special_characters(await lesson_ele.text_content()).strip()
                    lesson_url = BASE_URL + (await lesson_ele.get_attribute('href'))
                    
                    # Check if this URL has already been downloaded
                    if is_url_already_downloaded(CSV_TRACKING_PATH, lesson_url):
                        print(f"Already downloaded: {lesson_name} - skipping...")
                        continue
                    
                    save_file_path = f"./{course_name}/{unit_name}/{lesson_name}.mp4"
                    pdf_notes_path = f"./{course_name}/{unit_name}/{lesson_name} lesson note.pdf"
                    
                    video_page = await current_context.new_page()
                    
                    # Create a list to store m3u8 URLs for this lesson
                    m3u8_urls = []
                    # m3u8_request_details = []
                    
                    # Set up network interception to capture m3u8 requests
                    async def intercept_response_for_m3u8(response):
                        url = response.url
                        if '.m3u8' in url or 'playlist' in url.lower() or 'video' in url.lower():
                            m3u8_urls.append(url)
                            # # Capture request details
                            # request = response.request
                            # headers = await request.all_headers()
                            # m3u8_request_details.append({
                            #     'url': url,
                            #     'method': request.method,
                            #     'headers': headers
                            # })
                            
                    video_page.on("response", intercept_response_for_m3u8)
                    
                    
                    await video_page.goto(lesson_url)
                    await video_page.wait_for_load_state("domcontentloaded")
                    await video_page.locator(PLAY_BUTTON_SELECTOR).click()
                    # Wait a bit for video to load and network requests to complete
                    await video_page.wait_for_timeout(1000)
                    
                    # Hide the toolbox element if it exists
                    toolbox_element = await video_page.query_selector(TOOLBOX_SELECTOR)
                    if toolbox_element:
                        await video_page.evaluate("(element) => element.style.display = 'none'", toolbox_element)
                    
                    await video_page.pdf(
                        path=pdf_notes_path,
                        margin={ "top": '20px', "bottom": '20px', "right": '10px', "left": '10px' }
                    )
                    
                    if len(m3u8_urls) > 0:
                        download_result = download_m3u8_with_ffmpeg(m3u8_urls[0], save_file_path)
                        if download_result['success']:
                            print(f"Download successful! File size: {download_result['file_size']} bytes")
                            write_to_csv(CSV_TRACKING_PATH, [course_name, unit_name, lesson_name, save_file_path, lesson_url, m3u8_urls[0], pdf_notes_path])
                        else:
                            print(f"Download failed: {download_result['error']}")
                            write_to_csv(CSV_NOT_DOWNLOADED_TRACKING_PATH, [course_name, unit_name, lesson_name, save_file_path, lesson_url, m3u8_urls[0], pdf_notes_path, download_result['error']])
                    
                    await video_page.close()
                    
        await new_page.close()

# Run the async function with asyncio
asyncio.run(main())

