# start chrome --remote-debugging-port=9222
import asyncio
import re
import csv
import os
import time
import concurrent.futures
from queue import Queue
from threading import Thread, Lock
from playwright.async_api import async_playwright
from helper import clean_special_characters, write_to_csv, download_m3u8_with_ffmpeg, is_url_already_downloaded

# CSV paths and locks for thread-safe writing
CSV_TRACKING_PATH = "./downloaded_url.csv"
CSV_NOT_DOWNLOADED_TRACKING_PATH = "./not_downloaded.csv"
csv_lock = Lock()

# Course URLs to download
course_urls = [
    "/courses/30-day-beginner-challenge",
    "/courses/acoustic-beginners-level-1",
    "/courses/acoustic-beginners-level-2",
    "/courses/acoustic-fingerstyle-level-1",
    "/courses/acoustic-fingerstyle-level-2",
    "/courses/acoustic-fingerstyle-level-3",
    "/courses/electric-blues-essentials-level-1",
    "/courses/electric-blues-essentials-level-2",
    "/courses/electric-blues-essentials-level-3",
    "/courses/electric-beginners-level-1",
    "/courses/electric-beginners-level-2",
    "/courses/electric-beginners-level-3",
    "/courses/electric-intermediates-level-1",
    "/courses/electric-intermediates-level-2",
    "/courses/funk-essentials-level-1",
    "/courses/harmony",
    "/courses/home-studio-guide",
    "/courses/improvisation-level-1",
    "/courses/lead-guitar-beginners-level-1",
    "/courses/lead-guitar-beginners-level-2",
    "/courses/lead-guitar-intermediates-level-1",
    "/courses/lead-guitar-intermediates-level-2",
    "/courses/beginner-gym",
    "/courses/master-your-fingers",
    "/courses/metal-essentials",
    "/courses/metal-essentials-level-2",
    "/courses/pentatonic-mastery",
    "/courses/practical-modes-ionian",
    "/courses/rock-essentials-level-1",
    "/courses/the-12-songs-of-christmas",
    "/courses/the-basics",
    "/courses/unlocking-major-caged",
    "/courses/unlocking-minor-caged",
]

# CSS selectors
UNIT_SELECTOR = "div.join.join-vertical > div"
PLAY_BUTTON_SELECTOR = "body > main > div > div > div > div > div > div > div:nth-child(1) > div > div > div > button:first-child"
TOOLBOX_SELECTOR = "body > button"
NOTE_SELECTOR = "#notes"
LESSON_SELECTOR = "ol > li > a"
BASE_URL = 'https://www.guitarclub.io'
VIDEO_SELECTOR = "body > main > div > div > div.w-full.max-w-7xl.gap-4.m-auto.py-8.md\:py-16.px-4.md\:px-4.xl\:px-0 > div > div.md\:\[grid-area\:header\].md\:col-span-3 > div.md\:sticky.top-16.z-10 > div:nth-child(1) > div > div > div:nth-child(1) > video"

# Thread-safe write to CSV
def thread_safe_write_to_csv(file_path, content):
    with csv_lock:
        write_to_csv(file_path, content)

# Thread-safe check if URL is already downloaded
def thread_safe_is_url_already_downloaded(csv_path, url):
    with csv_lock:
        return is_url_already_downloaded(csv_path, url)

# Worker function to process a lesson download task
def download_lesson_worker(lesson_task):
    """
    Worker function to download a lesson
    
    Args:
        lesson_task (dict): Contains lesson details including m3u8_url and file paths
    """
    course_name = lesson_task['course_name']
    unit_name = lesson_task['unit_name']
    lesson_name = lesson_task['lesson_name']
    save_file_path = lesson_task['save_file_path']
    lesson_url = lesson_task['lesson_url']
    m3u8_url = lesson_task['m3u8_url']
    pdf_notes_path = lesson_task['pdf_notes_path']
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(save_file_path), exist_ok=True)
    
    print(f"[Thread] Downloading: {course_name} > {unit_name} > {lesson_name}")
    
    # Download video using ffmpeg
    download_result = download_m3u8_with_ffmpeg(m3u8_url, save_file_path)
    
    if download_result['success']:
        print(f"[Thread] Download successful: {lesson_name} - File size: {download_result['file_size']} bytes")
        thread_safe_write_to_csv(CSV_TRACKING_PATH, [
            course_name, unit_name, lesson_name, save_file_path, 
            lesson_url, m3u8_url, pdf_notes_path
        ])
    else:
        print(f"[Thread] Download failed: {lesson_name} - Error: {download_result['error']}")
        thread_safe_write_to_csv(CSV_NOT_DOWNLOADED_TRACKING_PATH, [
            course_name, unit_name, lesson_name, save_file_path, 
            lesson_url, m3u8_url, pdf_notes_path, download_result['error']
        ])
    
    return {
        'lesson_name': lesson_name,
        'success': download_result['success'],
        'file_size': download_result['file_size'] if download_result['success'] else 0
    }

# Worker thread that processes the download queue
def download_queue_worker(download_queue, max_workers=3):
    """
    Worker thread that processes tasks from the download queue
    
    Args:
        download_queue (Queue): Queue containing lesson download tasks
        max_workers (int): Maximum number of concurrent download workers
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while True:
            # Get a task from the queue
            task = download_queue.get()
            
            # Check for sentinel value to exit
            if task is None:
                download_queue.task_done()
                break
                
            try:
                # Submit the task to the executor
                future = executor.submit(download_lesson_worker, task)
                # Wait for the result (optional)
                result = future.result()
                print(f"[Queue] Completed: {result['lesson_name']}")
            except Exception as e:
                print(f"[Queue] Error processing task: {e}")
            finally:
                # Mark the task as done
                download_queue.task_done()
    
    print("[Queue] Download worker thread exiting")

async def extract_course_units(page, course_link):
    """
    Extract all units and their lessons from a course page
    
    Args:
        page: Playwright page object
        course_link (str): Course URL
        
    Returns:
        tuple: (course_name, list of unit elements)
    """
    await page.goto(BASE_URL + course_link)
    
    course_name = clean_special_characters(await page.title())
    os.makedirs(f'./{course_name}', exist_ok=True)
    
    # Wait for page to load
    await page.wait_for_load_state("domcontentloaded")
    
    # Find all elements with IDs that start with "unit"
    unit_elements = await page.query_selector_all(UNIT_SELECTOR)
    
    # Create a list to track seen IDs to avoid duplicates
    seen_ids = []
    unique_unit_elements = []
    
    for element in unit_elements:
        element_id = await element.get_attribute("id")
        if element_id and element_id not in seen_ids:
            seen_ids.append(element_id)
            unique_unit_elements.append(element)
    
    print(f"Found {len(unique_unit_elements)} unit elements in {course_name}")
    return course_name, unique_unit_elements

async def process_course(browser_context, course_link, download_queue):
    """
    Process a single course, gathering units and lessons
    
    Args:
        browser_context: Playwright browser context
        course_link (str): Course URL
        download_queue (Queue): Queue for download tasks
    """
    new_page = await browser_context.new_page()
    try:
        course_name, unit_elements = await extract_course_units(new_page, course_link)
        
        for unit_element in unit_elements:
            unit_id = await unit_element.get_attribute("id")
            unit_number_element = await unit_element.query_selector("div.flex.flex-col.grow > p:nth-child(1)")
            unit_name_element = await unit_element.query_selector("div.flex.flex-col.grow > p:nth-child(2)")
            
            if not unit_number_element:
                continue
                
            unit_name = (await unit_number_element.text_content()) + " - " + (await unit_name_element.text_content() if unit_name_element else "Unknown")
            unit_name = clean_special_characters(unit_name.strip())
            os.makedirs(f"./{course_name}/{unit_name}", exist_ok=True)
            
            lesson_elements = await unit_element.query_selector_all(LESSON_SELECTOR)
            print(f"Processing {unit_id} - {unit_name} with {len(lesson_elements)} lessons")
            
            for lesson_ele in lesson_elements:
                lesson_name = clean_special_characters(await lesson_ele.text_content()).strip()
                lesson_url = BASE_URL + (await lesson_ele.get_attribute('href'))
                
                # Check if this URL has already been downloaded
                if thread_safe_is_url_already_downloaded(CSV_TRACKING_PATH, lesson_url):
                    print(f"Already downloaded: {lesson_name} - skipping...")
                    continue
                
                save_file_path = f"./{course_name}/{unit_name}/{lesson_name}.mp4"
                pdf_notes_path = f"./{course_name}/{unit_name}/{lesson_name} lesson note.pdf"
                
                await process_lesson(browser_context, lesson_url, lesson_name, course_name, unit_name, save_file_path, pdf_notes_path, download_queue)
    finally:
        await new_page.close()

async def process_lesson(browser_context, lesson_url, lesson_name, course_name, unit_name, save_file_path, pdf_notes_path, download_queue):
    """
    Process a single lesson, extracting m3u8 URL and PDF notes
    
    Args:
        browser_context: Playwright browser context
        lesson_url (str): Lesson URL
        lesson_name (str): Lesson name
        course_name (str): Course name
        unit_name (str): Unit name
        save_file_path (str): Path to save the video
        pdf_notes_path (str): Path to save the PDF notes
        download_queue (Queue): Queue for download tasks
    """
    video_page = await browser_context.new_page()
    
    try:
        # Create a list to store m3u8 URLs for this lesson
        m3u8_urls = []
        
        # Set up network interception to capture m3u8 requests
        async def intercept_response_for_m3u8(response):
            url = response.url
            if '.m3u8' in url or 'playlist' in url.lower() or 'video' in url.lower():
                m3u8_urls.append(url)
                
        video_page.on("response", intercept_response_for_m3u8)
        
        await video_page.goto(lesson_url)
        await video_page.wait_for_load_state("domcontentloaded")
        await video_page.locator(PLAY_BUTTON_SELECTOR).click()
        # Wait a bit for video to load and network requests to complete
        await video_page.wait_for_timeout(3000)
        
        # Hide the toolbox element if it exists
        toolbox_element = await video_page.query_selector(TOOLBOX_SELECTOR)
        if toolbox_element:
            await video_page.evaluate("(element) => element.style.display = 'none'", toolbox_element)
        
        # Export the page as PDF
        await video_page.pdf(
            path=pdf_notes_path,
            margin={ "top": '20px', "bottom": '20px', "right": '10px', "left": '10px' }
        )
        
        # If m3u8 URL found, add download task to queue
        if len(m3u8_urls) > 0:
            download_task = {
                'course_name': course_name,
                'unit_name': unit_name,
                'lesson_name': lesson_name,
                'save_file_path': save_file_path,
                'lesson_url': lesson_url,
                'm3u8_url': m3u8_urls[0],
                'pdf_notes_path': pdf_notes_path
            }
            
            # Add task to download queue
            download_queue.put(download_task)
            print(f"Added to download queue: {lesson_name}")
        else:
            print(f"No m3u8 URL found for {lesson_name}")
            thread_safe_write_to_csv(CSV_NOT_DOWNLOADED_TRACKING_PATH, [
                course_name, unit_name, lesson_name, save_file_path, 
                lesson_url, "No m3u8 URL found", pdf_notes_path, "No m3u8 URL found"
            ])
    finally:
        await video_page.close()

async def main():
    # Create a download queue
    download_queue = Queue()
    
    # Start download worker thread
    download_thread = Thread(
        target=download_queue_worker, 
        args=(download_queue, 3),  # Process 3 downloads concurrently
        daemon=True
    )
    download_thread.start()
    
    # Start the course crawling process
    async with async_playwright() as playwright:
        # Connect to an existing instance of Chrome using the connect_over_cdp method.
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        current_context = browser.contexts[0]
        
        # Process courses concurrently
        tasks = []
        for course_link in course_urls:
            task = asyncio.create_task(process_course(current_context, course_link, download_queue))
            tasks.append(task)
        
        # Wait for all course processing tasks to complete
        await asyncio.gather(*tasks)
        
    # Signal download worker to exit
    download_queue.put(None)
    
    # Wait for all download tasks to complete
    download_queue.join()
    download_thread.join(timeout=1.0)
    
    print("All courses and downloads completed!")

if __name__ == "__main__":
    # Run the async function with asyncio
    asyncio.run(main())
