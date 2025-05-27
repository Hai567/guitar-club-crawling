import re, csv, subprocess, os, time


def url_to_ffmpeg(url, file_path):
    return f"""ffmpeg -headers 'accept: */*'$'\r\n''accept-language: en-US,en;q=0.9'$'\r\n''dnt: 1'$'\r\n''origin: {url}' -c copy '{file_path}'"""

def download_m3u8_with_ffmpeg(url, file_path, timeout=300):
    """
    Download video using ffmpeg and check if download succeeded or failed
    
    Args:
        url (str): The video URL to download
        file_path (str): The output file path
        timeout (int): Timeout in seconds (default: 300 = 5 minutes)
    
    Returns:
        dict: {
            'success': bool,
            'return_code': int,
            'output': str,
            'error': str,
            'file_exists': bool,
            'file_size': int
        }
    
    Example Use:
        result = download_ffmpeg("https://example.com/video.m3u8", "output.mp4")
        if result['success']:
            print(f"Download successful! File size: {result['file_size']} bytes")
        else:
            print(f"Download failed: {result['error']}")
            
        # You can also check specific details
        print(f"Return code: {result['return_code']}")
        print(f"File exists: {result['file_exists']}")
        print(f"File size: {result['file_size']} bytes")
    """
    # Build the ffmpeg command
    cmd = [
        'ffmpeg',
        '-headers', "accept: */*\r\naccept-language: en-US,en;q=0.9\r\ndnt: 1",
        '-i', url,
        '-c', 'copy',
        '-y',  # Overwrite output file
        file_path
    ]
    
    result = {
        'success': False,
        'return_code': None,
        'output': '',
        'error': '',
        'file_exists': False,
        'file_size': 0
    }
    
    try:
        print(f"Starting download: {file_path}")
        start_time = time.time()
        
        # Run the ffmpeg command
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        
        result['return_code'] = process.returncode
        result['output'] = process.stdout
        result['error'] = process.stderr
        
        # Check if the command succeeded
        if process.returncode == 0:
            # Check if the file was actually created and has content
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                result['file_exists'] = True
                result['file_size'] = file_size
                
                if file_size > 0:
                    result['success'] = True
                    duration = time.time() - start_time
                    print(f"✅ Download completed: {file_path} ({file_size} bytes, {duration:.1f}s)")
                else:
                    print(f"❌ Download failed: File created but empty ({file_path})")
            else:
                print(f"❌ Download failed: File not created ({file_path})")
        else:
            print(f"❌ Download failed: ffmpeg returned code {process.returncode}")
            print(f"Error: {process.stderr}")
            
    except subprocess.TimeoutExpired:
        result['error'] = f"Download timed out after {timeout} seconds"
        print(f"⏰ Download timed out: {file_path}")
        
    except subprocess.CalledProcessError as e:
        result['return_code'] = e.returncode
        result['error'] = f"Command failed with return code {e.returncode}: {e.stderr}"
        print(f"❌ Download error: {result['error']}")
        
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        print(f"❌ Unexpected error: {result['error']}")
    
    return result

def write_to_csv(file_path, content):
    """Write content to CSV file"""
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # If content is a list of rows, write multiple rows
            if isinstance(content, list) and len(content) > 0:
                # Check if it's a list of lists (multiple rows)
                if isinstance(content[0], (list, tuple)):
                    writer.writerows(content)
                else:
                    # Single row as a list
                    writer.writerow(content)
            elif isinstance(content, (list, tuple)):
                # Single row
                writer.writerow(content)
            else:
                # Single value, write as single cell
                writer.writerow([content])
                
        print(f"Successfully wrote to {file_path}")
    except Exception as e:
        print(f"Error writing to CSV file {file_path}: {e}")

def clean_special_characters(text, keep_spaces=True, replacement_char="_"):
    """
    Clean special characters from text and return a sanitized version
    
    Args:
        text (str): The input text to clean
        keep_spaces (bool): Whether to keep spaces (default: True)
        replacement_char (str): Character to replace special characters with (default: "_")
    
    Returns:
        str: Cleaned text with special characters removed or replaced
        
    Example Use:
        # Keep spaces, replace special chars with underscores
        clean_name = clean_special_characters("Unit 1: Basic Chords & Techniques!")
        # Result: "Unit 1_ Basic Chords _ Techniques"

        # Remove spaces too, good for filenames
        clean_filename = clean_special_characters("Unit 1: Basic Chords & Techniques!", keep_spaces=False)
        # Result: "Unit_1_Basic_Chords_Techniques"

        # Use different replacement character
        clean_dash = clean_special_characters("Unit 1: Basic Chords & Techniques!", replacement_char="-")
        # Result: "Unit 1- Basic Chords - Techniques"
    """
    if not text:
        return ""
    
    # Remove or replace common special characters
    # Keep alphanumeric characters, spaces (if keep_spaces=True), hyphens, and underscores
    if keep_spaces:
        # Allow letters, numbers, spaces, hyphens, and underscores
        cleaned_text = re.sub(r'[^a-zA-Z0-9\s\-_]', replacement_char, text)
    else:
        # Allow letters, numbers, hyphens, and underscores only
        cleaned_text = re.sub(r'[^a-zA-Z0-9\-_]', replacement_char, text)
    
    # Remove multiple consecutive replacement characters
    if replacement_char:
        pattern = re.escape(replacement_char) + r'+'
        cleaned_text = re.sub(pattern, replacement_char, cleaned_text)
    
    # Remove leading/trailing replacement characters and spaces
    cleaned_text = cleaned_text.strip(replacement_char + ' ')
    
    # Collapse multiple spaces into single spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    return cleaned_text

def is_url_already_downloaded(csv_path, url):
    """
    Check if a URL has already been downloaded by reading the CSV file
    
    Args:
        csv_path (str): Path to the CSV file containing downloaded URLs
        url (str): The URL to check
    
    Returns:
        bool: True if URL is already downloaded, False otherwise
        
    Example Use:
        if is_url_already_downloaded("./downloaded_url.csv", lesson_url):
            print("Already downloaded, skipping...")
        else:
            print("Not downloaded yet, proceeding with download...")
    """
    if not os.path.exists(csv_path):
        return False
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            
            # Read header row to find the column index for 'original_url'
            header = next(reader, None)
            if not header:
                return False
            
            # Find the index of the 'original_url' column
            original_url_index = None
            for i, column_name in enumerate(header):
                if column_name.strip().lower() == 'original_url':
                    original_url_index = i
                    break
            
            if original_url_index is None:
                print(f"Warning: 'original_url' column not found in CSV header: {header}")
                return False
            
            # Check each row for the URL
            for row in reader:
                if len(row) > original_url_index:  # Ensure row has the required column
                    original_url = row[original_url_index]
                    if original_url == url:
                        return True
        return False
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")
        return False
