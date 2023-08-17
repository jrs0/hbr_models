import os
os.chdir("scripts/prototypes")

import hes
import sqlalchemy as sql
import importlib

importlib.reload(hes)

####### CONNECT TO THE DATABASE #######

con = sql.create_engine("mssql+pyodbc://xsw")

####### FETCH RAW SPELL DATA #######

data = hes.get_spells_hes(con)


