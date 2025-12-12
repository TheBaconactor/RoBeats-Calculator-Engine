from gear_optimizer.data.csv_parser import parse_mini_rows

minis = parse_mini_rows('Data/Gear/Minis.csv')
hyun = [m for m in minis if 'HyuN' in m.get('Name', '')]
print(f'Found HyuN: {hyun}')
print(f'Total minis: {len(minis)}')

def score(m):
    return m.get('Chill', 0) * 3 + m.get('Perfect Points', 0) * 2 + m.get('Combo Multiplier', 0) * 2 + m.get('Fever Multiplier', 0) * 2

ranked = sorted(minis, key=score, reverse=True)
print('\nTop 20 by Chill heuristic score:')
for i, m in enumerate(ranked[:20]):
    print(f"{i+1}. {m.get('Name')}: score={score(m)}")

hyun_rank = next((i+1 for i,m in enumerate(ranked) if 'HyuN' in m.get('Name','')), None)
print(f'\nHyuN rank: {hyun_rank}')
