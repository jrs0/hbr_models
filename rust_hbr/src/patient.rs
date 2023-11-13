use serde::{Serialize, Deserialize};
use spell::Spell;
use mongodb::bson::oid::ObjectId;

use self::measurements::MeasurementHistory;

mod spell;
//mod mortality;
pub mod measurements;
//mod prescriptions;

#[derive(Serialize, Deserialize, Debug, Default)]
pub struct Patient {
    #[serde(rename = "_id", skip_serializing_if = "Option::is_none")]
    pub id: Option<ObjectId>,
    pub nhs_number: Option<String>,
    pub trust_number: Option<String>,
    pub age: Option<u32>,
    pub spells: Option<Vec<Spell>>,
    //pub mortality: Option<Mortality>,
    pub measurements: Option<MeasurementHistory>,
    //pub prescriptions: Option<PrescriptionsHistory>,
}

impl Patient {

}