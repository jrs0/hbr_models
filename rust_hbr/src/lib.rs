//! Contains random seed-controlled synthetic datasets for use in
//! testing data preprocessing functions.
//!

use datafusion::arrow::record_batch::RecordBatch;
use datafusion::parquet::arrow::arrow_writer::ArrowWriter;
use datafusion::parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use std::fs;

pub use pathology_blood::make_pathology_blood;

mod pathology_blood;
mod seeded_column_block;
mod synth_data;
pub mod patient;
pub mod clinical_code;
pub mod clinical_code_tree;
pub mod seeded_rng;
pub mod preprocess;

pub fn save_record_batch(filename: &str, batch: RecordBatch) {
    let file = fs::File::create(filename).unwrap();
    let mut writer = ArrowWriter::try_new(file, batch.schema(), None).unwrap();
    writer.write(&batch).expect("Writing batch");
    writer.close().unwrap();
}

pub fn load_record_batch(filename: &str) -> RecordBatch {
    let file = fs::File::open(filename).unwrap();
    let builder = ParquetRecordBatchReaderBuilder::try_new(file).unwrap();
    println!("Converted arrow schema is: {}", builder.schema());
    let mut reader = builder.build().unwrap();
    let record_batch = reader.next().unwrap().unwrap();
    println!("Read {} records.", record_batch.num_rows());
    record_batch
}

