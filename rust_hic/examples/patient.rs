//! Example showing serializing and deserializing the patient struct

use rust_hic::patient::Patient;

fn main() {
    let mut patient = Patient::default();
    patient.nhs_number = Some(String::from("123456789"));
    patient.age = Some(65);

    let serialized_patient = bson::to_bson(&patient);
    println!("{:?}", serialized_patient);
}