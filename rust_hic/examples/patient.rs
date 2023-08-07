//! Example showing serializing and deserializing the patient struct
//!
use std::collections::HashMap;

use polars::prelude::*;
use rust_hic::{
    make_pathology_blood, patient::Patient, preprocess::measurement_from_pathology_blood,
};

/// Get a string column from a polars dataframe. Panics if
/// the column is not present or the type is not String
/// (or cannot be converted to utf8)
fn get_utf8_column<'a>(df: &'a DataFrame, column_name: &str) -> &'a ChunkedArray<Utf8Type> {
    df.column(column_name)
        .expect("Column should be present")
        .utf8()
        .expect("Should be an String column")
}

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
    let subject = get_utf8_column(&df, "subject");
    let order_name = get_utf8_column(&df, "order_name");
    let test_name = get_utf8_column(&df, "test_name");
    let sample_collected = df
        .column("sample_collected_date_time")
        .expect("Column should be present");
    let result_available = df
        .column("result_available_date_time")
        .expect("Column should be present");
    let result = get_utf8_column(&df, "test_result");
    let unit = get_utf8_column(&df, "test_result_unit");

    // Loop over the series adding values to the Patient map
    // for n in 0..subject.len() {
    //     let measurement = measurement_from_pathology_blood(
    //         order_name[n],
    //         test_name[n],
    //         sample_collected[n],
    //         result_available[n],
    //         result[n],
    //         unit[n],
    //     );
    // }
}
