use bimap::BiMap;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct DiagnosisCode(ClinicalCodeRef);

#[derive(Serialize, Deserialize, Debug)]
pub struct ProcedureCode(ClinicalCodeRef);

/// Stores the data for a clinical code (an ICD-10 or OPCS-4 code), which 
/// comprises the code itself, the description, and the list of groups containing
/// the code. This struct is not passed around in the program -- it is stored in
/// a ClinicalCodeStore, and references are passed around instead.
#[derive(PartialEq, Eq, Hash, Serialize, Deserialize, Debug)]
pub struct ClinicalCode {
    code: String,
    description:  String,
    groups: Vec<String>,
}

/// An opaque reference to a clinincal code, which can be used to obtain information
/// about the code from a ClinicalCodeStore. Using a type instead of a raw u64 to make
/// it clear what it is for
#[derive(Serialize, Deserialize, Debug)]
pub struct ClinicalCodeRef {
    id: u64,
}

impl ClinicalCodeRef {

    /// Create a new reference to a clinical code from an id. The purpose of these
    /// functions is to avoid letting the user modify the id after creation.
    pub fn from(id: u64) -> Self {
        Self {
            id,
        }
    }

    /// Get the raw id
    pub fn id(&self) -> u64 {
        self.id
    }
}

/// Stores the data for all the clinical codes that have been seen by the
/// program.
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
    pub fn id_from(&mut self, clinical_code: ClinicalCode) -> ClinicalCodeRef {
        match self.ids_to_codes.get_by_right(&clinical_code) {
            // Code is already there, return id
            Some(id) => ClinicalCodeRef::from(*id),
            None => {
                 // Requires that elements are never removed, which is true
                let next_id = self.ids_to_codes.len().try_into()
                    .expect("Unexpected failure to convert length of map into 64bit id");
                self.ids_to_codes.insert(next_id, clinical_code);
                ClinicalCodeRef::from(next_id)
            }
        }
    }
}