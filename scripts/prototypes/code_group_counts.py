import pandas as pd
from py_hic.clinical_codes import get_codes_in_group, get_groups_in_codes_file
import re

def get_single_code_group(codes_file, code_group, diagnosis_or_procedure):
    '''
    Helper function to get the list of codes in a group, and append
    columns for the group name and whether it is a diagnosis or
    procedure group.

    codes_file: string
        The path to the codes file (absolute, or relative to working directory)
    code_group: string
        The name of the group in the codes file
    diagnosis_or_procedure: string
        Either "diagnosis" or "procedure". Used to tag the resulting codes.
    '''
    df = get_codes_in_group(codes_file, code_group)
    df["type"] = diagnosis_or_procedure
    df["group"] = code_group
    return df

def normalise_code(code):
    '''
    Remove all whitespace and any dot character,
    and convert characters in the code to lower case.
    '''
    alpha_num = re.sub(r'\W+', '', code)
    return alpha_num.lower()

def get_code_groups(diagnoses_file, procedures_file):
    '''
    Get a pandas dataframe of all the diagnosis (ICD-10) and procedure (OPCS-4) 
    groups defined in the diagnosis and procedure code files specified.
    The resulting table has four columns:
    
     - name: the code itself (letters are lowercase, no dots, no whitespace)
     - docs: the string description of the code
     - group: the name of the group that this code belongs to
     - type: either "diagnosis" (for ICD-10) or "procedure" (for OPCS-4)
    
     Note that the same code can appear in multiple rows, when it is in
     multiple groups (one row per group).
     '''
    dfs = []

    # Get all diagnosis groups
    diagnoses_groups = get_groups_in_codes_file(diagnoses_file)
    for group in diagnoses_groups:
        dfs.append(get_single_code_group(diagnoses_file, group, "diagnosis"))

    # Get all procedures groups
    procedures_groups = get_groups_in_codes_file(procedures_file)
    for group in procedures_groups:
        dfs.append(get_single_code_group(procedures_file, group, "procedure"))

    df = pd.concat(dfs)

    # Remove dots and whitespace from all codes and convert to lowercase
    df["name"] = df["name"].transform(normalise_code)

    return df