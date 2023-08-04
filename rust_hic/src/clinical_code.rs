//! Clinical codes (ICD-10 and OPCS-4) and clinical code store
//! 
//! The main struct is ClinicalCode, which contains the string name and description
//! of a code. However, in the main program, ClinicalCodeRef should be used, which 
//! refers to a ClinicalCode stored in the ClinicalCodeStore. This makes it much easier
//! to perform operations on the codes without expensive string operations.
//! 
//! Two type wrappers DiagnosisCode and ProcedureCode are provided to allow programs
//! to distinguish ICD-10 and OPCS-4 codes.

use bimap::BiMap;
use serde::{Deserialize, Serialize};

use crate::clinical_code_tree::Categories;

#[derive(Serialize, Deserialize, Debug)]
pub struct DiagnosisCode(ClinicalCodeRef);

#[derive(Serialize, Deserialize, Debug)]
pub struct ProcedureCode(ClinicalCodeRef);

/// Stores the data for a clinical code (an ICD-10 or OPCS-4 code), which
/// comprises the code itself, the description, and the list of groups containing
/// the code. This struct is not passed around in the program -- it is stored in
/// a ClinicalCodeStore, and references are passed around instead.
#[derive(Clone, PartialEq, Eq, Hash, Serialize, Deserialize, Debug)]
pub struct ClinicalCode {
    /// The name of the code, e.g. I22.1
    name: String,
    /// The descriptions of the code
    docs: String,
}

impl ClinicalCode {
    /// Create a new clinical code that has a name and a description.
    /// The code is not added to any groups to start with
    pub fn new(name: String, docs: String) -> Self {
        Self {
            name,
            docs,
            //groups: Vec::new(),
        }
    }

    /// Make a clinical code from a category/code node in a clinical code tree
    pub fn from(category: &Categories) -> Self {
        let clinical_code = Self::new(category.name().clone(), category.docs().clone());
        //clinical_code.groups = category.groups.clone();
        clinical_code
    }

    pub fn name(&self) -> &String {
        &self.name
    }

    pub fn docs(&self) -> &String {
        &self.docs
    }

}

/// An opaque reference to a clinincal code, which can be used to obtain information
/// about the code from a ClinicalCodeStore. Using a type instead of a raw u64 to make
/// it clear what it is for
#[derive(PartialEq, Eq, Serialize, Deserialize, Debug)]
pub struct ClinicalCodeRef {
    id: u64,
}

impl ClinicalCodeRef {
    /// Create a new reference to a clinical code from an id. The purpose of these
    /// functions is to avoid letting the user modify the id after creation.
    pub fn from(id: u64) -> Self {
        Self { id }
    }

    /// Get the raw id
    pub fn id(&self) -> u64 {
        self.id
    }
}

/// Simple wrapper to convert a code reference to a clinical code
/// and print it.
#[macro_export]
macro_rules! printcode {
    ($code_ref:expr, $code_store:expr) => {
        if let Some(clinical_code) = $code_store.clinical_code_from(&$code_ref) {
            println!("{:?}", clinical_code);
        } else {
            println!("No clinical code corresponding to reference");
        }
        
    }
}

/// Simple wrapper to convert a code reference to a clinical code
/// and get its name
#[macro_export]
macro_rules! name {
    ($code_ref:expr, $code_store:expr) => {
        if let Some(clinical_code) = $code_store.clinical_code_from(&$code_ref) {
            clinical_code.name()
        } else {
            panic!("No clinical code corresponding to reference");
        }
        
    }
}

/// Stores the data for all the clinical codes that have been seen by the
/// program.
#[derive(Debug)]
pub struct ClinicalCodeStore {
    /// The purpose of the bidirectional map is to try to make both inserting
    /// codes and retrieving code data fast. Code insertion is the bottleneck
    /// when codes are being parsed (although a cache layer mapping unparsed codes
    /// to ids in this store can help), and then code retrieval is the bottleneck
    /// when data is being obtained from the patient struct for the purpose of
    /// creating a dataframe for R or Python.
    ids_to_codes: BiMap<u64, ClinicalCode>,
}

impl ClinicalCodeStore {
    /// Create an empty ClinicalCodeStore
    pub fn new() -> Self {
        Self {
            ids_to_codes: BiMap::new(),
        }
    }

    /// Insert a new clinical code into the store,
    /// and obtain as a result an id that can be used to
    /// refer to it. If the clinical code is already in the
    /// store, return its id without re-inserting.
    pub fn clinical_code_ref_from(&mut self, clinical_code: ClinicalCode) -> ClinicalCodeRef {
        match self.ids_to_codes.get_by_right(&clinical_code) {
            // Code is already there, return id
            Some(id) => ClinicalCodeRef::from(*id),
            None => {
                // Requires that elements are never removed, which is true
                let next_id = self
                    .num_stored_codes()
                    .try_into()
                    .expect("Unexpected failure to convert length of map into 64bit id");
                self.ids_to_codes.insert(next_id, clinical_code);
                ClinicalCodeRef::from(next_id)
            }
        }
    }

    /// Get the clinincal code corresponding to a code
    /// reference. Returns None if the reference does not correspond
    /// to any clinical code. The result is a reference, so it is
    /// up to you to clone it if you want to modify it.
    pub fn clinical_code_from(&self, clinical_code_ref: &ClinicalCodeRef) -> Option<&ClinicalCode> {
        self.ids_to_codes.get_by_left(&clinical_code_ref.id())
    }

    /// Get the total number of codes stored in the map. This is also the
    /// value of the next id, because codes are not removed once they have
    /// been added.
    pub fn num_stored_codes(&self) -> usize {
        self.ids_to_codes.len()
    }
}

/// Tests for the clinical code data structure and the code store
///
/// The ClinicalCode structure is quite simple, and just stores the name, description
/// and groups inside the code. The most non-trivial function is checking whether
/// a code is in a group. The information stored in the code cannot be checked for
/// correctness here.
///
/// The code store must be checked to ensure that the id that is returned for a given
/// code does actually refer to the right code. Edge cases include:
/// * Inserting the same code twice; expect the same code
/// * Requesting an id that is not in the store; should return None
///
///
#[cfg(test)]
mod tests {

    use super::*;

    #[test]
    fn test_clinical_code_matches_input() {
        let name = String::from("I21.0");
        let docs = String::from("What the code means...");
        let code = ClinicalCode::new(name, docs);

        assert_eq!(code.name(), "I21.0");
        assert_eq!(code.docs(), "What the code means...");
    }

    #[test]
    fn test_code_store_initially_empty() {
        let clinical_code_store = ClinicalCodeStore::new();
        assert_eq!(clinical_code_store.num_stored_codes(), 0);
    }

    #[test]
    fn test_insertion_and_read_of_one_code_into_store() {
        let mut clinical_code_store = ClinicalCodeStore::new();
        let name = String::from("I21.0");
        let docs = String::from("What the code means...");
        let code = ClinicalCode::new(name, docs);

        let code_ref = clinical_code_store.clinical_code_ref_from(code);
        assert_eq!(clinical_code_store.num_stored_codes(), 1);

        let code_read = clinical_code_store.clinical_code_from(&code_ref);
        assert_ne!(code_read, None);
        let code_read = code_read.unwrap();
        assert_eq!(code_read.name(), "I21.0");
        assert_eq!(code_read.docs(), "What the code means...");
        //assert_eq!(code_read.groups().len(), 0);
    }

    #[test]
    fn test_insertion_and_read_of_multiple_codes_into_store() {

        // Insertions

        let mut clinical_code_store = ClinicalCodeStore::new();
        let name = String::from("I21.0");
        let docs = String::from("What the code means...");
        let code = ClinicalCode::new(name, docs);
        let code_ref_1 = clinical_code_store.clinical_code_ref_from(code);
        assert_eq!(clinical_code_store.num_stored_codes(), 1);

        let name = String::from("A00.1");
        let docs = String::from("Another description");
        let code = ClinicalCode::new(name, docs);
        let code_ref_2 = clinical_code_store.clinical_code_ref_from(code);

        assert_eq!(clinical_code_store.num_stored_codes(), 2);

        let name = String::from("K34.3");
        let docs = String::from("Yet another description");
        let code = ClinicalCode::new(name, docs);
        let code_ref_3 = clinical_code_store.clinical_code_ref_from(code);
        assert_eq!(clinical_code_store.num_stored_codes(), 3);

        // Reads

        let code_read = clinical_code_store.clinical_code_from(&code_ref_1);
        assert_ne!(code_read, None);
        let code_read = code_read.unwrap();
        assert_eq!(code_read.name(), "I21.0");
        assert_eq!(code_read.docs(), "What the code means...");

        let code_read = clinical_code_store.clinical_code_from(&code_ref_2);
        assert_ne!(code_read, None);
        let code_read = code_read.unwrap();
        assert_eq!(code_read.name(), "A00.1");
        assert_eq!(code_read.docs(), "Another description");      

        let code_read = clinical_code_store.clinical_code_from(&code_ref_3);
        assert_ne!(code_read, None);
        let code_read = code_read.unwrap();
        assert_eq!(code_read.name(), "K34.3");
        assert_eq!(code_read.docs(), "Yet another description");
    }


    // Edges cases below this point

    #[test]
    fn test_repeat_insertion_of_same_code_into_store() {
        let mut clinical_code_store = ClinicalCodeStore::new();
        let name = String::from("I21.0");
        let docs = String::from("What the code means...");
        let code = ClinicalCode::new(name, docs);
        let code_copy = code.clone();

        // First insert
        let code_ref_1 = clinical_code_store.clinical_code_ref_from(code);
        assert_eq!(clinical_code_store.num_stored_codes(), 1);

        // Second insert
        let code_ref_2 = clinical_code_store.clinical_code_ref_from(code_copy);
        assert_eq!(clinical_code_store.num_stored_codes(), 1);

        // Check that the references are the same
        assert_eq!(code_ref_1, code_ref_2);

        let code_read = clinical_code_store.clinical_code_from(&code_ref_1);
        assert_ne!(code_read, None);
        let code_read = code_read.unwrap();
        assert_eq!(code_read.name(), "I21.0");
        assert_eq!(code_read.docs(), "What the code means...");
    }

    #[test]
    fn test_request_for_nonexistent_code_is_none() {
        let mut clinical_code_store = ClinicalCodeStore::new();
        
        // Id does not exist
        let code_ref = ClinicalCodeRef::from(32);

        let code_read = clinical_code_store.clinical_code_from(&code_ref);
        assert_eq!(code_read, None);
    }

}
