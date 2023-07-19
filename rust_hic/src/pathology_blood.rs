//! The pathology blood table contains blood test result including haemoglobin,
//! platelet count, etc. The columns include the test name and category, the
//! result and unit, and sample collection date and processing times.

use datafusion::arrow::record_batch::RecordBatch;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use std::sync::Arc;

use datafusion::arrow::array::{StringArray, TimestampSecondArray};

use crate::seeded_column_block::{SeededColumnBlock, make_rng, make_string_column, into_record_batch};
use crate::synth_data::{Gender, make_gender, make_subject};

fn make_result_flag(rng: &mut ChaCha8Rng) -> Option<String> {
    if rng.gen() {
        Some(String::from("<"))
    } else {
        None
    }
}

/// Lab test data in the format required for the pathology_blood table.
/// String data type is used to match type in synthetic data table.
///
#[derive(Debug)]
struct BloodTest {
    /// Top-level category name (e.g. FULL BLOOD COUNT)
    pub order_name: String,
    /// Test name within order_name (e.g. haemoglobin)
    pub test_name: String,
    /// Test result, a string-encoded floating-point number of integer
    pub test_result: String,
    /// Physical unit (or None for a quantity with no unit)
    pub test_result_unit: Option<String>,
    /// Normal lower limit (None means not present or does not make sense)
    pub result_lower_range: Option<String>,
    /// Normal upper limit
    pub result_upper_range: Option<String>,
}

impl BloodTest {
    /// Regular full-blood-count haemoglobin (not electrophoresis)
    ///
    /// The gender is required to determine the normal test result range.
    /// The test result is an integer, in units g/L, with values like 145
    /// (note: often Hb is expressed in g/dL, which makes values like 14.5).
    /// In the pathology_blood table, results are integers in g/L.
    fn new_haemoglobin(test_result: u32, gender: Gender) -> Self {
        let (result_lower_range, result_upper_range) = match gender {
            Gender::Female => (Some(String::from("120")), Some(String::from("150"))),
            Gender::Male => (Some(String::from("130")), Some(String::from("170"))),
        };
        let test_result_unit = Some(String::from("g/L"));
        let test_result = test_result.to_string();
        Self {
            order_name: String::from("FULL BLOOD COUNT"),
            test_name: String::from("Haemoglobin"),
            test_result,
            test_result_unit,
            result_lower_range,
            result_upper_range,
        }
    }

    /// Platelet count
    ///
    /// The platelet count is a postive integer, which a normal range
    /// 150 - 400. Reduced platelet count is called thrombocytopenia.
    ///  
    fn new_platelets(test_result: u32) -> Self {
        let result_lower_range = Some(String::from("150"));
        let result_upper_range = Some(String::from("400"));
        let test_result_unit = Some(String::from("10*9/L"));
        let test_result = test_result.to_string();
        Self {
            order_name: String::from("FULL BLOOD COUNT"),
            test_name: String::from("Platelets"),
            test_result,
            test_result_unit,
            result_lower_range,
            result_upper_range,
        }
    }

}

/// Make a uniform random haemoglobin measurement in the range
/// 0 - 19g/dL
fn make_random_haemoglobin(rng: &mut ChaCha8Rng) -> BloodTest {
    let gender = make_gender(rng);
    let test_result = rng.gen_range(0..190);
    BloodTest::new_haemoglobin(test_result, gender)
}

/// Make a uniform random platelet count measurement in the range
/// 0 - 500e9/L
fn make_random_platelets(rng: &mut ChaCha8Rng) -> BloodTest {
    let test_result = rng.gen_range(0..500);
    BloodTest::new_platelets(test_result)
}

/// This is an example function that makes the subject column from
/// an id and a seed. The id should always stay the same (otherwise
/// the data will change). The colunn name is allowed to change (this
/// covers the case where you want to change the column name but not
/// change the data.)
fn make_subject_columns(
    block_id: &str,
    global_seed: u64,
    column_name: String,
    num_rows: usize,
) -> SeededColumnBlock {
    // Augment the id with the seed and hash to get the
    // seed to be used.
    let mut rng = make_rng(block_id, global_seed);

    let mut subject = Vec::new();
    for _ in 0..num_rows {
        subject.push(make_subject(&mut rng));
    }

    make_string_column(column_name, subject)
}

/// Creates a block of columns that includes the blood test name
/// and family, the test result, test unit, and upper and lower
/// ranges
fn make_blood_test_columns(block_id: &str, global_seed: u64, num_rows: usize) -> SeededColumnBlock {
    // Augment the id with the seed and hash to get the
    // seed to be used.
    let mut rng = make_rng(block_id, global_seed);

    let mut order_name = Vec::new();
    let mut test_name = Vec::new();
    let mut test_result = Vec::new();
    let mut test_result_unit = Vec::new();
    let mut result_lower_range = Vec::new();
    let mut result_upper_range = Vec::new();

    for _ in 0..num_rows {
        // Make a random blood test
        let blood_test = match rng.gen_range(0..2) {
            0 => make_random_haemoglobin(&mut rng),
            1 => make_random_platelets(&mut rng),
            _ => panic!("Blood test index out of range"),
        };

        // Make the test type and results
        order_name.push(blood_test.order_name);
        test_name.push(blood_test.test_name);
        test_result.push(blood_test.test_result);
        test_result_unit.push(blood_test.test_result_unit);
        result_lower_range.push(blood_test.result_lower_range);
        result_upper_range.push(blood_test.result_upper_range);
    }

    SeededColumnBlock {
        columns: vec![
            (
                String::from("order_name"),
                Arc::new(StringArray::from(order_name)) as _,
            ),
            (
                String::from("test_name"),
                Arc::new(StringArray::from(test_name)) as _,
            ),
            (
                String::from("test_result"),
                Arc::new(StringArray::from(test_result)) as _,
            ),
            (
                String::from("test_result_unit"),
                Arc::new(StringArray::from(test_result_unit)) as _,
            ),
            (
                String::from("result_lower_range"),
                Arc::new(StringArray::from(result_lower_range)) as _,
            ),
            (
                String::from("test_upper_range"),
                Arc::new(StringArray::from(result_upper_range)) as _,
            ),
        ],
    }
}

fn make_sample_time_columns(
    block_id: &str,
    global_seed: u64,
    num_rows: usize,
) -> SeededColumnBlock {
    let mut rng = make_rng(block_id, global_seed);

    let mut sample_collected_date_time = Vec::new();
    let mut result_available_date_time = Vec::new();

    for _ in 0..num_rows {
        // Sample collected at any date from 1970 to roughly now, and
        // up to 1 week processing time
        let sample_collected_timestamp = 60 * rng.gen_range(0..28150015);
        let processing_time = 60 * rng.gen_range(0..10080);
        sample_collected_date_time.push(sample_collected_timestamp);
        result_available_date_time.push(sample_collected_timestamp + processing_time);
    }

    SeededColumnBlock {
        columns: vec![
            (
                String::from("sample_collected_date_time"),
                Arc::new(TimestampSecondArray::from(sample_collected_date_time)) as _,
            ),
            (
                String::from("result_available_date_time"),
                Arc::new(TimestampSecondArray::from(result_available_date_time)) as _,
            ),
        ],
    }
}

/// This column is either < or Null. Unknown interpretation.
fn make_result_flag_column(block_id: &str, global_seed: u64, column_name: String, num_rows: usize) -> SeededColumnBlock {
    let mut rng = make_rng(block_id, global_seed);

    let mut result_flag = Vec::new();

    for _ in 0..num_rows {
        result_flag.push(make_result_flag(&mut rng));
    }

    make_string_column(column_name, result_flag)
}

/// Create the blood results table. Generated data is randomly generated based on
/// the global seed with no particular statistical characteristics (the purpose is the
/// format of the data). Currently includes the following blood tests:
/// 
/// * haemoglobin
/// * 
pub fn make_pathology_blood(block_id: &str, global_seed: u64, num_rows: usize) -> RecordBatch {
    let mut seeded_column_blocks = Vec::new();

    // Make patient id column
    let subject_block_id = format!("{block_id}subject");
    let subjects = make_subject_columns(
        subject_block_id.as_ref(),
        global_seed,
        String::from("subject"),
        num_rows,
    );
    seeded_column_blocks.push(subjects);

    // Lab department is always None
    let column = vec![None as Option<String>; num_rows];
    let column_name = String::from("laboratory_department");
    seeded_column_blocks.push(make_string_column(column_name, column));

    // Make the blood test columns (a block of columns including test name, result, units,
    // and ranges)
    let blood_test_block_id = format!("{block_id}blood_test");
    let blood_test_columns =
        make_blood_test_columns(blood_test_block_id.as_ref(), global_seed, num_rows);
    seeded_column_blocks.push(blood_test_columns);

    // Make columns for sample collected time and processing times
    let sample_time_block_id = format!("{block_id}sample_time");
    let sample_time_columns =
        make_sample_time_columns(sample_time_block_id.as_ref(), global_seed, num_rows);
    seeded_column_blocks.push(sample_time_columns);

    // Make the result flag columns
    let result_flag_block_id = format!("{block_id}result_flag");
    let column_name = String::from("result_flag");
    let result_flag_column =
        make_result_flag_column(result_flag_block_id.as_ref(), global_seed, column_name, num_rows);
    seeded_column_blocks.push(result_flag_column);

    // brc name is alwasy Bristol
    let column = vec![String::from("bristol"); num_rows];
    let column_name = String::from("brc_name");
    seeded_column_blocks.push(make_string_column(column_name, column));

    into_record_batch(seeded_column_blocks).unwrap()
}
