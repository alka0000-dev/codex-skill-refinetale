`Inventory.transfer_to` を追加しました。[inventory.py](<EVAL_WORKSPACE>/inventory.py:18)

対応内容:

- destination・sku・quantity の入力検証
- 同一倉庫間の no-op
- 在庫不足時の原子性維持
- 既存 `adjust` を source → destination の順で使用
- 成功時に両倉庫の新在庫数を返却

検証結果:

- `python3 -m unittest discover -s tests`: 5件成功
- Python構文検証: 成功
- `git diff --check`: 成功
