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

use crate::clinical_code::{ClinicalCode, ClinicalCodeRef, ClinicalCodeStore};

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

    /// Get the set of excludes. Even though the key itself may be empty,
    /// from the point of view of programming it is easier to just have
    /// that case as an empty set.
    fn exclude(&self) -> HashSet<String> {
        if let Some(exclude_set) = &self.exclude {
            exclude_set.clone()
        } else {
            HashSet::new()
        }
    }

    /// Returns the vector of sub-categories.
    fn categories(&self) -> Option<&Vec<Categories>> {
        self.categories.as_ref()
    }

    /// Returns true if the object is a leaf node (has no
    /// sub-categories; represents a single clinical code)
    fn is_leaf(&self) -> bool {
        self.categories.is_none()
    }

    /// Get the code or category name
    pub fn name(&self) -> &String {
        &self.name
    }

    /// Get the code or category description
    pub fn docs(&self) -> &String {
        &self.docs
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

fn get_codes_in_group(
    group: &String,
    categories: &Vec<Categories>,
    code_store: &mut ClinicalCodeStore,
) -> Vec<ClinicalCodeRef> {
    let mut codes_in_group = Vec::new();

    // Filter out the categories that exclude the group
    let categories_left = categories
        .iter()
        .filter(|cat| !cat.exclude().contains(group)); // keep if not excluded;

    // Loop over the remaining categories. For all the leaf
    // categories, if there is no exclude for this group,
    // include it in the results. For non-leaf categories,
    // call this function again and append the resulting
    for category in categories_left {
        if category.is_leaf() && !category.exclude().contains(group) {
            let clinical_code = ClinicalCode::from(category);
            let clinical_code_ref = code_store.clinical_code_ref_from(clinical_code);
            codes_in_group.push(clinical_code_ref);
        } else {
            let sub_categories = category
                .categories()
                .expect("There are always sub-categories for non-leaf");
            let mut new_codes = get_codes_in_group(group, sub_categories, code_store);
            codes_in_group.append(&mut new_codes);
        }
    }

    // Return the current list of codes
    return codes_in_group;
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

    /// Get all the clinical codes in a particular group
    ///
    /// The result is either a vector of references to clinical codes
    /// or an error string if the group does not exist in the code tree.
    ///
    pub fn codes_in_group(
        &self,
        group: &String,
        code_store: &mut ClinicalCodeStore,
    ) -> Result<Vec<ClinicalCodeRef>, &'static str> {
        if !self.groups.contains(group) {
            Err("Clinical code tree does not contain that group")
        } else {
            Ok(get_codes_in_group(group, &self.categories, code_store))
        }
    }

    /// Get the list of groups defined in the clinical code tree
    pub fn groups(&self) -> &HashSet<String> {
        &self.groups
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

    // Check that the correct codes are returned from the hard-coded test files.
    #[test]
    fn check_codes_in_group() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("icd10_example.yaml");

        let f = std::fs::File::open(file_path).expect("Failed to open icd10 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);

        let mut code_store = ClinicalCodeStore::new();

        // Get the ACS STEMI codes in the groups defined by the file
        let acs_stemi_schnier_codes = code_tree
            .codes_in_group(&format!("acs_stemi_schnier"), &mut code_store)
            .expect("Should succeed, code is present");
        assert_eq!(acs_stemi_schnier_codes.len(), 7);

        let code_names: Vec<_> = acs_stemi_schnier_codes
            .iter()
            .map(|code_ref| {
                let clinical_code = code_store
                    .clinical_code_from(code_ref)
                    .expect("Clinical code should be present");
                clinical_code.name()
            })
            .collect();

        // These are from looking at the selected items in the codes editor
        assert_eq!(
            code_names,
            vec!["I21.0", "I21.1", "I21.2", "I21.3", "I22.0", "I22.1", "I22.8"]
        );

        // Codes from the atrial_fib groups
        let atrial_fib_codes = code_tree
            .codes_in_group(&format!("atrial_fib"), &mut code_store)
            .expect("Should succeed, code is present");
        assert_eq!(atrial_fib_codes.len(), 6);

        let code_names: Vec<_> = atrial_fib_codes
            .iter()
            .map(|code_ref| {
                let clinical_code = code_store
                    .clinical_code_from(code_ref)
                    .expect("Clinical code should be present");
                clinical_code.name()
            })
            .collect();

        // These are from looking at the selected items in the codes editor
        assert_eq!(
            code_names,
            vec!["I48.0", "I48.1", "I48.2", "I48.3", "I48.4", "I48.9"]
        );
    }

    #[test]
    fn check_nonexistent_group_returns_error() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("icd10_example.yaml");

        let f = std::fs::File::open(file_path).expect("Failed to open icd10 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);

        let mut code_store = ClinicalCodeStore::new();

        // Try to read a group of codes which is not in the file
        let unknown_group = code_tree.codes_in_group(&format!("unknown_group"), &mut code_store);
        assert!(unknown_group.is_err());
    }

    /// Convenience macro to make a HashSet<String> from a vector
    /// of literals for testing. 
    macro_rules! set_of_strings {
        ($($x:expr),*) => (HashSet::from([$($x.to_string()),*]));
    }

    #[test]
    fn check_returned_groups_match_icd10_file() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("icd10_example.yaml");

        let f = std::fs::File::open(file_path).expect("Failed to open icd10 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);

        // Note the order of the groups is not defined -- just
        // the set is being checked
        let groups = code_tree.groups().clone();
        assert_eq!(
            groups,
            set_of_strings!(
                "acs_stemi_schnier",
                "acs_nstemi",
                "acs_unstable_angina",
                "bleeding",
                "chronic_ischaemia_heart_disease",
                "other_ischaemic_heart_diseases",
                "atrial_fib",
                "ckd1",
                "ckd2",
                "ckd3",
                "ckd4",
                "ckd5",
                "ckd",
                "ckd.other",
                "anaemia",
                "thrombocytopenia",
                "smoking",
                "copd",
                "cancer",
                "cirrhosis",
                "hepatic_failure",
                "portal_hypertension",
                "type_1_diabetes",
                "type_2_diabetes",
                "diabetes_unspecified",
                "ischaemic_stroke"
            )
        )
    }
}
