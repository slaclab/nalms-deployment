"""
Check that an alarm configuration csv file is well formed before it is converted to xml.

Every problem found is reported with the line it is on, and the script exits with a non-zero status if
there are any. When run by GitHub Actions the problems are also reported as annotations, which GitHub
shows against the matching lines of the pull request.
"""
import csv
import os
import sys
from typing import List, Tuple

import click

EXPECTED_HEADER = ['#Indent', 'Branch', 'PV', 'Description', 'Latch', 'Delay', 'Count', 'Filter', 'Guidance']

# Columns that only mean something for a PV, so a value in one of them on a branch row is a mistake
PV_ONLY_COLUMNS = ['Description', 'Latch', 'Delay', 'Count', 'Filter']

Problem = Tuple[int, str]

# A file with one early mistake can produce a great many problems, so only the first ones are listed.
# GitHub shows at most 10 annotations from one step.
MAX_PROBLEMS_LISTED = 50
MAX_ANNOTATIONS = 10


class Branch:
    """ A branch of the alarm tree, as far as it is needed for checking what is inside it """

    def __init__(self, name: str, line: int):
        self.name = name
        self.line = line
        self.child_branch_names = set()
        self.pv_names = set()
        self.has_children = False


def is_whole_number(text: str) -> bool:
    """ True for 0, 1, 2 and so on. Signs, decimals and anything else are not accepted. """
    return text.isascii() and text.isdigit()


def check_header(row: List[str], line: int) -> List[Problem]:
    header = [column.strip() for column in row]
    if header == EXPECTED_HEADER:
        return []

    problems = []
    missing = [column for column in EXPECTED_HEADER if column not in header]
    unexpected = [column for column in header if column not in EXPECTED_HEADER]
    if len(missing) == len(EXPECTED_HEADER):
        return [(line, f'The first line must be the header: {",".join(EXPECTED_HEADER)}')]
    if missing:
        problems.append((line, f'The header is missing these columns: {", ".join(missing)}'))
    if unexpected:
        problems.append((line, f'The header has columns that are not recognised: {", ".join(unexpected)}'))
    if not missing and not unexpected:
        problems.append((line, 'The header columns are in the wrong order'))
    problems.append((line, f'The first line must be exactly: {",".join(EXPECTED_HEADER)}'))
    return problems


def check_branch_row(values: dict, line: int, stack: List[Branch]) -> Tuple[List[Problem], Branch]:
    """
    Check a row that starts a branch. Returns the problems found and the new branch.
    """
    problems = []
    indent = values['#Indent']
    name = values['Branch']

    if not name:
        problems.append((line, 'A row with a value in #Indent starts a branch, so it needs a name in the Branch column'))

    pv_values = [column for column in PV_ONLY_COLUMNS if values[column]]
    if pv_values:
        problems.append((line, f'{", ".join(pv_values)} {"is" if len(pv_values) == 1 else "are"} only used for PVs, '
                               f'but this row starts a branch because it has a value in #Indent. Leave #Indent and '
                               f'Branch empty for a PV'))

    # stack[0] is the root of the tree, so a branch at level N goes inside stack[N]
    deepest_allowed = len(stack) - 1
    if not is_whole_number(indent):
        problems.append((line, f'#Indent must be a whole number such as 0, 1 or 2, not "{indent}"'))
        level = deepest_allowed
    else:
        level = int(indent)
        if level > deepest_allowed:
            if deepest_allowed == 0:
                problems.append((line, f'The first branch must have #Indent 0, not {level}'))
            else:
                problems.append((line, f'#Indent {level} skips a level. The branch above is at level '
                                       f'{deepest_allowed - 1}, so this one can be at most {deepest_allowed}'))
            # Carry on as if it were one level down, so that this one mistake is not reported again
            # for every row that follows
            level = deepest_allowed

    del stack[level + 1:]
    parent = stack[level]
    if name:
        if name in parent.child_branch_names:
            where = f'inside "{parent.name}"' if level > 0 else 'at the top level'
            problems.append((line, f'There is already a branch named "{name}" {where}'))
        parent.child_branch_names.add(name)
    parent.has_children = True

    return problems, Branch(name, line)


def check_pv_row(values: dict, line: int, stack: List[Branch]) -> List[Problem]:
    problems = []
    pv = values['PV']

    if values['Branch']:
        problems.append((line, f'This row has a Branch name ("{values["Branch"]}") but nothing in #Indent. '
                               f'Give it an #Indent to start a branch, or clear Branch if it is a PV'))
        if not pv:
            # It was almost certainly meant to be a branch, so the PV checks would only add noise
            return problems

    if len(stack) == 1:
        problems.append((line, 'A PV must be inside a branch, but there is no branch row above this one'))
    branch = stack[-1]

    if not pv:
        problems.append((line, 'This row has no PV name. Remove the row, or put the PV to monitor in the PV column'))
    else:
        if pv in branch.pv_names:
            problems.append((line, f'{pv} is already listed in the branch "{branch.name}". A PV can only appear '
                                   f'once in a branch'))
        branch.pv_names.add(pv)
    branch.has_children = True

    if values['Latch'].upper() not in ('TRUE', 'FALSE'):
        problems.append((line, f'Latch must be TRUE or FALSE, not "{values["Latch"]}"'))

    if not is_whole_number(values['Delay']):
        problems.append((line, f'Delay must be a whole number of seconds such as 0, not "{values["Delay"]}"'))

    if values['Count'] and not is_whole_number(values['Count']):
        problems.append((line, f'Count must be a whole number such as 0, or empty, not "{values["Count"]}"'))

    return problems


def validate(file_path: str) -> Tuple[List[Problem], int, int]:
    """
    Check an alarm configuration csv file.

    Returns the problems found as (line number, message), and the number of branches and PVs seen.
    """
    problems: List[Problem] = []
    branches: List[Branch] = []
    pv_count = 0

    # The root of the tree, which the top level branches go inside
    stack = [Branch('', 0)]

    try:
        # utf-8-sig accepts files both with and without the byte order mark that Excel adds
        with open(file_path, mode='r', encoding='utf-8-sig', newline='') as file:
            reader = csv.reader(file)
            header_seen = False
            line = 1
            for row in reader:
                # A quoted value can run over several lines, so note where the row started
                first_line, line = line, reader.line_num + 1

                # Entirely blank lines are skipped by the converter too
                if not row:
                    continue

                if not header_seen:
                    header_seen = True
                    header_problems = check_header(row, first_line)
                    if header_problems:
                        # Without the right columns nothing else can be checked reliably
                        return header_problems, 0, 0
                    continue

                if len(row) != len(EXPECTED_HEADER):
                    hint = ''
                    if len(row) > len(EXPECTED_HEADER):
                        hint = '. If a value contains a comma, wrap that value in double quotes'
                    elif reader.line_num > first_line:
                        hint = (f'. It runs from line {first_line} to line {reader.line_num}, which usually means '
                                f'a double quote was opened and not closed')
                    problems.append((first_line, f'This row has {len(row)} columns but there should be '
                                                 f'{len(EXPECTED_HEADER)}{hint}'))
                    # Whatever this row was meant to be, it was something inside the current branch
                    stack[-1].has_children = True
                    continue

                values = {column: value.strip() for column, value in zip(EXPECTED_HEADER, row)}

                if not any(values.values()):
                    problems.append((first_line, 'This row is empty apart from its commas. Remove it'))
                    continue

                if values['#Indent']:
                    row_problems, branch = check_branch_row(values, first_line, stack)
                    problems.extend(row_problems)
                    stack.append(branch)
                    branches.append(branch)
                else:
                    problems.extend(check_pv_row(values, first_line, stack))
                    pv_count += 1

            if not header_seen:
                return [(1, 'The file is empty')], 0, 0
    except UnicodeDecodeError as e:
        return [(1, f'The file is not valid UTF-8 text ({e.reason} at byte {e.start}). Save it as "CSV UTF-8"')], 0, 0
    except csv.Error as e:
        return [(reader.line_num, f'The file could not be read as csv: {e}')], 0, 0

    for branch in branches:
        if not branch.has_children:
            problems.append((branch.line, f'The branch "{branch.name}" has no PVs or branches inside it. '
                                          f'Add some, or remove the branch'))

    if not branches and not problems:
        problems.append((1, 'The file has no branches or PVs'))

    return sorted(problems), len(branches), pv_count


def report(file_path: str, problems: List[Problem]) -> None:
    in_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    click.echo(f'{file_path}: {len(problems)} problem{"" if len(problems) == 1 else "s"} found')
    for line, message in problems[:MAX_PROBLEMS_LISTED]:
        click.echo(f'  line {line}: {message}')
    if len(problems) > MAX_PROBLEMS_LISTED:
        click.echo(f'  ... and {len(problems) - MAX_PROBLEMS_LISTED} more. Fix the ones above and run this again')

    if in_github_actions:
        # Shown by GitHub against the matching line of the file in the pull request
        for line, message in problems[:MAX_ANNOTATIONS]:
            escaped = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            click.echo(f'::error file={file_path},line={line},title=Alarm configuration::{escaped}')


@click.command()
@click.argument('csv_files', nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
def main(csv_files):
    """ Check one or more alarm configuration csv files. """
    failed = False
    for csv_file in csv_files:
        problems, branch_count, pv_count = validate(csv_file)
        if problems:
            report(csv_file, problems)
            failed = True
        else:
            click.echo(f'{csv_file}: OK ({branch_count} branch{"" if branch_count == 1 else "es"}, '
                       f'{pv_count} PV{"" if pv_count == 1 else "s"})')

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
