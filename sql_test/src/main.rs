//! Simple example demonstrating reading from an SQL Server and converting
//! to a DataFusion DataFrame (via Arrow).
//!

use arrow_odbc::{odbc_api::{Environment, ConnectionOptions}, OdbcReader};
use datafusion::prelude::*;

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    // Your application is fine if you spin up only one Environment.
    let odbc_environment = Environment::new()?;
     
    // Connect with database.
    let connection = odbc_environment.connect_with_connection_string(
        "dsn=xsw", ConnectionOptions::default()
    )?;

    // This SQL statement does not require any arguments.
    let parameters = ();

    // Execute query and create result set
    let cursor = connection
        .execute("select top 50 aimtc_pseudo_nhs,  from abi.dbo.vw_apc_sem_001", parameters)?
        .expect("SELECT statement must produce a cursor");

    // Each batch shall only consist of maximum 10.000 rows.
    let max_batch_size = 10;

    // Read result set as arrow batches. Infer Arrow types automatically using the meta
    // information of `cursor`.
    let arrow_record_batches = OdbcReader::new(cursor, max_batch_size)?;

    let ctx = SessionContext::new();

    // Want to convert an array of RecordBatch to a single DataFrame with all
    // the rows. This isn't the right way, but it does work.
    let mut id = 0_u32; 
    for batch in arrow_record_batches {
        let batch = batch.unwrap();
        ctx.register_batch(&format!("t{id}")[..], batch)?;
        id += 1;
    }
    let mut df = ctx.table("t0").await?;
    for n in 0..id {
        let df_batch = ctx.table(&format!("t{n}")[..]).await?;
        df = df.union(df_batch).unwrap();
    }

    df.show().await?;

    Ok(())
}
