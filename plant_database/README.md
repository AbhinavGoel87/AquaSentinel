# Plant database

The doctor compares a new photo with the pictures in this folder. Restart the app after you add or replace pictures.

CoLeaf is the set that ships with this project. `CoLeaf DATASET.zip` sits in the Kshetra folder. Install it once:

Windows: `py -3 plant_database/install_coleaf.py`

macOS and Linux: `python3 plant_database/install_coleaf.py`

That unpacks about 1,000 coffee-leaf photos into ten groups: healthy, boron, calcium, iron, magnesium, manganese, nitrogen, phosphorus, potassium, and a mixed group. The mixed group is one class because those photos show more than one deficiency at once, and the match does not pick a single nutrient from them.

Each group is a folder:

```text
plant_database/entries/magnesium/
  entry.json
  examples/*.jpg
```

`entry.json` needs:

- `id` — a short word, the same as `treatment_id` when a treatment exists
- `kind` — `healthy`, `deficiency`, `disease`, or `discrepancy`
- `title` — what the farmer sees
- `farmer_message` — the explanation
- `recommended_action` — the step to take
- `treatment_id` — the nutrient word, or `null` if nothing should be added to the water
- `dose_seconds` — how long the irrigation-tank cycle may run, at most 180

A deficiency or disease that names a treatment must say that it goes into the irrigation water. The program refuses to start that cycle until the farmer presses the confirm button. An uncertain photo, a healthy match, and the mixed group cannot start a treatment.

The match is "closest example," not a lab result and not a promise that a nutrient is low.
