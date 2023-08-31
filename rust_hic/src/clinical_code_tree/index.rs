use std::cmp::Ordering;

use serde::{Deserialize, Serialize};

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
#[derive(PartialEq, Eq, PartialOrd, Ord, Debug, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Index {
    Leaf(String),
    Category(String, String),
}

impl Index {
    pub fn make_leaf(start: &str) -> Self {
        Self::Leaf(String::from(start))
    }

    pub fn make_category(start: &str, end: &str) -> Self {
        Self::Category(String::from(start), String::from(end))
    }

    /// Compare a normalised code with an Index to determine if the
    /// code lies in the Index range. A normalised code is all lowercase
    /// with no dots or white space.
    ///
    /// The function returns Equal if the code lies in the Index range.
    /// Otherwise it returns Less or Greater depending if the code is
    /// above this index or below it.
    ///
    /// Note: due to a discrepancy in the Index format (letters are
    /// upper case), letters in the normalised code are converted back
    /// to upper case before comparison with Index. This should be fixed
    /// in the Index (and therefore in the codes files too), so that all
    /// codes are in the lower case format.
    fn compare(&self, code: &String) -> Ordering {
        let code = code.to_ascii_uppercase();
        match self {
            Index::Leaf(index_code) => code.cmp(index_code),
            Index::Category(start, end) => {
                if code.cmp(start) == Ordering::Less {
                    // If the code is less than start, then
                    // the code is strictly below self
                    Ordering::Less
                } else if code[..end.len()].cmp(end) == Ordering::Greater {
                    // Else, if the code is greater than the
                    // _truncated_ upper index, then the code
                    // lies above self.
                    Ordering::Greater
                } else {
                    // Otherwise, the code is contained within the
                    // index.
                    Ordering::Equal
                }
            }
        }
    }
}

/// Tests for the index
///
/// The main thing to check is that the index compares correctly
/// with itself so that the sorting function in the code tree works
/// correctly.
#[cfg(test)]
mod tests {

    use super::*;

    #[test]
    fn single_element_index_compares_for_equality() {
        let i1 = Index::make_leaf("ABC");
        let i2 = Index::make_leaf("ABC");
        assert_eq!(i1, i2);
    }

    #[test]
    fn two_element_index_compares_for_equality() {
        let i1 = Index::make_category("ABC", "xyz");
        let i2 = Index::make_category("ABC", "xyz");
        assert_eq!(i1, i2);
    }

    #[test]
    fn single_element_index_compare_inequality() {
        let i1 = Index::make_leaf("A00");
        let i2 = Index::make_leaf("A01");
        assert!(i1 < i2);

        let i1 = Index::make_leaf("i212");
        let i2 = Index::make_leaf("i222");
        assert!(i1 < i2);
    }

    /// As far as sorting goes, priority should be given to the first
    /// index (the start of the range).
    #[test]
    fn two_element_index_compare_inequality_first_element() {
        let i1 = Index::make_category("A00", "Z00");
        let i2 = Index::make_category("A01", "X00");
        assert!(i1 < i2);
    }

    #[test]
    fn two_element_index_compare_inequality_second_element() {
        let i1 = Index::make_category("I00", "I01");
        let i2 = Index::make_category("I00", "I02");
        assert!(i2 > i1);
    }

    #[test]
    fn check_codes_lie_in_index_range() {
        let i = Index::make_category("I00", "I02");
        // Check the lower boundary edge case
        let code = format!("i000");
        assert_eq!(i.compare(&code), Ordering::Equal);
        // Check the upper boundary edge cases. Note that the
        // code is truncated to the length of the upper limit 
        // before comparison
        let code = format!("i02");
        assert_eq!(i.compare(&code), Ordering::Equal);
        let code = format!("i0223");
        assert_eq!(i.compare(&code), Ordering::Equal);
        // Check internal code
        let code = format!("i011");
        assert_eq!(i.compare(&code), Ordering::Equal);
    }

    #[test]
    fn check_codes_lie_below_index_range() {
        let i = Index::make_category("I00", "I02");
        // Check the upper boundary edge case
        let code = format!("h999");
        assert_eq!(i.compare(&code), Ordering::Less);
        // Check internal code
        let code = format!("a001");
        assert_eq!(i.compare(&code), Ordering::Less);
    }

    #[test]
    fn check_codes_lie_above_index_range() {
        let i = Index::make_category("I00", "I02");
        // Check the lower boundary edge case
        let code = format!("i030");
        assert_eq!(i.compare(&code), Ordering::Greater);
        // Check internal code
        let code = format!("z001");
        assert_eq!(i.compare(&code), Ordering::Greater);
    }

}
