import csv

with open("Data/Gear/Minis.csv", encoding="utf-8-sig") as f:
    rows = list(csv.reader(f))
headers = rows[0]
name_idx = headers.index("Mini Name")
names = set(r[name_idx] for r in rows[1:])
print(f"Total minis: {len(names)}")
for t in ["Juggernaut", "Lappy", "Kurante Metal Dimensions"]:
    print(f"  {t}: {t in names}")
