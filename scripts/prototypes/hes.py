import sqlalchemy as sql
import pandas as pd
import polars as pl
import time
import re
from code_group_counts import normalise_code


def diagnosis_and_procedure_columns():
    """
    Get the diagnosis and procedure part of the
    query, which is common to both the episodes and
    spells queries.
    """
    return (
        ",diagnosisprimary_icd as diagnosis_0"
        ",diagnosis1stsecondary_icd as diagnosis_1"
        ",diagnosis2ndsecondary_icd as diagnosis_2"
        ",diagnosis3rdsecondary_icd as diagnosis_3"
        ",diagnosis4thsecondary_icd as diagnosis_4"
        ",diagnosis5thsecondary_icd as diagnosis_5"
        ",diagnosis6thsecondary_icd as diagnosis_6"
        ",diagnosis7thsecondary_icd as diagnosis_7"
        ",diagnosis8thsecondary_icd as diagnosis_8"
        ",diagnosis9thsecondary_icd as diagnosis_9"
        ",diagnosis10thsecondary_icd as diagnosis_10"
        ",diagnosis11thsecondary_icd as diagnosis_11"
        ",diagnosis12thsecondary_icd as diagnosis_12"
        ",diagnosis13thsecondary_icd as diagnosis_13"
        ",diagnosis14thsecondary_icd as diagnosis_14"
        ",diagnosis15thsecondary_icd as diagnosis_15"
        ",diagnosis16thsecondary_icd as diagnosis_16"
        ",diagnosis17thsecondary_icd as diagnosis_17"
        ",diagnosis18thsecondary_icd as diagnosis_18"
        ",diagnosis19thsecondary_icd as diagnosis_19"
        ",diagnosis20thsecondary_icd as diagnosis_20"
        ",diagnosis21stsecondary_icd as diagnosis_21"
        ",diagnosis22ndsecondary_icd as diagnosis_22"
        ",diagnosis23rdsecondary_icd as diagnosis_23"
        ",primaryprocedure_opcs as procedure_0"
        ",procedure2nd_opcs as procedure_1"
        ",procedure3rd_opcs as procedure_2"
        ",procedure4th_opcs as procedure_3"
        ",procedure5th_opcs as procedure_4"
        ",procedure6th_opcs as procedure_5"
        ",procedure7th_opcs as procedure_6"
        ",procedure8th_opcs as procedure_7"
        ",procedure9th_opcs as procedure_8"
        ",procedure10th_opcs as procedure_9"
        ",procedure11th_opcs as procedure_10"
        ",procedure12th_opcs as procedure_11"
        ",procedure13th_opcs as procedure_12"
        ",procedure14th_opcs as procedure_13"
        ",procedure15th_opcs as procedure_14"
        ",procedure16th_opcs as procedure_15"
        ",procedure17th_opcs as procedure_16"
        ",procedure18th_opcs as procedure_17"
        ",procedure19th_opcs as procedure_18"
        ",procedure20th_opcs as procedure_19"
        ",procedure21st_opcs as procedure_20"
        ",procedure22nd_opcs as procedure_21"
        ",procedure23rd_opcs as procedure_22"
        ",procedure24th_opcs as procedure_23"
    )


def make_episodes_query(start_date, end_date):
    return (
        "select aimtc_pseudo_nhs as patient_id"
        ",aimtc_age as age"
        ",sex as gender"
        ",pbrspellid as spell_id"
        ",aimtc_providerspell_start_date as spell_start_date"
        ",aimtc_providerspell_end_date as spell_end_date"
        ",startdate_consultantepisode as episode_start_date"
        ",enddate_consultantepisode as episode_end_date"
        + diagnosis_and_procedure_columns()
        + " from abi.dbo.vw_apc_sem_001"
        f" where startdate_consultantepisode between '{start_date}' and '{end_date}'"
    )


def make_spells_query(start_date, end_date):
    return (
        "select aimtc_pseudo_nhs as patient_id"
        ",aimtc_age as age"
        ",sex as gender"
        ",pbrspellid as spell_id"
        ",aimtc_providerspell_start_date as spell_start_date"
        ",aimtc_providerspell_end_date as spell_end_date"
        + diagnosis_and_procedure_columns()
        + " from abi.dbo.vw_apc_sem_spell_001"
        f" where aimtc_providerspell_start_date between '{start_date}' and '{end_date}'"
    )


def get_hes_data(start_date, end_date, spells_or_episodes):
    if spells_or_episodes not in ["spells", "episodes"]:
        raise ValueError(
            f"spells_or_episodes argument must be 'spells' or 'episodes', not {spells_or_episodes}"
        )
    con = sql.create_engine("mssql+pyodbc://xsw")
    start = time.time()
    if spells_or_episodes == "episodes":
        raw_data = pd.read_sql(make_episodes_query(start_date, end_date), con)
    else:
        raw_data = pd.read_sql(make_spells_query(start_date, end_date), con)
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


def convert_codes_to_long(df, record_id):
    """
    df is a table containing the diagnosis and procedure columns returned
    from get_hes_data(). The result is a table with index column
    record_id, a column of normalised diagnosis or procedure codes with the
    prefix icd10_ or opcs4_, and a position column indicating the code
    position (0 for primary, increasing for more secondary).

    The record_id is either "spell_id" or "episode_id", depending on whether
    the table contains spells or episodes.
    
    Testing: not yet tested
    """
    pattern = re.compile("(diagnosis|procedure)")
    code_cols = [s for s in df.columns if pattern.search(s)]

    # Pivot all the diagnosis and procedure codes into one
    # columns. Consider https://stackoverflow.com/questions/47684961/
    # melt-uneven-data-in-columns-and-ignore-nans-using-pandas
    # for speed.

    if record_id == "spell_id":
        long_codes = pd.melt(df, id_vars=["spell_id"], value_vars=code_cols).dropna()
    elif record_id == "episode_id":
        # Implicitly use index as the record_id
        long_codes = pd.melt(df, value_vars=code_cols).dropna()
    else:
        print(f"Unrecognised record_id {record_id}, should be 'spell_id' or 'episode_id'")

    long_codes.value = long_codes.value.apply(normalise_code)
    # Prepend icd10 or opc4 to the codes to indicate which are which
    # (because some codes appear in both ICD-10 and OPCS-4)
    pattern = re.compile("diagnosis")
    long_codes["clinical_code_type"] = [
        "diagnosis" if pattern.search(s) else "procedure" for s in long_codes.variable
    ]
    long_codes["clinical_code"] = long_codes.value
    long_codes["position"] = (
        long_codes["variable"]
        .replace("(diagnosis|procedure)_", "", regex=True)
        .astype(int)
    )
    long_codes = long_codes.drop(columns=["variable", "value"])
    return long_codes


def make_linear_position_scale(long_codes, N=23):
    """
    Using the result from convert_codes_to_long, remap the
    clinical code position to a linear scale where 1 is the
    last secondary, and N+1 is primary, where N is the total
    number of diagnosis or procedure columns.

    Testing: not yet tested
    """
    df = long_codes.copy()
    df.position = N + 1 - df.position
    return df
