# Plant database

Put the doctor rover's reference pictures here. The Raspberry Pi compares a new photo with these examples. Restart the app after you add or replace pictures.

Each problem is a folder:

```text
plant_database/entries/magnesium/
  entry.json
  examples/leaf.png
```

`entry.json` needs:

- `id` — a short word, the same as `treatment_id` when a treatment exists
- `kind` — `healthy`, `deficiency`, `disease`, or `discrepancy`
- `title` — what the farmer sees
- `farmer_message` — the explanation
- `recommended_action` — the step to take
- `treatment_id` — `magnesium`, `sulfur`, `pest`, or `null` if nothing should be added to the water
- `dose_seconds` — how long the irrigation-tank cycle may run, at most 180

A deficiency or disease that names a treatment must say that it goes into the irrigation water. The program refuses to start that cycle until the farmer presses the confirm button. An uncertain photo cannot start a treatment.

Replace the example pictures with your own leaf photos. Use daylight, fill the frame with the leaf, and keep the file a PNG or JPEG under 5 MB. Do not put drinking-water instructions in the action text. This tank is the irrigation tank.

The match is "closest example," not a lab result and not a promise that a nutrient is low.
