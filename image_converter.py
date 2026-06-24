# image_converter.py
import os
import sys
import subprocess
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def get_magick_path():
    """
    Returns the absolute path to magick.exe.
    When running from source, looks in the same directory as this script.
    When bundled by PyInstaller, looks inside the temporary extraction folder.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temporary folder and stores path in sys._MEIPASS
        base_path = sys._MEIPASS
    else:
        # Normal Python execution: use the directory of this script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    magick_exe = os.path.join(base_path, 'magick.exe')
    if not os.path.isfile(magick_exe):
        raise FileNotFoundError(
            f"ImageMagick executable not found at:\n{magick_exe}\n"
            "Please place magick.exe in the project root and try again."
        )
    return magick_exe


def convert_image_to_webp(input_filepath, output_filepath, quality=80, lossless=False):
    """Converts a single image to WebP format using ImageMagick."""
    try:
        magick = get_magick_path()
    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
        return False

    output_dir_path = os.path.dirname(output_filepath)
    if output_dir_path:
        os.makedirs(output_dir_path, exist_ok=True)

    cmd = [
        magick,
        input_filepath,
        "-quality", str(quality),
    ]
    
    if not input_filepath.lower().endswith('.webp'):
        cmd.extend(["-define", f"webp:lossless={str(lossless).lower()}"])
    
    cmd.append(output_filepath)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode != 0:
            print(f"ImageMagick error converting {input_filepath}: {result.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"Unexpected error while calling ImageMagick for {input_filepath}: {e}")
        return False


def process_images(input_path, output_dir=None, quality=80, lossless=False,
                   recursive=False, no_overwrite=False, progress_callback=None,
                   parallel=False, max_workers=None):
    """Process images and convert to WebP using ImageMagick."""

    images_to_convert = []
    base_input_dir = ""

    if os.path.isfile(input_path):
        if input_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp')):
            images_to_convert = [input_path]
            base_input_dir = os.path.dirname(input_path)
        else:
            message = f"Input is not a supported image file: {input_path}"
            if progress_callback:
                progress_callback(0, 0, message)
            else:
                print(message)
            return
    elif os.path.isdir(input_path):
        base_input_dir = input_path
        image_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp')
        if recursive:
            for root, _, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith(image_extensions):
                        images_to_convert.append(os.path.join(root, file))
        else:
            for file in os.listdir(input_path):
                filepath = os.path.join(input_path, file)
                if os.path.isfile(filepath) and file.lower().endswith(image_extensions):
                    images_to_convert.append(filepath)
    else:
        message = f"Error: Invalid input path: {input_path}"
        if progress_callback:
            progress_callback(0, 0, message)
        else:
            print(message)
        return

    if not images_to_convert:
        message = "No supported image files (PNG, JPG, JPEG, TIFF, BMP, WebP) found to convert."
        if progress_callback:
            progress_callback(0, 0, message)
        else:
            print(message)
        return

    total_images = len(images_to_convert)
    converted_count = 0
    skipped_count = 0
    failed_count = 0

    if parallel:
        if max_workers is None:
            import multiprocessing
            max_workers = min(32, (multiprocessing.cpu_count() or 1) + 4)
        
        def process_single_file(input_filepath):
            filename = os.path.basename(input_filepath)
            base_filename, _ = os.path.splitext(filename)
            output_webp_filename = base_filename + ".webp"
            
            if output_dir:
                if recursive and os.path.isdir(base_input_dir) and base_input_dir != os.path.dirname(input_filepath):
                    relative_subdir = os.path.relpath(os.path.dirname(input_filepath), start=base_input_dir)
                    target_output_dir_for_file = os.path.join(output_dir, relative_subdir)
                else:
                    target_output_dir_for_file = output_dir
            else:
                target_output_dir_for_file = os.path.dirname(input_filepath)
            
            if not os.path.exists(target_output_dir_for_file):
                try:
                    os.makedirs(target_output_dir_for_file, exist_ok=True)
                except OSError as e:
                    return ('failed', filename, f"Error creating output directory: {e}", None)
            
            output_webp_filepath = os.path.join(target_output_dir_for_file, output_webp_filename)
            
            if no_overwrite and os.path.exists(output_webp_filepath):
                rel_path = os.path.relpath(output_webp_filepath, output_dir if output_dir else base_input_dir)
                return ('skipped', filename, f"Skipping: {filename} (already exists at {rel_path})", output_webp_filepath)
            
            try:
                if convert_image_to_webp(input_filepath, output_webp_filepath, quality, lossless):
                    rel_path = os.path.relpath(output_webp_filepath, output_dir if output_dir else base_input_dir)
                    return ('converted', filename, f"Converted: {filename} -> {rel_path}", output_webp_filepath)
                else:
                    return ('failed', filename, f"Failed to convert {filename}.", None)
            except Exception as e:
                return ('failed', filename, f"Unexpected error processing {filename}: {e}", None)
        
        lock = threading.Lock()
        
        if progress_callback is None:  # CLI mode with tqdm
            with tqdm(total=total_images, desc="Converting Images (Parallel)", unit="img") as pbar:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {executor.submit(process_single_file, f): f for f in images_to_convert}
                    
                    for future in as_completed(future_to_file):
                        status, filename, message, output_filepath = future.result()
                        
                        with lock:
                            if status == 'converted':
                                converted_count += 1
                            elif status == 'skipped':
                                skipped_count += 1
                            elif status == 'failed':
                                failed_count += 1
                            pbar.set_postfix_str(f"C:{converted_count} S:{skipped_count} F:{failed_count}")
                            pbar.update(1)
                        
                        print(message)
        else:  # GUI mode with progress_callback
            completed = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(process_single_file, f): f for f in images_to_convert}
                
                for future in as_completed(future_to_file):
                    status, filename, message, output_filepath = future.result()
                    
                    with lock:
                        completed += 1
                        if status == 'converted':
                            converted_count += 1
                        elif status == 'skipped':
                            skipped_count += 1
                        elif status == 'failed':
                            failed_count += 1
                        progress_callback(completed, total_images, message)
        
        summary_message = f"Finished. Converted: {converted_count}, Skipped: {skipped_count}, Failed: {failed_count}."
        if progress_callback:
            progress_callback(total_images, total_images, summary_message)
        else:
            print(summary_message)
        return
    
    # Sequential processing
    with tqdm(total=total_images, desc="Converting Images", unit="img", disable=(progress_callback is not None)) as pbar:
        for i, input_filepath in enumerate(images_to_convert):
            current_progress = i + 1
            filename = os.path.basename(input_filepath)
            base_filename, _ = os.path.splitext(filename)
            output_webp_filename = base_filename + ".webp"
            
            if output_dir:
                if recursive and os.path.isdir(base_input_dir) and base_input_dir != os.path.dirname(input_filepath):
                    relative_subdir = os.path.relpath(os.path.dirname(input_filepath), start=base_input_dir)
                    target_output_dir_for_file = os.path.join(output_dir, relative_subdir)
                else:
                    target_output_dir_for_file = output_dir
            else:
                target_output_dir_for_file = os.path.dirname(input_filepath)

            if not os.path.exists(target_output_dir_for_file):
                try:
                    os.makedirs(target_output_dir_for_file, exist_ok=True)
                except OSError as e:
                    message = f"Error creating output subdirectory {target_output_dir_for_file} for {filename}: {e}"
                    if progress_callback:
                        progress_callback(current_progress, total_images, message)
                    else:
                        print(message)
                    pbar.update(1)
                    failed_count += 1
                    continue

            output_webp_filepath = os.path.join(target_output_dir_for_file, output_webp_filename)

            if no_overwrite and os.path.exists(output_webp_filepath):
                message = f"Skipping: {filename} (already exists)"
                if progress_callback:
                    progress_callback(current_progress, total_images, message)
                else:
                    rel_path = os.path.relpath(output_webp_filepath, output_dir if output_dir else base_input_dir)
                    print(f"Skipping: {filename} (already exists at {rel_path})")
                pbar.update(1)
                skipped_count += 1
                if not progress_callback:
                    pbar.set_postfix_str(f"C:{converted_count} S:{skipped_count} F:{failed_count}")
                continue

            try:
                if convert_image_to_webp(input_filepath, output_webp_filepath, quality, lossless):
                    converted_count += 1
                    message = f"Converted: {filename}"
                    if progress_callback:
                        progress_callback(current_progress, total_images, message)
                    else:
                        rel_path = os.path.relpath(output_webp_filepath, output_dir if output_dir else base_input_dir)
                        print(f"Converted: {filename} -> {rel_path}")
                else:
                    failed_count += 1
                    message = f"Failed to convert {filename}."
                    if progress_callback:
                        progress_callback(current_progress, total_images, message)
            except Exception as e:
                failed_count += 1
                message = f"Unexpected error processing {filename}: {e}"
                if progress_callback:
                    progress_callback(current_progress, total_images, message)
                else:
                    print(message)
            finally:
                pbar.update(1)
                if not progress_callback:
                    pbar.set_postfix_str(f"C:{converted_count} S:{skipped_count} F:{failed_count}")

    summary_message = f"Finished. Converted: {converted_count}, Skipped: {skipped_count}, Failed: {failed_count}."
    if progress_callback:
        progress_callback(total_images, total_images, summary_message)
    else:
        print(summary_message)