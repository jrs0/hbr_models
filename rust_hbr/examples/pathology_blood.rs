use datafusion::prelude::*;
use rust_hbr::{load_record_batch, save_record_batch, make_pathology_blood};
use polars::prelude::*;


#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {

    let df = make_pathology_blood("pathology_blood", 0, 100);
    println!{"{df}"};


    //save_record_batch("example.parquet", batch);

    //let batch = load_record_batch("example.parquet");

   /*  let ctx = SessionContext::new();
    let df = ctx
        .read_batch(batch)
        .expect("Failed to convert batch to dataframe");

    df.show().await?; */

    Ok(())
}