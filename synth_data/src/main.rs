use datafusion::arrow::record_batch::RecordBatch;
use datafusion::parquet::arrow::arrow_writer::ArrowWriter;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;


use datafusion::parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use datafusion::prelude::*;

use std::fs;

use pathology_blood::make_pathology_blood;

mod pathology_blood;

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

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let mut rng = ChaCha8Rng::seed_from_u64(3);

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
