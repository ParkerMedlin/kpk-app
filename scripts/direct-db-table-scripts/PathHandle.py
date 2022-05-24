import os
from urllib.parse import urlparse


class PathHandler(object):

    def __init__(self, absolute_path:str) -> None:
        self.absolute_path = absolute_path


    def get_filename_from_absolute(self) -> str:
        parsed_url = urlparse(self.absolute_path)
        return os.path.basename(parsed_url.path)

    
    def get_relative_from_absolute(self) -> str:
        parsed_url = urlparse(self.absolute_path)
        return parsed_url.path

    
    def get_parent_folder_from_absolute(self) -> str:
        parsed_url = urlparse(self.absolute_path)
        return os.path.dirname(parsed_url.path)

    
    def get_scheme_and_root_from_absolute(self) -> str:
        parsed_url = urlparse(self.absolute_path)
        return f"{parsed_url.scheme}//{parsed_url.netloc}"
        
    
    def convert_to_absolute_local(self, local_root:str, global_root:str) -> str:
        return local_root + os.sep + self.absolute_path[len(global_root):].replace("/", os.sep)

    
    def convert_to_absolute_global(self, local_root:str, global_root:str) -> str:
        return global_root + "/" + self.absolute_path[len(local_root):].replace(os.sep, "/")