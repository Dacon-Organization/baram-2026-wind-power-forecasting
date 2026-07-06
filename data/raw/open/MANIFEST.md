# Official Data Manifest

생성일: 2026-07-06 KST

원본 위치: `C:\Users\kik32\Downloads\open\`

복사 위치: `data/raw/open/`

Hash 알고리즘: SHA256

| 상대 경로 | 크기(bytes) | SHA256 |
|-----------|------------:|--------|
| `data/raw/open/data_description.md` | 11694 | `515ba62cba293e877e20fc993d8e0ff84770f76fa0335debdbd7ed60b9e58819` |
| `data/raw/open/info.xlsx` | 3823422 | `89e83a52e0eb2ce367a3573a96d6795ed4b4d4ac624965cb3530beec0cbd2bd6` |
| `data/raw/open/sample_submission.csv` | 359229 | `c925d2066a834f937f8091ed55acfe50ff86c8be4745b52c3adc95b056c5aaaa` |
| `data/raw/open/test/gfs_test.csv` | 28037722 | `aa33febb24ecd46b82be34880a06910e16a3382319287548e6ce2af721b4f848` |
| `data/raw/open/test/ldaps_test.csv` | 43122637 | `60e94f7cc80384eee335e90dc896b6cf4d36b35cde8d37bc03bd5c08a788b0fa` |
| `data/raw/open/train/gfs_train.csv` | 84315594 | `cd56b67d357e7bbaff5d0d51d3537d935c9e7a3f012e9f37516bdc4d38c66a5d` |
| `data/raw/open/train/ldaps_train.csv` | 129687357 | `61ae944e7ae1fcb17391be6737792a2205c6507bf2446ed5d9d0daf07fdea026` |
| `data/raw/open/train/scada_unison_train.csv` | 16788646 | `5d8ccd7ac6b127865d0b2f18de257ceb23dcbf3b0056c209e8b02f1470c6c9be` |
| `data/raw/open/train/scada_vestas_train.csv` | 33458140 | `f024f3ca57bbe2a6106f515d32c1457d75f519fb27068308680b20fb6f04dcc1` |
| `data/raw/open/train/train_labels.csv` | 1138967 | `47bb64252195cf4734e67394d6e50485f27a608def3b5a8791fcc7674bbceb03` |

검증 명령:

```powershell
$project = "C:\Users\kik32\workspace\Dacon\2026-BARAM-Wind-Power-Prediction-AI-Competition"
Get-ChildItem -Recurse -File -LiteralPath "$project\data\raw\open" |
  Sort-Object FullName |
  ForEach-Object {
    $rel = $_.FullName.Substring($project.Length + 1).Replace("\", "/")
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLower()
    "$rel`t$($_.Length)`t$hash"
  }
```
