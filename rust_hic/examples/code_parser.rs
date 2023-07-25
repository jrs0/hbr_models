use rust_hic::clinical_code_tree::ClinicalCodeTree;
use serde_yaml;

fn main() {
    let f = std::fs::File::open("..\\codes_editor\\icd10_example.yaml")
        .expect("Failed to open file");
    

    println!("{:?}", d);
}