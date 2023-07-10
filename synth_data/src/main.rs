use datafusion::arrow::record_batch::RecordBatch;
use datafusion::arrow::array::{ArrayRef, Float32Array, Int32Array, TimestampSecondArray};
use datafusion::parquet::arrow::arrow_writer::ArrowWriter;
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use std::sync::Arc;

use datafusion::prelude::*;
use datafusion::parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;

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



fn make_synth_data() -> RecordBatch {
    let col_1 = Arc::new(Int32Array::from_iter([1, 2, 3])) as _;
    let col_2 = Arc::new(Float32Array::from_iter([1., 6.3, 4.])) as _;
    let timestamp = Arc::new(TimestampSecondArray::from(vec![1, 1000, 100000])) as _;
    RecordBatch::try_from_iter([("col1", col_1), ("col_2", col_2), ("timestamp", timestamp)]).unwrap()
}

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {

    let mut rng = ChaCha8Rng::seed_from_u64(3);
    println!("{}", rng.gen_range(0..100));
    println!("{}", rng.gen_range(0f64..100f64));

    let batch = make_synth_data();

    save_record_batch("example.parquet", batch);

    let batch = load_record_batch("example.parquet");

    let ctx = SessionContext::new();
    let df = ctx.read_batch(batch).expect("Failed to convert batch to dataframe");

    df.show().await?;

    Ok(())
}
