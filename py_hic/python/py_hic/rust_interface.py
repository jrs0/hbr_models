## The main (user-level) interface to the rust_hic library is defined
## in this file.
##

from py_hic import _lib_name
import os

def get_groups_in_codes_file(codes_file_path):
    '''
    Get the list of valid group names defined in a codes file
    '''
    if not os.path.exists(codes_file_path):
        raise ValueError("The codes file '", codes_file_path, "' does not exist")
    return _lib_name.rust_get_groups_in_codes_file(codes_file_path)