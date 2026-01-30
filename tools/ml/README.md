## Transformer prototype (inventory meta seeding)

Goal: learn a model that predicts a good **seed set of variants** from a subset of songs, then let the existing
GPU solver validate/repair.

This is a *prototype* to test feasibility. It does **not** claim global optimality.

### 0) Always use a DB snapshot

Never point these scripts at the live `evolution.db`. Create a snapshot first (SQLite backup API) and use that path.

### 1) Build a variant universe (vocab)

Example:

`python inventory_meta_coverage_main.py --db-path artifacts/db_backups/<snapshot>.db --build-variant-frequency-universe artifacts/bench_compare/<ts>/variant_universe_top5000.json --variant-frequency-top-candidates 5 --variant-frequency-patterns-per-candidate 1000 --variant-frequency-universe-size 5000 --seed 1`

### 2) Generate a toy training dataset

This runs many small GPU solves on random song subsets and records the resulting inventories as labels.

`python tools/ml/generate_transformer_dataset.py --db-path artifacts/db_backups/<snapshot>.db --universe artifacts/bench_compare/<ts>/variant_universe_top5000.json --out artifacts/ml/transformer_ds.pt --examples 200 --subset-size 128 --inventory-cap 30 --k 128 --seed 1`

Optional coverage-weighted labels:

`python tools/ml/generate_transformer_dataset.py --db-path artifacts/db_backups/<snapshot>.db --universe artifacts/bench_compare/<ts>/variant_universe_top5000.json --out artifacts/ml/transformer_ds.pt --examples 200 --subset-size 128 --inventory-cap 30 --k 128 --seed 1 --label-weighting covered_linear`

Optional label mode that caps each variant to one contribution per covered song (fractional support):

`python tools/ml/generate_transformer_dataset.py --db-path artifacts/db_backups/<snapshot>.db --universe artifacts/bench_compare/<ts>/variant_universe_top5000.json --out artifacts/ml/transformer_ds.pt --examples 200 --subset-size 128 --inventory-cap 30 --k 128 --seed 1 --label-mode song_support --label-weighting covered_linear`

### 3) Train

`python tools/ml/train_transformer_seed.py --data artifacts/ml/transformer_ds.pt --out artifacts/ml/seed_transformer.pt --epochs 5 --batch-size 16 --lr 3e-4`

#### 3a) Train on DirectML (Windows + AMD GPU)

Install `torch-directml` and pass `--device dml`. For strict "no CPU fallback", use `--strict-no-cpu`.

`python tools/ml/train_transformer_seed.py --data artifacts/ml/transformer_ds.pt --out artifacts/ml/seed_transformer.pt --epochs 5 --batch-size 16 --lr 3e-4 --device dml --loss bce_custom --optimizer adamw_safe_oop --pos-weight 20 --strict-no-cpu`

### 4) Predict seed variants JSON

Produces a JSON compatible with `inventory_meta_coverage_main.py --seed-inventory-variants ...`.

`python tools/ml/predict_seed_variants.py --model artifacts/ml/seed_transformer.pt --data artifacts/ml/transformer_ds.pt --out artifacts/ml/pred_seed_top100.json --cap 100 --subset-size 128 --samples 64 --seed 1`

Emit multiple caps in one pass:

`python tools/ml/predict_seed_variants.py --model artifacts/ml/seed_transformer.pt --data artifacts/ml/transformer_ds.pt --out artifacts/ml/pred_seed.json --caps 30,50,70 --subset-size 128 --samples 128 --device dml --strict-no-cpu`

#### 4a) Strict DirectML inference (no ONNX, no CPU fallback)

`python tools/ml/predict_seed_variants.py --model artifacts/ml/seed_transformer.pt --data artifacts/ml/transformer_ds.pt --out artifacts/ml/pred_seed_top100.json --cap 100 --subset-size 128 --samples 128 --batch-size 32 --device dml --strict-no-cpu`

#### 4b) ONNX export + DirectML inference (Windows + AMD GPU)

Export:

`python tools/ml/export_transformer_onnx.py --model artifacts/ml/seed_transformer.pt --data artifacts/ml/transformer_ds.pt --out artifacts/ml/seed_transformer.onnx`

Infer with DirectML:

`python tools/ml/predict_seed_variants_onnx.py --model artifacts/ml/seed_transformer.onnx --data artifacts/ml/transformer_ds.pt --out artifacts/ml/pred_seed_top100.json --cap 100 --subset-size 128 --samples 128 --batch-size 32 --provider dml`

### 5) Run solver with the model seed

`python inventory_meta_coverage_main.py --db-path artifacts/db_backups/<snapshot>.db --solver gpu_full --inventory-cap 100 --partitions-per-song 256 --adaptive-rounds 0 --adaptive-keep-per-song 0 --seed 1 --seed-inventory-variants artifacts/ml/pred_seed_top100.json --output artifacts/ml/seeded_run.json`

### 5b) Search multiple model seeds + GPU eval (Stockfish-style branching)

This samples multiple seed sets from the model (Gumbel-topK) and evaluates each on a small allowlist
using the GPU solver, then optionally runs a full solve on the best candidate.

`python tools/ml/search_seed_variants.py --model artifacts/ml/seed_transformer.pt --data artifacts/ml/transformer_ds.pt --db-path artifacts/db_backups/<snapshot>.db --out-dir artifacts/ml/seed_search --seed-cap 50 --inventory-cap 100 --candidates 12 --subset-size 128 --samples 64 --strategy gumbel --temperature 1.0 --eval-song-count 256 --eval-k 128 --eval-restarts 3 --eval-lns-attempts 200 --device dml --strict-no-cpu`

To run the full solver on the best candidate afterward:

`python tools/ml/search_seed_variants.py --model artifacts/ml/seed_transformer.pt --data artifacts/ml/transformer_ds.pt --db-path artifacts/db_backups/<snapshot>.db --out-dir artifacts/ml/seed_search --seed-cap 50 --inventory-cap 100 --candidates 12 --strategy gumbel --eval-song-count 256 --eval-k 128 --eval-restarts 3 --run-full --full-k 256 --full-restarts 5 --full-lns-attempts 200 --device dml --strict-no-cpu`

### 6) Analyze datasets and runs

Dataset stats (heavy-tail, variants-seen, covered correlations):

`python tools/ml/analyze_transformer_dataset.py --data artifacts/ml/transformer_ds.pt`

Run stats (covered-by-element + seed distribution when you pass a universe):

`python tools/ml/analyze_inventory_result.py --result artifacts/ml/seeded_run.json --db-path artifacts/db_backups/<snapshot>.db --universe artifacts/bench_compare/<ts>/variant_universe_top5000.json`
