use std::sync::Arc;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use datafusion::arrow::{record_batch::RecordBatch, error::ArrowError};

use datafusion::arrow::array::{Array, StringArray, TimestampSecondArray};

use blake2::{Blake2b512, Digest};

enum Gender {
    Female,
    Male,
}

/// Generate a patient id for the pathology_blood table (format "bristol_nnnn")
fn make_subject(rng: &mut ChaCha8Rng) -> String {
    let patient_id = rng.gen_range(1..=50000);
    format! {"bristol_{patient_id}"}
}

/// Pick gender randomly (only male or female)
fn make_gender(rng: &mut ChaCha8Rng) -> Gender {
    if rng.gen() {
        Gender::Female
    } else {
        Gender::Male
    }
}

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
            test_name: String::from("haemoglobin"),
            test_result,
            test_result_unit,
            result_lower_range,
            result_upper_range,
        }
    }
}

/// A set of synthetic data columns which are randomly
/// generated from one seeded and which are considered
/// as one logical unit.
/// 
/// The purpose of the block is to be the smallest unit
/// of reproducible synthetic data. SeededColumns can 
/// be combined together into a RecordBatch.
/// 
/// The data is stored in a format that can be passed
/// easily to the RecordBatch::try_from_iter method 
/// (i.e. as tuples of column name and column data).
struct SeededColumnBlock {
    columns: Vec<(String, Arc<dyn Array>)>,
}

impl SeededColumnBlock {
    fn columns(self) -> Vec<(String, Arc<dyn Array>)> {
        self.columns
    }
}

/// Convert a list of SeededColumnBlocks (which are themselves 
/// groups of columns) into a RecordBatch (a table). This
/// function is used to combine the minimal reproducible and
/// seedable units into a single synthetic table.
fn into_record_batch(seeded_column_blocks: Vec<SeededColumnBlock>) -> Result<RecordBatch, ArrowError> {
    let columns = seeded_column_blocks
        .into_iter()
        .map(|x| x.columns())
        .flatten();
    RecordBatch::try_from_iter(columns)
}

/// Make a random number generator from a global seed
/// and a string id (used to give each independent block
/// of synthetic data a different seed). The block_id is
/// concatenated with the global seed and the result is
/// hashed. The resulting hash seeds the random number
/// generator.
fn make_rng(block_id: &str, global_seed: u64) -> ChaCha8Rng {
    let message = format!("{block_id}{global_seed}");
    let mut hasher = Blake2b512::new();
    hasher.update(message);
    let seed = hasher.finalize()[0..32].try_into()
        .expect("Unexpectedly failed to obtain correct-length slice");
    ChaCha8Rng::from_seed(seed)
}

/// This is an example function that makes the subject column from
/// an id and a seed. The id should always stay the same (otherwise
/// the data will change). The colunn name is allowed to change (this
/// covers the case where you want to change the column name but not
/// change the data.)
fn make_subject_columns(block_id: &str, global_seed: u64, column_name: String, num_rows: usize) -> SeededColumnBlock {
    
    // Augment the id with the seed and hash to get the
    // seed to be used.
    let mut rng = make_rng(block_id, global_seed);

    let mut subject = Vec::new();
    for _ in 0..num_rows {
        subject.push(make_subject(&mut rng));
    }

    SeededColumnBlock {
        columns: vec![(column_name, Arc::new(StringArray::from(subject)) as _)]
    }
}

/// Example function which creates a synthetic data table out of
/// one or more seeded blocks (just one currently). The table itself
/// also gets a block_id.
fn make_pathology_blood_2(block_id: &str, global_seed: u64) -> RecordBatch {

    let mut seeded_column_blocks = Vec::new();

    let subject_block_id = format!("{block_id}subject");
    let subjects = make_subject_columns(subject_block_id.as_ref(), global_seed,
                            String::from("subject"), 100);

    into_record_batch(seeded_column_blocks).unwrap()
}   

pub fn make_pathology_blood(rng: &mut ChaCha8Rng, num_rows: usize) -> RecordBatch {
    let mut subject = Vec::new();
    let mut laboratory_department = Vec::new();
    let mut order_name = Vec::new();
    let mut test_name = Vec::new();
    let mut test_result = Vec::new();
    let mut test_result_unit = Vec::new();
    let mut sample_collected_date_time = Vec::new();
    let mut result_available_date_time = Vec::new();
    let mut result_flag = Vec::new();
    let mut result_lower_range = Vec::new();
    let mut result_upper_range = Vec::new();
    let mut brc_name = Vec::new();

    for _ in 0..num_rows {
        subject.push(make_subject(rng));
        laboratory_department.push(None as Option<String>);

        let gender = make_gender(rng);
        let hb_result = rng.gen_range(0..190);
        let hb = BloodTest::new_haemoglobin(hb_result, gender);

        order_name.push(hb.order_name);
        test_name.push(hb.test_name);
        test_result.push(hb.test_result);
        test_result_unit.push(hb.test_result_unit);
        result_lower_range.push(hb.result_lower_range);
        result_upper_range.push(hb.result_upper_range);

        // Sample collected at any date from 1970 to roughly now, and
        // up to 1 week processing time
        let sample_collected_timestamp = 60 * rng.gen_range(0..28150015);
        let processing_time = 60 * rng.gen_range(0..10080);
        sample_collected_date_time.push(sample_collected_timestamp);
        result_available_date_time.push(sample_collected_timestamp + processing_time);

        result_flag.push(make_result_flag(rng));
        brc_name.push("bristol");
    }

    RecordBatch::try_from_iter([
        ("subject", Arc::new(StringArray::from(subject)) as _),
        (
            "laboratory_department",
            Arc::new(StringArray::from(laboratory_department)) as _,
        ),
        ("order_name", Arc::new(StringArray::from(order_name)) as _),
        ("test_name", Arc::new(StringArray::from(test_name)) as _),
        ("test_result", Arc::new(StringArray::from(test_result)) as _),
        (
            "test_result_unit",
            Arc::new(StringArray::from(test_result_unit)) as _,
        ),
        (
            "sample_collected_date_time",
            Arc::new(TimestampSecondArray::from(sample_collected_date_time)) as _,
        ),
        (
            "result_available_date_time",
            Arc::new(TimestampSecondArray::from(result_available_date_time)) as _,
        ),
        ("result_flag", Arc::new(StringArray::from(result_flag)) as _),
        (
            "result_lower_range",
            Arc::new(StringArray::from(result_lower_range)) as _,
        ),
        (
            "result_upper_range",
            Arc::new(StringArray::from(result_upper_range)) as _,
        ),
        ("brc_name", Arc::new(StringArray::from(brc_name)) as _),
    ])
    .unwrap()
}