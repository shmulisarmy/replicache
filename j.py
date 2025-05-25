import os
import json

def collect_code_files(root_dir: str, excluded: list = [], extensions=None) -> dict:
    """
    Walk through a directory and collect a dictionary of file paths to their content.

    Parameters:
        root_dir (str): The root directory to scan.
        extensions (set): Set of file extensions to include, e.g., {'.py', '.js'}

    Returns:
        dict: {relative_file_path: file_content}
    """
    code_files = {}

    for subdir, _, files in os.walk(root_dir):
        for file in files:
            filepath = os.path.join(subdir, file)
            if extensions is None or os.path.splitext(file)[1] in extensions and file not in excluded:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        relative_path = os.path.relpath(filepath, root_dir)
                        code_files[relative_path] = f.read()
                except (UnicodeDecodeError, FileNotFoundError):
                    # Skip files that can't be read as text
                    continue

    return code_files

# Example usage:
if __name__ == "__main__":
    root_directory = "."  # Change this to the directory you want
    file_extensions = {'.py'}  # {'.py', '.js', '.html', '.css'}  # You can adjust these

    result = collect_code_files(root_directory, excluded=["j.py"], extensions=file_extensions)
    
    # Print a summary
    with open("code_files.json", "w") as f:
        json.dump(result, f, indent=4)
