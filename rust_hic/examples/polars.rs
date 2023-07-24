use connectorx::prelude::*;
use std::convert::TryFrom;

let mut source_conn = SourceConn::try_from("mssql://XSW-000-SP09/ABI?trusted_connection=true").expect("parse conn str failed");
let queries = &[CXQuery::from("select top 10 * from abi.dbo.vw_apc_sem_001"), CXQuery::from("select top 12 * from abi.dbo.vw_apc_sem_001")];
let destination = get_arrow(&source_conn, None, queries).expect("run failed");

let data = destination.arrow();