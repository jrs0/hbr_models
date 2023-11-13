//! Generic information used across the different synthetic data, such as the
//! subject (patient id), which is present in all tables.

use rand::prelude::*;
use rand_chacha::ChaCha8Rng;

pub enum Gender {
    Female,
    Male,
}

/// Generate a patient id for the pathology_blood table (format "bristol_nnnn")
pub fn make_subject(rng: &mut ChaCha8Rng) -> String {
    let patient_id = rng.gen_range(1..=50000);
    format! {"bristol_{patient_id}"}
}

/// Pick gender uniform randomly (only male or female)
pub fn make_gender(rng: &mut ChaCha8Rng) -> Gender {
    if rng.gen() {
        Gender::Female
    } else {
        Gender::Male
    }
}