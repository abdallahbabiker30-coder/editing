# Before/after reel playbook (skin clinic, TikTok + Instagram Reels)

Research date: 30 Oct 2026. Sources: Trendtrack's TikTok library (organic and ads, sorted by views and shares), Trendtrack's Meta ad search, and web reading on the platforms' 2026 rules. This builds on `reels/references.md`; the refs there (Liz Claire 13.1M, Zarpash 15.4M, DermDoctor 25.8M, Dr. Qazi) still apply and aren't repeated here.

I could read each reference's caption, length, sound and stats, but the video files themselves are blocked from this environment, so the edit patterns below come from metadata plus format, not frame-by-frame viewing.

---

## 1. What the winners have in common

| # | Reel | Views · shares | Length | Hook / caption | Sound | Lesson |
|---|---|---|---|---|---|---|
| 1 | [@aviante__ chemical peel](https://www.tiktok.com/@aviante__/video/7646511921595731231) | **72.1M** · 162K shares · 208K saves | 14 s | "Nothing could have prepared me for this 😭" | Trending: "Saxophones getting louder (Slowed)" | Short, emotional, the downtime *is* the story, sound builds into the reveal |
| 2 | [@onedocxhairdocmy Pico laser (ad)](https://www.tiktok.com/@onedocxhairdocmy/video/7652611046774934792) | **23M** · 5.9K shares | 15 s | "Dulu… / Now: 'eh, my skin looks like the upgrade version?'" (then vs now meme) | Original voiceover | Meme framing works *in ads*. Caption carries a results disclaimer: "transformation shown after 5 months of consistent treatment; results vary" |
| 3 | [@onedocxhairdocmy "Not all lasers are safe" (ad)](https://www.tiktok.com/@onedocxhairdocmy/video/7538727991715564818) | **10.7M** | ~15 s | Contrarian warning | Original | A contrarian or safety hook outperforms "look at this result" |
| 4 | [@onedocxhairdocmy "Why does getting pretty hurt so much?" (ad)](https://www.tiktok.com/@onedocxhairdocmy/video/7535448591754677522) | **9M** | ~15 s | Pain / honesty hook | Original | Same idea as Liz Claire: owning the discomfort earns trust |
| 5 | [@pielclinic Hydrafacial (ad)](https://www.tiktok.com/@pielclinic/video/7478026473752907014) | **11.5M** | short | Satisfying process | Original | Process footage of the machine on the skin is a hook on its own |
| 6 | [@doctor.truesdale facelift](https://www.tiktok.com/@doctor.truesdale/video/7582719471006027063) | **9.2M** · 111K shares | 54 s | "When you look so good you forget your age 😂" | Trending song | Humour drives shares, and the caption lists the procedures |
| 7 | [@jasonemermd acne-scar journey](https://www.tiktok.com/@jasonemermd/video/7504465573032561963) | 85K · 1.1K shares, **70% engagement** | 98 s | "No filter. Real results." | Original | Exactly our case: **Before → Immediately after (red, swollen) → Later result**, shown honestly |
| 8 | [@dralexisstephens RF microneedling](https://www.tiktok.com/@dralexisstephens/video/7475681253648272686) | 192K | **11 s** | "Before & After: 3 sessions" | Original | Very short and loopable. The education lives in the caption, not the video |
| 9 | [@beautyphi "Let's hear it for the GUYS"](https://www.tiktok.com/@beautyphi/video/7431611088732491013) | 659K · 1K shares, on a 320-follower account | short | Audience call-out | — | Naming *who* it's for pulls views even on a tiny account |
| 10 | [@samaraaalam × Skinatomy](https://www.tiktok.com/@samaraaalam/video/7630935910598659349) | 76K | — | "♻️ REPOST if I look better" | — | An engagement-bait CTA that asks for reposts (Reels sends / TikTok reposts are top ranking signals) |

**The patterns:**

1. **Length: 10–16 s wins.** The 72M, 23M, 10M and 9M reels are all 14–18 s. Longer ones (54–98 s) only work when someone is talking or there's a real story arc. A short reel that gets replayed beats a long one watched halfway.
2. **Show the result (or the most dramatic frame) in the first 1–2 s.** Reels decides around the 1 s mark, TikTok around 1.5 s. Never open on a logo, a slow before or a title card.
3. **The hook is a feeling or a tension, not a description.** "Nothing could have prepared me", "not all lasers are safe", "why does it hurt", "what no one tells you". "Before and after of laser treatment" is the weakest possible hook.
4. **Honesty sells better than perfection in skin.** Redness, peeling and the "immediately after" stage are what people share (refs 1, 4, 7 and Liz Claire 13.1M). This lines up with our honesty rule.
5. **Sound splits by use.** The organic winners ride a trending sound that *builds* (a rising saxophone, an escalating track) so the reveal lands on the drop. The ad winners use original voiceover or their own sound. → Always export two cuts.
6. **The caption does the explaining.** On-screen text stays at 3–7 words per beat; the treatment details, session count and disclaimer go in the post caption.
7. **Series beat one-offs.** "Part 1 → follow for session 2" turns one patient into 3–5 posts and gives people a reason to follow.

---

## 2. Five reusable structures

Times are for a ~14 s reel at 30 fps. Each one maps to segments in `ba_reel.py` (section 5).

### A. Reveal first (the default; `example_config.json`)
| Time | Shot | On-screen text | Segment |
|---|---|---|---|
| 0–1.6 | Close push-in on the most dramatic AFTER frame | Hook (≤7 words) | `still` + `hit` |
| 1.6–2.5 | Rapid before/after flicker, 0.15 s each | "Same face. 1 hour apart." | `flash` |
| 2.5–4.5 | BEFORE, slow push | Label + real timestamp | `still` |
| 4.5–6.7 | Wipe BEFORE → AFTER with a light line | Label switches | `wipe` |
| 6.7–9.1 | Split screen, other side of the face | BEFORE ▲ / ▼ AFTER | `split` |
| 9.1–11.5 | Slider sweep zoomed on the cheek texture | "Now look at the texture" | `slider` |
| 11.5–13.1 | AFTER hold | Honest line ("Yes, it's red. This is day 1.") | `still` |
| 13.1–15.3 | Blurred end card | Series CTA + "Book · link in bio" | `card` |

### B. Process → reveal ("watch till the end")
0–3 s machine on skin (close, satisfying), then 3–8 s quick cuts of the session, then 8–11 s a hard cut to the BEFORE, then a wipe to the AFTER on the beat drop, then a 1.5 s end card. Hook text: "Watch her skin after 1 session". Needs 5–10 s of treatment footage (`clip` segments).

### C. Then vs now meme (OneDoc 23M style; best for organic + trending sound)
Two cards only. 0–4 s BEFORE with "Me trying every cream for 3 years" (or "Dulu" / "قبل"), then a hard cut on the beat to the AFTER with "Me after [treatment]" for 4 s, then loop. 8–10 s total. Use a trending sound. Only use it with a *later* after photo, never the same-day red one.

### D. Journey series (Jason Emer format)
BEFORE, then **IMMEDIATELY AFTER (red, swollen)**, then **WEEK 2**, then **WEEK 6**, each labelled with a date. 20–30 s. It can't be faked and it's the most trusted format. Our patient is already at step 2.

### E. Doctor + proof
The doctor says one line to camera ("Not all lasers are safe for darker skin. Here's what we did."), cut to B/A as proof, back to the doctor for the CTA. 20–35 s. This is the best ad format because voiceover = original sound = ad-safe.

---

## 3. Hook bank (on-screen, ≤7 words)

| Type | English | Arabic |
|---|---|---|
| Honest | What session 1 REALLY looks like | الجلسة الأولى… هذا شكلها الحقيقي |
| Honest | Nobody tells you about this part | محد يقول لك عن هالجزء |
| Time-stamp | Same face. 1 hour apart. | نفس الوجه. بعد ساعة وحدة |
| Contrarian | Not every laser is safe for your skin | مو كل ليزر آمن لبشرتك |
| Curiosity | Wait for the texture… | انتظري لين تشوفين الملمس |
| Emotion | She hid these scars for 5 years | خبّت هالآثار ٥ سنين |
| Call-out | If you have acne marks, watch this | إذا عندك آثار حبوب، شوفي هذا |
| Meme | Me vs me after session 3 | أنا قبل… وأنا بعد الجلسة الثالثة |
| CTA (shares) | Send this to someone who needs it | أرسليه لصديقتك اللي تحتاجه |
| CTA (series) | Follow for session 2 | تابعينا للجلسة الثانية |

Fill in the treatment name once we have it ("What 1 session of [CO2 laser] really looks like"); naming the treatment on screen is what DermDoctor's 25.8M reel does.

---

## 4. Rules for every reel

**Text**
- Font: **Helvetica Bold Compact**. The stand-in is Nimbus Sans Narrow Bold (`reels/fonts/`) until the real file is uploaded.
- Style: white rounded box with black text (native TikTok look) for hooks; a dark pill with white text for labels; white with a black outline for big end-card lines.
- Size 78–96 px for hooks, 52–60 px for labels. Max 2 lines, max 7 words per beat, and each line stays on screen long enough to read twice (~1.2 s per 4 words).
- Safe zone: keep text between y = 220 and y = 1500 and away from the right 140 px (likes/share buttons). The renderer's named positions already respect this.
- **Arabic:** Helvetica Bold Compact has no Arabic letters. The script renders Arabic with a fallback (DejaVu Sans Bold) until we get a matching Arabic font file (e.g. Helvetica Neue Arabic Bold).

**Honesty and policy** (applies to ads *and* organic)
- Label an immediate post-session photo as **"straight after session 1"** with the real timestamps; never call it a result.
- Same light, same angle, no filters, no retouching, no makeup on either side. Platforms and viewers both catch brightness tricks.
- Put a disclaimer in the post caption: "Individual results vary. Photo shown [immediately after / X weeks after] [N] sessions."
- **Meta (FB/IG) ads:** cosmetic before/after is allowed for **18+ targeting only**, without body-shaming copy ("Tired of your ugly scars?" gets rejected). Anti-aging/wrinkle before/after side-by-sides are still not allowed. ([Meta health & wellness policy](https://transparency.meta.com/policies/ad-standards/restricted-goods-services/health-wellness))
- **TikTok ads:** TikTok's March 2026 opening for aesthetic procedures covers the **US and Canada only**. Elsewhere, before/after comparisons in ads are generally rejected ([TikTok update](https://ads.tiktok.com/help/article/update-to-cosmetic-surgery-na-march-2026), [misleading-content policy](https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content)). For TikTok ads outside the US/CA, run **structure B or E** without the side-by-side, and keep the side-by-side versions for organic posts and Meta.
- Many Gulf health authorities also require an approved ad permit for medical advertising. The clinic should confirm theirs before paid runs.

**Sound**
- Ads: no commercial songs. Use the renderer's built-in sound design (whoosh on wipes, sub hit on reveals; synthesised, so it's 100% ours), an original track, voiceover, or TikTok's Commercial Music Library / Meta Sound Collection.
- Organic: export the **no-music** cut and add the trending sound in-app. Pick sounds that *build*, and line the wipe up with the drop (the renderer prints segment start times).

**Post caption** (not on screen): hook line, then treatment + session count, then 1–2 lines of education (e.g. scar types), then the disclaimer, then the CTA ("DM 'SKIN' to book"), then 3–5 hashtags: #beforeandafter #acnescars #[treatment] #[city]skin #skintransformation.

---

## 5. Using the template script

`ba_reel.py` turns a JSON file into a finished 1080x1920 reel (H.264, AAC, -14 LUFS).

```bash
python3 ba_reel.py my_reel.json --preview   # contact sheet of key frames (~1 min)
python3 ba_reel.py my_reel.json             # full render (~3–5 min)
```

**Assets.** Each photo gets two **anchor points** (e.g. eye corner and nose tip, in pixels of the original photo). Set `align_to` on the AFTER and it gets scaled and rotated so those two points sit exactly on the BEFORE's. That's what keeps the face from jumping during wipes and flashes. Frame the reference photo with `focus` (source px), `scale` (output px per source px, ~0.7 for a face close-up from a 4K iPhone photo) and `frame_pos`.

**Segment types**

| type | what it does | key options |
|---|---|---|
| `still` | one photo with a camera move | `asset`, `zoom: [from, to]`, `center: [x, y]` or `[[x0,y0],[x1,y1]]` |
| `clip` | video section | `src`, `start`, `dur`, `speed`, `focus_x`, `zoom` |
| `wipe` | reveal B over A with a light line | `from`, `to`, `direction: lr/rl/tb/bt`, `hold` |
| `slider` | before/after slider sweeping across | `from`, `to`, `sweeps` |
| `split` | stacked or side-by-side | `assets`, `layout: stack/side`, `zooms`, `centers` |
| `flash` | rapid A/B flicker | `assets`, `every` (s) |
| `card` | end card over a blurred photo or flat colour | `asset`, `blur`, `dim`, `bg`, `logo`, `logo_path` |

Any segment can take `"hit": true` (sub hit at its start) and a `text` list: `{text, pos: top/upper/center/lower/bottom or y, size, style: box/label/outline/plain, start, end, anim: pop/fade/none}`. Top-level `overlays` take the same items with absolute `start`/`end` times. `music` + `music_volume` + `music_start` add a track and also export a `-no-music` copy.

**Capture protocol for the next patients** (this is what makes the template work):
1. Same spot, same wall, same overhead light, phone on a tripod at face height, ~60 cm away.
2. Five angles every time: front, 45° left, left profile, 45° right, right profile. No makeup, hair covered the same way, neutral expression.
3. Shoot at the same times: before, straight after, 2 weeks, 6 weeks (structure D).
4. 5–10 s of video of the device on the skin during the session (structures B and E), in 4K 30 fps.
5. Optional: one line from the patient or doctor to camera.

---

## 6. Checklist before export
- [ ] Result or most dramatic frame visible by 1.0 s
- [ ] Hook ≤7 words, a feeling or tension rather than a description
- [ ] Faces aligned (no jump on the wipe or flash)
- [ ] Every after labelled honestly with a time or date
- [ ] Text inside the safe zone, Helvetica Bold Compact
- [ ] 10–16 s (unless structure D or E)
- [ ] Ad cut: no commercial music, no side-by-side for TikTok outside US/CA, 18+ targeting on Meta
- [ ] Organic cut: no-music file plus a trending sound added in-app
- [ ] Caption: treatment, sessions, disclaimer, CTA, 3–5 hashtags
