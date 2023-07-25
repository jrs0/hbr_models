//! Check clinical codes against an exhaustive list and convert
//! to a standard form.
//! 

use serde::{Serialize, Deserialize};
use std::collections::HashSet;

/// Index used to sort the code categories.
/// 
/// The index contains one or two string values.
/// The first value, which is required, is the
/// lexicographical start point for the category.
/// For example, the top level ICD-10 code category
/// begins with index A00. The second value, which 
/// is present only for proper categories, defines
/// the end-point of the category. For example, 
/// the category ending B99 includes all categories
/// and codes whose name (without the dot) truncated
/// to three characters is lexicographically less than
/// or equal to B99.
#[derive(Debug, Serialize, Deserialize)]
#[serde(untagged)]
enum Index {
    String(String),
    Vec(String, String)
}

/// The Code/Categories struct
/// 
/// This struct represents a sub-tree of clinical codes.
/// The distinction is whether the categories field is 
/// None -- if it is, it is a leaf node (a code), and if
/// not, it is a category.
/// 
/// The struct maps to the structure of the codes yaml file.
/// 
#[derive(Serialize, Deserialize, Debug)]
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

#[derive(Serialize, Deserialize, Debug)]
pub struct ClinicalCodeTree {
    categories: Vec<Categories>,
    /// The list of clinical code group names that are
    /// present in this code tree
    groups: HashSet<String>,
}