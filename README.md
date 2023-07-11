# ARC-HBR from HIC Data

This repository contains an implementation of the ARC HBR (academic research consortium high bleeding risk) score using data from the health informatics collaborative (HIC) cardiovascular data. 

Real-world hospital dataset are not designed with the calculation of particular clinical risk scores in mind. As a result, data required for a risk score such as ARC-HBR may not be present in the data, or data may need to be modified, combined, or otherwise preprocessed in order to obtain inputs for the score. 

To use these datasets as the basis for a clinically useful tool, it must be possible to 
1. Develop models in a exploratory/prototyping context (e.g. using R or python), to assess the utility of the information in the dataset.
2. Be able, in principle, to translate the models into a form that can be deployed in a clinical context.

The goal of this repository is to present a common code base that can be used for step 1, and also provides a route for step 2 by making a core part of the preprocessing code usable as the prototype or initial basis for a deployed tool. The intention is to try to minimise the differences between the data used for model development and the data that would be used in a deployed tool.

Although the repository is a calculation of the ARC-HBR score, the intention is to create a framework flexible enough for developing other models for the prediction of bleeding and ischaemic risk in patients with acute coronary syndromes.

## Overall Structure

The purpose of the code is to place a layer between the raw data source and the risk-score calculation code. This decouples the risk-score calculation (and other modelling) from the structure of the original data source. This way, the risk-score calculation and any other models can be based on an input data source whose fields are exactly defined by a specification.

The conversion of the raw data source into this specified format is referred to here as preprocessing. The preprocessing steps can be documented and tested, and then reused if they are appropriate in the deployed context. The strict separation of the preprocessing allows independent testing and validation of the the model/risk-score development code, and focuses the validation of a prospective deployment to whether or not sufficiently good preprocessing can be achieved that meets the data source specification.

A specification for data source is contained in [Specification](specification.md). 