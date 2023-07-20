use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct ClinicalCode {
    /// A reference to the code data
    clinical_code: u64, 
}

// Strong type aliases for diagnoses and procedures
#[derive(Serialize, Deserialize, Debug)]
pub struct DiagnosisCode(ClinicalCode);

#[derive(Serialize, Deserialize, Debug)]
pub struct ProcedureCode(ClinicalCode);