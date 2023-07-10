# Testing Plan

All code that preprocesses data will be tested on synthetic data, that matches the form of the real data (both the schema and the characteristics of the data found in the columns).

Synthetic data will not be stored in the repository. Instead, it will be generated using a seed. This keeps the repository itself lightweight, while enabling extensive testing both locally and in CI using potentially large testing sets.

This file describes the specification of the synthetic data sources that are used as part of the testing.

