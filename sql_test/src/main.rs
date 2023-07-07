use arrow_odbc::{odbc_api::{Environment, ConnectionOptions}, OdbcReader};
use datafusion::prelude::*;

fn main() -> Result<(), anyhow::Error> {
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
        .execute("select top 4 aimtc_pseudo_nhs from abi.dbo.vw_apc_sem_001", parameters)?
        .expect("SELECT statement must produce a cursor");

    // Each batch shall only consist of maximum 10.000 rows.
    let max_batch_size = 2;

    // Read result set as arrow batches. Infer Arrow types automatically using the meta
    // information of `cursor`.
    let arrow_record_batches = OdbcReader::new(cursor, max_batch_size)?;

    for batch in arrow_record_batches {
        // ... process batch ...
        for item in batch.iter() {
            println!("{:?}", item);
        }
    }

    let ctx = SessionContext::new();


    Ok(())
}
