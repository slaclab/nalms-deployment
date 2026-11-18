"""
Tests for validate_csv_for_phoebus.py, the check that every pull request has to pass.

Each case is a small csv file built from the rows below. HEADER is line 1, so the first row passed to
write_csv() is line 2 of the file.
"""
import os

import pytest
from click.testing import CliRunner

from validate_csv_for_phoebus import MAX_ANNOTATIONS, MAX_PROBLEMS_LISTED, main, validate

HEADER = '#Indent,Branch,PV,Description,Latch,Delay,Count,Filter,Guidance'
GLOBAL = '0,Global,SUMMARY:PV,,,,,,Guidance for the whole tree'
COMMON = '1,Common,,,,,,,'
PV_A = ',,PV:A,first pv,TRUE,0,0,,'
PV_B = ',,PV:B,second pv,FALSE,5,3,OTHER:PV > 0,Call someone'


@pytest.fixture
def write_csv(tmp_path):
    def _write(*rows, header=HEADER, newline='\n', encoding='utf-8'):
        path = tmp_path / 'alarms.csv'
        lines = ([header] if header is not None else []) + list(rows)
        text = newline.join(lines) + newline
        path.write_bytes(text.encode(encoding))
        return str(path)
    return _write


def problems_for(path):
    problems, _, _ = validate(path)
    return problems


# --- files that are fine -------------------------------------------------------------------------

def test_valid_file_has_no_problems_and_is_counted(write_csv):
    problems, branches, pvs = validate(write_csv(GLOBAL, COMMON, PV_A, PV_B))
    assert problems == []
    assert (branches, pvs) == (2, 2)


def test_file_saved_by_excel_is_accepted(write_csv):
    # Byte order mark, Windows line endings and a lowercase boolean
    path = write_csv(GLOBAL, COMMON, ',,PV:A,first pv,true,0,,,', newline='\r\n', encoding='utf-8-sig')
    assert problems_for(path) == []


def test_blank_lines_are_ignored(write_csv):
    assert problems_for(write_csv(GLOBAL, '', COMMON, PV_A, '', '')) == []


def test_quoted_commas_quotes_and_special_characters_are_accepted(write_csv):
    row = ',,PV:A,"Temp > 5 & <ok> ""quoted"", with comma",TRUE,0,0,,'
    assert problems_for(write_csv(GLOBAL, COMMON, row)) == []


def test_count_may_be_empty(write_csv):
    assert problems_for(write_csv(GLOBAL, COMMON, ',,PV:A,d,TRUE,0,,,')) == []


def test_same_pv_in_different_branches_is_accepted(write_csv):
    assert problems_for(write_csv(GLOBAL, COMMON, PV_A, '1,Other,,,,,,,', PV_A)) == []


def test_same_branch_name_under_different_parents_is_accepted(write_csv):
    path = write_csv(GLOBAL, '1,X,,,,,,,', '2,Same,,,,,,,', PV_A, '1,Y,,,,,,,', '2,Same,,,,,,,', PV_B)
    assert problems_for(path) == []


def test_branch_may_go_back_up_several_levels(write_csv):
    path = write_csv(GLOBAL, '1,A,,,,,,,', '2,B,,,,,,,', PV_A, '0,Second top level,,,,,,,', PV_B)
    assert problems_for(path) == []


def test_the_real_cryo_configuration_passes():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert problems_for(os.path.join(repo, 'alarm-config', 'cryo.csv')) == []


# --- one mistake each: (rows, line the problem is on, text the message must contain) ---------------

SINGLE_MISTAKES = {
    'latch blank': ([GLOBAL, COMMON, ',,PV:A,d,,0,0,,'], 4, 'Latch must be TRUE or FALSE, not ""'),
    'latch not a boolean': ([GLOBAL, COMMON, ',,PV:A,d,yes,0,0,,'], 4, 'Latch must be TRUE or FALSE, not "yes"'),
    'delay not a number': ([GLOBAL, COMMON, ',,PV:A,d,TRUE,soon,0,,'], 4, 'Delay must be a whole number'),
    'delay blank': ([GLOBAL, COMMON, ',,PV:A,d,TRUE,,0,,'], 4, 'Delay must be a whole number'),
    'delay negative': ([GLOBAL, COMMON, ',,PV:A,d,TRUE,-5,0,,'], 4, 'Delay must be a whole number'),
    'delay decimal': ([GLOBAL, COMMON, ',,PV:A,d,TRUE,1.5,0,,'], 4, 'Delay must be a whole number'),
    'count not a number': ([GLOBAL, COMMON, ',,PV:A,d,TRUE,0,many,,'], 4, 'Count must be a whole number'),
    'pv name missing': ([GLOBAL, COMMON, ',,,d,TRUE,0,0,,'], 4, 'This row has no PV name'),
    'pv twice in one branch': ([GLOBAL, COMMON, PV_A, PV_A], 5, 'PV:A is already listed in the branch "Common"'),
    'pv before any branch': ([PV_A, GLOBAL, PV_B], 2, 'A PV must be inside a branch'),
    'indent skips a level': ([GLOBAL, '2,Too deep,,,,,,,', PV_A], 3, '#Indent 2 skips a level'),
    'first branch not at zero': (['1,Common,,,,,,,', PV_A], 2, 'The first branch must have #Indent 0, not 1'),
    'indent not a number': (['top,Global,,,,,,,', PV_A], 2, '#Indent must be a whole number'),
    'branch without a name': ([GLOBAL, '1,,,,,,,,', PV_A], 3, 'needs a name in the Branch column'),
    'two branches with the same name and parent': (
        [GLOBAL, '1,Same,,,,,,,', PV_A, '1,Same,,,,,,,', PV_B], 5, 'already a branch named "Same" inside "Global"'),
    'two top level branches with the same name': (
        [GLOBAL, PV_A, GLOBAL, PV_B], 4, 'already a branch named "Global" at the top level'),
    'empty branch': ([GLOBAL, '1,Empty,,,,,,,', '1,Full,,,,,,,', PV_A], 3, 'The branch "Empty" has no PVs or branches'),
    'empty branch at the end': ([GLOBAL, COMMON, PV_A, '1,Last,,,,,,,'], 5, 'The branch "Last" has no PVs or branches'),
    'branch name without an indent': ([GLOBAL, ',Common,,,,,,,', PV_A], 3, 'has a Branch name ("Common") but nothing in #Indent'),
    'unquoted comma in a value': ([GLOBAL, COMMON, ',,PV:A,desc with, comma,TRUE,0,0,,'], 4, 'has 10 columns but there should be 9'),
    'too few columns': ([GLOBAL, COMMON, ',,PV:A,d,TRUE'], 4, 'has 5 columns but there should be 9'),
    'row of only commas': ([GLOBAL, COMMON, PV_A, ',,,,,,,,'], 5, 'empty apart from its commas'),
}


@pytest.mark.parametrize('case', SINGLE_MISTAKES)
def test_single_mistake_is_reported_once_on_the_right_line(write_csv, case):
    rows, line, text = SINGLE_MISTAKES[case]
    problems = problems_for(write_csv(*rows))
    assert len(problems) == 1, problems
    assert problems[0][0] == line
    assert text in problems[0][1]


def test_pv_settings_on_a_branch_row_are_reported_together(write_csv):
    problems = problems_for(write_csv(GLOBAL, '1,Common,PV:A,first pv,TRUE,0,0,,', PV_B))
    assert len(problems) == 1
    assert problems[0][0] == 3
    assert 'Description, Latch, Delay, Count are only used for PVs' in problems[0][1]


def test_pv_column_on_a_branch_row_is_allowed_as_a_note(write_csv):
    assert problems_for(write_csv(GLOBAL, '1,Common,SUMMARY:PV2,,,,,,', PV_A)) == []


# --- problems with the file as a whole -----------------------------------------------------------

def test_header_typo_names_the_columns(write_csv):
    problems = problems_for(write_csv(GLOBAL, COMMON, PV_A, header=HEADER.replace('Latch', 'Latching')))
    messages = ' | '.join(message for _, message in problems)
    assert all(line == 1 for line, _ in problems)
    assert 'missing these columns: Latch' in messages
    assert 'not recognised: Latching' in messages


def test_header_in_the_wrong_order(write_csv):
    header = '#Indent,PV,Branch,Description,Latch,Delay,Count,Filter,Guidance'
    problems = problems_for(write_csv(GLOBAL, COMMON, PV_A, header=header))
    assert 'wrong order' in problems[0][1]


def test_missing_header_gives_one_message(write_csv):
    problems = problems_for(write_csv(GLOBAL, COMMON, PV_A, header=None))
    assert problems == [(1, f'The first line must be the header: {HEADER}')]


def test_empty_file(tmp_path):
    path = tmp_path / 'empty.csv'
    path.write_text('')
    assert problems_for(str(path)) == [(1, 'The file is empty')]


def test_header_only(write_csv):
    assert problems_for(write_csv()) == [(1, 'The file has no branches or PVs')]


def test_file_that_is_not_utf8(write_csv):
    problems = problems_for(write_csv(GLOBAL, COMMON, ',,PV:A,caf\xe9,TRUE,0,0,,', encoding='latin-1'))
    assert len(problems) == 1
    assert 'not valid UTF-8' in problems[0][1]


# --- line numbers and noise ----------------------------------------------------------------------

def test_line_number_is_right_after_a_value_that_spans_lines(write_csv):
    path = write_csv(GLOBAL, COMMON, ',,PV:A,d,TRUE,0,0,,"line one', 'line two"', ',,PV:B,d,maybe,0,0,,')
    assert problems_for(path) == [(6, 'Latch must be TRUE or FALSE, not "maybe"')]


def test_several_mistakes_are_all_reported_in_line_order(write_csv):
    path = write_csv(GLOBAL, COMMON, ',,PV:A,d,yes,0,0,,', ',,,d,TRUE,0,0,,', ',,PV:C,d,TRUE,x,0,,')
    assert [line for line, _ in problems_for(path)] == [4, 5, 6]


def test_one_wrong_indent_does_not_cause_a_problem_on_every_later_row(write_csv):
    # The second row is too deep. The PVs and branches after it are fine and must not be reported.
    rows = [GLOBAL, '2,Too deep,,,,,,,', PV_A, '1,Next,,,,,,,', PV_B, '2,Child,,,,,,,', PV_A]
    assert [line for line, _ in problems_for(write_csv(*rows))] == [3]


def test_a_branch_nested_under_a_wrongly_indented_one_is_reported_too(write_csv):
    # "Too deep" has to become level 1, so "Deeper" has to change as well. Both lines need fixing.
    rows = [GLOBAL, '2,Too deep,,,,,,,', PV_A, '3,Deeper,,,,,,,', PV_B]
    assert [line for line, _ in problems_for(write_csv(*rows))] == [3, 5]


def test_malformed_row_does_not_also_report_its_branch_as_empty(write_csv):
    problems = problems_for(write_csv(GLOBAL, COMMON, ',,PV:A,d,TRUE'))
    assert [line for line, _ in problems] == [4]


# --- the command itself --------------------------------------------------------------------------

def test_command_succeeds_and_summarises_a_valid_file(write_csv):
    path = write_csv(GLOBAL, COMMON, PV_A, PV_B)
    result = CliRunner().invoke(main, [path])
    assert result.exit_code == 0
    assert 'OK (2 branches, 2 PVs)' in result.output


def test_command_fails_and_lists_problems_with_line_numbers(write_csv):
    path = write_csv(GLOBAL, COMMON, ',,PV:A,d,yes,0,0,,')
    result = CliRunner().invoke(main, [path])
    assert result.exit_code == 1
    assert '1 problem found' in result.output
    assert 'line 4: Latch must be TRUE or FALSE, not "yes"' in result.output
    assert '::error' not in result.output


def test_command_fails_if_any_of_several_files_has_a_problem(write_csv, tmp_path):
    good = tmp_path / 'good.csv'
    good.write_text('\n'.join([HEADER, GLOBAL, PV_A]) + '\n')
    bad = write_csv(GLOBAL, COMMON, ',,PV:A,d,yes,0,0,,')
    result = CliRunner().invoke(main, [str(good), bad])
    assert result.exit_code == 1
    assert 'good.csv: OK' in result.output


def test_command_emits_annotations_when_run_by_github_actions(write_csv, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    path = write_csv(GLOBAL, COMMON, ',,PV:A,d,yes,0,0,,')
    result = CliRunner().invoke(main, [path])
    assert f'::error file={path},line=4,title=Alarm configuration::Latch must be TRUE or FALSE, not "yes"' in result.output


def test_long_lists_of_problems_are_capped(write_csv, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    total = MAX_PROBLEMS_LISTED + 7
    rows = [GLOBAL, COMMON] + [f',,PV:{n},d,yes,0,0,,' for n in range(total)]
    result = CliRunner().invoke(main, [write_csv(*rows)])
    assert f'{total} problems found' in result.output
    assert result.output.count('  line ') == MAX_PROBLEMS_LISTED
    assert '... and 7 more' in result.output
    assert result.output.count('::error') == MAX_ANNOTATIONS
