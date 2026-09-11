# RootVerse Datasets

This folder holds the language content that feeds the app (phrase packs,
FLN lessons, translation samples).

## ⚠️ Language-data integrity rule (SIH rule #8)

**Never invent Santhali text.** Every Santhali string in this repository is one of:

1. **VERIFIED** — provided/reviewed by a qualified Santhali speaker or linguist
   (record reviewer name, source and date in the `validated_by` / `source` columns), or
2. **PLACEHOLDER** — marked `REQUIRES_LANGUAGE_VALIDATION` in the Santhali column.

Prototype builds must visibly treat placeholders as unverified. Generated text is
never presented as linguistically verified.

## Folders

| Folder | Purpose | Format |
|---|---|---|
| `classroom_phrases/` | Classroom instruction phrases (Hindi, English, Santhali, category, audio path) | CSV / JSON |
| `fln_lessons/` | Foundational literacy & numeracy lesson content | CSV / JSON |
| `translation_samples/` | Hindi↔Santhali sentence pairs for MT evaluation | TSV / JSON |

## Planned schema — classroom phrases (CSV)

```csv
id,hindi,english,santhali_ol_chiki,validation_status,category,audio_path,validated_by,source
1,अपनी किताब खोलो,Open your book,REQUIRES_LANGUAGE_VALIDATION,PLACEHOLDER,instruction,,,
```

`validation_status` ∈ `VERIFIED` | `PLACEHOLDER`.

## Planned schema — FLN lessons (JSON)

```json
{
  "id": "numbers-1-10",
  "title_hindi": "एक से दस तक गिनती",
  "class_level": 1,
  "subject": "numeracy",
  "hindi_text": "...",
  "santhali_ol_chiki": "REQUIRES_LANGUAGE_VALIDATION",
  "learning_objective": "Student counts 1–10 aloud",
  "activity_instruction": "...",
  "audio_path": null,
  "validation_status": "PLACEHOLDER"
}
```

> FLN content is *designed to align with* NIPUN Bharat learning goals;
> no official certification is claimed.
