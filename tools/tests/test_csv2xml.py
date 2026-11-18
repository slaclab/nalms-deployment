"""
Tests for alarm_csv2xml.py, which turns an alarm configuration csv file into the xml the alarm server reads.
"""
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner

from alarm_csv2xml import csvtoxml

HEADER = '#Indent,Branch,PV,Description,Latch,Delay,Count,Filter,Guidance'


@pytest.fixture
def convert(tmp_path):
    """ Convert the given rows and return the root element of the xml that was written """
    def _convert(*rows, config_name='CRYO', encoding='utf-8', newline='\n'):
        csv_path = tmp_path / 'alarms.csv'
        xml_path = tmp_path / 'alarms.xml'
        csv_path.write_bytes((newline.join([HEADER] + list(rows)) + newline).encode(encoding))
        result = CliRunner().invoke(csvtoxml, ['-i', str(csv_path), '-o', str(xml_path), '-c', config_name])
        assert result.exit_code == 0, result.output
        return ET.parse(xml_path).getroot()
    return _convert


def test_root_is_a_config_with_the_given_name(convert):
    root = convert('0,Global,,,,,,,', ',,PV:A,d,TRUE,0,0,,')
    assert root.tag == 'config'
    assert root.get('name') == 'CRYO'


def test_branches_are_nested_by_indent(convert):
    root = convert(
        '0,Global,,,,,,,',
        '1,Common,,,,,,,',
        ',,PV:A,d,TRUE,0,0,,',
        '1,Utilities,,,,,,,',
        '2,Instrument Air,,,,,,,',
        ',,PV:B,d,TRUE,0,0,,',
        '0,Second,,,,,,,',
        ',,PV:C,d,TRUE,0,0,,',
    )
    assert [c.get('name') for c in root.findall('component')] == ['Global', 'Second']
    global_branch = root.find("component[@name='Global']")
    assert [c.get('name') for c in global_branch.findall('component')] == ['Common', 'Utilities']
    assert global_branch.find("component[@name='Common']/pv").get('name') == 'PV:A'
    assert global_branch.find("component[@name='Utilities']/component[@name='Instrument Air']/pv").get('name') == 'PV:B'
    assert root.find("component[@name='Second']/pv").get('name') == 'PV:C'


def test_pv_settings_are_written(convert):
    root = convert('0,Global,,,,,,,', ',,PV:A,The description,TRUE,5,3,OTHER:PV > 0,')
    pv = root.find('.//pv')
    assert pv.get('name') == 'PV:A'
    assert pv.findtext('description') == 'The description'
    assert pv.findtext('delay') == '5'
    assert pv.findtext('count') == '3'
    assert pv.findtext('filter') == 'OTHER:PV > 0'


@pytest.mark.parametrize('value, expected', [('TRUE', 'true'), ('FALSE', 'false'), ('true', 'true'), ('False', 'false')])
def test_latching_is_written_in_lowercase(convert, value, expected):
    # The schema only accepts lowercase booleans
    root = convert('0,Global,,,,,,,', f',,PV:A,d,{value},0,0,,')
    assert root.findtext('.//pv/latching') == expected


def test_empty_count_and_filter_are_left_out(convert):
    pv = convert('0,Global,,,,,,,', ',,PV:A,d,TRUE,0,,,').find('.//pv')
    assert pv.find('count') is None
    assert pv.find('filter') is None


def test_guidance_on_a_pv_row_goes_on_that_pv(convert):
    root = convert(
        '0,Global,,,,,,,Guidance for the branch',
        ',,PV:A,d,TRUE,0,0,,Guidance for PV A',
        ',,PV:B,d,TRUE,0,0,,',
    )
    branch = root.find('component')
    assert [g.findtext('details') for g in branch.findall('guidance')] == ['Guidance for the branch']
    assert branch.find("pv[@name='PV:A']/guidance/details").text == 'Guidance for PV A'
    assert branch.find("pv[@name='PV:B']/guidance") is None


def test_values_are_stripped_and_special_characters_survive(convert):
    root = convert('0, Global ,,,,,,,', ',, PV:A ,"Temp > 5 & <ok> ""quoted"", with comma",TRUE,0,0,,')
    assert root.find('component').get('name') == 'Global'
    pv = root.find('.//pv')
    assert pv.get('name') == 'PV:A'
    assert pv.findtext('description') == 'Temp > 5 & <ok> "quoted", with comma'


def test_file_saved_by_excel_is_converted(convert):
    root = convert('0,Global,,,,,,,', ',,PV:A,d,TRUE,0,0,,', encoding='utf-8-sig', newline='\r\n')
    assert root.find('component').get('name') == 'Global'
    assert root.find('.//pv').get('name') == 'PV:A'


def test_blank_lines_are_skipped(convert):
    root = convert('0,Global,,,,,,,', '', ',,PV:A,d,TRUE,0,0,,', '')
    assert len(root.findall('.//pv')) == 1
