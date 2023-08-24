import scipy.sparse
import numpy as np

def get_column_index(code_to_column, code):
    '''
    Convert a code to its corresponding index in
    the dictionary code_to_column. If the code has
    been seen before, return its index. If it has
    not been seen before, add the code and return 
    its index. The code_to_column dictionary is
    updated in place.
    '''
    # Add the index of the current code to the index
    # list
    if code in code_to_column:
        # Append the column index
        column_index = code_to_column[code]
    else:
        # Add the code as a new column index 
        column_index = len(code_to_column)
        code_to_column[code] = column_index

    return column_index

def encode_sparse(long_codes):
    '''
    The input is a table of codes (full_code
    column) in long format, by the spell_id,
    and containing the clinical code position
    in the position column. The output is a
    sparse matrix.
    '''
    sorted_by_spell = long_codes.sort_values("spell_id")

    lil_matrix_rows = []
    lil_matrix_data = []

    # A map from a code in the full_code column to
    # a column index. This grows as more codes are
    # encountered while traversing the table
    code_to_column = {}

    # This variable tracks the current spell_id and
    # indicates when a particular row is finished. Note
    # min is still required as index has not changed by
    # sort
    current_spell_id = sorted_by_spell.spell_id.min()
    current_lil_matrix_row = []
    current_lil_matrix_data = []

    for _, row in sorted_by_spell.head(20).iterrows():
        
        spell_id = row["spell_id"]

        print(current_spell_id, spell_id)
        if current_spell_id != spell_id:
            print("Next spell")
            # Append the row for this spell (constructed
            # in previous iterations of the for loop) to
            # the main list of lists
            lil_matrix_rows.append(current_lil_matrix_row)
            lil_matrix_data.append(current_lil_matrix_data)

            # Reset the rows
            current_lil_matrix_row = []
            current_lil_matrix_data = []

            # Update the current spell
            current_spell_id = spell_id

        print("Normal")
        # Get the code and position data
        full_code = row["full_code"]
        position = row["position"]
        print(f"{full_code}, {position}")
        
        column_index = get_column_index(code_to_column, full_code)

        # Append the column index and data to the current
        # list
        current_lil_matrix_row.append(column_index)
        # Append the column data. This is either the
        # linear code position, or just a TRUE/FALSE
        # marker if dummy encoding. (TODO)
        current_lil_matrix_data.append(position)

    # Find matrix dimensions
    num_rows = len(lil_matrix_rows)
    num_cols = len(code_to_column)

    print(f"Rows: {lil_matrix_rows}")
    print(f"nzv: {lil_matrix_data}")

    # Create the sparse matrix
    #num_non_zeros = long_codes.spell_id.nunique()
    mat = scipy.sparse.lil_matrix((num_rows, num_cols), dtype=np.float32)
    mat.rows = lil_matrix_rows
    mat.data = lil_matrix_data

    return mat
    


