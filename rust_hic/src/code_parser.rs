//! Check clinical codes against an exhaustive list and convert
//! to a standard form.
//! 

#[derive(Debug)]
pub struct Index {
    start: String,
    end: End,
}

#[derive(Debug)]
pub struct Categories {
    /// The name of the code or category; e.g. A01.0
    name: String,
    /// The code description; e.g. 
    docs: String,
    /// The index used to order the sub-categories
    index: Index,
    /// The set of sub-categories
    categories: Vec<Category>,
    /// A set of code groups that do not contain this
    /// category or any sub-category
    exclude: Option<HashSet<String>>,
}
