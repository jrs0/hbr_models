//! The main Rust-language interface layer between rust_hbr (the Rust crate)
//! and rhic (the R package).
//! 
//! Data is typically returned to R in a base-R format like a raw list or
//! vector. You don't want to call the functions here (anything starting with
//! "rust_")  directly. Instead, use the functions in the R/ folder which return
//! the same information in a more R-friendly format (such as tibble, or after
//! any extra conversion to more usable types has been performed).
//! 

use extendr_api::prelude::*;
use rust_hbr::{clinical_code::ClinicalCodeStore, clinical_code_tree::ClinicalCodeTree};

/// Get the clinical codes in a particular code group defined
/// in a codes file.
///
/// The result is a named list (intended as a dataframe) with the
/// columns:
/// * name: the name of the code in the group (e.g. A01.0)
/// * docs: the description of the code 
/// 
/// TODO: figure out a good way to handle errors.
/// 
/// @export
#[extendr]
fn rust_get_codes_in_group(codes_file_path: &str, group: &str) -> List {
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

/// Get the code groups defined in a codes file
/// 
/// Returns a character vector of group names defined in
/// the codes file. This can be used as the basis for fetching
/// all the code groups using rust_get_codes_in_group.
/// 
#[extendr]
fn rust_get_groups_in_codes_file(codes_file_path: &str) -> Vec<String> {
    let f = std::fs::File::open(codes_file_path).expect("Failed to open codes file");
    let code_tree = ClinicalCodeTree::from_reader(f);
    // get the code groups and return here
    code_tree.groups().iter().cloned().collect()
}

// Macro to generate exports.
// This ensures exported functions are registered with R.
// See corresponding C code in `entrypoint.c`.
extendr_module! {
    mod rhic;
    fn rust_get_codes_in_group;
    fn rust_get_groups_in_codes_file;
}
