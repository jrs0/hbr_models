import sqlalchemy as sql
import pandas as pd
import time
import re
from code_group_counts import normalise_code

def make_mortality_query(start_date, end_date):
    return (
        "select derived_pseudo_nhs as patient_id"
        ", REG_DATE_OF_DEATH as date_of_death"
        ", S_UNDERLYING_COD_ICD10 as cause_of_death_0"
        ", S_COD_CODE_1 as cause_of_death_1"
        ", S_COD_CODE_2 as cause_of_death_2"
        ", S_COD_CODE_3 as cause_of_death_3"
        ", S_COD_CODE_4 as cause_of_death_4"
        ", S_COD_CODE_5 as cause_of_death_5"
        ", S_COD_CODE_6 as cause_of_death_6"
        ", S_COD_CODE_7 as cause_of_death_7"
        ", S_COD_CODE_8 as cause_of_death_8"
        ", S_COD_CODE_9 as cause_of_death_9"
        ", S_COD_CODE_10 as cause_of_death_10"
        ", S_COD_CODE_11 as cause_of_death_11"
        ", S_COD_CODE_12 as cause_of_death_12"
        ", S_COD_CODE_13 as cause_of_death_13"
        ", S_COD_CODE_14 as cause_of_death_14"
        ", S_COD_CODE_15 as cause_of_death_15"
        " from abi.civil_registration.mortality"
        f" where REG_DATE_OF_DEATH between '{start_date}' and '{end_date}'"
        " and derived_pseudo_nhs is not null"
        # This particular value marks invalid NHS number
        " and derived_pseudo_nhs != '9000219621'"
    )

def get_mortality_data(start_date, end_date):

    con = sql.create_engine("mssql+pyodbc://xsw")
    start = time.time()
    raw_data = pd.read_sql(make_mortality_query(start_date, end_date), con)
    stop = time.time()
    print(f"Time to fetch mortality data: {stop - start}")
    return raw_data


def convert_codes_to_long(df):
    """
    df is a table containing the cause of death columns from get_mortality_data(),
    by patient_id. The result is a table with index column
    patient_id, a column of normalised ICD-10 codes, and a position column indicating the code
    position (0 for primary, increasing for more secondary).
    
    Testing: not yet tested
    """
    pattern = re.compile("cause_of_death")
    code_cols = [s for s in df.columns if pattern.search(s)]

    # Pivot all the diagnosis and procedure codes into one
    # columns. Consider https://stackoverflow.com/questions/47684961/
    # melt-uneven-data-in-columns-and-ignore-nans-using-pandas
    # for speed.
    
    long_codes = pd.melt(df, id_vars=["patient_id"], value_vars=code_cols).dropna()

    long_codes["value"] = long_codes["value"].apply(normalise_code)
    # Prepend icd10 or opc4 to the codes to indicate which are which
    # (because some codes appear in both ICD-10 and OPCS-4)
    long_codes["cause_of_death"] = long_codes.value
    long_codes["position"] = (
        long_codes["variable"]
        .replace("cause_of_death_", "", regex=True)
        .astype(int)
    )
    long_codes = long_codes.drop(columns=["variable", "value"])
    return long_codes

def get_all_cause_death(idx_episodes, mortality_dates, follow_up):
    """
    Find which index episodes were followed by all-cause death within
    the follow-up period.
    """
    df = idx_episodes.merge(mortality_dates, how="left", on="patient_id")
    df["all_cause_death_outcome"] = ~df["date_of_death"].isna() & (
        pd.to_datetime(df["date_of_death"]) - df["idx_date"] < follow_up
    )
    return df[["idx_episode_id", "all_cause_death_outcome"]]