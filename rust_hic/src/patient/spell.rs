use serde::{Serialize, Deserialize};
use episode::Episode;
use chrono::Utc;

mod episode;

#[derive(Serialize, Deserialize, Debug)]
pub struct Spell {
    #[serde(with = "bson::serde_helpers::chrono_datetime_as_bson_datetime")]
    start: chrono::DateTime<Utc>,
    #[serde(with = "bson::serde_helpers::chrono_datetime_as_bson_datetime")]
    end: chrono::DateTime<Utc>,
    episodes: Option<Vec<Episode>>,
}
