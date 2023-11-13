//! Preprocessing code for interpreting data from data sources
//!

use crate::patient::measurements::{Measurement, MeasurementValue};

/// Simple error string helper
fn field_error_string(field_name: &str, expected: &str, found: String) -> String {
    format!("Unexpected {} {} for {}", field_name, found, expected)
}

/// Read a measurement from the corresponding columns of the
/// HIC (Hospital Information Collaborative) pathology_blood
/// table.
///
///
pub fn measurement_from_pathology_blood(
    order_name: String,
    test_name: String,
    sample_collected: String,
    result_available: String,
    test_result: String,
    test_result_unit: String,
) -> Result<Measurement, String> {
    match test_name.as_ref() {
        "Platelets" => {
            if order_name != "FULL BLOOD COUNT" {
                Err(field_error_string(
                    "order_name",
                    "FULL_BLOOD_COUNT",
                    order_name,
                ))
            } else if test_result_unit != "10*9/L" {
                Err(field_error_string(
                    "test_result_unit",
                    "10*9/L",
                    test_result_unit,
                ))
            } else {
                let value = MeasurementValue::from_integer_string(test_result)?;
                let measurement_date = None;
                let measurement_available = None;
                let data_source = None;
                Ok(Measurement {
                    value,
                    measurement_date,
                    measurement_available,
                    data_source,
                })
            }

        }
        &_ => Err(format!("Unrecognised test_name {}", test_name)),
    }
}
