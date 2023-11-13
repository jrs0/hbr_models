use blake2::{Blake2b512, Digest};
use rand_chacha::ChaCha8Rng;
use rand::SeedableRng;

/// Make a random number generator from a global seed
/// and a string id. 
/// 
/// The global seed is a single piece of information intended
/// to control all randomness in the program. However, in order
/// to be able to create multiple random number generators for
/// different bits of the program (i.e. one for picking clinical
/// codes, another for generating synthetic data, etc.) a unique
/// string id is passed to make the resulting random number
/// generator different from the others.
/// 
/// It is up to the user of the function to ensure that on id
/// is used more than once with the same global seed( unless the 
/// same random numbers are desired).
/// 
/// The id concatenated with the global
/// seed and the result is hashed. The resulting hash 
/// seeds the random number generator.
/// 
pub fn make_rng(global_seed: u64, id: &str) -> ChaCha8Rng {
    let message = format!("{id}{global_seed}");
    let mut hasher = Blake2b512::new();
    hasher.update(message);
    let seed = hasher.finalize()[0..32]
        .try_into()
        .expect("Unexpectedly failed to obtain correct-length slice");
    ChaCha8Rng::from_seed(seed)
}