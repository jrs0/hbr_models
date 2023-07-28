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
///
/// The result is 
/// 
/// TODO: figure out a good way to hand errors.
/// 
/// @export
#[extendr]
fn get_codes_in_group(codes_file_path: &str, group: &str) -> List {
    let f = std::fs::File::open(codes_file_path).expect("Failed to open codes file");

    let code_tree = ClinicalCodeTree::from_reader(f);
    let mut code_store = ClinicalCodeStore::new();

    let clinical_code_refs = code_tree
        .codes_in_group(&String::from(group), &mut code_store)
        .expect("Should succeed, code is present");

    let mut name = Vec::new();
    let mut docs = Vec::new();
    for code_ref in clinical_code_refs {
        let clinical_code = code_store
            .clinical_code_from(&code_ref)
            .expect("Clinical code should be present");
        name.push(clinical_code.name().clone());
        docs.push(clinical_code.docs().clone());
    }

    // Don't be fooled here -- interpret this as
    // a dictionary or map defined like
    // {"name": name, "docs": docs}; in R, the
    // lvalues are strings, but they are "unquoted"
    // (they are not variables).
    list!(name = name, docs = docs)
}

// Macro to generate exports.
// This ensures exported functions are registered with R.
// See corresponding C code in `entrypoint.c`.
extendr_module! {
    mod rhic;
    fn hello_world;
    fn get_codes_in_group;
}
