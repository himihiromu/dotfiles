# Review Priority Policy
レビューの指摘は以下の優先度に従う。

- **Critical**: 視聴者離脱の原因となる重大問題、技術的エラー
- **Major**: 理解を阻害する問題、構造的欠陥
- **Minor**: 表現の改善、微調整
- **Suggestion**: 品質向上のための任意改善

優先度の高いものから順に対応する。
CriticalまたはMajorが一つでも残っている場合、REVIEW_NEEDS_FIX とする。
MinorまたはSuggestionのみの場合は REVIEW_APPROVED とする。
