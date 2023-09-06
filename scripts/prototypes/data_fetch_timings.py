# Quick script benchmarking different attempts to fetch the HES data.

import sqlalchemy as sql
import pandas as pd
import time
import polars as pl

con = sql.create_engine("mssql+pyodbc://xsw")


# 1. Comparing pandas and polars

# Overall, pandas seems faster, even though polars is supposed
# to use connectorx and partition the query into parallel queries
# on a column. Most importantly, polars did not appear to return
# all the data.

# 34 s from UHBW, 7,356,371 rows (spells)
# 22 s from home
start = time.time()
raw_spells = pd.read_sql(
    "select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_spell_001", con
)
stop = time.time()
stop - start

# 48 s from UHBW, 11,051,315 rows (episodes)
# 45 s from home
start = time.time()
raw_episodes = pd.read_sql("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", con)
stop = time.time()
stop - start

# Using polars

# Old method (polars 0.18, deprecated)
# 58 s from UHBW, 7,356,371 rows (spells)
# 29 s from home
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_spells = pl.read_database(
    "select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_spell_001",
    connection=connection_uri,
)
stop = time.time()
stop - start

# Old method (polars 0.18, deprecated)
# 97 s from UHBW, 11,051,315 rows (episodes), deprecated
# 44 s from home
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_episodes = pl.read_database(
    "select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", connection=connection_uri
)
stop = time.time()
stop - start

# Not sure why the two newer methods below don't return all
# the data. Turns out that if you specify the partition_on
# and partition_num arguments, not all the data is returned.
# Omitting them does not appear to slow down the function.

# New method (polars 0.19, uses connectorx)
# 48 s from home, 7,356,371 (7,177,052 when using partition)
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_spells = pl.read_database_uri(
    query="select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_spell_001",
    uri=connection_uri,
    engine="connectorx",
    # partition_on="aimtc_pseudo_nhs",
    # partition_num=10,
)
stop = time.time()
stop - start

# New method (polars 0.19, uses connectorx)
# 37 s from home, 11,051,315 (10,810,725 when using partition)
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_episodes = pl.read_database_uri(
    query="select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001",
    uri=connection_uri,
    engine="connectorx",
    # partition_on="aimtc_pseudo_nhs",
    # partition_num=10,
)
stop = time.time()
stop - start

# 2. Workload of interest

# The query of interest is a fetch of all the episodes
# in HES (approximately 10m rows), with about 50 diagnosis
# and procedure columns. Only episodes are benchmarked.

def make_query():
    return (
        "select AIMTC_Pseudo_NHS as nhs_number,"
        "diagnosisprimary_icd as diagnosis_0,"
        "diagnosis1stsecondary_icd as diagnosis_1,"
        "diagnosis2ndsecondary_icd as diagnosis_2,"
        "diagnosis3rdsecondary_icd as diagnosis_3,"
        "diagnosis4thsecondary_icd as diagnosis_4,"
        "diagnosis5thsecondary_icd as diagnosis_5,"
        "diagnosis6thsecondary_icd as diagnosis_6,"
        "diagnosis7thsecondary_icd as diagnosis_7,"
        "diagnosis8thsecondary_icd as diagnosis_8,"
        "diagnosis9thsecondary_icd as diagnosis_9,"
        "diagnosis10thsecondary_icd as diagnosis_10,"
        "diagnosis11thsecondary_icd as diagnosis_11,"
        "diagnosis12thsecondary_icd as diagnosis_12,"
        "diagnosis13thsecondary_icd as diagnosis_13,"
        "diagnosis14thsecondary_icd as diagnosis_14,"
        "diagnosis15thsecondary_icd as diagnosis_15,"
        "diagnosis16thsecondary_icd as diagnosis_16,"
        "diagnosis17thsecondary_icd as diagnosis_17,"
        "diagnosis18thsecondary_icd as diagnosis_18,"
        "diagnosis19thsecondary_icd as diagnosis_19,"
        "diagnosis20thsecondary_icd as diagnosis_20,"
        "diagnosis21stsecondary_icd as diagnosis_21,"
        "diagnosis22ndsecondary_icd as diagnosis_22,"
        "diagnosis23rdsecondary_icd as diagnosis_23,"
        "primaryprocedure_opcs as procedure_0,"
        "procedure2nd_opcs as procedure_1,"
        "procedure3rd_opcs as procedure_2,"
        "procedure4th_opcs as procedure_3,"
        "procedure5th_opcs as procedure_4,"
        "procedure6th_opcs as procedure_5,"
        "procedure7th_opcs as procedure_6,"
        "procedure8th_opcs as procedure_7,"
        "procedure9th_opcs as procedure_8,"
        "procedure10th_opcs as procedure_9,"
        "procedure11th_opcs as procedure_10,"
        "procedure12th_opcs as procedure_11,"
        "procedure13th_opcs as procedure_12,"
        "procedure14th_opcs as procedure_13,"
        "procedure15th_opcs as procedure_14,"
        "procedure16th_opcs as procedure_15,"
        "procedure17th_opcs as procedure_16,"
        "procedure18th_opcs as procedure_17,"
        "procedure19th_opcs as procedure_18,"
        "procedure20th_opcs as procedure_19,"
        "procedure21st_opcs as procedure_20,"
        "procedure22nd_opcs as procedure_21,"
        "procedure23rd_opcs as procedure_22,"
        "procedure24th_opcs as procedure_23 "
        "from ABI.dbo.vw_apc_sem_001"
    )

# 751 s from home
start = time.time()
raw_episodes = pd.read_sql(make_query(), con)
stop = time.time()
stop - start

# 728 s from home, 11,051,315 rows
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_episodes = pl.read_database_uri(
    query=make_query(),
    uri=connection_uri,
    engine="connectorx",
    # partition_on="aimtc_pseudo_nhs",
    # partition_num=10,
)
stop = time.time()
stop - start