プロフィールcodecを新形式へ更新しました。

- [profile_codec.py](<EVAL_WORKSPACE>/profile_codec.py)
  - version 2で`user_id`と`display_name`を保存
  - `Profile("u")`の表示名を`"u"`に設定
  - version 1の読み込み互換を維持
  - 欠落・型不正・空文字・未知versionを`InvalidProfile`化
  - JSON構文エラーの元例外を非公開化

検証結果: `python3 -m unittest discover -s tests` — 4件成功。追加の境界値確認も成功しました。
