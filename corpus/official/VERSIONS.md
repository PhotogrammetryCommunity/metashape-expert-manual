# Official Documentation Versions

Recorded for reproducibility. Update this file every time the corpus is
re-downloaded.

## Downloaded 2026-05-22

| Document | URL | Local file | Size | SHA-256 |
|----------|-----|------------|------|---------|
| Metashape Professional Edition User Manual | <https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf> | `metashape-pro-2_3_en.pdf` | 8.2 MB | `c6ebac6cf545e5bea00c65b770006ce2dfdcbdc504801148ec585f2c02a95db3` |
| Metashape Standard Edition User Manual | <https://www.agisoft.com/pdf/metashape_2_3_en.pdf> | `metashape-standard-2_3_en.pdf` | 5.2 MB | `9df75b30b8155501844cd7fb6cdb639e9a9f34510b9c0664ff4fea0d2718b7d5` |
| Python API Reference | <https://www.agisoft.com/pdf/metashape_python_api_2_3_1.pdf> | `metashape-python-api-2_3_1.pdf` | 1.5 MB | `d683ca7e1965eecdb5eea0d9cbac261bcf74e701a61e9d7d8c001968dab102f9` |
| Metashape changelog (GUI) | <https://www.agisoft.com/pdf/metashape_changelog.pdf> | `metashape-changelog.pdf` | 300 KB | `65ec942ed54cd9b6524c3eddde6873e4c0a3a9acdc1d67a046897252e5e1ecda` |

The Python API Reference PDF includes its own change log as
**chapter 3 ("Python API Change Log")**. Together with the GUI
changelog above, this gives an authoritative, per-version record of
every renamed method, removed kwarg, or moved class — used during
Tier 1 verification to disambiguate forum-era references.

## Version notes

The latest published manuals are **Metashape 2.3** (Pro and Standard)
and **Python API 2.3.1**. The validation environment in this project
is Metashape 2.2 (per `STATUS.md`). Article `applies_to:` fields
should reflect the version actually validated against, not the latest
published manual.

When Metashape 2.4 ships, follow the refresh procedure in
`corpus/README.md` and update the GUI changelog in step with the new
release.
