use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use datafusion::prelude::*;
use synth_data::{load_record_batch, save_record_batch, make_pathology_blood};

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