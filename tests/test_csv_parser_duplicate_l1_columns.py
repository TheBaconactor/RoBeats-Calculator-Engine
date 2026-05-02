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
