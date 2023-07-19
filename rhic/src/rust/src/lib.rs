use extendr_api::prelude::*;
use datafusion::prelude::*;
use rust_hic::{make_pathology_blood, save_record_batch, load_record_batch};

/// Test interface to Rust library
/// @export
#[extendr]
fn hello_world() {
    println!("Hello world!");
    let batch = make_pathology_blood("pathology_blood", 0, 100);

    save_record_batch("example.parquet", batch);

    let batch = load_record_batch("example.parquet");

    let ctx = SessionContext::new();
    let df = ctx
        .read_batch(batch)
        .expect("Failed to convert batch to dataframe");

}

// Macro to generate exports.
// This ensures exported functions are registered with R.
// See corresponding C code in `entrypoint.c`.
extendr_module! {
    mod rhic;
    fn hello_world;
}
