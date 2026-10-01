# Audio sources

All audio was generated with ElevenLabs on the team's account, for this course demonstration only.

## Pitch video (`app/promo/audio/`)

Generated on 1 October 2026 for the 60-second pitch video only.

| File | Model | Credits |
|---|---|---|
| `music.mp3` | `eleven_music_v2_5` | 900 |
| `vo_*.mp3` (8 clips: `vo_hook`, `vo_problem`, `vo_reveal`, `vo_sales`, `vo_why`, `vo_unusual`, `vo_trust`, `vo_close`) | `eleven_v3`, voice "Emma - Professional Commercial Voice" (`9HBoEQ8LqyvVZFYDodnr`) | 621 |

The prompt used for `music.mp3`:

```text
Upbeat modern tech product-launch instrumental at 120 BPM: driving four-on-the-floor kick, tight claps,
pulsing synth bass, bright plucked synth arpeggios and clean electric guitar stabs, confident and
optimistic with crisp modern production. A punchy four-second intro, energy building through the middle,
a short filtered breakdown around 35 seconds, then a final lift into one big ending hit at 58 seconds.
About 60 seconds long, no vocals.
```

Each `vo_*.mp3` is one voiceover line for one scene. In `app/make_promo.py`, the `"vo"` key of each entry in
`SCENES` names the clip that plays on that scene (for example `"vo": "hook"` plays `vo_hook.mp3`), and
`CLAIMS` lists what each line says about the recording it plays over. The video itself is described in
[running-the-app](running-the-app.md).

## Explain this page (`app/web/explain/`)

| File | What it is |
|---|---|
| `<screen>-<audience>.mp3` | One clip per screen and audience. Model `eleven_v3`, voice "Emma - Professional Commercial Voice" (`9HBoEQ8LqyvVZFYDodnr`), 1 October 2026. |
| `scripts.json` | The exact text of every clip. |
| `timings.json` | Word timings measured from each clip's pauses by `app/make_explain_timings.py`, so the captions keep pace with the voice. |

The screens are cover, changes, tracks, tools, briefing, scorecard, story and home; the audiences are
stakeholder and developer. That makes 16 clips, for example `cover-stakeholder.mp3` and
`cover-developer.mp3`. The figure of about 4,200 credits covers the 14 clips for the seven screens other than home.

To replace a clip:

1. Change its text in `scripts.json`.
2. Generate the new mp3 with the same model and voice, and save it under the same file name.
3. From the `app` folder, re-measure the caption timings:

   **Mac**

   ```bash
   ./demo.sh timings
   ```

   **Windows**

   ```powershell
   .venv\Scripts\python make_explain_timings.py
   ```
