# ptai-library

Open-source AI library catalog for the **Personal AI Tutor** Android app (`com.ptai`).

The app downloads `manifest.json` from this repository and lists the libraries inside it. Each library is installed with one tap; the app verifies the SHA-256 of every file before using it.

## What is inside
| Category | Libraries | Source |
|---|---|---|
| `llm` | Qwen2.5 0.5B / 1.5B Instruct (MediaPipe `.task`, Apache-2.0) | Hugging Face `litert-community` |
| `ocr` | Tesseract `ara`, `eng`, `heb` language data (Apache-2.0) | `tesseract-ocr/tessdata_fast` |

## How it works
`manifest.json` is **generated, not hand-written**. The workflow `Build manifest` runs `scripts/build_manifest.py` on GitHub Actions, which pins the upstream commit, reads the real file size and SHA-256 from the source, and skips any entry it cannot verify or whose licence is not on the allow-list. Run it manually from the Actions tab, or edit `catalog/sources.json` and push.

Only permissive licences (Apache-2.0, MIT, BSD-3-Clause, CC-BY-4.0) are allowed. Gated models that need a login are skipped.

Scripts in this repo are MIT licensed. Each library keeps its own licence (shown in the manifest).
