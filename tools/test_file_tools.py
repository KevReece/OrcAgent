import unittest
import os
import shutil
import json
from tools.file_tools import get_tools
from tools.context import ToolsContext

def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True
    )

class TestFileUtils(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory for testing."""
        self.test_dir = "temp_test_dir_for_orcagent"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)
        tools = get_tools(make_tools_context(self.test_dir))
        
        class Self:
            def __init__(self, tools):
                self.write_to_file = tools[0]
                self.append_to_file = tools[1]
                self.read_file = tools[2]
                self.list_directory = tools[3]
                self.create_directory = tools[4]
                self.create_file = tools[5]
                self.delete_file = tools[6]
                self.delete_directory = tools[7]
                self.copy_directory = tools[8]
                self.replace_in_file = tools[9]
                self.file_head = tools[10]
                self.file_tail = tools[11]
                self.file_grep = tools[12]
                self.find_files = tools[13]
                self.diff_files = tools[14]
                self.apply_unified_diff = tools[15]
                self.move_file = tools[16]
                self.copy_file = tools[17]
                self.get_file_metadata = tools[18]
                self.file_exists = tools[19]
                self.is_directory = tools[20]
        
        self.file_tools = Self(tools)

    def tearDown(self):
        """Clean up the temporary directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_write_and_read_file(self):
        content = "Hello, OrcAgent!"
        self.assertEqual("Successfully wrote to file 'test.txt'.", self.file_tools.write_to_file("test.txt", content))
        self.assertEqual(content, self.file_tools.read_file("test.txt"))
        self.assertIn("Error reading file", self.file_tools.read_file("nonexistent.txt"))

    def test_append_to_file(self):
        self.file_tools.write_to_file("append.txt", "A")
        self.assertEqual("Successfully appended to file 'append.txt'.", self.file_tools.append_to_file("append.txt", "B"))
        self.assertEqual("AB", self.file_tools.read_file("append.txt"))
        # Append to new file creates it
        self.assertEqual("Successfully appended to file 'new.txt'.", self.file_tools.append_to_file("new.txt", "X"))
        self.assertEqual("X", self.file_tools.read_file("new.txt"))

    def test_create_and_list_directory(self):
        self.assertEqual("Successfully created directory 'new_dir'.", self.file_tools.create_directory("new_dir"))
        self.assertIn("new_dir", self.file_tools.list_directory())
        self.file_tools.write_to_file("new_dir/test.txt", "content")
        self.assertEqual(['test.txt'], self.file_tools.list_directory("new_dir"))

    def test_delete_file(self):
        self.file_tools.write_to_file("deleteme.txt", "content")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "deleteme.txt")))
        self.assertEqual("Successfully deleted file 'deleteme.txt'.", self.file_tools.delete_file("deleteme.txt"))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "deleteme.txt")))

    def test_delete_directory(self):
        self.file_tools.create_directory("delete_this_dir")
        self.file_tools.write_to_file("delete_this_dir/test.txt", "content")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "delete_this_dir")))
        self.assertEqual("Successfully deleted directory 'delete_this_dir'.", self.file_tools.delete_directory("delete_this_dir"))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "delete_this_dir")))

    def test_copy_directory(self):
        self.file_tools.create_directory("src_dir/sub")
        self.file_tools.write_to_file("src_dir/sub/file.txt", "content")
        self.assertEqual("Successfully copied directory 'src_dir' to 'dst_dir'.", self.file_tools.copy_directory("src_dir", "dst_dir"))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "dst_dir/sub/file.txt")))
        # Destination exists
        self.assertIn("already exists", self.file_tools.copy_directory("src_dir", "dst_dir"))

    def test_replace_in_file(self):
        self.file_tools.write_to_file("replace.txt", "Hello world world")
        self.file_tools.replace_in_file("replace.txt", "world", "OrcAgent")
        self.assertEqual("Hello OrcAgent OrcAgent", self.file_tools.read_file("replace.txt"))

    def test_head_and_tail(self):
        content = "\n".join([f"Line {i}" for i in range(20)])
        self.file_tools.write_to_file("headtail.txt", content)
        self.assertEqual("Line 0\nLine 1\nLine 2", "\n".join(self.file_tools.file_head("headtail.txt", 3).splitlines()))
        self.assertEqual("Line 17\nLine 18\nLine 19", "\n".join(self.file_tools.file_tail("headtail.txt", 3).splitlines()))

    def test_grep(self):
        self.file_tools.write_to_file("grep_test.txt", "hello world\nanother line\nhello again")
        self.file_tools.create_directory("sub")
        self.file_tools.write_to_file("sub/grep_test2.txt", "another hello")
        result = self.file_tools.file_grep("hello")
        self.assertIn("grep_test.txt", result)
        self.assertIn("sub/grep_test2.txt", result)
        self.assertEqual(len(result["grep_test.txt"]), 2)

    def test_find_files(self):
        self.file_tools.write_to_file("a.txt", "")
        self.file_tools.create_directory("sub")
        self.file_tools.write_to_file("sub/b.py", "")
        found_files = self.file_tools.find_files(pattern="*.txt")
        self.assertIn("./a.txt", found_files)
        found_files_sub = self.file_tools.find_files(search_dir="sub", pattern="*.py")
        self.assertIn("sub/b.py", found_files_sub)

    def test_diff_files(self):
        self.file_tools.write_to_file("file1.txt", "a\nb\nc")
        self.file_tools.write_to_file("file2.txt", "a\nx\nc")
        diff_result = self.file_tools.diff_files("file1.txt", "file2.txt")
        self.assertIn("-b", diff_result)
        self.assertIn("+x", diff_result)

    def test_apply_unified_diff(self):
        self.file_tools.write_to_file("base.txt", "a\nb\nc")
        self.file_tools.write_to_file("target.txt", "a\nx\nc")
        diff_result = self.file_tools.diff_files("base.txt", "target.txt")
        # Apply patch back to base.txt to make it equal to target.txt
        self.assertIn("Successfully applied patch", self.file_tools.apply_unified_diff(diff_result))
        self.assertEqual(self.file_tools.read_file("target.txt"), self.file_tools.read_file("base.txt"))

    def test_move_file(self):
        self.file_tools.write_to_file("move_src.txt", "content")
        self.file_tools.create_directory("move_dest_dir")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "move_src.txt")))
        self.file_tools.move_file("move_src.txt", "move_dest_dir/moved.txt")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "move_src.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "move_dest_dir/moved.txt")))

    def test_copy_file(self):
        self.file_tools.write_to_file("copy_src.txt", "content")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "copy_src.txt")))
        self.file_tools.copy_file("copy_src.txt", "copy_dest.txt")
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "copy_src.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "copy_dest.txt")))
        self.assertEqual(self.file_tools.read_file("copy_src.txt"), self.file_tools.read_file("copy_dest.txt"))

    def test_get_file_metadata(self):
        self.file_tools.write_to_file("metadata.txt", "12345")
        metadata_str = self.file_tools.get_file_metadata("metadata.txt")
        metadata = json.loads(metadata_str)
        self.assertEqual(5, metadata["size"])
        self.assertTrue("mtime" in metadata)

    def test_exists_and_is_dir(self):
        self.file_tools.create_directory("exists_dir")
        self.file_tools.write_to_file("exists_dir/f.txt", "")
        self.assertTrue(self.file_tools.file_exists("exists_dir"))
        self.assertTrue(self.file_tools.is_directory("exists_dir"))
        self.assertTrue(self.file_tools.file_exists("exists_dir/f.txt"))
        self.assertFalse(self.file_tools.is_directory("exists_dir/f.txt"))

if __name__ == '__main__':
    unittest.main() 