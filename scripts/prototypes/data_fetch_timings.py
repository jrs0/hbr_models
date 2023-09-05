import sqlalchemy as sql
import pandas as pd
import time

con = sql.create_engine("mssql+pyodbc://xsw")

# 34 s from UHBW, 7,356,371 rows (spells)
start = time.time()
raw_spells = pd.read_sql("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_spell_001", con)
stop = time.time()
stop - start

# 48 s from UHBW, 11,051,315 rows (episodes)
start = time.time()
raw_episodes = pd.read_sql("select aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", con)
stop = time.time()
stop - start