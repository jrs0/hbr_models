import sqlalchemy as sql
import pandas as pd
import polars as pl
import time
import re
from code_group_counts import normalise_code
import numpy as np


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
    '''
    You have to add the nhs_number not
    null condition, otherwise pandas will convert the column
    to floating point (with the associated undefined equality
    comparison which comes along with it).
    '''
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
        # Consider adding parentheses around the between .. and construction.,
        # Don't think it makes any difference, but would be safer probably.
        f" where startdate_consultantepisode between '{start_date}' and '{end_date}'"
        " and aimtc_pseudo_nhs is not null"
        # Brace yourself -- this specific NHS number is used to mean "NHS number 
        # is not valid".
        " and aimtc_pseudo_nhs != '9000219621'"
        # Records are also invalid if the commissioner code is not in this list
        " and aimtc_organisationcode_codeofcommissioner in ('5M8','11T','5QJ','11H','5A3','12A','15C','14F','Q65')"
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
        " and aimtc_pseudo_nhs is not null"
        # See comments above for exclusions
        " and aimtc_pseudo_nhs != '9000219621'"
        " and aimtc_organisationcode_codeofcommissioner in ('5M8','11T','5QJ','11H','5A3','12A','15C','14F','Q65')"
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

    if record_id not in ["episode_id", "spell_id"]:
        raise ValueError(
            f"Unrecognised record_id {record_id}; should be 'spell_id' or 'episode_id'"
        )

    long_codes = pd.melt(df, id_vars=[record_id], value_vars=code_cols).dropna()

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

def make_code_group_counts(long_clinical_codes, raw_episodes_data):
    """
    Convert the episodes data into code counts
    
    Use the approximately 50 diagnosis and procedure
    columns in raw_episodes_data to count the number of
    each code occurring in a code group in each episode.
    Code groups are currently hard coded to point to the
    files in ../codes_files/.
    
    The input dataset needs an episode_id column and columns
    of the form diagnosis_n, procedure_n where n runs from
    0 (primary) to N. 
    """
    code_groups = codes.get_code_groups(
        "../codes_files/icd10.yaml", "../codes_files/opcs4.yaml"
    )

    # Count the total number of clinical code groups in each episode. This is
    # achieved by joining the names of the code groups onto the long codes
    # where the type (diagnosis or procedure) matches and also the normalised
    # code (e.g. i211) matches. The groups are pivoted to become columns,
    # with values equal to the number of occurrences of each group in each
    # episode. Due to the inner join of groups onto episodes, any episode with
    # no codes in a group will be dropped. These must be added back on at
    # the end as zero rows.
    code_group_counts = (
        long_clinical_codes.merge(
            code_groups,
            how="inner",
            left_on=["clinical_code_type", "clinical_code"],
            right_on=["type", "name"],
        )[["episode_id", "group"]]
        .pivot_table(index="episode_id", columns="group", aggfunc=len, fill_value=0)
        .merge(raw_episodes_data["episode_id"], how="right", on="episode_id")
        .fillna(0)
    )
    
    return code_group_counts

def get_raw_episodes_data(start_date, end_date, from_file):
    """
    Fetch the raw episodes data (one row per episode), with
    patient_id, age, gender, spell_id, spell and episode start
    and end dates, and diagnosis and procedure columns.
    
    NOTE: if you read from file, then start_date and end_date will
    be ignored.
    
    Use start_date and end_date to limit the range of data 
    returned. The dataset is saved in datasets/raw_episodes_data.pkl.
    Set from_file = True to read from this file instead of SQL.
    """

    # Fetch the raw data. 6 years of data takes 283 s to fetch (from home),
    # so estimating full datasets takes about 1132 s. Same query took 217 s
    # in ICB. Fetching the full dataset takes 1185 s (measured at home),
    # and returns about 10.8m rows. However, excluding rows according to
    # documented exclusions results in about 6.7m rows, and takes about
    # 434 s to fetch (from home)
    if not from_file:
        print("Fetching episodes dataset from SQL")
        raw_episodes_data = get_hes_data(start_date, end_date, "episodes")
        raw_episodes_data.to_pickle("datasets/raw_episodes_dataset.pkl")
    else:
        print("Reading episodes dataset from file")
        raw_episodes_data = pd.read_pickle("datasets/raw_episodes_dataset.pkl")
    
    num_rows = len(raw_episodes_data.index)
    print(f"Dataset contains {num_rows} rows")
    
    # Replace empty string with NaN across the dataset
    raw_episodes_data.replace("", np.nan, inplace=True)
    
    # Store the episode id explicitly as a column
    raw_episodes_data["episode_id"] = raw_episodes_data.index
    
    # Ensure that the spell_id column does not contain NaN
    num_empty_spell_id = raw_episodes_data["spell_id"].isnull().sum()
    print(f"Dropping {num_empty_spell_id} rows with missing spell_id")
    raw_episodes_data.dropna(subset="spell_id", inplace=True)
    
    # Exclude rows where all of the diagnosis/procedure columns are NULL
    rows_before_dropping_empty_codes = len(raw_episodes_data.index)
    pattern = re.compile("(diagnosis|procedure)")
    code_cols = [s for s in raw_episodes_data.columns if pattern.search(s)]
    raw_episodes_data.dropna(subset=code_cols, how="all", inplace=True)
    num_empty_codes = rows_before_dropping_empty_codes - len(raw_episodes_data.index)
    print(f"Dropped {num_empty_codes} rows missing any diagnosis or procedure code")
    
    return raw_episodes_data


def get_episode_start_dates(raw_episodes_data):
    """
    Also need to know the episode start times for comparison of different
    episodes
    """
    return raw_episodes_data[
        ["episode_id", "episode_start_date", "patient_id"]
    ]

def get_age_and_gender(raw_episodes_data):
    """
    Get the age and gender columns
    """
    return raw_episodes_data[["episode_id", "age", "gender"]]

def get_index_episodes(code_group_counts, raw_episodes_data):
    """
    Find the index episodes, which are the ones that contain an ACS or PCI and
    are also the first episode of the spell.
    """
    df = (
        code_group_counts.merge(
            raw_episodes_data[["episode_id", "spell_id", "episode_start_date"]],
            how="left",
            on="episode_id",
        )
        .sort_values("episode_start_date")
        .groupby("spell_id")
        .first()
    )
    assert (
        df.shape[0] == raw_episodes_data.spell_id.nunique()
    ), "Expecting df to have one row per spell in the original dataset"
    idx_episodes = (
        df[(df["acs_bezin"] > 0) | (df["pci"] > 0)]
        .reset_index()[["episode_id", "spell_id"]]
        .rename(columns={"episode_id": "idx_episode_id", "spell_id": "idx_spell_id"})
    )

    # Calculate information about the index event. All index events are
    # ACS or PCI, so if PCI is not performed then the case is medically
    # managed.
    df = idx_episodes.merge(
        code_group_counts, how="left", left_on="idx_episode_id", right_on="episode_id"
    )
    idx_episodes["idx_pci_performed"] = df["pci"] > 0
    idx_episodes["idx_stemi"] = df["mi_stemi_schnier"] > 0
    idx_episodes["idx_nstemi"] = df["mi_nstemi_schnier"] > 0
    idx_episodes = (
        idx_episodes.merge(
            get_episode_start_dates(raw_episodes_data), how="left", left_on="idx_episode_id", right_on="episode_id"
        )
        .merge(get_age_and_gender(raw_episodes_data), how="left", left_on="idx_episode_id", right_on="episode_id")
        .rename(
            columns={
                "episode_start_date": "idx_date",
                "age": "dem_age",
                "gender": "dem_gender",
            }
        )
        .filter(regex="(idx_|dem_|patient_id)")
    )
    return idx_episodes