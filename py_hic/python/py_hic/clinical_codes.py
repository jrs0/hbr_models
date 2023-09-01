## The main (user-level) interface to the rust_hic library is defined
## in this file.
##

from py_hic import _lib_name
import os
import pandas


def get_groups_in_codes_file(codes_file_path):
    """
    Get the list of valid group names defined in a codes file
    """
    if not os.path.exists(codes_file_path):
        raise ValueError(f"The codes file '{codes_file_path}' does not exist")

    return _lib_name.rust_get_groups_in_codes_file(codes_file_path)


def get_codes_in_group(codes_file_path, group):
    """
    Get a pandas dataframe of all the docs in a particular group
    defined in a codes file.

    The datafrane contains two columns: "name", for the clinical code
    name (e.g. "I22.1"); and "docs, for the description of the code
    (e.g. "Subsequent myocardial infarction of inferior wall").
    The group is defined by the codes file (e.g. icd10.yaml), and
    code groups can be edited using the codes editor program.
    """

    # This will also check if the codes file exists
    valid_groups = _lib_name.rust_get_groups_in_codes_file(codes_file_path)

    if not group in valid_groups:
        raise ValueError(
            f"code group '{group}' is not present in codes file '{codes_file_path}'"
        )

    return pandas.DataFrame(_lib_name.rust_get_codes_in_group(codes_file_path, group))

class ClinicalCode:
    def __init__(self, name, docs):
        '''
        Create a new clinical code storing the code name (e.g. I21.0) and docs
        (e.g. Acute transmural myocardial infarction of anterior wall).
        '''
        self.name = name
        self.docs = docs

class ClinicalCodeParser:
    def __init__(self, diagnosis_codes_file_path, procedure_codes_file_path):
        """
        Create a new code parser for diagnosis and procedure codes using
        the code trees provided in the two file paths
        """
        self._parser = _lib_name.RustClinicalCodeParser(
            diagnosis_codes_file_path, procedure_codes_file_path
        )

    def find_exact_diagnosis(self, code):
        '''
        Find an exact match for the diagnosis code provided in the
        argument, or raise a ValueError if the code does not match
        anything in the diagnosis code tree.
        '''
        code = self._parser.find_exact_diagnosis(code)
        return ClinicalCode(code[0], code[1])



