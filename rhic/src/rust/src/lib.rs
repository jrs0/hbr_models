use extendr_api::prelude::*;
use datafusion::prelude::*;

/// Test interface to Rust library
/// @export
#[extendr]
fn hello_world() {
    println!("Hello world!");
}

// Macro to generate exports.
// This ensures exported functions are registered with R.
// See corresponding C code in `entrypoint.c`.
extendr_module! {
    mod rhic;
    fn hello_world;
}
