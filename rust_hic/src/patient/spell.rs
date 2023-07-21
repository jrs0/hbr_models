//! Hospital Spell struct
//! 
//! In hospital episode statistics, a spell is a group of episodes
//! which represent one patient visit to a hospital. Each episode is
//! associated with a consultant, and contains a list of diagnoses and 
//! procedures. The use of "code" below means a diagnosis or procedure
//! code.
//! 
//! A spell has a start and an end date, and a list of episodes. Operations
//! on a spell include:
//! * finding whether any episode contains a particular code,
//!   or a code in a group.
//! * getting the set of all diagnosis or procedure codes that 
//!   occurred in the spell (as a flat list).
//! * finding "important" codes (by some criterion)
//! * getting the number of episodes
//! * getting the duration of the spell (either by spell data,
//!   or by looking at the episode start/end dates)
//! 
//! It is also possible to generate a random spell. This contains randomly
//! generated episodes, which contain random data, subject to the
//! constraints that the episodes occur within the spell timeframe.
//! 

use serde::{Serialize, Deserialize};
use episode::Episode;
use chrono::Utc;
use rand_chacha::ChaCha8RNg;

mod episode;

#[derive(Serialize, Deserialize, Debug)]
pub struct Spell {
    #[serde(with = "bson::serde_helpers::chrono_datetime_as_bson_datetime")]
    start: chrono::DateTime<Utc>,
    #[serde(with = "bson::serde_helpers::chrono_datetime_as_bson_datetime")]
    end: chrono::DateTime<Utc>,
    episodes: Option<Vec<Episode>>,
}

impl Spell {
    // TODO: put useful spell-level functions here
}

/// Create a random spell
/// 
/// 
fn make_random_spell(rng: &mut ChaCha8Rng) {

}
