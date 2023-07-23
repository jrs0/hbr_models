import { useState, useRef, useEffect, useMemo, ChangeEvent } from 'react';
import { invoke } from "@tauri-apps/api/tauri"
import Link from 'next/link'

import Collapsible from 'react-collapsible';

import styles from '../styles/Category.module.css'
import record_styles from '../styles/ClinicalCodeComp.module.css'

import { parse_search_terms } from "../services/search_term"

// Information for the tick box that selects categories or codes
interface CategorySelector {
    checked: boolean;
    onChange: () => void;
}

function Checkbox({ checked, onChange }: CategorySelector) {
    const checkboxRef = useRef<HTMLInputElement>(null);
    return <input
                ref={checkboxRef}
                type="checkbox"
                checked={checked}
                onChange={onChange} />
};

interface HighlightCounts {
    total_included: number,
    total_highlighted: number,
    included_highlighted: number,
}

interface Category {
    name: string,
    docs: string,
    index: string,
    categories: Category[],
    exclude?: string[],
    highlight?: boolean,
    counts?: HighlightCounts,
}

interface TopLevelCategory {
    categories: Category[]
    groups: string[]
    highlight?: boolean,
    counts?: HighlightCounts,
}

function is_leaf(category: Category | TopLevelCategory) {
    return category.categories === undefined
}

function append_group_to_exclude_list(category: Category, group: string) {
    if (category.exclude !== undefined) {
        category.exclude.push(group)
    } else {
        category.exclude = [group]
    }
}

function remove_group_from_exclude_list(category: Category, group: string) {
    if (category.exclude !== undefined) {
	const index = category.exclude.indexOf(group);
        if (index > -1) {
            category.exclude.splice(index, 1);
        }
	if (category.exclude.length == 0) {
	    delete category.exclude
	}	
    }
}

function has_group_in_exclude_list(category: Category | TopLevelCategory, group: string) {
    return ("exclude" in category) && (category.exclude !== undefined)
	&& category.exclude.includes(group);
}

function is_excluded(category: Category | TopLevelCategory, group: string, parent_excluded: boolean) {
    return has_group_in_exclude_list(category, group) || parent_excluded
}

function is_included(category: Category | TopLevelCategory, group: string, parent_excluded: boolean) {
    return !is_excluded(category, group, parent_excluded)
}

function sub_categories(category: Category | TopLevelCategory) {
    
    if (!is_leaf(category)) {
	return category.categories
    } else {
	return []
    }
}

/// Remove a group from the exclude key list of a category and
/// all its sub categories
function remove_group_exclude_from_sub_tree(category: Category, group: string) {
    remove_group_from_exclude_list(category, group)
    sub_categories(category).map(sub_category =>
	remove_group_exclude_from_sub_tree(sub_category, group))
}

interface CategoryData {
    index: number, // Where is this category in the parent child list
    category: Category, // The data for this category
    parent_excluded: boolean, // Whether the parent is excluded
    toggle_cat: (indices: number[],
		 included: boolean) => void, // Callback to enable/disable
    group: string, // The currently selected group
}

function CategoryHeader({ category }: { category: Category }) {
    return <span className={styles.category_row}>
	<span className={styles.category_name}>
	    {category.name}
	</span>
	<span className={styles.category_desc}>
	    {category.docs}
	</span>
    </span>
}


interface SearchTerms {
    include_groups: string[],
    exclude_groups: string[],
}

function matches_search_terms(lower_case_string: string, search_terms: SearchTerms) {

    if (search_terms.include_groups.length === 0
	&& search_terms.exclude_groups.length === 0) {
	return false
    }
    
    const any_included_term = search_terms
	.include_groups
	.map(term => lower_case_string.includes(term))
	.some(Boolean)
    
    const no_excluded_terms = search_terms
	.exclude_groups
	.map(term => !lower_case_string.includes(term))
	.every(Boolean)

    return any_included_term && no_excluded_terms
}

function name_contains_match(category: Category | TopLevelCategory, search_terms: SearchTerms) {
    if ("name" in category) {
	const name_string = category.name.toLowerCase()
	return matches_search_terms(name_string, search_terms)
    } else {
	return false
    }
}

function docs_contains_match(category: Category | TopLevelCategory, search_terms: SearchTerms) {
    if ("docs" in category) {
	const docs_string = category.docs.toLowerCase()
	return matches_search_terms(docs_string, search_terms)
    } else {
	return false
    }
}

function is_highlighted(category: Category | TopLevelCategory) {
    return category.highlight === true
}

function CategoryElem({ index, category, parent_excluded,
			toggle_cat, group }: CategoryData) {
    
    const [hidden, setHidden] = useState(true)
    
    const included = is_included(category, group, parent_excluded)
    const excluded = is_excluded(category, group, parent_excluded)
    
    function handleChange() {
        toggle_cat([index], included)
    }
    
    function toggle_cat_sub(indices: number[], included: boolean) {
        let new_indices = [index].concat(indices)
        toggle_cat(new_indices, included)
    }

    let classname;
    let style;
    if (is_highlighted(category)) {
	if (category.counts !== undefined) {
	    const counts = category.counts
	    const change = 100 * counts.included_highlighted / counts.total_highlighted
	    style = { "--change": `${change}%` } as React.CSSProperties
	    classname = styles.highlighted
	}
    }
    
    if (is_leaf(category)) {
	return <div className ={classname} style={style}>
	    <Checkbox checked={included}
		      onChange={handleChange} />
	    <span>
		<span className={styles.category_name}>
		    {category.name}
		</span>
		<span className={styles.category_desc}>
		    {category.docs}
		</span>
	    </span>
	</div>	
    } else {	
	return <div>
	    <div className ={classname} style={style}>
		<span className={styles.checkbox}>
		    <Checkbox checked={included}
			      onChange={handleChange} />
		</span>
		<span className={styles.category_header}
		      onClick={() => setHidden(!hidden)}>
		    <CategoryHeader category={category} />
		</span>
	    </div>
	    <ol className={styles.category_list}> {
		category.categories.map((node,index) => {
		    if (!hidden) {
			return <li key={node.index}>
			    <CategoryElem index={index}
					  category={node}
					  parent_excluded={!included}
					  toggle_cat={toggle_cat_sub}
					  group={group} />
			</li>
		    }
		})
	    } </ol>
	</div>
    }
}

function get_category_ref(top_level_category: TopLevelCategory, indices: number[]) {

    // Get the first category as a special case (convert from top level
    // category to plain category)
    let category = top_level_category.categories[indices[0]];
    indices.slice(1).forEach((n) => {
	if (!is_leaf(category)) {
	    category = category.categories[n]
	} else {
	    throw new Error("Expected to find a category in get_category_ref() (wrong indices?)");
	}
    })
    return category;
}

function first_super_category_excluding_group(top_level_category: TopLevelCategory, category_indices: number[], group: string) {
    let indices_copy = category_indices.slice()
    while (true) {
	let category = get_category_ref(top_level_category, indices_copy)
	if (has_group_in_exclude_list(category, group)) {
	    break;
	}
	indices_copy.pop()
    }
    return indices_copy
}

function exclude_all_sub_categories_except_nth(category: Category, n: number, group: string) {
    sub_categories(category)
	.map((sub_category, index) => {
	    if (index != n) {
		append_group_to_exclude_list(sub_category, group)
	    }
	})
}

function make_include_path_to_sub_category(super_category: Category, relative_indices: number[], group: string) {
    remove_group_from_exclude_list(super_category, group)
    let category = super_category
    relative_indices.forEach((n) => {
	exclude_all_sub_categories_except_nth(category, n, group)
        category = sub_categories(category)[n]
    })
}

function include_subtree_in_group(top_level_category: TopLevelCategory, category_indices: number[], group: string) {
    const super_category_indices =
	first_super_category_excluding_group(top_level_category,
					     category_indices,
					     group)
    let relative_indices =
	category_indices.slice(super_category_indices.length)
    const super_category = get_category_ref(top_level_category,
					    super_category_indices)
    make_include_path_to_sub_category(super_category, relative_indices, group)
}

function exclude_subtree_from_group(category: Category, group: string) {
    remove_group_exclude_from_sub_tree(category, group)
    append_group_to_exclude_list(category, group)
}

function add_highlight_key(category: TopLevelCategory | Category) {
    category.highlight = true
}

function remove_highlight_key(category: TopLevelCategory | Category) {
    delete category.highlight
}

function add_category_highlights(category: Category | TopLevelCategory,
				 search_terms: SearchTerms): boolean {
    
    let highlighted = false
    if (is_leaf(category)) {
	highlighted = name_contains_match(category, search_terms)
		   || docs_contains_match(category, search_terms)
    } else {
	highlighted = sub_categories(category)
	    .map(sub_category => add_category_highlights(sub_category, search_terms))
	    .some(Boolean)
    }
    if (highlighted) {
	add_highlight_key(category)
    } else {
	remove_highlight_key(category)
    }
    return highlighted
}

function strip_highlight_counts(category: Category | TopLevelCategory) {
    delete category.counts
    if (!is_leaf(category)) {
	sub_categories(category)
		       .map(strip_highlight_counts)
    }
}

function strip_highlight_keys(category: Category | TopLevelCategory) {
    delete category.highlight
    if (!is_leaf(category)) {
	sub_categories(category)
	    .map(strip_highlight_keys)
    }
}

function add_highlight_counts(a: HighlightCounts, b: HighlightCounts) {
    return {
	total_included: a.total_included + b.total_included,
	total_highlighted: a.total_highlighted + b.total_highlighted,
	included_highlighted: a.included_highlighted + b.included_highlighted,
    }
}

function count_highlighted_leaves(category: Category | TopLevelCategory, group: string, parent_excluded: boolean): HighlightCounts {
    let category_is_included = is_included(category, group, parent_excluded)
    if (is_leaf(category)) {
	category.counts = {
	    total_included: 0,
	    total_highlighted: 0,
	    included_highlighted: 0,
	}
	if (category_is_included) {
	    category.counts.total_included = 1
	}
	if (is_highlighted(category)) {
	    category.counts.total_highlighted = 1
	    if (category_is_included) {
		category.counts.included_highlighted = 1
	    }
	}
    } else {
	category.counts = sub_categories(category)
	    .map(sub_category => (
		count_highlighted_leaves(
		    sub_category,
		    group,
		    !category_is_included
		)))
	    .reduce(add_highlight_counts, {
		total_included: 0,
		total_highlighted: 0,
		included_highlighted: 0,		
	    })
    }
    return category.counts
}

export default function Home() {

    let [top_level_category, setTopLevelCategory] = useState<TopLevelCategory>({categories: [], groups: []});
    const [searchTerm, setSearchTerm] = useState('');
    
    function save_file() {
	const top_level_category_copy = structuredClone(top_level_category);
	strip_highlight_counts(top_level_category_copy)
	strip_highlight_keys(top_level_category_copy)
	console.log(top_level_category_copy)
        invoke('save_yaml', {
	    topLevelCategory: top_level_category_copy
	})
    }

    function get_groups() {
	if (top_level_category.groups.length != 0) {
            return top_level_category.groups
	} else {
	    throw new Error("There are no groups in the current top level category");
	}
    }

    // State for the current group
    // BUG: not starting with the correct
    // group, because it needs to be set
    // when the file is loaded.
    const [group, setGroup] = useState("");

    let open = false;
    if(searchTerm.length > 0) {
	open = true;
    }
    
    // Function to load the codes yaml file
    function load_file() {
        invoke('get_yaml')
	    .then((result) => {

		// From rust
		let res: TopLevelCategory = JSON.parse(result as string);
		
		// Currently just a quick hack to avoid crashing if
		// the user closes the dialog box
		// Note: all .then are executed
		// asynchronously, so put
		// sequential steps in here
		if (res.groups !== undefined) {
		    if (res.groups.length > 0) {
			setGroup(res.groups[0])
		    } else {
			alert("No groups found. Add some groups and reload the file.")
			return
		    }
		} else {
		    alert("Did not find groups key. Add a groups key containing an array of groups.")
		    return
		}
		// If you get here, then the state is valid
		setTopLevelCategory(res)
	    })
    }

    const handleGroupChange = (event: ChangeEvent<HTMLSelectElement>) => {
        setGroup(event.target.value);
    };

    const handleSearchTermChange = (event: React.ChangeEvent<any>) => {
	const search_term = event.target.value
	setSearchTerm(search_term);
    };
    
    function toggle_cat(indices: number[], included: boolean) {
        let top_level_category_copy = structuredClone(top_level_category);
        let category = get_category_ref(top_level_category_copy, indices)
        if (included) {
	    exclude_subtree_from_group(category, group)
        } else {
	    include_subtree_in_group(top_level_category_copy,
				     indices, group)
        }
        setTopLevelCategory(top_level_category_copy)
    }

    const parsed_search_terms = parse_search_terms(searchTerm)
    add_category_highlights(top_level_category, parsed_search_terms)

    const counts = count_highlighted_leaves(top_level_category, group, false)
    
    // TODO: Currently using the length of the categories array
    // as a proxy for whether the file is loaded. Fix.
    if (top_level_category.categories.length == 0) {
        return <div>
            <h1>Code Group Editor</h1>
	    <p className={styles.info}>Load a codes file to define groups of codes</p>
	    <div>
		<span className={styles.button}
		      onClick={load_file}>Load file</span>
		<Link className={styles.button} href="/">Back</Link>
	    </div>
	</div>
    } else {
        return <div>
            <h1>Code Group Editor</h1>
	    <p className={styles.info}>Use the groups selector to pick a group, and then use the checkboxes to include or exclude categories or codes from the group. When you are finished, save the resulting groups to a file.</p>
	    <div>
		<span className={styles.button}
	onClick={save_file}>Save as</span>
	<Link className={styles.button} href="/">Back</Link>
	</div>
	<div className={styles.groups}>
	    <div>
		Specify comma-separated phrases to search code names and descriptions. Input strings are case insensitive, and can include spaces, but only matches for the whole string are highlighted. Codes are highlighted on matching any of the search strings, and categories are highlighted if they contain a highlighted code anywhere.
	    </div>
	    <label htmlFor="search">Search: </label>
	    <input autoComplete="off" id="search" type="text" onChange={handleSearchTermChange}/>
	</div>
	<b>{counts.total_highlighted}</b> highlighted by search, with <b>{counts.included_highlighted}</b> of these included in <b>{group}</b> group
	<div>
	</div>
	<div className={styles.groups}>
	    Groups: <select onChange={handleGroupChange}> {
		get_groups().map((grp) => (
		    <option key={grp}>{grp}</option>
		))
	    } </select>
	    <div>
		<b>{group}</b> group includes <b>{counts.total_included}</b> codes in total
	    </div>
	</div>

	<ol className={styles.category_list}> {
	    top_level_category.categories.map((node,index) => {
		return <li key={node.index}>
		    <CategoryElem index={index}
				  category={node}
				  parent_excluded={false}
				  toggle_cat={toggle_cat}
				  group={group}
		    />
		</li>
	    })
	} </ol>
	</div>
	
    }
}
