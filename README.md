# ARC-HBR from HIC Data

This repository contains an implementation of the ARC-HBR (academic research consortium high bleeding risk) score using data from the health informatics collaborative (HIC) cardiovascular data.

Real-world hospital dataset are not designed with the calculation of particular clinical risk scores in mind. As a result, data required for a risk score such as ARC-HBR may not be present in the data, or data may need to be modified, combined, or otherwise preprocessed in order to obtain inputs for the score. 

To use these datasets as the basis for a clinically useful tool, it must be possible to 
1. Develop models in a exploratory/prototyping context (e.g. using R or python), to assess the utility of the information in the dataset.
2. Be able to translate the models into a form that can be deployed in a clinical context.

The goal of this repository is to present a common code base that can be used for step 1, and also provides a route for step 2 by making a core part of the preprocessing code usable as the prototype or initial basis for a deployed tool. 

The combination of steps 1 and 2 has multiple benefits:
* Emphasis on testing and careful documentation is present also for step 1, as it would be for the development of a deployed software product, which will improve the reliability of the data analysis.
* If step 1 is successful, and good models are found that should ideally be deployed, then less effort is required to port the code to the deployment context.
* If the preprocessing steps are complicated, there is assurance (due to the tests and documentation) that new code developed for the deployment context will do the same thing as the prototype code.

A concrete specification for the code is contained in [Specification](`1_specification.md`). 