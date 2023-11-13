use serde::{Serialize, Deserialize};
use crate::clinical_code::{DiagnosisCode, ProcedureCode};
use chrono::Utc;


#[derive(Serialize, Deserialize, Debug)]
pub struct Episode {
    #[serde(with = "bson::serde_helpers::chrono_datetime_as_bson_datetime")]
    start: chrono::DateTime<Utc>,
    #[serde(with = "bson::serde_helpers::chrono_datetime_as_bson_datetime")]
    end: chrono::DateTime<Utc>,
    primary_diagnosis: Option<DiagnosisCode>,
    secondary_diagnoses: Option<Vec<DiagnosisCode>>,
    primary_procedure: Option<ProcedureCode>,
    secondary_procedures: Option<Vec<ProcedureCode>>,    
}

