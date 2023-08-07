use chrono::Utc;
use serde::{Deserialize, Serialize};

/// Used as a tag to indicate whether a piece of
/// information originated in primary or secondary care.
#[derive(Serialize, Deserialize, Debug)]
pub enum DataSource {
    PrimaryCare,
    SecondaryCare,
}

#[derive(Serialize, Deserialize, Debug)]
pub enum MeasurementValue {
    Integer(i64),
    Real(f64),
    String(String),
}

impl MeasurementValue {

    /// Convert a string containing an integer measurement to a 
    /// MeasurementValue. Returns error if the parse fails.
    pub fn from_integer_string(int_as_string: String) -> Result<Self, String> {
        if let Ok(value) = int_as_string.parse() {
            Ok(Self::Integer(value))
        } else {
            Err(format!(
                "Failed to convert {} to integer measurement value",
                int_as_string,
            ))
        }
    }
}

#[serde_with::serde_as]
#[derive(Serialize, Deserialize, Debug)]
pub struct Measurement {
    /// The value of the measurement at this time point
    pub value: MeasurementValue,
    /// The time the measurement was performed (or when the
    /// sample was collected from the patient -- i.e. the time
    /// that the value applied to).
    #[serde_as(as = "Option<bson::DateTime>")]
    pub measurement_date: Option<chrono::DateTime<Utc>>,
    /// When the measurement was made available, if the result
    /// required a test that takes time to perform
    #[serde_as(as = "Option<bson::DateTime>")]
    pub measurement_available: Option<chrono::DateTime<Utc>>,
    /// Whether the measurement came from a primary or secondary
    /// care data source.
    pub data_source: Option<DataSource>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct MeasurementHistory {
    /// The name of the measurement
    measurement_name: String,
    /// The unit of measurement
    measurement_unit: String,
    /// The list of measurements results with times
    timeseries: Vec<Measurement>,
}
