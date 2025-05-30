# Guitar Course Multithreaded Crawler

This is a multithreaded version of the Guitar Course crawler. It allows downloading multiple lessons concurrently, which significantly improves download speeds.

## Setup

1. Make sure you have Python installed
2. Install the required dependencies:
    ```
    pip install -r requirements_multithreads.txt
    ```
3. Make sure you have ffmpeg installed and available in your PATH

## Usage

1. Start Chrome with remote debugging enabled:
    ```
    start chrome --remote-debugging-port=9222
    ```
2. Log in to your Guitar Club account in the Chrome browser
3. Run the crawler:
    ```
    python crawler_multithreads.py
    ```

## Features

-   Downloads multiple lessons concurrently (3 by default)
-   Processes multiple courses simultaneously (2 by default)
-   Automatically saves PDF lesson notes
-   Tracks downloaded and failed downloads in CSV files
-   Resumes interrupted downloads (skips already downloaded lessons)
-   Improved error handling and recovery

## Configuration

You can adjust the following parameters in the code:

-   `max_workers` in `download_queue_worker` function: Number of concurrent downloads
-   `sem = asyncio.Semaphore(2)` in `main` function: Number of courses to process simultaneously
-   Customize the download paths by modifying the directory paths

## Output Files

-   `downloaded_url_multithreads.csv`: Tracks successfully downloaded lessons
-   `not_downloaded_multithreads.csv`: Tracks failed downloads
-   Downloaded videos and PDF notes are saved in the `multithreads_downloads` directory

## Troubleshooting

-   If you encounter "connection lost" errors, try reducing the number of concurrent downloads
-   If video URLs aren't being captured, try increasing the wait time after clicking the play button
-   Check Chrome is running with remote debugging enabled on port 9222
