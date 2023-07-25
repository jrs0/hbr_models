//! Contains the functiond required for generating a block of columns from
//! a seed. The purpose of generating block is columns is to decouple the
//! random data generated in different tables (and different columns within the
//! same table), so that adding or removing columns or tables based on the same
//! global seed does not change randomly generated data in other tables. This 
//! is important for maintainability of the tests, which may come to rely on the
//! exact data in already defined tables.
//! 

use rand::prelude::*;
use rand_chacha::ChaCha8Rng;
use std::sync::Arc;
use datafusion::arrow::array::{Array, StringArray};
use arrow_odbc::arrow::{array::GenericByteArray, datatypes::GenericStringType};
use datafusion::arrow::{error::ArrowError, record_batch::RecordBatch};
use blake2::{Blake2b512, Digest};
use polars::series::Series;
use polars::frame::DataFrame;

/// A set of synthetic data columns which are randomly
/// generated from one seeded and which are considered
/// as one logical unit.
///
/// The purpose of the block is to be the smallest unit
/// of reproducible synthetic data. SeededColumns can
/// be combined together into a RecordBatch.
///
pub struct SeededColumnBlock {
    pub columns: Vec<Series>,
}

/// Convert a list of SeededColumnBlocks (which are themselves
/// groups of columns) into a Polars dataframe
pub fn to_polars(
    seeded_column_blocks: Vec<SeededColumnBlock>,
) -> DataFrame {
    let columns = seeded_column_blocks
        .into_iter()
        .map(|x| x.columns)
        .flatten();
    DataFrame::new(columns)
}

/// Make a random number generator from a global seed
/// and a string id (used to give each independent block
/// of synthetic data a different seed). The block_id is
/// concatenated with the global seed and the result is
/// hashed. The resulting hash seeds the random number
/// generator.
pub fn make_rng(block_id: &str, global_seed: u64) -> ChaCha8Rng {
    let message = format!("{block_id}{global_seed}");
    let mut hasher = Blake2b512::new();
    hasher.update(message);
    let seed = hasher.finalize()[0..32]
        .try_into()
        .expect("Unexpectedly failed to obtain correct-length slice");
    ChaCha8Rng::from_seed(seed)
}

/// Utility function. This is only needed to simplify creating single
/// columns, and is generic to work with both String and Option<String>.
/// It should really be part of the implementation of SeededColumnBlock -- also, 
/// can jsut get rid of it if the generics get too complicated.
/// 
pub fn make_string_column<T>(column_name: String, column: Vec<T>) -> SeededColumnBlock
where
    GenericByteArray<GenericStringType<i32>>: From<Vec<T>>,
{
    SeededColumnBlock {
        columns: vec![(column_name, Arc::new(StringArray::from(column)) as _)],
    }
}