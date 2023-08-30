import sqlalchemy as sql
import pandas as pd
import polars as pl
import time
import re
from code_group_counts import normalise_code

# Fixed query for getting spells data from HES (BNSSG-ICB).
query = """select AIMTC_Pseudo_NHS as nhs_number,
    AIMTC_Age as age,
    Sex as gender,
    PBRspellID as spell_id,
    AIMTC_ProviderSpell_Start_Date as spell_start_date,
    AIMTC_ProviderSpell_End_Date as spell_end_date,
    diagnosisprimary_icd as diagnosis_0,
    diagnosis1stsecondary_icd as diagnosis_1,
    diagnosis2ndsecondary_icd as diagnosis_2,
    diagnosis3rdsecondary_icd as diagnosis_3,
    diagnosis4thsecondary_icd as diagnosis_4,
    diagnosis5thsecondary_icd as diagnosis_5,
    diagnosis6thsecondary_icd as diagnosis_6,
    diagnosis7thsecondary_icd as diagnosis_7,
    diagnosis8thsecondary_icd as diagnosis_8,
    diagnosis9thsecondary_icd as diagnosis_9,
    diagnosis10thsecondary_icd as diagnosis_10,
    diagnosis11thsecondary_icd as diagnosis_11,
    diagnosis12thsecondary_icd as diagnosis_12,
    diagnosis13thsecondary_icd as diagnosis_13,
    diagnosis14thsecondary_icd as diagnosis_14,
    diagnosis15thsecondary_icd as diagnosis_15,
    diagnosis16thsecondary_icd as diagnosis_16,
    diagnosis17thsecondary_icd as diagnosis_17,
    diagnosis18thsecondary_icd as diagnosis_18,
    diagnosis19thsecondary_icd as diagnosis_19,
    diagnosis20thsecondary_icd as diagnosis_20,
    diagnosis21stsecondary_icd as diagnosis_21,
    diagnosis22ndsecondary_icd as diagnosis_22,
    diagnosis23rdsecondary_icd as diagnosis_23,
    primaryprocedure_opcs as procedure_0,
    procedure2nd_opcs as procedure_1,
    procedure3rd_opcs as procedure_2,
    procedure4th_opcs as procedure_3,
    procedure5th_opcs as procedure_4,
    procedure6th_opcs as procedure_5,
    procedure7th_opcs as procedure_6,
    procedure8th_opcs as procedure_7,
    procedure9th_opcs as procedure_8,
    procedure10th_opcs as procedure_9,
    procedure11th_opcs as procedure_10,
    procedure12th_opcs as procedure_11,
    procedure13th_opcs as procedure_12,
    procedure14th_opcs as procedure_13,
    procedure15th_opcs as procedure_14,
    procedure16th_opcs as procedure_15,
    procedure17th_opcs as procedure_16,
    procedure18th_opcs as procedure_17,
    procedure19th_opcs as procedure_18,
    procedure20th_opcs as procedure_19,
    procedure21st_opcs as procedure_20,
    procedure22nd_opcs as procedure_21,
    procedure23rd_opcs as procedure_22,
    procedure24th_opcs as procedure_23
    from ABI.dbo.vw_apc_sem_spell_001
    where AIMTC_ProviderSpell_Start_Date between '2022-08-01' and '2023-01-01'  
    """

def get_spells_hes_pandas():
    con = sql.create_engine("mssql+pyodbc://xsw")
    start = time.time()
    raw_data = pd.read_sql(query, con)  # (query=query, connection=connection_uri)
    stop = time.time()
    print(f"Time to fetch spells data: {stop - start}")
    return raw_data

def get_spells_hes_polars():
    connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
    start = time.time()
    raw_data = pl.read_database(query=query, connection=connection_uri)
    stop = time.time()
    print(f"Time to fetch spells data: {stop - start}")
    return raw_data

def convert_codes_to_long(df):
    '''
    df is a table containing the diagnosis and procedure columns returned
    from get_spells_hes_pandas(). The result is a table with index column
    spell_id, a column of normalised diagnosis or procedure codes with the
    prefix icd10_ or opcs4_, and a position column indicating the code
    position (0 for primary, increasing for more secondary).
    '''
    pattern = re.compile("(diagnosis|procedure)")
    code_cols = [s for s in df.columns if pattern.search(s)]
    index_cols = ["spell_id"]

    # Pivot all the diagnosis and procedure codes into one
    # columns. Consider https://stackoverflow.com/questions/47684961/
    # melt-uneven-data-in-columns-and-ignore-nans-using-pandas
    # for speed.
    long_codes = pd.melt(df, id_vars=index_cols, value_vars=code_cols).dropna()
    long_codes.value = long_codes.value.apply(normalise_code)
    # Prepend icd10 or opc4 to the codes to indicate which are which
    # (because some codes appear in both ICD-10 and OPCS-4)
    pattern = re.compile("diagnosis")
    diagnosis_or_procedure = ["icd10_" if pattern.search(s) else "opcs4_" for s in long_codes.variable]
    long_codes["full_code"] = diagnosis_or_procedure + long_codes.value
    long_codes["position"] = long_codes["variable"].replace("(diagnosis|procedure)_", "", regex = True).astype(int)
    long_codes = long_codes.drop(columns=["variable", "value"])
    return long_codes

def make_linear_position_scale(long_codes, N = 23):
    '''
    Using the result from convert_codes_to_long, remap the
    clinical code position to a linear scale where 1 is the
    last secondary, and N+1 is primary, where N is the total
    number of diagnosis or procedure columns
    '''
    df = long_codes.copy()
    df.position = N + 1 - df.position
    return df

