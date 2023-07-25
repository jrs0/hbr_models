//! Check clinical codes against an exhaustive list and convert
//! to a standard form.
//! 


struct Index {
    start: String,
    end: End,
}

struct Category {
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
    exclude: HashSet<String>,
}

struct TopLevelCategory {
    /// The set of code groups present in this tree of
    /// codes
    groups: HashSet<String>,
    /// The set of code categories at the top level
    categories: Vec<Categories>,
}

