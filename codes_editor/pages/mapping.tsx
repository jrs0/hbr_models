import Link from 'next/link'

/* function Column({ col }) {
 *     return (
 *         <div>
 *             <div>Name: {col.name}</div>
 *             <div>Strategy: {col.strategy}</div>
 *             <div>Use: {col.use}</div>
 *             <div>Source columns</div>
 *             <ul>
 *                 {col.source_columns.map((scol) => (
 *                     <li>
 *                         <div>Name: {scol.name}</div>
 *                         <div>Docs: {scol.docs}</div>
 *                     </li>
 *                 ))}
 *             </ul>
 *         </div>
 *     )
 * }
 * 
 * function Table({ tab }) {
 *     return (
 *         <div>
 *             <div> Name: {tab.name} </div>
 *             <div> Docs: {tab.docs} </div>
 *             <div> Columns: </div>
 *             <ul>
 *                 {tab.columns.map((col) => (
 *                     <li>
 *                         <Column col={col} />
 *                     </li>
 *                 ))}
 *             </ul>
 *         </div>
 *     )
 * } */

export default function Home() {

    /* let def = [
     *     {
     *         name: "apc",
     *         source: "ABI.dbo.vw_APC_SEM_001",
     *         docs: "The SUS database contains hospital episode statistics, which contain records of patient care activities that take place in a hospital visit.",
     *         columns: [
     *             {
     *                 name: "nhs_number",
     *                 docs: "The NHS number identifies the patient. The field is anonymised.",
     *                 source_columns: [
     *                     {
     *                         name: "AIMTC_Pseudo_NHS",
     *                         docs: ""
     *                     },
     *                     {
     *                         name: "NHSnumber",
     *                         docs: "This one looks like it is NULL everywhere. Also, this is an INT column"
     *                     }
     *                 ],
     *                 strategy: "coalesce_exclude_null",
     *                 use: "yes"
     *             }
     *         ]
     *     },
     *     {
     *         name: "attr",
     *         docs: "The SWD attributes table contains records of patient attributes at the latest snapshot through the year (monthly updates), PLUS a few other measures such as 'air quality' that is NOT present in the activity history table (these additional measures is the only reason to keep a separate reference to this table, otherwise we could have just filter the activity history table by most recent).",
     *         source: "MODELLING_SQL_AREA.dbo.swd_attribute",
     *         columns: [
     *             {
     *                 name: "nhs_number",
     *                 docs: "The NHS number identifies the patient. The field is anonymised.",
     *                 source_columns: [
     *                     {
     *                         name: "AIMTC_Pseudo_NHS",
     *                         docs: ""
     *                     },
     *                     {
     *                         name: "NHSnumber",
     *                         docs: "This one looks like it is NULL everywhere. Also, this is an INT column"
     *                     }
     *                 ],
     *                 strategy: "coalesce_exclude_null",
     *                 use: "yes"
     *             }
     *         ]
     *     },
     * ]

     * return (
     *     <div>
     *         <Link href="/">Back</Link>
     *         <ul>
     *             {def.map((tab) => (
     *                 <li>
     *                     <Table tab={tab} />
     *                 </li>
     *             ))}
     *         </ul>
     *     </div>
     * ) */

    return <p>Todo</p>
}

