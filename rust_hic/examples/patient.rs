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
    // let subject = get_utf8_column(&df, "subject").into_iter();
    // let order_name = get_utf8_column(&df, "order_name").into_iter();
    // let test_name = get_utf8_column(&df, "test_name").into_iter();
    // let sample_collected = df
    //     .column("sample_collected_date_time")
    //     .expect("Column should be present");
    // let result_available = df
    //     .column("result_available_date_time")
    //     .expect("Column should be present");
    // let result = get_utf8_column(&df, "test_result").into_iter();
    // let unit = get_utf8_column(&df, "test_result_unit").into_iter();

    // This feels like the wrong thing to
    // for  {
    //     let measurement = measurement_from_pathology_blood(
    //         order_name,
    //         test_name,
    //         format!("sample_collected[n]"),
    //         format!("result_available[n]"),
    //         result,
    //         unit,
    //     );
    // }

    let df_reduced = df
    .lazy()
        .select([
            "subject",
            "order_name",
            "test_name",
            "test_result",
            "test_result_unit",
            "sample_collected_date_time",
            "result_available_date_time",
        ])
        .collect()
        .unwrap();

    println!("{}", df_reduced);
}
