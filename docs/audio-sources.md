# Audio sources

All audio was generated with ElevenLabs on the team's account, for this course demonstration only.

## Pitch video (`app/promo/audio/`)

Generated with ElevenLabs (user's account), 1 October 2026, for this demo video only.
- `music.mp3`: eleven_music_v2_5, prompt: "Upbeat modern tech product-launch instrumental at 120 BPM: driving
  four-on-the-floor kick, tight claps, pulsing synth bass, bright plucked synth arpeggios and clean electric
  guitar stabs, confident and optimistic with crisp modern production. A punchy four-second intro, energy
  building through the middle, a short filtered breakdown around 35 seconds, then a final lift into one big
  ending hit at 58 seconds. About 60 seconds long, no vocals." (900 credits)
- `vo_*.mp3`: eleven_v3, voice "Emma - Professional Commercial Voice" (9HBoEQ8LqyvVZFYDodnr), one line per
  scene; the exact lines are the scene texts in make_promo.py's comments and the README (621 credits).

## Explain this page (`app/web/explain/`)

- `<screen>-<audience>.mp3`: eleven_v3, voice "Emma - Professional Commercial Voice" (9HBoEQ8LqyvVZFYDodnr),
  1 October 2026. One clip per screen (cover, changes, tracks, tools, briefing, scorecard, story) for each
  audience (stakeholder, developer): 14 clips, about 4,200 credits. The exact lines are in `scripts.json`.
- `timings.json`: word timings measured from each clip's pauses by `app/make_explain_timings.py`, so the
  captions keep pace with the voice.
