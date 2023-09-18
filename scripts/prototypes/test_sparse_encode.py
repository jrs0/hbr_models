import sparse_encode as spe

def test_get_column_index():
    '''
    Check that the function can handle
    insertions of new codes and getting column
    index of previously inserted codes.
    '''
    
    # Blank code-to-index map
    code_to_index = {}

    # Test inserting a code
    index = spe.get_column_index(code_to_index, "abc")
    assert index == 0
    assert code_to_index["abc"] == 0

    # Test inserting a second code
    index = spe.get_column_index(code_to_index, "cde")
    assert index == 1
    assert code_to_index["cde"] == 1

    # Test getting index of abc again
    index = spe.get_column_index(code_to_index, "abc")
    assert index == 0
    assert code_to_index["abc"] == 0  

