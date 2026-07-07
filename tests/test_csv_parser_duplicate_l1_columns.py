import csv

from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows


def _write_csv(path, header, row):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerow(row)


def test_parse_mini_rows_ignores_duplicate_l1_stat_columns(tmp_path):
    file_path = tmp_path / "Minis.csv"
    header = [
        "Type",
        "Mini Name",
        "FvFil",
        "L1 Stats",
        "FvFil",
    ]
    row = [
        "Chill",
        "Mini Example",
        "",
        "",
        "8",
    ]
    _write_csv(file_path, header, row)

    minis = parse_mini_rows(str(file_path))
    assert len(minis) == 1
    assert minis[0]["Name"] == "Mini Example"
    # The first (primary) FvFil cell is blank, so value should remain 0 and
    # must not be pulled from the duplicated level-1 column.
    assert minis[0]["Fever Fill Rate"] == 0


def test_parse_mini_rows_reads_song_target_column(tmp_path):
    file_path = tmp_path / "Minis.csv"
    header = [
        "Type",
        "Mini Name",
        "Song Target",
    ]
    row = [
        "Chill",
        "Mini Example",
        '["Song A by Artist","Song A (Hard) by Artist"]',
    ]
    _write_csv(file_path, header, row)

    minis = parse_mini_rows(str(file_path))
    assert len(minis) == 1
    assert minis[0]["Song Target"] == ["Song A by Artist", "Song A (Hard) by Artist"]
    assert minis[0]["Mini Ascension Enabled"] is True
    assert minis[0]["Mini Ascension Level"] == 10


def test_parse_mini_rows_keeps_l1_color_stats_for_mini_ascension(tmp_path):
    file_path = tmp_path / "Minis.csv"
    header = [
        "Type",
        "Mini Name",
        "Rush",
        "Vibe",
        "L1 Stats",
        "Rush",
        "Vibe",
        "Song Target",
    ]
    row = [
        "Vibe",
        "Ringmaster Roxie",
        "35",
        "65",
        "",
        "7",
        "13",
        '["Clouds in the Blue (Hard) by Camellia"]',
    ]
    _write_csv(file_path, header, row)

    minis = parse_mini_rows(str(file_path))
    assert len(minis) == 1
    assert minis[0]["Rush"] == 35
    assert minis[0]["Vibe"] == 65
    assert minis[0]["Mini Ascension Base Rush"] == 7
    assert minis[0]["Mini Ascension Base Vibe"] == 13


def test_parse_gear_rows_ignores_duplicate_l1_stat_columns(tmp_path):
    file_path = tmp_path / "Gears.csv"
    header = [
        "Type",
        "Gear Name",
        "FvFil",
        "L1 Stats",
        "FvFil",
    ]
    row = [
        "Hat",
        "Gear Example",
        "",
        "",
        "9",
    ]
    _write_csv(file_path, header, row)

    gears = parse_gear_rows(str(file_path))
    assert len(gears) == 1
    assert gears[0]["Name"] == "Gear Example"
    assert gears[0]["Fever Fill Rate"] == 0
