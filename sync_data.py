import csv
import json
import re
import requests

def sync_spreadsheet_to_json(sheet_url, output_filename="buddies_master.json"):
    print("--- 1. スプレッドシートのダウンロード ---")
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError("無効なスプレッドシートURLです。")
    spreadsheet_id = match.group(1)

    gid = re.search(r"gid=([0-9]+)", sheet_url)
    gid_str = f"&gid={gid.group(1)}" if gid else ""

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv{gid_str}"

    response = requests.get(url)
    response.encoding = "utf-8"
    lines = response.text.splitlines()
    reader = list(csv.reader(lines))

    if len(reader) < 7:
        raise ValueError("スプレッドシートの行数が足りません。7行目にヘッダーが必要です。")

    header = reader[6]

    print("--- 2. 対象列のインデックス探索（7行目） ---")
    idx_A = idx_B = idx_C = idx_D = None
    for i in range(len(header) - 3):
        if (
            "メラメラ" in header[i] and 
            "ポカポカ" in header[i+1] and 
            "ウルウル" in header[i+2] and 
            "アイテム" in header[i+3]
        ):
            idx_A, idx_B, idx_C, idx_D = i, i + 1, i + 2, i + 3
            break

    idx_name = next((i for i, c in enumerate(header) if "バディーズ名" in c), None)
    idx_region = next((i for i, c in enumerate(header) if "地方" in c), None)

    if None in [idx_name, idx_region, idx_A, idx_B, idx_C, idx_D]:
        raise ValueError("必要な列がヘッダー（7行目）に見つかりません。")

    print("--- 3. データの抽出とラベル翻訳（8行目以降） ---")
    split_data = {"variable": [], "immutable": []}

    for row in reader[7:]:
        max_required_idx = max(idx_name, idx_region, idx_D)
        if len(row) <= max_required_idx:
            continue

        name = row[idx_name].strip()
        region = row[idx_region].strip()

        if not name or not region:
            continue

        def parse_val(val_str):
            cleaned = val_str.strip()
            if not cleaned:
                return 0
            try:
                return int(float(cleaned))
            except ValueError:
                return 0

        a = parse_val(row[idx_A])
        b = parse_val(row[idx_B])
        c = parse_val(row[idx_C])
        d = parse_val(row[idx_D])

        # すべて0の行はデータ行ではないためスキップ
        if a == 0 and b == 0 and c == 0 and d == 0:
            continue

        # 🚨 【判定・翻訳ルール】
        # 1. A, B, C のいずれかが 4 の場合 ➔ 3人以上なら4になるタイプ
        if a == 4 or b == 4 or c == 4:
            target_stat = "a" if a == 4 else ("b" if b == 4 else "c")
            split_data["variable"].append({
                "name": name,
                "region": region,
                "calc_type": "flat_4_if_3",
                "target": target_stat
            })
        
        # 2. A, B, C のいずれかが 6 の場合 ➔ 人数がそのままステータスになるタイプ
        elif a == 6 or b == 6 or c == 6:
            target_stat = "a" if a == 6 else ("b" if b == 6 else "c")
            split_data["variable"].append({
                "name": name,
                "region": region,
                "calc_type": "scale_by_x",
                "target": target_stat
            })
            
        # 3. D が 2 で他が 0 の場合 ➔ 3人以上ならアイテム2個になるタイプ
        elif d == 2 and a == 0 and b == 0 and c == 0:
            split_data["variable"].append({
                "name": name,
                "region": region,
                "calc_type": "item_2_if_3",
                "target": "d"
            })
            
        # 4. 上記以外 ➔ 固定キャラ（数値をそのまま配列で保存）
        else:
            split_data["immutable"].append({
                "name": name,
                "region": region,
                "calc_type": "immutable",
                "stats": [a, b, c, d]
            })

    print("--- 4. ラベル付きJSONファイルへの書き出し ---")
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(split_data, f, ensure_ascii=False, indent=2)

    print(f"処理完了: {output_filename}")
    print(f" ┗ 可変キャラ (variable) : {len(split_data['variable'])}件")
    print(f" ┗ 固定キャラ (immutable): {len(split_data['immutable'])}件")

if __name__ == "__main__":
    URL = "https://docs.google.com/spreadsheets/d/1ByoFfpGVAlasZA3u7wGHGXHj8cT5GymYfflpPOo4fKw/edit?gid=0#gid=0"
    sync_spreadsheet_to_json(URL, "buddies_master.json")
