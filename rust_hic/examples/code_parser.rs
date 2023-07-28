use rust_hic::{clinical_code_tree::ClinicalCodeTree, clinical_code::ClinicalCodeStore};

fn main() {
    let f = std::fs::File::open("..\\codes_editor\\icd10_example.yaml")
        .expect("Failed to open file");
    
    // Should execute without panic
    let code_tree = ClinicalCodeTree::from_reader(f);

    let mut code_store = ClinicalCodeStore::new();

    // Get the ACS STEMI codes in the groups defined by the file
    let acs_stemi_biobank_codes = code_tree
        .codes_in_group(&format!("acs_stemi_biobank"), &mut code_store)
        .expect("Should succeed, code is present");

    
}