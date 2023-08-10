# Prototype Scripts

Good R mirrors for using in UHVW (the last one works best):
* http://cran.us.r-project.org
* http://lib.stat.cmu.edu/R/CRAN/
* https://pbil.univ-lyon1.fr/CRAN/

Always install R packages with a command like:

```r
install.packages("rextendr", repos = "https://pbil.univ-lyon1.fr/CRAN/")
```

## Design of R scripts

The prototype R scripts in this folder are written using a consistent method in an attempt to make them easier to understand and check. The following guidelines have been followed:

* As far as possible, the same column names have been used for the same things across the scripts. Sometimes this entails renaming something in a script that looks pointless (e.g. "spell_time" to "spell_date"), but it was thought that consistency across the scripts would be more helpful than consistency with the original column names in the data sources.
* Tables used as intermediate calculations have been kept as small as possible, and as normalised as possible (a single key links all the tables, and tables contain ideally non-overlapping non-primary-key columns). The following pattern has been adopted for calculating intermediate tables:
    * Left-join together previous tables to obtain the information required
    * Perform calculations, and then select only the columns that provide the new information, discarding those that duplicate information in previous tables. These steps are often combined using `transmute`, which performs a mutate-and-select in the same step. This attempts to make the new table independent of previous ones.
* Any column that is used as a primary key for joining ends in "_id". No other column name ends in "_id".
