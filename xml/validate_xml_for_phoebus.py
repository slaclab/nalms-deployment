from pathlib import Path

import click
import os
import xml.etree.ElementTree as ET


def validate_xml(xml_file_name: str, xml_content: str) -> bool:
    """
    Check if the input xml file will be parsed correctly by the Phoebus alarm server. Currently just detects
    duplicate PV names on the same branch of the alarm tree. (Duplicates on different branches are allowed)

    Parameters
    ----------
    xml_file_name: str
        Name of the xml file being validated
    xml_content: str
        Contents of the xml file being validated

    Returns
    -------
    True if the file will work with Phoebus, False otherwise
    """
    validates_successfully = True
    try:
        root = ET.fromstring(xml_content)
        for component in root.findall('.//component'):
            pv_names = set()
            for pv in component.findall('./pv'):
                pv_name = pv.get('name')
                if pv_name in pv_names:
                    print(f'ERROR: Duplicate PV name found: {pv_name}')
                    validates_successfully = False
                pv_names.add(pv_name)
        return validates_successfully
    except ET.ParseError as e:
        print(f'Error parsing {xml_file_name}: {e}')
        return False


@click.command()
@click.option('--xml-dir', 'xml_dir', type=click.Path(exists=True),
              default=os.path.dirname(os.path.abspath(__file__)),
              show_default=True,
              help="Directory path containing xml files to validate. Defaults to this script's directory.")
def main(xml_dir):
    xml_dir = Path(xml_dir)

    fail = False
    for xml_file in xml_dir.glob('**/*.xml'):
        print(f'Validating {xml_file}...')

        with open(xml_file, 'r') as f:
            xml_content = f.read()
            if not validate_xml(xml_file.name, xml_content):
                fail = True

    if fail:
        raise click.Abort()


if __name__ == "__main__":
    main()
