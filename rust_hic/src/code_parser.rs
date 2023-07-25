//! Check clinical codes against an exhaustive list and convert
//! to a standard form.
//! 

use serde::{Serialize, Deserialize};
use std::collections::HashSet;

#[derive(Serialize, Deserialize, Debug)]
pub struct Index {
    //start: String,
    //end: End,
    values: Vec<String>,
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
