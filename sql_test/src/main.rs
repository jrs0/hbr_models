use sqlx::mssql::MssqlPoolOptions;

#[async_std::main]
async fn main() -> Result<(), sqlx::Error> {
    // Create a connection pool
    //  for MySQL, use MySqlPoolOptions::new()
    //  for SQLite, use SqlitePoolOptions::new()
    //  etc.
    let pool = MssqlPoolOptions::new()
        .max_connections(5)
        .connect("mssql://@xsw").await
        .expect("Failed to connect to database");

    // Make a simple query to return the given parameter (use a question mark `?` instead of `$1` for MySQL)
    // let row: (i64,) = sqlx::query_as("select top 10 * from abi.dbo.vw_apc_sem_001")
    //     //.bind(150_i64)
    //     .fetch_one(&pool).await?;

    // assert_eq!(row.0, 150);

    Ok(())
}