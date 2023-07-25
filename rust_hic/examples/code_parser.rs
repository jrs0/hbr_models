use rust_hic::code_parser::ClinicalCodeTree;
use serde_yaml;

fn main() {
    let f = std::fs::File::open("..\\codes_editor\\icd10_example.yaml")
        .expect("Failed to open file");
    let d: ClinicalCodeTree = serde_yaml::from_reader(f)
        .expect("Failed to deserialize to Categories");

    println!("{:?}", d);
}