import scipy.sparse
import numpy as np

def encode_sparse(long_codes):
    '''
    The input is a table of codes (full_code
    column) in long format, by the spell_id,
    and containing the clinical code position
    in the position column. The output is a
    sparse matrix
    '''
    sorted_by_spell = long_codes.sort_values("spell_id")

    # A map from a code in the full_code column to
    # a column index. This grows as more codes are
    # encountered while traversing the table
    code_to_column = {}
    for spell_id, row in sorted_by_spell.head(50).iterrows():
        full_code = row["full_code"]
        position = row["position"]
        print(f"{spell_id}, {full_code}, {position}")

    num_rows = long_codes.spell_id.nunique()
    lil_matrix_rows = []
    lil_matrix_data = []
    scipy.sparse.lil_matrix((len(lil_matrix_rows), num_rows), dtype=np.float32)

