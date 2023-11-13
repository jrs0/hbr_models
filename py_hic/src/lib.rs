//! The main Rust-language interface layer between rust_hbr (the Rust crate)
//! and py_hic (the Python package).

use pyo3::{exceptions::PyValueError, prelude::*};
use rust_hbr::{clinical_code::ClinicalCodeStore, clinical_code_tree::ClinicalCodeTree};
use std::collections::HashMap;

/// Class for parsing diagnosis and procedure codes by searching
/// for them in a codes file. Used to check code validity and
/// also retrieve documentation for the code.
#[pyclass]
struct RustClinicalCodeParser {
    code_store: ClinicalCodeStore,
    diagnosis_code_tree: ClinicalCodeTree,
    procedure_code_tree: ClinicalCodeTree,
}

#[pymethods]
impl RustClinicalCodeParser {
    #[new]
    fn new(diagnosis_codes_file_path: &str, procedure_codes_file_path: &str) -> PyResult<Self> {
        let diagnosis_code_tree = if let Ok(f) = std::fs::File::open(diagnosis_codes_file_path) {
            ClinicalCodeTree::from_reader(f)
        } else {
            return Err(PyValueError::new_err("Failed to open diagnosis codes file"));
        };

        let procedure_code_tree = if let Ok(f) = std::fs::File::open(procedure_codes_file_path) {
            ClinicalCodeTree::from_reader(f)
        } else {
            return Err(PyValueError::new_err("Failed to open procedure codes file"));
        };

        let mut code_store = ClinicalCodeStore::new();

        Ok(Self {
            code_store,
            diagnosis_code_tree,
            procedure_code_tree,
        })
    }

    /// Find an exact match for the provided diagnosis or procedure code 
    /// and return the code name and docs as a tuple, or a python error
    /// if the code does not match anything in the code tree. Pass either
    /// "diagnosis" or "procedure" in the diagnosis_or_procedure argument
    /// to determine which tree to use. Throws a python error if you pass
    /// any other string.
    fn find_exact_diagnosis(&mut self, code: &str, diagnosis_or_procedure: &str) -> PyResult<(String, String)> {
        let code_tree = if diagnosis_or_procedure == "diagnosis" {
            &self.diagnosis_code_tree
        } else if diagnosis_or_procedure == "procedure" {
            &self.procedure_code_tree
        } else {
            return Err(PyValueError::new_err(format!(
                "Must pass one of 'diagnosis' or 'procedure', not '{diagnosis_or_procedure}'"
            )))
        };
        if let Ok(matched_code_ref) = code_tree
            .find_exact(code.to_string(), &mut self.code_store)
        {
            let matched_code = self
                .code_store
                .clinical_code_from(&matched_code_ref)
                .expect("If code was matched, expected code ref to be valid");
            Ok((
                matched_code.name().to_string(),
                matched_code.docs().to_string(),
            ))
        } else {
            Err(PyValueError::new_err(format!(
                "No match for {code} found in diagnosis tree"
            )))
        }
    }
}

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
#[pyfunction]
fn rust_get_codes_in_group(codes_file_path: &str, group: &str) -> HashMap<String, Vec<String>> {
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

    let mut code_list = HashMap::new();
    code_list.insert(format!("name"), name);
    code_list.insert(format!("docs"), docs);
    code_list
}

/// Get the code groups defined in a codes file
///
/// Returns a character vector of group names defined in
/// the codes file. This can be used as the basis for fetching
/// all the code groups using rust_get_codes_in_group.
///
#[pyfunction]
fn rust_get_groups_in_codes_file(codes_file_path: &str) -> Vec<String> {
    let f = std::fs::File::open(codes_file_path).expect("Failed to open codes file");
    let code_tree = ClinicalCodeTree::from_reader(f);
    // get the code groups and return here
    code_tree.groups().iter().cloned().collect()
}

/// A Python module implemented in Rust.
#[pymodule]
#[pyo3(name = "_lib_name")]
fn my_lib_name(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_get_codes_in_group, m)?)?;
    m.add_function(wrap_pyfunction!(rust_get_groups_in_codes_file, m)?)?;
    m.add_class::<RustClinicalCodeParser>()?;
    Ok(())
}
