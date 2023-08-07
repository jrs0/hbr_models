use rust_hic::{
    clinical_code::ClinicalCodeStore,
    clinical_code_tree::ClinicalCodeTree, seeded_rng::make_rng,
    printcode
};

fn main() {
    let f =
        std::fs::File::open("..\\codes_editor\\icd10_example.yaml").expect("Failed to open file");

    // Should execute without panic
    let code_tree = ClinicalCodeTree::from_reader(f);

    let mut code_store = ClinicalCodeStore::new();

    // Get the ACS STEMI codes in the groups defined by the file
    println!("All ACS STEMI codes:");
    code_tree
        .codes_in_group(&format!("acs_stemi_schnier"), &mut code_store)
        .expect("Should succeed, code is present")
        .iter()
        .for_each(|code_ref| printcode!(code_ref, code_store));

    // Get a few random clinical codes from the code tree
    let mut rng = make_rng(321, "code_gen_id");
    let code1 = code_tree.random_clinical_code(&mut rng, &mut code_store);
    println!("An arbitrary random code:");
    printcode!(code1, code_store);

    // Pick 5 codes at random from the atrial_fib group
    println!("Random atrial fib codes:");
    for _ in 0..5 {
        let random_code = code_tree
            .random_clinical_code_from_group(&mut rng, &mut code_store, &format!("atrial_fib"))
            .expect("Should be able to pick a valid code");
        printcode!(random_code, code_store);
    }
}
