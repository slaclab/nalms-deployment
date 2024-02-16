from typing import List

import click
import csv


def check_duplicate_pvs(file_path: str) -> List[str]:
    """
    Checks for any PVs which appear in the same branch of the alarm tree multiple times. Duplicate PVs are otherwise
    ok as long as they appear in different branches.

    Parameters
    ----------
    file_path: str
        Path to the file to validate

    Returns
    -------
    List[str] -- List of PVs that appear to be duplicates. Will be empty if no duplicates are found.
    """
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        duplicate_pvs = []
        seen_pvs = set()

        for row in reader:
            first_element = row[0]

            # Check if the first element is a number
            try:
                float(first_element)
                processing_pvs = False
                seen_pvs.clear()
            except ValueError:
                processing_pvs = True

            # Check if the same PV name is in the same branch more than once
            if processing_pvs:
                pv_name = row[2]

                if pv_name in seen_pvs:
                    duplicate_pvs.append(pv_name)
                else:
                    seen_pvs.add(pv_name)

        return duplicate_pvs


@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
def main(csv_file):
    duplicate_pvs = check_duplicate_pvs(csv_file)
    if duplicate_pvs:
        click.echo(f'Found duplicate pvs: {duplicate_pvs}')
        raise click.Abort()


if __name__ == "__main__":
    main()
