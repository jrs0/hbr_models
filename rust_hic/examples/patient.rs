//! Example showing serializing and deserializing the patient struct
//! 
use std::collections::HashMap;

use rust_hic::{make_pathology_blood, patient::Patient};

fn main() {
    // Create a new patient with some details
    let mut patient = Patient::default();
    patient.nhs_number = Some(String::from("123456789"));
    patient.age = Some(65);

    // Serialize the patient
    let serialized_patient = bson::to_bson(&patient);
    println!("{:?}", serialized_patient);

    // Make a map of patients from the patient id (trust number)
    // to a Patient struct

    //let mut patients = HashMap::new();

    // Make synthetic blood test results
    let df = make_pathology_blood("pathology_blood", 0, 100);

    // Get the columns of interest
    let subject = df.column("subject").expect("Column should be present");
    let order_name = df.column("order_name").expect("Column should be present");
    let test_name = df.column("test_name").expect("Column should be present");
    let sample_collected = df
        .column("sample_collected_date_time")
        .expect("Column should be present");
    let result_available = df
        .column("result_available_date_time")
        .expect("Column should be present");

    // Loop over the series adding values to the Patient map
    for n in 0..subject.len() {
        
    }

}
