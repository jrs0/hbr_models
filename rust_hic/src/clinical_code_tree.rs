//! Data structures for managing a tree of clinical codes
//! and code groups
//!
//! The key structure is ClinicalCodeTree, which has a method
//! to create from a byte reader (from_reader()). This can
//! be a yaml file or yaml string. This function sorts the
//! categories by index even if they are not sorted in the
//! original file, meaning the parser can assume the categories
//! are sorted. The original file is one of icd10.yaml or opcs4.yaml
//! (or anything else in that format -- it should serialize/
//! deserialize correctly.
//!
//! The ClinicalCodeTree defines a tree of Categories, where each
//! leaf node is (for example) an ICD-10 code and each non-leaf
//! node is a  category of codes. Once the structure is available,
//! various operations can be performed using it, for example,
//! picking a (uniform) random code, identifying whether a code
//! exists or not and fetching its documentation, or fetching all
//! the codes in a given code group.

use index::Index;
use rand::seq::SliceRandom;
use rand_chacha::ChaCha8Rng;
use serde::{Deserialize, Serialize};
use std::io::Read;
use std::{cmp::Ordering, collections::HashSet};

use crate::clinical_code::{ClinicalCode, ClinicalCodeRef, ClinicalCodeStore};

mod index;

/// The Code/Categories struct
///
/// This struct represents a sub-tree of clinical codes.
/// The distinction is whether the categories field is
/// None -- if it is, it is a leaf node (a code), and if
/// not, it is a category.
///
/// TODO: RENAME TO CATEGORY
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

/// Pick a sub-category at random. Panics if there are no
/// sub-categories (do not call on leaf nodes). Returns
/// error if there are no sub-categories (input vector is
/// length zero)
fn pick_subcategory_uniform_random<'a>(
    categories: &'a Vec<Categories>,
    rng: &mut ChaCha8Rng,
) -> Result<&'a Categories, &'static str> {
    if categories.len() == 0 {
        Err("No categories to pick from")
    } else {
        let choice = categories
            .choose(rng)
            .expect("Should be Some, categories list is not empty");
        Ok(&choice)
    }
}

impl Categories {
    /// Get a random clinical code from one of the (leaf)
    /// sub-categories of this category.  
    fn random_clinical_code(&self, rng: &mut ChaCha8Rng) -> ClinicalCode {
        if self.is_leaf() {
            ClinicalCode::from(self)
        } else {
            let sub_categories = self
                .categories()
                .expect("Non-leaf node will have sub-categories");
            let choice = pick_subcategory_uniform_random(sub_categories, rng)
                .expect("Subcategory list is non-empty, so should not fail");
            choice.random_clinical_code(rng)
        }
    }

    /// Sort the categories recursively in place
    fn sort_categories(&mut self) {
        match &mut self.categories {
            Some(categories) => sort_categories_list_in_place(categories),
            None => (),
        };
    }

    /// Get the set of excludes. Even though the key itself may be empty,
    /// it is easier to just have that case as an empty set.
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

    /// Get the index of this code or category
    pub fn index(&self) -> &Index {
        &self.index
    }

}

/// Remove whitespace, dots and convert all characters
/// to lowercase. Note that other (non-dot) non-alphanumeric
/// characters are retained
fn normalise_code(code: String) -> String {
    code.to_lowercase()
        .replace(".", "")
        .split_whitespace()
        .collect()
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

/// Return the category in the supplied vector that contains the code,
/// or return the error variant "not found" if the code is not present
/// in any category. The search is performed using the index of the
/// category.
fn locate_code_in_categories<'a>(
    code: &String,
    categories: &'a Vec<Categories>,
) -> Result<&'a Categories, &'static str> {
    // Look through the index keys at the current level
    // and find the position of the code. Inside the codes
    // structure, the index keys provide an array to search
    // (using binary search) for the ICD code in str.

    // auto position = std::upper_bound(categories.begin(),
    // 			     categories.end(),
    // 			     code);
    // const bool found = (position != std::begin(categories)) &&
    // ((position-1)->contains(code));

    // Determine whether a code is in the category by comparing
    let compare_code_with_category = |cat: &Categories| -> Ordering {
        let cat_name = cat.name();
        let cat_index = cat.index();
        println!("Comparing {code} to category {cat_name} with index {:?}", cat_index);
        cat.index().compare(code)
    };

    match categories.binary_search_by(compare_code_with_category) {
        Ok(position) => {
            println!("Position {position}");
            Ok(&categories[position])
        }
        Err(position) => {
            println!("Failed at position {position}");
            Err("not found")
        },
    }

    // If found == false, then a match was not found. This
    // means that the code is not a valid member of any member
    // of this level, so it is not a valid code. TODO it still
    // may be possible to return the category above as a fuzzy
    // match -- consider implementing
    // if (!found) {
    // throw ParserException::CodeNotFound {};
    // }

    // Decrement the position to point to the largest category
    // c such that c <= code
    // position--;

    // return *position;
}

/// Return the name and docs field of a code (depending on the bool argument)
/// if it exists in the categories tree, or return an error variant if the
/// code is not present in the list of categories.
///
/// Note: You can also use this function to find the groups that a code is in.
/// See the corresponding C++ function https://github.com/jrs0/rdb/blob/main
/// /src/category.cpp#L192. In that case, you need to return a type that wraps
/// the ClinicalCodeRef and also some reference to the groups.
///
fn locate_code_in_tree(
    code: String,
    categories: &Vec<Categories>,
    code_store: &mut ClinicalCodeStore,
) -> Result<ClinicalCodeRef, &'static str> {
    // Locate the category containing the code at the current level
    if let Ok(cat) = locate_code_in_categories(&code, categories) {
        // If there is a subcategory, make a call to this function
        // to process the next category down. Otherwise you are
        // at a leaf node, so start returning up the call graph.
        // TODO: since this function is linearly recursive,
        // there should be a tail-call optimisation available here
        // somewhere.
        if !cat.is_leaf() {
            let sub_categories = cat
                .categories()
                .expect("Expecting sub-categories for non-leaf node");
            
            println!("Subcats:");
            for cat in sub_categories {
                let cat_name = cat.name();
                println!("- {cat_name}");
            }

            // There are sub-categories -- parse the code at the next level
            // down (put a try catch here for the case where the next level
            // down isn't better)
            locate_code_in_tree(code, sub_categories, code_store)
        } else {
            Ok(code_store.clinical_code_ref_from(ClinicalCode::from(cat)))
        }
    } else {
        Err("not found")
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

    /// Generate a clinical code at random from the tree of codes
    ///
    /// Always returns a clinical code (i.e. a leaf), never a category.
    /// The random element is picked by choosing from the sub-categories
    /// uniformly at random until a code is reached.
    pub fn random_clinical_code(
        &self,
        rng: &mut ChaCha8Rng,
        code_store: &mut ClinicalCodeStore,
    ) -> ClinicalCodeRef {
        let clinical_code = pick_subcategory_uniform_random(&self.categories, rng)
            .expect("Should be Some, Categories list should not be empty")
            .random_clinical_code(rng);
        code_store.clinical_code_ref_from(clinical_code)
    }

    /// Pick an element uniformly at random from the specified
    /// code group
    ///
    /// Returns an error if the code group is undefined, or if
    /// the code group is empty.
    pub fn random_clinical_code_from_group(
        &self,
        rng: &mut ChaCha8Rng,
        code_store: &mut ClinicalCodeStore,
        group: &String,
    ) -> Result<ClinicalCodeRef, &'static str> {
        if let Ok(codes_in_group) = self.codes_in_group(group, code_store) {
            if let Some(code) = codes_in_group.choose(rng) {
                Ok(*code)
            } else {
                Err("Code group is empty")
            }
        } else {
            Err("Error occurred fetching codes in group")
        }
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

    /// Find a particular code in the tree, or return an error
    /// if it is not present.
    ///
    /// Apart from converting the input code into a normalised
    /// form (no whitespace, no dot, and all lower case characters),
    /// and compared with the normalised form of the code in the
    /// code tree. The code is only considered a match if the two
    /// normalised codes match exactly. The code will not match
    /// if (for example)
    /// - The code is simply invalid (does not fall within any category)
    /// - The code has trailing material at the end
    /// - The code has any of the standard uses of X, D or A (or other
    ///   modifiers) which would make the match not exact.
    ///
    /// If the match succeeds, then a reference to the code is returned.
    /// If the match fails, an error variant is returned with the error
    /// string "no match", or another error (if it occurred).
    ///
    /// Each call to this function will search the entire tree, which is
    /// slow (even though it is a binary search). In code that repeatedly
    /// searches for exact code matches, you should cache the result of
    /// this function in a map from the code String argument to ClinicalCodeRef.
    ///
    /// Note: traversing the tree looking for a code also gives you the groups
    /// the code is in for free (that operation also requires a tree traversal).
    /// So it might be a good idea to store the groups too, instead of having
    /// to traverse the tree twice.
    pub fn find_exact(
        &self,
        code: String,
        code_store: &mut ClinicalCodeStore,
    ) -> Result<ClinicalCodeRef, &'static str> {
        let normalised_code = normalise_code(code);
        locate_code_in_tree(normalised_code, &self.categories, code_store)
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

    use crate::{name, seeded_rng::make_rng};

    use super::*;

    // Helper macros to generate a category
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

    // Helper macro to generate a clinical code
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

    // Reference clinical code tree structure for comparison
    fn code_tree_example_1() -> ClinicalCodeTree {
        ClinicalCodeTree {
            categories: vec![
                category!(
                    "cat1",
                    "category 1",
                    Index::make_dual("cat11", "cat12"),
                    vec![
                        leaf!("cat11", "sub cat 11", Index::make_single("cat11")),
                        leaf!("cat12", "sub cat 12", Index::make_single("cat12")),
                    ]
                ),
                category!(
                    "cat2",
                    "category 2",
                    Index::make_dual("cat2", "cat2"),
                    vec![
                        leaf!("cat21", "sub cat 21", Index::make_single("cat21")),
                        leaf!("cat22", "sub cat 22", Index::make_single("cat22")),
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
    fn check_code_normalisation() {
        let string = format!("A00.0");
        assert_eq!(normalise_code(string), "a000");
        let string = format!(" A 00.0 ");
        assert_eq!(normalise_code(string), "a000");
        let string = format!("i21.1x ");
        assert_eq!(normalise_code(string), "i211x");
        let string = format!("     j10.x ");
        assert_eq!(normalise_code(string), "j10x");
        // Note non-dot non-alphanuemric character are
        // currently kept
        let string = format!("A00.0|");
        assert_eq!(normalise_code(string), "a000|");
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
    fn test_clinical_code_from_category() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("icd10_example.yaml");

        let f = std::fs::File::open(file_path).expect("Failed to open icd10 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);

        let mut code_store = ClinicalCodeStore::new();
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

    #[test]
    fn check_randomly_chosen_code_is_in_group() {
        let mut file_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        file_path.push("resources");
        file_path.push("test");
        file_path.push("icd10_example.yaml");

        let f = std::fs::File::open(file_path).expect("Failed to open icd10 file");

        // Should execute without panic
        let code_tree = ClinicalCodeTree::from_reader(f);

        let mut code_store = ClinicalCodeStore::new();

        // atrial_fib code group
        let mut codes_in_group: Vec<_> = vec!["I48.0", "I48.1", "I48.2", "I48.3", "I48.4", "I48.9"]
            .iter_mut()
            .map(|string| String::from(*string))
            .collect();

        // Generate 100 random codes and check they are all
        // in the group
        let mut rng = make_rng(222, "clinical_code_test_id");
        for _ in 0..100 {
            let random_code = code_tree
                .random_clinical_code_from_group(&mut rng, &mut code_store, &format!("atrial_fib"))
                .expect("Should be able to pick a valid code");

            assert!(codes_in_group.contains(name!(random_code, code_store)))
        }
    }
}
