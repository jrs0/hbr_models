//! Data structures for managing a tree of clinical codes
//! and code groups
//!
//! The key structure is ClinicalCodeTree, which has a method
//! to create from a byte reader (from_reader()). This can
//! be a yaml file or yaml string. This function sorts the
//! categories by index even if they are not sorted in the
//! original file, meaning the parser can assume the categories
//! are sorted.

use index::Index;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::io::Read;

mod index;

/// The Code/Categories struct
///
/// This struct represents a sub-tree of clinical codes.
/// The distinction is whether the categories field is
/// None -- if it is, it is a leaf node (a code), and if
/// not, it is a category.
///
#[derive(PartialEq, Eq, Serialize, Deserialize, Debug)]
pub struct Categories {
    /// The name of the code or category; e.g. A01.0
    name: String,
    /// The code description; e.g.
    docs: String,
    /// The index used to order the sub-categories
    index: Index,
    /// The set of sub-categories. If there are no
    /// categories, then the struct is a code, and
    /// the name and docs are the information about
    /// the code. If there are sub-categories, then
    /// the name and docs apply to the category
    categories: Option<Vec<Categories>>,
    /// A set of code groups that do not contain this
    /// category or any sub-category
    exclude: Option<HashSet<String>>,
}

fn sort_categories_list_in_place(categories: &mut Vec<Categories>) {
    // Sort the categories by the index field
    categories.sort_by(|c1, c2| c1.index.cmp(&c2.index));

    // Also sort all sub-categories
    for category in categories.iter_mut() {
        category.sort_categories();
    }
}

impl Categories {
    /// Sort the categories recursively in place
    fn sort_categories(&mut self) {
        match &mut self.categories {
            Some(categories) => sort_categories_list_in_place(categories),
            None => (),
        };
    }
}

macro_rules! category {
    ($name:expr, $docs:expr, $index:expr, $categories:expr) => {
        Categories {
            name: String::from($name),
            docs: String::from($docs),
            index: $index,
            exclude: None,
            categories: Some($categories),
        }
    };
}

macro_rules! leaf {
    ($name:expr, $docs:expr, $index:expr) => {
        Categories {
            name: String::from($name),
            docs: String::from($docs),
            index: $index,
            exclude: None,
            categories: None,
        }
    };
}

/// The code definition file structure
///
/// This struct maps to the contents of a code file
/// for ICD-10 and OPCS-4 codes. It includes the code
/// tree itself, a list of code groups, and tags embedded
/// in the tree indicating which codes are in which group.
#[derive(PartialEq, Eq, Serialize, Deserialize, Debug)]
pub struct ClinicalCodeTree {
    categories: Vec<Categories>,
    /// The list of clinical code group names that are
    /// present in this code tree
    groups: HashSet<String>,
}

impl ClinicalCodeTree {
    /// Read a clinical code tree from a byte source
    ///
    /// The key function performed here is sorting the
    /// categories based on index, which is not assumed to
    /// be true in the byte source (e.g. underlying yaml file).
    ///
    /// You can pass the result of std::fs::File::open() on
    /// a yaml file to this function.
    pub fn from_reader<R>(reader: R) -> Self
    where
        R: Read,
    {
        let mut tree: Self =
            serde_yaml::from_reader(reader).expect("Failed to deserialize to Categories");
        sort_categories_list_in_place(&mut tree.categories);
        tree
    }
}

/// Tests for the code tree
///
/// The following things need checking:
/// * whether a code file deserializes to the structure correctly [partially done]
/// * whether the struct categories are sorted correctly [partially done]
/// * whether the code tree struct serializes correctly to a file [not started]
///
///
#[cfg(test)]
mod tests {

    use std::path::PathBuf;

    use super::*;

    // Reference clinical code tree structure for comparison
    fn code_tree_example_1() -> ClinicalCodeTree {
        ClinicalCodeTree {
            categories: vec![
                category!(
                    "cat1",
                    "category 1",
                    Index::make_category("cat11", "cat12"),
                    vec![
                        leaf!("cat11", "sub cat 11", Index::make_leaf("cat11")),
                        leaf!("cat12", "sub cat 12", Index::make_leaf("cat12")),
                    ]
                ),
                category!(
                    "cat2",
                    "category 2",
                    Index::make_category("cat2", "cat2"),
                    vec![
                        leaf!("cat21", "sub cat 21", Index::make_leaf("cat21")),
                        leaf!("cat22", "sub cat 22", Index::make_leaf("cat22")),
                    ]
                ),
            ],
            groups: HashSet::from([
                String::from("group1"),
                String::from("group2"),
                String::from("another"),
            ]),
        }
    }

    #[test]
    fn deserialize_pre_sorted() {
        let yaml = r#"
        categories:
        - name: cat1
          docs: category 1
          index:
          - cat11
          - cat12
          categories:
          - name: cat11
            docs: sub cat 11
            index: cat11
          - name: cat12
            docs: sub cat 12
            index: cat12
        - name: cat2
          docs: category 2
          index:
          - cat2
          - cat2
          categories:
          - name: cat21
            docs: sub cat 21
            index: cat21
          - name: cat22
            docs: sub cat 22
            index: cat22
        groups:
        - group1
        - group2
        - another
        "#;

        let code_tree = ClinicalCodeTree::from_reader(yaml.as_bytes());
        assert_eq!(code_tree, code_tree_example_1());
    }

    #[test]
    fn deserialize_unsorted() {
        let yaml = r#"
        categories:
        - name: cat2
          docs: category 2
          index:
          - cat2
          - cat2
          categories:
          - name: cat21
            docs: sub cat 21
            index: cat21
          - name: cat22
            docs: sub cat 22
            index: cat22
        - name: cat1
          docs: category 1
          index:
          - cat11
          - cat12
          categories:
          - name: cat12
            docs: sub cat 12
            index: cat12
          - name: cat11
            docs: sub cat 11
            index: cat11
        groups:
        - group1
        - group2
        - another
        "#;

        let code_tree = ClinicalCodeTree::from_reader(yaml.as_bytes());
        assert_eq!(code_tree, code_tree_example_1());
    }

    #[test]
    fn check_icd10_example_file_loads() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("icd10_example.yaml");

        let f = std::fs::File::open(file_path).expect("Failed to open icd10 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);
    }

    #[test]
    fn check_opcs4_example_file_loads() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("opcs4_example.yaml");
        println!("{}", file_path.display());

        let f = std::fs::File::open(file_path).expect("Failed to open opcs4 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);
    }
}
