# 台本レビュー修正ループを判定する
script_reviews と revise_script のループが {cycle_count} 回繰り返されています。
各レビューと修正履歴を比較し、指摘が減少し反映されているなら LOOP_HEALTHY、
上流判断が必要なら LOOP_ESCALATE、同じ問題が解消されず進展がないなら LOOP_ABORT を出してください。
判定語は一つだけ出してください。
