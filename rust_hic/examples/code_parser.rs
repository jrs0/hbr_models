use rust_hic::{clinical_code_tree::ClinicalCodeTree, clinical_code::ClinicalCodeStore, seeded_rng::make_rng};

fn main() {
    let f = std::fs::File::open("..\\codes_editor\\icd10_example.yaml")
        .expect("Failed to open file");
    
    // Should execute without panic
    let code_tree = ClinicalCodeTree::from_reader(f);

    let mut code_store = ClinicalCodeStore::new();

    // Get the ACS STEMI codes in the groups defined by the file
    let acs_stemi_schnier_codes = code_tree
        .codes_in_group(&format!("acs_stemi_schnier"), &mut code_store)
        .expect("Should succeed, code is present");

    // Get a few random clinical codes from the code tree
    let mut rng = make_rng(123, "code_gen_id");
    let code1 = code_tree.random_clinical_code(&mut rng, &mut code_store);
    println!("{:?}", code_store.clinical_code_from(&code1));
}