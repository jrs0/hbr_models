use datafusion::arrow::array::{
    ArrayRef, Float32Array, Int32Array, StringArray, TimestampSecondArray,
};
use datafusion::arrow::record_batch::RecordBatch;
use datafusion::parquet::arrow::arrow_writer::ArrowWriter;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use std::sync::Arc;

use datafusion::parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use datafusion::prelude::*;

use std::fs;

fn save_record_batch(filename: &str, batch: RecordBatch) {
    let file = fs::File::create(filename).unwrap();
    let mut writer = ArrowWriter::try_new(file, batch.schema(), None).unwrap();
    writer.write(&batch).expect("Writing batch");
    writer.close().unwrap();
}

fn load_record_batch(filename: &str) -> RecordBatch {
    let file = fs::File::open(filename).unwrap();
    let builder = ParquetRecordBatchReaderBuilder::try_new(file).unwrap();
    println!("Converted arrow schema is: {}", builder.schema());
    let mut reader = builder.build().unwrap();
    let record_batch = reader.next().unwrap().unwrap();
    println!("Read {} records.", record_batch.num_rows());
    record_batch
}

// start pathology_blood

enum Gender {
    Female,
    Male,
    Other,
}

/// Generate a patient id for the pathology_blood table (format "bristol_nnnn")
fn make_subject(rng: &mut ChaCha8Rng) -> String {
    let patient_id = rng.gen_range(1..=50000);
    format! {"bristol_{patient_id}"}
}

/// Lab test data in the format required for the pathology_blood table.
/// String data type is used to match type in synthetic data table.
///
#[derive(Debug)]
struct BloodTest {
    /// Top-level category name (e.g. FULL BLOOD COUNT)
    pub order_name: Option<String>,
    /// Test name within order_name (e.g. haemoglobin)
    pub test_name: Option<String>,
    /// Test result, a string-encoded floating-point number of integer
    pub test_result: Option<String>,
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
            Gender::Other => unimplemented!("Unknown haemoglobin range for other gender"),
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

fn make_pathology_blood(rng: &mut ChaCha8Rng, num_rows: usize) -> RecordBatch {
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


        let hb = BloodTest::new_haemoglobin(120, Gender::Female);

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

        result_flag.push(Some("<"));
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

// end pathology_blood

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let mut rng = ChaCha8Rng::seed_from_u64(3);
    let subject = make_subject(&mut rng);
    println!("Subject: {subject}");

    let batch = make_pathology_blood(&mut rng, 20);

    save_record_batch("example.parquet", batch);

    let batch = load_record_batch("example.parquet");

    let ctx = SessionContext::new();
    let df = ctx
        .read_batch(batch)
        .expect("Failed to convert batch to dataframe");

    df.show().await?;

    Ok(())
}
