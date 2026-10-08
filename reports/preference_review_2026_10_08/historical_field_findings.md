# Historical continuing-field recovery

The restoration workspace contains VEC_2022_DISTRIBUTIONS_LONG.csv and its compiler output VEC_2022_CATEGORY_FLOWS_LONG.csv. The compiler maintains an explicit active candidate set, derives AliveSetAfter at each category exit and tracks primary-origin parcels proportionally through candidate transfers. This is stronger field metadata than inferring recipients from positive percentages. It remains reconstructed category-origin evidence, not full ballot rankings or proof of legacy manual-row provenance.

Candidate-name/category joins against the testing workspace show zero classification mismatches. The extracted file covers 88 districts and 250 category-exit fields. Of 440 legacy non-ON rows, 244 are nonempty; 243 nonempty rows have an extracted category-exit field, and two empty Narracan rows also have extracted fields. Five extracted ON category exits are outside the legacy five-party row inventory.

Among 1,048 legacy off-diagonal zero cells: 259 lie outside an available extracted continuing field; 13 lie inside that field, and every one of those 13 has positive allocated votes in the extraction; 776 belong to rows without an extracted category-exit field. The last group includes finalists and absent categories and must not automatically be called missing evidence.

Five nonempty legacy rows have positive destinations outside the corresponding extracted field: IND in Morwell, Bendigo East and Macedon (OTH destination), and OTH in Melton and South-West Coast (GRN destination). These may reflect different historical compression/pass-through definitions rather than simple transcription errors. Attach no field blindly to those legacy rows.

The 13 inside-field legacy zeros occur in Preston OTH→IND, Frankston OTH→GRN, Point Cook OTH→IND, Morwell OTH→IND, five Narracan GRN/OTH recipient cells, Shepparton OTH→IND, Bendigo East OTH→IND, Macedon OTH→IND and South-West Coast GRN→OTH. The separate row/cell audit files preserve exact values and destination sets.

The demonstration seats illustrate the difference: Pakenham OTH exits to ALP+GRN+IND+LNP; Pascoe Vale and Ashwood OTH exit to ALP+GRN+LNP; Yan Yean OTH exits to ALP+LNP. Morwell OTH exits to ALP+IND+LNP+ON, but its legacy raw OTH row omits IND; Morwell's IND row also conflicts with the extracted field. Merely changing zero handling cannot reconcile those different constructions.

No model parameters, matrices or Google Sheets cells were changed by this audit. Recommended next trial: build a separate explicitly field-keyed VEC evidence source, preserving extraction method and field provenance, then test its use without changing the existing ON insertion method. Report incompatible legacy rows separately. Replacement of production evidence or retirement of matrices requires a separate decision; do not choose it based solely on a more favourable ALP seat count.
