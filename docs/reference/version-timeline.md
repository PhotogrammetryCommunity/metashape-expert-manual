# Metashape / PhotoScan version timeline

This page maps **release date → product name and version → headline
behavioural changes**, so authors can resolve an undated forum post to a
version, and so readers can calibrate how much an old piece of advice
still applies.

> **Status:** initial best-effort. Dates marked with `~` need
> verification against the official Agisoft changelog or release notes.

## Version-at-time lookup

When you cite a forum post dated `YYYY-MM-DD`, look up which row covers
that date and use the `Cite as` value in the citation.

| Released | Product | Version | Cite as | Headline changes |
|----------|---------|---------|---------|------------------|
| ~2010 | PhotoScan | 0.7 | `PhotoScan 0.7` | First public alpha/beta. |
| ~2012 | PhotoScan | 0.9 | `PhotoScan 0.9` | Iterations through 0.x. |
| ~2013-02 | PhotoScan | 1.0 | `PhotoScan 1.0` | First stable major. |
| ~2014-12 | PhotoScan | 1.1 | `PhotoScan 1.1` | |
| ~2015-08 | PhotoScan | 1.2 | `PhotoScan 1.2` | Reference Preselection introduced. |
| ~2017-04 | PhotoScan | 1.3 | `PhotoScan 1.3` | Mesh-from-depth-maps; refined alignment. |
| ~2017-12 | PhotoScan | 1.4 | `PhotoScan 1.4` | Last release under the PhotoScan name. |
| **2019-01** | **Metashape** | **1.5** | `Metashape 1.5` | **Renamed from PhotoScan.** Free upgrade for existing users. |
| ~2020-02 | Metashape | 1.6 | `Metashape 1.6` | |
| ~2021-03 | Metashape | 1.7 | `Metashape 1.7` | |
| ~2022-01 | Metashape | 1.8 | `Metashape 1.8` | Last 1.x major. License activation in 1.8 and earlier ended 2023-12-20. |
| **~2022-12** | **Metashape** | **2.0** | `Metashape 2.0` | **Major rework.** "Dense Cloud" renamed to "Point Cloud". ML-based depth maps. New laser-scan support. |
| ~2023-10 | Metashape | 2.1 | `Metashape 2.1` | 2.1.0 pre-release announced 2023-10-07. |
| ~2024 | Metashape | 2.2 | `Metashape 2.2` | AI-assisted mask generation (`MaskingMode.MaskingModeAI`); AprilTag detection (7 variants in `Metashape.TargetType`); "save project after each step" checkbox in main workflow dialogs; Vulkan-checkbox placeholder in *Preferences → GPU* (no effect in 2.2.x). See [*New features in Agisoft Metashape 2.2.x* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000173952). |
| ~2025 | Metashape | 2.3 | `Metashape 2.3` | Latest published user manuals. Automatic colour enhancement. Texture-mode improvements (Keep UV + Natural texturing workaround via Texture Transfer); `out_of_focus_filter` parameter. See [*New features in Agisoft Metashape 2.3.x* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000177202). |

## Notes on dating

- **2018-01 to 2019-01 is a transition period** — many forum posts in
  that window reference PhotoScan even though the rename was imminent.
  Cite as `PhotoScan 1.4` if pre-rename, `Metashape 1.5` if post.
- **Build dates differ from version dates.** A post mentioning "1.7.4
  build 15925 (1 March 2023)" references a *patch* of 1.7, not the
  initial 1.7.0 release. The `Cite as` value uses the major.minor only.
- **Forum users sometimes lag behind the latest release.** A post dated
  2024-06 might reference Metashape 2.0 even though 2.1 had shipped. If
  the post text states the version, prefer the stated version over the
  date-derived one.

## How to refine this table

When you find a release date in:

- the Agisoft "Latest Releases / Bugfixes" knowledge-base article
  (<https://agisoft.freshdesk.com/support/solutions/articles/31000159199>),
- the Agisoft forum's *Announcements* board,
- a press release,

…update the row above and remove the `~` if the date becomes definitive.
File a PR with the source linked.
