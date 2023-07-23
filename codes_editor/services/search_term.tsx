/**
 * \brief Parse a simple space-separated list of search terms
 *
 * The format is "term1, term2, !term3, term4", where ! means
 * a term will be excluded. The list is split on comma [,],
 * and leading and trailing whitespace is removed from the tokens.
 * This allows space to be used as part of the search terms
 * (important for clinical code descriptions).
 *
 * The terms with and without ! are returned separately
 * (with the ! removed)
 *
 */
export function parse_search_terms(searchTerm: string) {

    if (searchTerm.length === 0) {
	return {
	    include_groups: [],
	    exclude_groups: [],
	}
    }
    
    const individual_search_terms = searchTerm
	.toLowerCase()
	.split(/,/)
	.map(token => token.trim())
	.filter(token => token.length !== 0)

    
    let include_groups = individual_search_terms
	.filter(function(term) {
	    return term.charAt(0) !== "!"
	})
    
    let exclude_groups = individual_search_terms
	.filter(function(term) {
	    return term.charAt(0) === "!"
	}).map(function(term) {
	    return term.replace("!", '')
	})
    
    return {
	include_groups: include_groups,
	exclude_groups: exclude_groups
    }
}
