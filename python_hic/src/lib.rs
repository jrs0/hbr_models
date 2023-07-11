use pyo3::prelude::*;
use synth_data

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn make_data_example() -> PyResult {
    
    OK(())
}

/// A Python module implemented in Rust.
#[pymodule]
fn python_hic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(make_data_example, m)?)?;
    Ok(())
}