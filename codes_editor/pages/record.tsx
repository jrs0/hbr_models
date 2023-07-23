import { useState } from 'react';
import { invoke } from "@tauri-apps/api/tauri"
import Link from 'next/link'

import record_styles from '../styles/ClinicalCodeComp.module.css'
import styles from '../styles/Category.module.css'

import Collapsible from 'react-collapsible';
import InfiniteScroll from 'react-infinite-scroll-component';

import { parse_search_terms } from "../services/search_term"

interface EventCount {
    name: string,
    count: number,
}

interface Events {
    before: EventCount[],
    after: EventCount[],
}

interface Timestamp {
    timestamp: number,
    readable: string,
}

interface ClinicalCode {
    name: string
    docs: string
    groups: string[]
}

// From: https://stackoverflow.com/questions/60291002/
// can-typescript-restrict-keyof-to-a-list-of-properties-of-a-particular-type
// This type returns all keys that have a value of type string
type TypedKeyOf<KeyType, T> = {
    [K in keyof T]:
    T[K] extends KeyType ? K : never
}[keyof T]


function get_event_counts(events: Events, name: keyof Events) {
    if (name in events) {
	return events[name]
    } else {
	return []
    }
}

function EventCountBlock({ event_count_list }:
			 { event_count_list: EventCount[] }) {
    return <div>
	{event_count_list.map(event_count =>
	    <div key={event_count.name}>
		<b>{event_count.count}</b>
		{event_count.name}
	    </div>)}
    </div>
}

function EventCountComp({ events }: { events: Events }) {
    return <div className = {record_styles.event_count}>
	<b>Event Counts</b>
	<div>
	    <div className ={record_styles.side_by_side}>
		<b>Before</b>
		<EventCountBlock event_count_list={get_event_counts(events, "before")} />
	    </div>

	    <div className ={record_styles.side_by_side}>
		<b>After</b>
		<EventCountBlock event_count_list={get_event_counts(events, "after")} />	
	    </div>
	    </div>
	</div>
}

function clinical_code_groups(clinical_code: ClinicalCode) {
    if ("groups" in clinical_code) {
	return clinical_code.groups
    } else {
	return []
    }
}

function clinical_code_contains_group(clinical_code: ClinicalCode,
				      group_substring: string) {
    return clinical_code_groups(clinical_code).some(function(group) {
	return group.includes(group_substring)
    })
}

function ClinicalCodeComp({ clinical_code, group_style }:
			  { clinical_code: ClinicalCode,
			    group_style: string }) {

    return <span>
	{
	    clinical_code_groups(clinical_code).map(group =>
		<span
		    key={group}
		    className={`${record_styles.tag} ${record_styles[group_style]}`}>
		    {group}
		</span>)
	}
	<span className ={record_styles.tag}><b>{clinical_code.name}</b></span>
	<span>{clinical_code.docs}</span>
    </span>
}

interface Mortality {
    alive: boolean
    date_of_death: Timestamp
    cause_of_death: ClinicalCode
}

interface Episode {
    start_date: Timestamp,
    end_date: Timestamp,
    primary_diagnosis: ClinicalCode,
    primary_procedure: ClinicalCode,
    secondary_diagnoses: ClinicalCode[],
    secondary_procedures: ClinicalCode[],
}

function PrimaryClinicalCode(episode: Episode,
			     name: TypedKeyOf<ClinicalCode, Episode>,
			     group_style: string) {
    if (name in episode) {
	return <ClinicalCodeComp
		   clinical_code ={episode[name]}
		   group_style ={group_style} />
    } else {
	return <>
	    None
	</>
    }
}


function SecondaryClinicalCodes(episode: Episode,
				name: TypedKeyOf<ClinicalCode[], Episode>,
				group_style: string) {
    if (name in episode) {
	return <div>{episode[name].map(clinical_code =>
	    <div key={clinical_code.name}>
		<ClinicalCodeComp
		    clinical_code ={clinical_code}
		    group_style ={group_style} />
	    </div>
	    )}
	</div>
    } else {
	return <>
	    None
	</>
    }    
}

function get_optional_array<T extends object, K>(
    record: T,
    key: TypedKeyOf<ArrayLike<K>, T>) {
    if (key in record) {
	return record[key]
    } else {
	return []
    }
}

function append_to_set(set_to_modify: Set<string>,
		       set_to_append: ArrayLike<string> | Set<string>) {
    Array.from(set_to_append).forEach(item => set_to_modify.add(item))
}

function get_clinical_code_groups(episode: Episode, diagnosis: boolean) {
    let clinical_code_groups = new Set<string>()

    let primary: keyof Episode = "primary_procedure"
    let secondaries: keyof Episode = "secondary_procedures"
    if (diagnosis) {
	primary = "primary_diagnosis"
	secondaries = "secondary_diagnoses"
    }
    
    if (primary in episode) {
	let groups = get_optional_array(episode[primary], "groups")
	append_to_set(clinical_code_groups, groups)
    }
    get_optional_array(episode, secondaries)
	.map(clinical_code => {
	    let groups = get_optional_array(clinical_code, "groups")
	    append_to_set(clinical_code_groups, groups)
	})
    return clinical_code_groups
}

function episode_contains_clinical_code_group_anywhere(episode: Episode,
						       group: string) {
    if ("primary_diagnosis" in episode) {
	if (clinical_code_contains_group(episode.primary_diagnosis, group)) {
	    return true
	}
    }

    if ("primary_procedure" in episode) {
	if (clinical_code_contains_group(episode.primary_procedure, group)) {
	    return true
	}
    }

    if ("secondary_diagnoses" in episode) {
	const found_group = episode
	    .secondary_diagnoses
	    .some(function(code) {
		return clinical_code_contains_group(code, group)
	    })
	if (found_group) {
	    return true
	}
    }

    if ("secondary_procedures" in episode) {
	const found_group = episode
	    .secondary_procedures
	    .some(function(code) {
		return clinical_code_contains_group(code, group)
	    })
	if (found_group) {
	    return true
	}
    }
    return false
}

function ClinicalCodesBlock({ episode, diagnosis}:
			    { episode: Episode,
			      diagnosis: boolean }) {

    let block_title = "Procedures"
    let primary_name: keyof Episode = "primary_procedure"
    let secondary_name: keyof Episode = "secondary_procedures"
    let group_style = "procedure_group"
    if (diagnosis) {
	block_title = "Diagnoses"
	primary_name = "primary_diagnosis"
	secondary_name = "secondary_diagnoses"	
	group_style = "diagnosis_group"
    }

    return <div className = {record_styles.clinical_codes_block}>
	<b>{block_title}</b>
	<div>{PrimaryClinicalCode(episode, primary_name, group_style)}
	</div>
	<hr/>
	<div>{SecondaryClinicalCodes(episode, secondary_name, group_style)}
	</div>	
    </div>
}

function DiagnosisBlock({ episode }: { episode: Episode }) {
    return <ClinicalCodesBlock
	       episode={episode}
	       diagnosis = {true} />
}

function ProcedureBlock({ episode }: { episode: Episode }) {
    return <ClinicalCodesBlock episode={episode} diagnosis = {false} />
}

function EpisodeComp({ episode }: { episode: Episode }) {
    return <div className ={record_styles.episode}>
	<div>Episode start: <Date timestamp ={episode.start_date} /></div>
	<div>Episode end: <Date timestamp ={episode.end_date} /></div>
	<div>
	    <DiagnosisBlock episode={episode} />
	    <ProcedureBlock episode={episode} />
	</div>
    </div>
}

interface Spell {
    id: string,
    start_date: Timestamp,
    end_date: Timestamp,
    episodes: Episode[],
}

function SpellComp({ spell }: { spell: Spell }) {
    return <div className ={record_styles.spell}>
	<div>Spell id: {spell.id}</div>
	<div>Spell start: <Date timestamp ={spell.start_date} /></div>
	<div>Spell end: <Date timestamp ={spell.end_date} /></div>
	<div>Contains: {spell_contains_clinical_code_group_anywhere(spell, "acs_nstemi")}</div>
	<b>Episodes</b>
	{spell.episodes.map(episode =>
	    // Using this as a key is a bug, but episodes have no key yet
	    // so this is just a workaround. TO FIX!
	    <div key ={episode.start_date.timestamp}>
	    <EpisodeComp episode = {episode} />
	</div>)}
    </div>
}

function Date({ timestamp }: { timestamp: Timestamp }) {
    return <span>
	{timestamp.readable}
    </span>
}

interface AcsRecord {
    nhs_number: string,
    age_at_index: number,
    date_of_index: Timestamp,
    presentation: string,
    inclusion_trigger: string,
    index_spell: Spell,
    spells_after: Spell[],
    spells_before: Spell[],
    mortality: Mortality,
    event_counts: Events,
}

function Presentation({ record }: { record: AcsRecord }) {
    if (record.presentation === "STEMI") {
	return <span className = {`${record_styles.tag} ${record_styles.stemi}`}>
	    STEMI
	</span>
    } else {
	return <span className = {`${record_styles.tag} ${record_styles.nstemi}`}>
	    NSTEMI
	</span>
    }
}

function Trigger({ record }: { record: AcsRecord }) {
    if (record.inclusion_trigger === "ACS") {
	return <span className = {`${record_styles.tag} ${record_styles.acs}`}>
	    ACS
	</span>
    } else {
	return <span className = {`${record_styles.tag} ${record_styles.pci}`}>
	    PCI
	</span>
    }
}

function PatientInfo({ record }: { record: AcsRecord }) {
    return <div className ={record_styles.patient_info}>
	<b>Patient <Presentation record = {record} /><Trigger record={record} /> Age {record.age_at_index} -- Index date: <Date timestamp = {record.date_of_index} /> -- {record.nhs_number} </b>
    </div>
}

function get_cause_of_death(mortality: Mortality) {
    if ("cause_of_death" in mortality) {
	return <ClinicalCodeComp
		   clinical_code ={mortality.cause_of_death}
		   group_style ="diagnosis_group" />
    } else {
	return <span>Unknown</span>
    }
}

function Mortality({ mortality }: { mortality: Mortality }) {
    
    let alive = "Alive"
    if (mortality.alive) {
	return <div>
	    <b>Mortality</b>: Alive
	</div>
    } else {
	return <div>
	    <b>Mortality</b>:
	       {get_cause_of_death(mortality)}
	       (<Date timestamp = {mortality.date_of_death} />)
	</div>
    }
}

function CollapsibleTrigger({ name }: { name: string }) {
    return <div className = {record_styles.collapsible_trigger}>
	{name}
    </div>
}

function get_all_clinical_code_groups(spell: Spell, diagnosis: boolean) {
    let clinical_code_groups = new Set<string>()
    if ("episodes" in spell) {
	spell.episodes
	     .map(episode => {
		 let episode_groups = get_clinical_code_groups(episode,
							       diagnosis)
		 append_to_set(clinical_code_groups, episode_groups)
	     })
    }
    return clinical_code_groups
    
}

function IndexSpellSummary({ index_spell }: { index_spell: Spell }) {
    return <div className = {record_styles.collapsible_trigger}>
    Index Spell: {
	Array.from(get_all_clinical_code_groups(index_spell, true))
	     .map(group => <span
			       key ={group}
			       className={`${record_styles.tag} ${record_styles.diagnosis_group}`}>
		 {group}
	     </span>)
    }
    {
	Array.from(get_all_clinical_code_groups(index_spell, false))
	     .map(group => <span
			       key ={group}
			       className={`${record_styles.tag} ${record_styles.procedure_group}`}>
		 {group}
	     </span>)
    }
    </div>
}

function AcsRecordComp({ record } : { record: AcsRecord }) {
    let spells_after_key: keyof AcsRecord = "spells_after";
    let spells_before_key: keyof AcsRecord = "spells_before";
    return <div  className ={record_styles.record}>
    <PatientInfo record = {record} />
    <Mortality mortality = {record.mortality} />
    <Collapsible
	className ={record_styles.collapsible}
		   contentInnerClassName={record_styles.collapsible_content_inner}
		   trigger=<CollapsibleTrigger name="Event Counts" />
	lazyRender={true}>
	<EventCountComp events ={record.event_counts} />
    </Collapsible>
    <Collapsible
	trigger=<IndexSpellSummary index_spell ={record.index_spell} />
	contentInnerClassName={record_styles.collapsible_content_inner}
	lazyRender={true}>
	<SpellComp spell = {record.index_spell} />
    </Collapsible>
    <Collapsible
	trigger=<CollapsibleTrigger name="Spells After" />
	contentInnerClassName={record_styles.collapsible_content_inner}
	lazyRender={true}>
	<div> {
	    get_optional_array<AcsRecord, Spell>(record,
						 spells_after_key)
		.map(spell =>
		    <SpellComp
			key={spell.id}
			spell = {spell} />
		)
	} </div>
    </Collapsible>
    <Collapsible
	trigger=<CollapsibleTrigger name="Spells Before" />
	contentInnerClassName={record_styles.collapsible_content_inner}
	lazyRender={true}>
	<div> {
	    get_optional_array<AcsRecord, Spell>(record,
						 spells_before_key)
		.map(spell =>
		    <SpellComp
			key ={spell.id}
			spell = {spell} />
		)
	} </div>	    
    </Collapsible>	
    </div>
}

function spell_contains_clinical_code_group_anywhere(spell: Spell,
						     group: string) {
    return spell.episodes.some(function(episode) {
	return episode_contains_clinical_code_group_anywhere(episode, group)
    })
}

function contains_clinical_code_group_anywhere(record: AcsRecord,
					       group: string) {
    if (spell_contains_clinical_code_group_anywhere(record.index_spell,
						    group)) {
	return true
    }


    let spells_after_key: keyof AcsRecord = "spells_after";
    let found = get_optional_array<AcsRecord, Spell>(record,
						     spells_after_key)
	.some(function(spell) {
	    return spell_contains_clinical_code_group_anywhere(spell, group)
	})
    if (found) {
	return true
    }

    let spells_before_key: keyof AcsRecord = "spells_before";
    found = get_optional_array<AcsRecord, Spell>(record,
						 spells_before_key)
	.some(function(spell) {
	    return spell_contains_clinical_code_group_anywhere(spell, group)
	})
    if (found) {
	return true
    }

    return false
}

export default function Home() {

    let [acs_records, setAcsRecords] = useState<AcsRecord[]>([]);
    
    const [searchTerm, setSearchTerm] = useState('');

    const [displayLimit, setDisplayLimit] = useState(20);
    const [hasMore, setHasMore] = useState(true);
    
    const handleChange = (event: React.ChangeEvent<any>) => {
	setDisplayLimit(20)
	setHasMore(true)
	setSearchTerm(event.target.value);
    };

    function fetchData(searched_records_length: number) {
	setDisplayLimit(displayLimit + 20)
	if (displayLimit > searched_records_length) {
	    setHasMore(false)
	}
	console.log("Fetching more ", hasMore, displayLimit)
    }

    
    // Function to load the codes yaml file
    function load_file() {
        invoke('get_yaml')
	    .then((result) => {

		// From rust
		let acs_records: AcsRecord[] = JSON.parse(result as string);
		setAcsRecords(acs_records);
		console.log("Done reading file")
	    })
    }

    function make_record_components(records: AcsRecord[]) {
	return <div>
	    {records.map(record =>
		<AcsRecordComp
		    key={record.index_spell.id}
		    record = {record} />)}
	</div>
    }

    
    if (acs_records.length == 0) {
	return <div>
            <h1>Patient ACS/PCI Record Viewer</h1>
	    <p className={styles.info}>Load a records file.</p>
	    <div>
		<span className={styles.button}
		      onClick={load_file}>Load file</span>
		<Link className={styles.button} href="/">Back</Link>
	    </div>
	</div>
    } else {

	let { include_groups, exclude_groups } = parse_search_terms(searchTerm);
	
	console.log("include", include_groups)
	console.log("exclude", exclude_groups)

	
	const searched_records = acs_records.filter(function(record) {

	    if (searchTerm == "") {
		return true;
	    }
	    
	    let included_groups_anywhere = include_groups
		.every(function(group) {
		    return contains_clinical_code_group_anywhere(record,
								 group)
		})
	    
	    let excluded_groups_nowhere =
		exclude_groups.every(function(group) {
		    return !contains_clinical_code_group_anywhere(record,
								  group)
		})

	    return included_groups_anywhere && excluded_groups_nowhere

	    
	});
	
	const top_searched_records = searched_records.slice(0, displayLimit)
	
	return <div>
	    <label htmlFor="search">Search clinical code groups: </label>
	    <input id="search" type="text" onChange={handleChange}/>
	    <div>Total number of records: {searched_records.length}</div>
	    <hr />
	    
	    <InfiniteScroll
		dataLength={top_searched_records.length}
		next={() => fetchData(searched_records.length)}
		hasMore={hasMore}
		loader={<h4>Loading...</h4>}
		endMessage={
		    <p style={{ textAlign: 'center' }}>
			<b>You have seen all records!</b>
		    </p>
		}
	    >
		{make_record_components(top_searched_records)}
	    </InfiniteScroll>
	</div>
    }
}
