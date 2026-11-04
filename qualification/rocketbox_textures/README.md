# Official MIT Rocketbox source-color texture qualification

**Independent bounded source-only workcell** stacked on existing [MIT 80-bone native walk #274](https://github.com/SemperSupra/stable-character-pipeline/pull/274) at immutable HEAD `8307fb98a1e47083a657a708d27b2ea4420f4b2a`. Full source is official Microsoft `microsoft/Microsoft-Rocketbox` commit `0943055db6ec570bcef9f2c8b41c9e5467c808f9` under MIT notice.

Selected 4 upstream original complete color TGA objects (12,582,956 bytes **each**, not generic thumbnails, normal/specular or replacement image assets):

| Path within Female_Adult_XX/Textures | Exact Git blob SHA1 |
|---|---|
| Female_Adult_01/Textures/f001_body_color.tga | `25852db0db1f44a0de0643ce1e09c88aef587e6f` |
| Female_Adult_01/Textures/f001_head_color.tga | `0cdc62ab47da3dca01aff0bb179159865a559c63` |
| Female_Adult_02/Textures/f002_body_color.tga | `5eb8ee83281a7526544a80ddf9804507670eb049` |
| Female_Adult_02/Textures/f002_head_color.tga | `8f59bb553f24d3581de68bcf4683695c014bcc0f` |

GitHub Actions uses only standard $0 public runner; directly retrieves four exact original source files and MIT license from the pinned official commit, verifies each Git object hash with actual `git hash-object` and the Go verifier (not filename-only), exact length and valid native uncompressed truecolor TGA raster header. The self-authored synthetic negative tests cover unsupported encoding, palette, dimensions, pixel depth, truncation, forged footer, Git blob hash, size and symlink. Outputs JSON source receipt with full SHA256 and dimensions, retained only 7 days in public GHA; **no third-party TGA binaries are uploaded into public Git, PR patches, or Actions artifacts**.

Human: source manifest/document and rights boundary. Automation: Go standard library CLI/tests. Agents: typed JSON receipt with explicit `blender_uv_mapping=NOT_RUN`, `character_realism=UNKNOWN`, `product_accepted=false`. This test does NOT establish material assignments, original 80-bone UV compatibility, license compliance by itself, visual quality, full human identity or protected source rights. A future independently scoped native Blender material-binding reviewer may consume **only verified** source bytes after owner review.

Original protected Naomi/Alison, private runners, corpus/rights/custody, merge/release/deployment and CPE gates unchanged. Source and evidence index in Git/DLE; large source bytes only in approved private custody if owner explicitly admits.
