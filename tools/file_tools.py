# file_utils.py

import os
import shutil
import glob
import re
import difflib
import json
from typing import Dict, List

from logger.log_wrapper import get_logger  # noqa: F401 (reserved for future structured logging in tools)
from tools.context import ToolsContext

# --- Security Helper ---
def is_safe_path(base, path, follow_symlinks=True):
    """
    Checks if the resolved path is safely within the base directory.
    """
    if follow_symlinks:
        # Resolve both paths consistently to handle symlinks properly (e.g., /var -> /private/var on macOS)
        base_resolved = os.path.realpath(base)
        path_resolved = os.path.realpath(path)
    else:
        base_resolved = os.path.abspath(base)
        path_resolved = os.path.abspath(path)
    return os.path.commonpath([base_resolved, path_resolved]) == base_resolved


def get_tools(tools_context: ToolsContext):
    """File System Operations Tools"""
    
    def init(self, agent_work_dir: str):
        self.agent_work_dir = agent_work_dir
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir)

    def write_to_file(filename: str, content: str):
        """
        Writes content to a file. The path is relative to the agent's working directory.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
            return f"Successfully wrote to file '{filename}'."
        except Exception as e:
            return f"Error writing to file: {e}"

    def append_to_file(filename: str, content: str):
        """
        Appends content to a file. Creates the file if it doesn't exist.
        Path is relative to the agent's working directory.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'a') as f:
                f.write(content)
            return f"Successfully appended to file '{filename}'."
        except Exception as e:
            return f"Error appending to file: {e}"

    def read_file(filename: str):
        """
        Reads the content of a file. The path is relative to the agent's working directory.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def file_exists(path: str):
        """
        Returns True if the path exists (file or directory) within the agent's working directory; otherwise False.
        """
        target = os.path.join(self.agent_work_dir, path)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), target):
            return False
        try:
            return os.path.exists(target)
        except Exception:
            return False

    def is_directory(path: str):
        """
        Returns True if the path is an existing directory within the agent's working directory; otherwise False.
        """
        target = os.path.join(self.agent_work_dir, path)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), target):
            return False
        try:
            return os.path.isdir(target)
        except Exception:
            return False

    def list_directory(path: str = "."):
        """
        Lists the contents of a directory. Path is relative to the agent's working directory.
        """
        dirpath = os.path.join(self.agent_work_dir, path)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), dirpath):
            return "Error: Path is outside the agent's working directory."
        try:
            return os.listdir(dirpath)
        except Exception as e:
            return f"Error listing directory: {e}"

    def create_directory(path: str):
        """
        Creates a new directory. Path is relative to the agent's working directory.
        """
        dirpath = os.path.join(self.agent_work_dir, path)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), dirpath):
            return "Error: Path is outside the agent's working directory."
        try:
            os.makedirs(dirpath, exist_ok=True)
            return f"Successfully created directory '{path}'."
        except Exception as e:
            return f"Error creating directory: {e}"

    def delete_file(filename: str):
        """
        Deletes a file. The path is relative to the agent's working directory.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            os.remove(filepath)
            return f"Successfully deleted file '{filename}'."
        except Exception as e:
            return f"Error deleting file: {e}"

    def delete_directory(path: str):
        """
        Deletes a directory and all its contents recursively. Path is relative to the agent's working directory.
        """
        dirpath = os.path.join(self.agent_work_dir, path)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), dirpath):
            return "Error: Path is outside the agent's working directory."
        try:
            shutil.rmtree(dirpath)
            return f"Successfully deleted directory '{path}'."
        except Exception as e:
            return f"Error deleting directory: {e}"

    def copy_directory(source: str, destination: str):
        """
        Copies a directory and its contents recursively within the agent's working directory.
        Fails if destination already exists.
        """
        source_path = os.path.join(self.agent_work_dir, source)
        dest_path = os.path.join(self.agent_work_dir, destination)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), source_path) or not is_safe_path(os.path.abspath(self.agent_work_dir), dest_path):
            return "Error: One or both paths are outside the agent's working directory."
        try:
            if not os.path.isdir(source_path):
                return f"Error: Source directory '{source}' does not exist."
            if os.path.exists(dest_path):
                return f"Error: Destination '{destination}' already exists."
            shutil.copytree(source_path, dest_path)
            return f"Successfully copied directory '{source}' to '{destination}'."
        except Exception as e:
            return f"Error copying directory: {e}"

    def replace_in_file(filename: str, old_text: str, new_text: str):
        """
        Replaces all occurrences of old_text with new_text in the specified file.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            content = content.replace(old_text, new_text)
            with open(filepath, 'w') as f:
                f.write(content)
            return f"Successfully replaced text in '{filename}'."
        except Exception as e:
            return f"Error replacing text in file: {e}"

    def file_head(filename: str, num_lines: int = 10):
        """
        Returns the first N lines of a file.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            return "".join(lines[:num_lines])
        except Exception as e:
            return f"Error reading head of file: {e}"

    def file_tail(filename: str, num_lines: int = 10):
        """
        Returns the last N lines of a file.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            return "".join(lines[-num_lines:])
        except Exception as e:
            return f"Error reading tail of file: {e}"

    def file_grep(pattern: str, search_dir: str = "."):
        """
        Searches for a regex pattern in files within a specified directory.
        Returns a dictionary with filenames as keys and a list of matching lines as values.
        """
        search_path = os.path.join(self.agent_work_dir, search_dir)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), search_path):
            return "Error: Search path is outside the agent's working directory."
        
        matches: Dict[str, List[str]] = {}
        try:
            for root, _, files in os.walk(search_path):
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', errors='ignore') as f:
                            for i, line in enumerate(f):
                                if re.search(pattern, line):
                                    relative_path = os.path.relpath(filepath, self.agent_work_dir)
                                    if relative_path not in matches:
                                        matches[relative_path] = []
                                    matches[relative_path].append(f"{i+1}: {line.strip()}")
                    except Exception:
                        # Ignore files that can't be opened
                        pass
            return matches if matches else "No matches found."
        except Exception as e:
            return f"Error during grep: {e}"

    def find_files(search_dir: str = ".", pattern: str = "*"):
        """
        Finds files matching a pattern in a directory.
        Uses glob for pattern matching. e.g., '*.py', '**/*.txt' (for recursive).
        """
        search_path = os.path.join(self.agent_work_dir, search_dir)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), search_path):
            return "Error: Search path is outside the agent's working directory."
        
        recursive = "**" in pattern
        try:
            # We need to change the current directory to the search path for glob to work correctly
            # with relative paths and `recursive=True`
            original_cwd = os.getcwd()
            os.chdir(search_path)
            
            found_files = glob.glob(pattern, recursive=recursive)
            
            os.chdir(original_cwd) # Change back to the original directory
            
            # Return the found files with paths relative to the agent's working directory
            return [os.path.join(search_dir, f) for f in found_files]
        except Exception as e:
            return f"Error during find_files: {e}"

    def diff_files(file1: str, file2: str):
        """
        Compares two files and returns their differences in a unified diff format.
        """
        file1_path = os.path.join(self.agent_work_dir, file1)
        file2_path = os.path.join(self.agent_work_dir, file2)
        
        if not is_safe_path(os.path.abspath(self.agent_work_dir), file1_path) or \
           not is_safe_path(os.path.abspath(self.agent_work_dir), file2_path):
            return "Error: One or both file paths are outside the agent's working directory."
        
        try:
            with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
                diff = difflib.unified_diff(
                    f1.readlines(), 
                    f2.readlines(), 
                    fromfile=file1, 
                    tofile=file2, 
                    lineterm=''
                )
                return '\n'.join(diff)
        except Exception as e:
            return f"Error comparing files: {e}"

    def apply_unified_diff(diff_text: str):
        """
        Applies a unified diff (generated by diff_files) to the original file in the agent's working directory.
        Limitations: supports patches produced for files within the agent work dir; does not handle renames.
        """
        try:
            lines = diff_text.splitlines()
            if not lines:
                return "Error: Empty diff."

            from_file = None
            i = 0
            # Parse headers
            while i < len(lines):
                line = lines[i]
                if line.startswith('--- '):
                    from_file = line[4:].strip()
                elif line.startswith('+++ '):
                    # Destination header not used by this simplified applier
                    _ = line[4:].strip()
                    i += 1
                    break
                i += 1

            if not from_file:
                return "Error: Missing '---' header in diff."

            # Resolve path and read original
            # The headers carry the path as provided to diff; use it as a relative path
            from_path = os.path.join(self.agent_work_dir, from_file)
            if not is_safe_path(os.path.abspath(self.agent_work_dir), from_path):
                return "Error: Patch targets path outside working directory."
            if not os.path.exists(from_path):
                return f"Error: Target file '{from_file}' does not exist."
            with open(from_path, 'r') as f:
                orig_lines = f.read().splitlines()

            new_lines = []
            orig_idx = 0

            # Process hunks
            while i < len(lines):
                line = lines[i]
                if not line.startswith('@@ '):
                    i += 1
                    continue
                # Parse hunk header: @@ -a,b +c,d @@
                try:
                    header = line
                    # Extract original start
                    minus_part = header.split('@@')[1].strip().split(' ')[0]  # like '-a,b'
                    a_str = minus_part.split(',')[0].lstrip('-')
                    a = int(a_str) if a_str else 1
                except Exception:
                    return "Error: Invalid hunk header."

                i += 1
                # Copy unchanged lines before this hunk
                copy_until = a - 1  # 1-based
                while orig_idx < copy_until - 1 and orig_idx < len(orig_lines):
                    new_lines.append(orig_lines[orig_idx])
                    orig_idx += 1

                # Apply hunk body
                while i < len(lines) and not lines[i].startswith('@@ '):
                    h = lines[i]
                    if h.startswith(' '):
                        # context line
                        new_lines.append(h[1:])
                        orig_idx += 1
                    elif h.startswith('-'):
                        # deletion
                        orig_idx += 1
                    elif h.startswith('+'):
                        # addition
                        new_lines.append(h[1:])
                    elif h.startswith('--- ') or h.startswith('+++ '):
                        # next file header; stop processing
                        break
                    i += 1
                # do not increment i here; while loop handles it

            # Append remaining original lines
            while orig_idx < len(orig_lines):
                new_lines.append(orig_lines[orig_idx])
                orig_idx += 1

            # Write back
            with open(from_path, 'w') as f:
                f.write("\n".join(new_lines))
            return f"Successfully applied patch to '{from_file}'."
        except Exception as e:
            return f"Error applying patch: {e}"

    def move_file(source: str, destination: str):
        """
        Moves or renames a file or directory.
        """
        source_path = os.path.join(self.agent_work_dir, source)
        dest_path = os.path.join(self.agent_work_dir, destination)
        
        if not is_safe_path(os.path.abspath(self.agent_work_dir), source_path) or \
           not is_safe_path(os.path.abspath(self.agent_work_dir), dest_path):
            return "Error: One or both paths are outside the agent's working directory."
        
        try:
            shutil.move(source_path, dest_path)
            return f"Successfully moved '{source}' to '{destination}'."
        except Exception as e:
            return f"Error moving file: {e}"

    def copy_file(source: str, destination: str):
        """
        Copies a file.
        """
        source_path = os.path.join(self.agent_work_dir, source)
        dest_path = os.path.join(self.agent_work_dir, destination)
        
        if not is_safe_path(os.path.abspath(self.agent_work_dir), source_path) or \
           not is_safe_path(os.path.abspath(self.agent_work_dir), dest_path):
            return "Error: One or both paths are outside the agent's working directory."
        
        try:
            shutil.copy2(source_path, dest_path)
            return f"Successfully copied '{source}' to '{destination}'."
        except Exception as e:
            return f"Error copying file: {e}"

    def get_file_metadata(filename: str):
        """
        Gets metadata for a file (size, modification time, creation time) and returns it as a JSON string.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        
        try:
            stat_info = os.stat(filepath)
            metadata = {
                "size": stat_info.st_size,
                "mtime": stat_info.st_mtime,
                "ctime": stat_info.st_ctime,
            }
            return json.dumps(metadata)
        except Exception as e:
            return f"Error getting file metadata: {e}"

    def create_file(filename: str, content: str = ""):
        """
        Creates a new file with optional content. Path is relative to the agent's working directory.
        This is a convenience function that combines directory creation and file writing.
        """
        filepath = os.path.join(self.agent_work_dir, filename)
        if not is_safe_path(os.path.abspath(self.agent_work_dir), filepath):
            return "Error: Path is outside the agent's working directory."
        
        try:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Create the file
            with open(filepath, 'w') as f:
                f.write(content)
            
            return f"Successfully created file '{filename}'."
        except Exception as e:
            return f"Error creating file: {e}"
    
    # Return list of tools
    return [
        write_to_file,
        append_to_file,
        read_file,
        list_directory,
        create_directory,
        create_file,
        delete_file,
        delete_directory,
        copy_directory,
        replace_in_file,
        file_head,
        file_tail,
        file_grep,
        find_files,
        diff_files,
        apply_unified_diff,
        move_file,
        copy_file,
        get_file_metadata,
        file_exists,
        is_directory,
    ]
        