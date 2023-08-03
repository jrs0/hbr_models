library(tidyverse)
library(glmnet)

data(QuickStartExample)
x <- QuickStartExample$x
y <- QuickStartExample$y

fit <- glmnet(x, y)
fit

plot(fit, label = TRUE)
