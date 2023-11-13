use std::cmp::Ordering;

use serde::{Deserialize, Serialize};

/// Index used to sort the code categories.
///
/// An index is a pair of String (a, b), where
/// a <= b lexicographically. It represents
/// the range of a Category, and is used for
/// sorting categories into order or comparing
/// a code with a category for binary search purposes.
/// Both A and B are the same length, and A may equal B.
/// 
/// The rule which determines whether a code c is in
/// the range (a, b) is as follows:
/// - truncate c to the length of a and b to produce c';
/// - compare c' with a and b lexicographically.
/// 
/// If a <= c' <= b, then c lies in the range defined by
/// (a, b). Otherwise, c is above (a, b) if c' > b, or
/// below (a, b) if c' < a.
/// 
/// In the case where a = b, only a needs to be stored,
/// and the Single enum variant is used. Else the Dual
/// variant is used, which stores (a, b). Note also that
/// in this case, c is in (a, a) if and only if c' = a.
///
#[derive(PartialEq, Eq, PartialOrd, Ord, Debug, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Index {
    Single(String),
    Dual(String, String),
}

impl Index {
    pub fn make_single(start: &str) -> Self {
        Self::Single(String::from(start))
    }

    /// Return true if self (a, b) contains code,
    /// otherwise returns false. 
    pub fn contains(&self, code: &String) -> bool {
        match self {
            Self::Single(a) => {
                let c_prime = &code[..a.len()];
                c_prime == a
            },
            Self::Dual(a, b) => {
                let c_prime = code[..a.len()].to_string();
                (a <= &c_prime) && (&c_prime >= b)
            }
        }
    }

    /// Return true if self (a, b) is above code (i.e.
    /// code is below 
    pub fn is_lt(&self, code: &String) -> bool {
        match self {
            Self::Single(a) => {
                let c_prime = &code[..a.len()];
                c_prime == a
            },
            Self::Dual(a, b) => {
                let c_prime = &code[..a.len()].to_string();
                (a <= c_prime) && (c_prime <= b)
            }
        }
    }    


    pub fn make_dual(start: &str, end: &str) -> Self {
        Self::Dual(String::from(start), String::from(end))
    }

    /// Compare a normalised code with an Index to determine if the
    /// code lies in the Index range. A normalised code is all lowercase
    /// with no dots or white space.
    ///
    /// The function returns Equal if the code lies in the Index range.
    /// Otherwise it returns Less if the Index (self) is strictly below 
    /// the code, and Greater if self is strictly above the code. This
    /// might feel the wrong way round, but think of it like "how does 
    /// self compare with the argument" (it is consistent with the 
    /// direction of std::cmp).
    /// 
    /// Note: due to a discrepancy in the Index format (letters are
    /// upper case), letters in the normalised code are converted back
    /// to upper case before comparison with Index. This should be fixed
    /// in the Index (and therefore in the codes files too), so that all
    /// codes are in the lower case format.
    pub fn compare(&self, code: &String) -> Ordering {
        let code = code.to_ascii_uppercase();
        match self {
            Self::Single(a) => {
                let c_prime = &code[..a.len()].to_string();
                if c_prime == a {
                    Ordering::Equal
                } else if c_prime < a {
                    Ordering::Greater
                } else {
                    Ordering::Less
                }
            },
            Self::Dual(a, b) => {
                let c_prime = &code[..a.len()].to_string();
                if (a <= c_prime) && (c_prime <= b) {
                    Ordering::Equal
                } else if c_prime < a {
                    Ordering::Greater
                } else {
                    Ordering::Less
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
        let i1 = Index::make_single("ABC");
        let i2 = Index::make_single("ABC");
        assert_eq!(i1, i2);
    }

    #[test]
    fn two_element_index_compares_for_equality() {
        let i1 = Index::make_dual("ABC", "xyz");
        let i2 = Index::make_dual("ABC", "xyz");
        assert_eq!(i1, i2);
    }

    #[test]
    fn single_element_index_compare_inequality() {
        let i1 = Index::make_single("A00");
        let i2 = Index::make_single("A01");
        assert!(i1 < i2);

        let i1 = Index::make_single("i212");
        let i2 = Index::make_single("i222");
        assert!(i1 < i2);
    }

    /// As far as sorting goes, priority should be given to the first
    /// index (the start of the range).
    #[test]
    fn two_element_index_compare_inequality_first_element() {
        let i1 = Index::make_dual("A00", "Z00");
        let i2 = Index::make_dual("A01", "X00");
        assert!(i1 < i2);
    }

    #[test]
    fn two_element_index_compare_inequality_second_element() {
        let i1 = Index::make_dual("I00", "I01");
        let i2 = Index::make_dual("I00", "I02");
        assert!(i2 > i1);
    }

    #[test]
    fn check_codes_lie_in_index_range() {
        let i = Index::make_dual("I00", "I02");
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
    fn check_index_range_lies_above_codes() {
        let i = Index::make_dual("I00", "I02");
        // Check the upper boundary edge case
        let code = format!("h999");
        assert_eq!(i.compare(&code), Ordering::Greater);
        // Check internal code
        let code = format!("a001");
        assert_eq!(i.compare(&code), Ordering::Greater);
    }

    #[test]
    fn check_index_range_lies_below_codes() {
        let i = Index::make_dual("I00", "I02");
        // Check the lower boundary edge case
        let code = format!("i030");
        assert_eq!(i.compare(&code), Ordering::Less);
        // Check internal code
        let code = format!("z001");
        assert_eq!(i.compare(&code), Ordering::Less);
    }

}
