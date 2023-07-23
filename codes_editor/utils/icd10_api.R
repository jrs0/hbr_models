##' The functions in this file can be used to obtain a blank icd10
##' codes configuration file.

##' Get the authentication token for the WHO ICD API
##'
##' Call this function once to get the token, and then use it
##' in the icd10_api calls. To use this function, create
##' a file secret/icd10_cred.yaml in extdata, with credentials.
##' See the example file icd10_cred.yaml in extdata for the
##' template.
##'
##' Note: this function can be mocked for testing.
##'
##' @title Get the API token
##' @return The token (named list)
icd_api_token <- function(credential_path = "secret/icd10-cred.yaml")
{
    ## Authenticate the endpoint
    secret <- yaml::read_yaml(credential_path)

    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    payload <- c(secret, list
    (
        scope = 'icdapi_access',
        grant_type = 'client_credentials'
    ))
    token <- httr::POST(token_endpoint, body = payload)
    httr::content(token)
}

##' After authenticating, make a request to an API endpoint. Use
##'
##' Note: this function can be mocked for testing.
##'
##' @title Make a request to the WHO ICD API
##' @param token The authentication token (containing access_token key)
##' @param endpoint The URL endpoint
##' @param data A named list of the headers to send
##' @return A named list of the contents of the request
##'
icd_api_request <- function(token, endpoint, data = list())
{
    headers <-
        httr::add_headers(!!!data,
                          Authorization = paste0("Bearer ",token$access_token),
                          accept = "application/json",
                          `API-Version` = "v2",
                          `Accept-Language` = "en")

    xx <- httr::GET(url = endpoint, headers)
    if (xx$status == 401)
    {
        stop("401 returned; token invalid or expired.")
    }
    else if (xx$status == 404)
    {
        stop(paste0(xx$status, " returned; the endpoint '", endpoint, "' does not exist"))
    }
    else if (xx$status != 200)
    {
        stop(paste0(xx$status, " returned; unknown error."))
    }
    httr::content(xx)

}

icd_api_get_releases <- function(token) {
    endpoint <- "https://id.who.int/icd/release/10"
    icd_api_request(token, endpoint)
}

##' Use this function to automatically process the ICD-10 classifications into
##' a codes definition file that can be used to process diagnosis code columns.
##' This function uses the 2016 release of ICD-10.
##'
##' Use this function to get each chapter of the ICD codes, as a nested list
##' object. For now, getting each chapter separately is a better way to avoid
##' the token timing out. The results can be combined to form a full ICD-10
##' file.
##'
##' @title Generate a codes file from the ICD-10 API
##' @param token The access token obtained from icd_api_token
##' @param release The release year (default "2016"; Options "2019",
##' "2016", "2010", "2008")
##' @param item The item to retrieve; a string appended to the end of the
##' endpoint URL. This can be a chapter or a lower level item.
##' @param endpoint The endpoint URL to request. Generated from other arguments
##' if the endpoint is not provided.
##' @return A leaf or category object (named list)
##' @export
icd_api_get_codes <- function(token, release = "2016", item = "I",
                                endpoint = paste(root, release, item, sep = "/"))
{
    ## This is the base API url
    root <- "https://id.who.int/icd/release/10"

    res <- icd_api_request(token, endpoint)

    ## Each request returns a named list containing the contents of this
    ## level of the ICD hierarchy. The two most important fields are `@value`,
    ## (which is inside a key called `title`),
    ## which contains the text description of this level; and `child`, which
    ## is a list of ICD objects directly beneath this node in the tree. Each
    ## element of `child` is a URL endpoint, which can be used in another call
    ## to this function.
    ##
    ## At leaf nodes, the `child` key is missing. This signifies that the lowest
    ## level (a particular code) has been reached.
    ##
    ## If there is a code field, then it contains either a code range
    ## (e.g. I20-I25) for a non-leaf node, or it contains an ICD code
    ## (e.g. I22.0).
    ##
    ## Two other important keys, which are not currently used for anything,
    ## are the `inclusion` and `exclusion` lists for a particular node.

    if (is.null(res$child))
    {
        ## Then the current node is a leaf node. Return the map
        ## to be stored at the leaf level
        message("Fetched code '", res$code, "'")
        list(code = res$code,
             docs = res$title$`@value`)
    }
    else
    {
        ## Else, loop over the child nodes
        message("Descending into category '", res$code, "'")
        list(
            category = res$code,
            docs = res$title$`@value`,
            child = res$child %>%
                sapply(function(ep) {
                    list(icd_api_get_codes(token, endpoint = ep))
                })
        )
    }
}

##' Fetch all the ICD10 code chapters into separate files.
##'
##' The function outputs files of the form icd10_I.yaml
##' where I is replaced with the chapter number.
##'
##' @title Fetch ICD-10 codes
##' @param token The access token for the API
##' @param release The release year
##' @param dir Where to put the output files
##' @export
icd_api_fetch_all <- function(token, release = "2016", dir = ".")
{
    ## This is the base API url
    endpoint <- paste("https://id.who.int/icd/release/10",
                      release, sep="/")

    ## Fetch the chapter endpoints
    ch_ep <- icd_api_request(token, endpoint)$child
    ch_names <- ch_ep %>%
        purrr::map(~ strsplit(., "/") %>% unlist() %>% tail(n=1))

    ch_names %>%
        purrr::map(function(ch) {

            ep <- paste("https://id.who.int/icd/release/10",
                        release, ch, sep="/")
            val <- icd_api_get_codes(token, endpoint = ep)

            message("Writing codes to output file")
            if (!dir.exists(dir))
            {
                dir.create(dir)
            }

            filename <- paste0("/icd10_", ch, ".yaml")
            yaml::write_yaml(val, paste(dir, filename, sep="/"))
        })

}

##' Combine icd10_.yaml files into a single file
##'
##' @title Combine ICD-10 chapter files
##' @param dir Where to look for the files to combine
##' 
##' @export
##' 
icd_combine_files <- function(dir = system.file(folder, "icd10/", package="icdb"))
{
    files <- list.files(dir, pattern = "^icd10_(.)*.yaml$", full.names = TRUE)

    xx <- list(category = "ICD-10",
               docs = "ICD-10 codes, 2016 release",
               child = list())
    for (f in files)
    {
        yy <- yaml::read_yaml(f)
        xx$child <- c(xx$child, list(yy))
    }

    ## Write output file
    yaml::write_yaml(list(xx), paste(dir, "icd10.yaml", sep="/"))

}

##' To facilite searching for codes in the configuration
##' file, it is important for each object (category or code)
##' to store a range of codes that it contains. R supports
##' lexicographical comparison of characters by default,
##' so all that is required is to store a pair representing
##' the start of the range and the end of the range. This
##' function adds an index key to the structure passed as
##' the argument.
##'
##' The index key represents the first allowable code in
##' the category. This function replaces the code key in
##' the leaf nodes with an index, which contains the code
##' at that level.
##'
##' @title Index a codes definition structure
##' @return The codes structure with indices (a nested list)
##' @param codes The input nested list of codes
icd10_index_codes <- function(codes)
{
    ## For the new codes structure
    result <- list()
    
    for (object in codes)
    {
        if (!is.null(object$category))
        {
            ## Process the child objects
            object$child <- icd10_index_codes(object$child)

            ## Check if the category is a code range or
            ## a code, meaning it starts with a capital
            ## letter followed by a number, e.g.
            ## A00-A03 or I22. If the category is not
            ## in this form, then copy the value of
            ## the first index one level down (this
            ## is valid because of the order of evaulation
            ## of this function -- inside to out).
            if (grepl("[A-Z][0-9]", object$category))
            {
                ## Store the index as a range (start
                ## and end inclusive).
                object$index <- object$category %>%
                    stringr::str_split("-") %>%
                    unlist()
            }
            else
            {
                ## Object is a chapter. Copy the first
                ## index from one level down, using the
                ## start and end values for the range.

                ## Before doing that, the indexes must
                ## be sorted
                ## Get the sorted order of this level 
                k <- object$child %>%
                    ## Get the first value (the starting
                    ## value) of each range and sort
                    ## by that
                    purrr::map(~ .x$index[[1]]) %>%
                    unlist() %>%
                    order()

                ## Use the index k to reorder the level
                reordered <- object$child[k]

                ## Compute the range start and end based on the
                ## reordered list
                N <- length(reordered)
                object$index <- c(
                    ## Start of first range
                    reordered %>% purrr::chuck(1, "index", 1), 
                    ## End of last range
                    reordered %>%
                    purrr::chuck(N, "index", 2)
                )
            }


        }
        else if (!is.null(object$code))
        {
            object$index <- object$code %>%
                stringr::str_replace_all("\\.", "")
        }
        else
        {
            stop("Expected category or codes key in codes definition object")
        }

        result <- c(result, list(object))
    }

    ## Return the copy of the structure with indices
    result
}
