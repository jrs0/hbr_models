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

    lil_matrix_rows = []
    lil_matrix_data = []

    # A map from a code in the full_code column to
    # a column index. This grows as more codes are
    # encountered while traversing the table
    code_to_column = {}

    # This variable tracks the current spell_id and
    # indicates when a particular row is finished
    current_spell_id = sorted_by_spell.spell_id[0] 
    current_lil_matrix_row = []
    current_lil_matrix_data = []

    for spell_id, row in sorted_by_spell.head(50).iterrows():
        
        if current_spell_id != spell_id:
            # Append the row for this spell to the 
            # sparse data
            lil_matrix_rows.append(current_lil_matrix_row)
            lil_matrix_data.append(current_lil_matrix_data)

            # Reset the rows
            current_lil_matrix_row = []
            current_lil_matrix_data = []

            # Update the current spell
            current_spell_id = spell_id
        
        # Get the code and position data
        full_code = row["full_code"]
        position = row["position"]
        
        # Add the index of the current code to the index
        # list
        if full_code in code_to_column:
            # Append the column index
            column_index = code_to_column[full_code]
            current_lil_matrix_row.append(column_index)

            # Append the column data. This is either the
            # linear code position, or just a TRUE/FALSE
            # marker if dummy encoding. (TODO)
            current_lil_matrix_data.append(position)
        else:
            # Add the code as a new column index 
            code_to_column[full_code] = len(code_to_column)

    # Create the sparse matrix
    num_non_zeros = long_codes.spell_id.nunique()
    mat = scipy.sparse.lil_matrix((len(lil_matrix_rows), num_non_zeros), dtype=np.float32)
    mat.rows = lil_matrix_rows
    mat.data = lil_matrix_data

    return mat