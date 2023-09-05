import sqlalchemy as sql
import pandas as pd
import time
import polars as pl

con = sql.create_engine("mssql+pyodbc://xsw")

# 34 s from UHBW, 7,356,371 rows (spells, pandas)
start = time.time()
raw_spells = pd.read_sql("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_spell_001", con)
stop = time.time()
stop - start

# 58 s from UHBW, 7,356,371 rows (spells, polars)
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_spells = pl.read_database("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_spell_001", connection=connection_uri)
stop = time.time()
stop - start

# 48 s from UHBW, 11,051,315 rows (episodes)
start = time.time()
raw_episodes = pd.read_sql("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", con)
stop = time.time()
stop - start

# 97 s from UHBW, 11,051,315 rows (episodes, polars)
connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_spells = pl.read_database("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", connection=connection_uri)
stop = time.time()
stop - start

connection_uri = "mssql://XSW-000-SP09/ABI?trusted_connection=true"
start = time.time()
raw_episodes = pl.read_database_uri("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", connection_uri)
stop = time.time()
stop - start