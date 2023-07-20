use serde::{Serialize, Deserialize};
use spell::Spell;
use mongodb::bson::oid::ObjectId;

mod spell;

#[derive(Serialize, Deserialize, Debug)]
struct Patient {
    #[serde(rename = "_id", skip_serializing_if = "Option::is_none")]
    id: Option<ObjectId>,
    nhs_number: Option<String>,
    trust_number: Option<String>,
    age: Option<u32>,
    spells: Option<Vec<Spell>>,
    //mortality: Option<Mortality>,
}
