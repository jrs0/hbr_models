//! Contains the functiond required for generating a block of columns from
//! a seed. The purpose of generating block is columns is to decouple the
//! random data generated in different tables (and different columns within the
//! same table), so that adding or removing columns or tables based on the same
//! global seed does not change randomly generated data in other tables. This 
//! is important for maintainability of the tests, which may come to rely on the
//! exact data in already defined tables.
//! 

use polars::prelude::*;

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
        .flatten()
        .collect();
    DataFrame::new(columns).expect("Failed to create dataframe")
}
