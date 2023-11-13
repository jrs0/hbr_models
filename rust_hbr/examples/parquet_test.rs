use std::{fs, path::Path, sync::Arc};

use datafusion::parquet::{
    file::reader::FileReader,
    file::{
        properties::WriterProperties, reader::SerializedFileReader, writer::SerializedFileWriter,
    },
    schema::parser::parse_message_type,
};

fn main() {
    // Write to file
    let path = Path::new("sample.parquet");

    let message_type = "
  message schema {
    REQUIRED INT32 b;
  }
";
    let schema = Arc::new(parse_message_type(message_type).unwrap());
    let file = fs::File::create(&path).unwrap();
    let mut writer = SerializedFileWriter::new(file, schema, Default::default()).unwrap();
    let mut row_group_writer = writer.next_row_group().unwrap();

    while let Some(mut col_writer) = row_group_writer.next_column().unwrap() {
        // ... write values to a column writer
        col_writer.close().unwrap()
    }
    row_group_writer.close().unwrap();
    writer.close().unwrap();

    let bytes = fs::read(&path).unwrap();
    assert_eq!(&bytes[0..4], &[b'P', b'A', b'R', b'1']);

    // Read from file
    if let Ok(file) = fs::File::open(&path) {
        let reader = SerializedFileReader::new(file).unwrap();

        let parquet_metadata = reader.metadata();
        assert_eq!(parquet_metadata.num_row_groups(), 1);

        let row_group_reader = reader.get_row_group(0).unwrap();
        assert_eq!(row_group_reader.num_columns(), 1);
    }
}
