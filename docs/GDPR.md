# GDPR assessment — 4iMask Anonymizer

**Document version:** 1.0
**Application version covered:** 4iMask Anonymizer 1.1.0
**Reference texts:** Regulation (EU) 2016/679 (GDPR)
**Version française :** [RGPD.md](./RGPD.md)

---

## 1. Purpose

4iMask Anonymizer is a desktop application that detects the faces present in a video file
and masks them (blur, mosaic or solid box) in order to produce a less identifying copy of
the original video. An additional option (*Back-facing (pose)*) also masks the heads of
people seen from behind, which no face detector can find.

> **Scope of the masking: faces and heads, nothing else.**
> 4iMask masks detected faces, and heads when the pose option is enabled. It does not
> look for, detect or mask any other identifying element: silhouette, licence plate,
> badge, screen, document, tattoo or distinctive sign remain visible in the produced
> video. This limitation is structural, not a matter of configuration: it drives the
> whole analysis below, and section 6 in particular.

This document describes:

- the processing of personal data carried out **by the software itself**;
- what the software does not do;
- the **limitations** of the anonymisation produced, which determine the legal
  qualification of the output file;
- the obligations that remain with the using organisation.

It is not legal advice and does not replace the assessment to be carried out by the
controller or its data protection officer (DPO).

---

## 2. Roles and responsibilities

| Party | Role | Rationale |
|---|---|---|
| Organisation installing and using 4iMask | **Controller** (Art. 4(7)) | It determines the purposes (why these videos are anonymised) and the means (which machine, which videos, which retention). |
| 4iTEC, software publisher | **Tool supplier** | The publisher receives, hosts and accesses no data. It does not process data on behalf of the controller: the relationship therefore does not fall under Article 28 (processor) for the use of the software. |
| Filmed individual | **Data subject** (Art. 4(1)) | Rights are exercised against the controller, not against the publisher. |

Processing runs **entirely on the user's machine**. No processing agreement is required
for the mere use of the software.

---

## 3. Data processed by the application

| Category | Content | Location | Retention | Purpose |
|---|---|---|---|---|
| Source video | Frames that may contain identifiable individuals (Art. 4(1)) | File chosen by the user, left **unchanged** | Solely under the user's control | Face and head detection and masking |
| Output video | Resized copy, detected faces and heads masked, **without audio track** | Same folder as the source, `_anonymized_<format>` suffix | Solely under the user's control | Deliverable of the processing |
| Posture points (*pose* option) | Coordinates of body points used to locate the head of a person seen from behind | Memory only | For the duration of the frame's processing | Position the mask where the face is not visible |
| Technical logs | Timestamp, **full path** of the processed file, detection model, masking option, mask size, errors | `logs/` subfolder of the launch directory | Automatic rotation: the 5 most recent files are kept, the others deleted at startup | Technical diagnostics |
| Windows domain name | `USERDOMAIN` environment variable, read at startup | Memory only, **not logged, not transmitted** | Runtime | Usage guard (see section 11) |
| Display preferences | Chosen language and "privacy notice read" flag | Windows registry / user configuration file (`QSettings`) | Until uninstall or manual removal | Display the notice in the right language and not repeat it at every launch |

**In-memory processing:** each frame is decoded, analysed and rewritten frame by frame.
No intermediate frame, no thumbnail, no face coordinates and no posture points are
written to disk.

---

## 4. What the application does not do

- **No network connection.** No video upload, no telemetry, no usage statistics, no
  update check, no user account.
- **No identification of individuals.** The bundled models (YOLOv11n-face, CenterFace,
  YuNet, and the YOLO11n pose model) *locate* faces, people and posture points in the
  frame. They compute no biometric template, compare no face against a reference database
  and store no signature. See section 5.
- **No training.** The models are frozen and executed locally; your videos are not used
  to train or improve them, and are not sent to any model publisher.
- **No automatic deletion.** The source file is neither modified nor deleted: its removal
  is a matter for the controller's retention policy.

---

## 5. Face detection is not biometric processing

The qualification under Article 9(1) GDPR ("biometric data for the purpose of uniquely
identifying a natural person") rests on the **purpose of identification**.

4iMask performs **detection**: the model answers the question "is there a face at this
position in the frame?". It produces no template, performs no comparison and does not
make it possible to recognise who the person is. The processing carried out by the
software therefore **does not fall under Article 9(1)**, and its purpose — reducing
identifiability — supports data minimisation (Art. 5(1)(c)).

The same reasoning applies to the pose option. The posture points it computes could, in a
different use, serve to identify someone by their gait; that is not the case here. They
are computed frame by frame, used solely to position a mask, never aggregated into a
sequence, never compared and never stored. The purpose of unique identification, which
alone would trigger Article 9(1), is absent.

The **source frames**, however, remain personal data within the meaning of Article 4(1)
as soon as an individual is identifiable in them, and reading them is fully within the
scope of the GDPR.

For completeness: 4iMask is not a remote biometric identification system within the
meaning of Regulation (EU) 2024/1689 on artificial intelligence.

---

## 6. Scope and limitations of the anonymisation produced

> ⚠️ **Key point.** The file produced by 4iMask cannot be assumed "anonymous" within the
> meaning of Recital 26 GDPR without prior review.

### 6.1 Detection is not exhaustive

No detection model achieves 100 % recall. Frequently missed:

- faces in profile or partially turned away;
- very small faces (distant person, video downscaled to 360p);
- blurred, underexposed, backlit or fast-moving faces;
- partially occluded faces (mask, helmet, hand, reflection).

The *Back-facing (pose)* option specifically covers people seen from behind, whom the
three face detectors cannot find. It adds to the face detector rather than replacing it,
and slows processing down. **It is disabled by default**: if the scene contains people
filmed from behind, it must be enabled explicitly.

The resizing applied before detection (360p to 1080p) mechanically degrades the detection
of distant faces: **prefer the highest resolution** when the scene contains people in the
background.

### 6.2 Masking options are not equally robust

| Option | Robustness | Note |
|---|---|---|
| **Solid box** | Highest | The information under the box is destroyed. |
| **Mosaic** (pixelation) | Medium | Coarse pixelation retains information that can be exploited by reconstruction. |
| **Blur** | Lowest | A light blur can be partially inverted; increasing the mask size strengthens the effect without guaranteeing it. |

For external distribution or publication, the **Solid box** option is recommended.

The pose option infers the position of the head from posture. When posture does not allow
it to be located, the upper part of the person is masked instead: the mask may then cover
more than the head. This over-masking is deliberate — leaving a head visible is more
damaging than masking slightly too much.

### 6.3 Masking covers faces and heads only

**4iMask masks detected faces only, plus heads when the pose option is enabled.** No
other identifying element is looked for or processed — neither automatically, nor through
any configuration option. The following remain intact in the output video:

- silhouette, gait, build, hairstyle, distinctive clothing;
- tattoos, scars, prostheses, visible religious symbols;
- licence plates, badges, screens, documents, letters, labels;
- contextual elements allowing re-identification by cross-referencing (location, date,
  small headcount, identifiable workstation).

Masking these elements, where necessary, must be done **manually** in a video editor: no
setting of 4iMask will do it.

The audio track, on the other hand, is **not carried over** to the output file: voices are
effectively removed.

### 6.4 Legal consequence

The result constitutes a **reduction of the re-identification risk**, not irreversible
anonymisation within the meaning of Recital 26. As long as re-identification remains
reasonably possible given the means available, the output file **remains personal data**
and stays subject to the GDPR: lawful basis, retention period, security, data subject
rights.

**Recommended procedure before any distribution:**

1. watch the produced video in full;
2. check that no face or head is left unmasked, in particular at scene changes, when
   people enter the frame, during fast movements and for people filmed from behind;
3. check the identifying elements listed in 6.3;
4. if in doubt, reprocess at a higher resolution or with the **Solid box** option, or complete
   with manual masking in a video editor;
5. record this review if the video is intended for wide distribution.

---

## 7. Obligations of the using organisation

The software is a technical means; compliance rests with the controller. Points to cover:

- **Lawful basis** (Art. 6) for the initial processing of the videos *and* for their
  anonymisation: legitimate interest, legal obligation, public interest task or consent
  depending on context. Anonymisation is most often a minimisation measure attached to
  the main processing.
- **Information of the filmed individuals** (Art. 12 to 14): at capture time, through
  on-site signage, internal notice or contractual clause.
- **Record of processing activities** (Art. 30): describe the use of 4iMask as a
  technical measure of the relevant processing.
- **Data protection impact assessment — DPIA** (Art. 35): required in particular for
  systematic monitoring of a publicly accessible area, large-scale processing or
  monitoring of employees. The use of 4iMask is then a risk-reduction measure to be
  documented in the DPIA.
- **Storage limitation** (Art. 5(1)(e)): define a retention period for source videos and
  **delete the originals** once the masked version has been validated, where the purpose
  no longer justifies keeping them.
- **Security** (Art. 32): source and output files reside on the workstation. Disk
  encryption, access control to the machine and to the working folders, and periodic
  cleanup of the `logs/` folder (it contains the paths, and therefore the names, of the
  processed files).
- **Personal data breach** (Art. 33-34): distributing an insufficiently masked video is a
  personal data breach and must be handled as such.

---

## 8. Data subject rights

The rights of access, rectification, erasure, restriction and objection (Art. 15 to 22)
are exercised **against the controller**, i.e. the organisation holding the videos.

As the software publisher holds no data, it cannot respond to any rights request and can
neither locate nor delete a video.

---

## 9. Security

- Local processing, with no network exposure introduced by the application.
- Detection models are embedded in the deliverable: no download on first launch, and
  therefore no runtime dependency on a remote repository.
- The software does not elevate its privileges and only writes to the locations described
  in section 3.
- Logs contain no image, no face coordinates and no person identifier — but they do
  contain the **full path** of processed files, which may reveal a name, a case number or
  a site. This folder must be protected at the same level as the videos themselves.

---

## 10. Processors and transfers outside the European Union

- **Processors:** none.
- **Transfers outside the EU:** none.
- **Third-party services called at runtime:** none.

---

## 11. Known points of attention

Items identified that warrant a decision by the controller:

1. **Full path logging.** The video file name appears in clear text in `logs/`. If file
   names contain personal data (person's name, case number), consider logging only the
   base name or disabling logging on the machines concerned.
2. **Location of the `logs/` folder.** It is created in the application's launch
   directory, not in the user profile: its location therefore depends on the shortcut
   used. To be checked at deployment time so that it is covered by the purge policy.
3. **Usage guard through `USERDOMAIN`.** The authorised perimeter is defined by a list of
   Windows domains written into the deliverable at build time from a repository secret;
   it is not versioned. This mechanism is an internal usage control, not data security:
   the list travels inside the binary and the environment variable it reads is
   user-controlled. It does not protect the videos and must not be presented as a
   security measure within the meaning of Article 32.
4. **Output file written next to the source.** If the source folder is a network share or
   a broadly accessible location, the produced video is written there with the same
   access rights. Provide a dedicated working folder.

---

## 12. Information displayed in the application

In line with the transparency principle (Art. 5(1)(a)), the application informs the user
directly in the interface:

- a **permanent banner** at the top of the window states that masking covers faces and
  heads only, that processing is local, and that the produced video must be reviewed
  before distribution;
- a **detailed notice** is shown at first launch (and whenever this notice changes
  substantively), covering what is processed, the faces-only scope, what is written to
  disk, what the application does not do and the limitations of masking;
- the **"Privacy / GDPR"** link at the bottom of the window reopens that notice at any
  time and opens this document;
- a **clickable flag** at the bottom of the window switches the whole interface between
  French and English, this information included. The flag shown is the one of the active
  language. The initial language follows the machine locale; the user's choice is
  persisted and also determines which version of the full document is opened from the
  notice.

The notice text is maintained in `apps/privacy.py`, the interface labels in
`apps/i18n.py`. Both must stay consistent with this document and its French version
`docs/RGPD.md`: any substantive change must be reflected in both languages and both
documents, together with an increment of `NOTICE_VERSION` so that users see the notice
again.

---

## 13. Contact

Questions about this document or the behaviour of the software:
<https://github.com/frankkubler/4imask/issues>.

Data subject requests: to be addressed to the controller holding the videos (see
section 8).

---

## 14. Document history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08 | Creation — covers 4iMask Anonymizer 1.1.0, pose detection included. French version: `RGPD.md` |
