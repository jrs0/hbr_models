//! Data structures for managing a tree of clinical codes
//! and code groups
//!

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
/// * whether a code file deserializes to the structure correctly
/// * whether the struct categories are sorted correctly
/// * whether the code tree struct serializes correctly to a file
///
///
#[cfg(test)]
mod tests {

    use super::*;

    fn yaml_example_1() -> &'static str {
        r#"
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
        "#
    }

    fn code_tree_example_1() -> ClinicalCodeTree{
        ClinicalCodeTree {
            categories: vec![
                Categories {
                    name: String::from("cat1"),
                    docs: String::from("category 1"),
                    index: Index::new()
                },
            ],
            groups: HashSet::from([
                String::from("group1"),
                String::from("group2"),
                String::from("another")
                ]),
        }
    }

    #[test]
    fn deserialize_pre_sorted() {
        let yaml = yaml_example_1();

        let code_tree = ClinicalCodeTree::from_reader(yaml.as_bytes());
        println!("{:?}", code_tree);
        assert_eq!(code_tree, code_tree_example_1());

    }

    
}
