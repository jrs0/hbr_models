use extendr_api::prelude::*;
use rust_hic::{clinical_code::ClinicalCodeStore, clinical_code_tree::ClinicalCodeTree};

/// Test interface to Rust library
/// @export
#[extendr]
fn hello_world() {
    println!("Hello world!");
}

/// Get the clinical codes in a particular code group defined
/// in a codes file.
/// @export
#[extendr]
fn get_codes_in_group(codes_file_path: &str, group: &str) -> Vec<String> {
    let f = std::fs::File::open(codes_file_path).expect("Failed to open codes file");

    let code_tree = ClinicalCodeTree::from_reader(f);
    let mut code_store = ClinicalCodeStore::new();

    let clinical_code_refs = code_tree
        .codes_in_group(&String::from(group), &mut code_store)
        .expect("Should succeed, code is present");

    let code_names: Vec<_> = clinical_code_refs
        .iter()
        .map(|code_ref| {
            let clinical_code = code_store
                .clinical_code_from(code_ref)
                .expect("Clinical code should be present");
            clinical_code.name().clone()
        })
        .collect();

    code_names
}

// Macro to generate exports.
// This ensures exported functions are registered with R.
// See corresponding C code in `entrypoint.c`.
extendr_module! {
    mod rhic;
    fn hello_world;
    fn get_codes;
}
