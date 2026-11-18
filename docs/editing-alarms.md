# Editing alarm configurations

Each alarm configuration is a CSV file in `alarm-config/`, for example `alarm-config/cryo.csv`.
The CSV is the only file to edit. The matching XML file, which is what the alarm server reads,
is generated from it automatically.

## In short

1. Edit the CSV on a branch and open a pull request.
2. The checks validate the CSV and add the regenerated XML to the pull request.
3. Someone else with write access to the repository approves the pull request.
4. You merge it. The alarm server reloads the new configuration within about two minutes.
   Nothing needs to be deployed by hand.

You need write access to the repository to do this. Changes cannot be pushed straight to
`main`, they have to go through a pull request.

## The CSV format

The first line is the header and must stay as it is:

```
#Indent,Branch,PV,Description,Latch,Delay,Count,Filter,Guidance
```

Every other line is either a branch of the alarm tree or a PV inside the branch above it.

**Branch rows** have a number in `#Indent` and a name in `Branch`:

```
0,Global,,,,,,,
1,Utilities,,,,,,,Guidance shown for the whole branch
2,Instrument Air,,,,,,,
```

- `#Indent` is the depth in the tree. `0` is a top level branch, `1` is inside the most recent
  `0`, and so on. A branch can be at most one level deeper than the branch before it.
- `Guidance` is an optional message for operators explaining what an alarm in this branch
  means and who to contact.
- The other columns are ignored on a branch row. The existing files put the branch's summary
  PV in the `PV` column as a note.

**PV rows** leave `#Indent` and `Branch` empty. The PV belongs to the nearest branch row above it:

```
,,SIOC:CP08:CR01:HEARTBEAT,CP0 CTRL - Utilities IOC,TRUE,0,0,,
```

| Column | Meaning |
|---|---|
| `PV` | The PV to monitor. |
| `Description` | Text displayed in the alarm table when the alarm is triggered. |
| `Latch` | `TRUE` latches the alarm to its highest severity until it is acknowledged and has cleared. `FALSE` lets the alarm recover without being acknowledged. |
| `Delay` | The alarm is raised only if the PV stays in alarm for at least this many seconds. `0` raises it immediately. |
| `Count` | Used with `Delay`. The alarm is also raised if the PV goes into alarm this many times within the delay, even if it never stays in alarm for the whole delay. `0` turns this off. |
| `Filter` | Optional expression, usually based on other PVs, that enables the alarm. The alarm is only enabled while the expression is greater than zero. |
| `Guidance` | Optional message explaining what the alarm means and who to contact. |

Wrap a value in double quotes if it contains a comma.

These columns correspond to the Phoebus alarm configuration options described in the
[NALMS configuration documentation](https://slaclab.github.io/nalms/configuration/).

## What the checks do

On every pull request that touches `alarm-config/` or `tools/`, the
"Convert alarm config csv to xml" workflow:

1. Checks that no PV is listed twice in the same branch. The same PV may appear in different
   branches.
2. Converts the CSV to XML.
3. Validates the XML against the Phoebus alarm configuration schema.
4. If the XML changed, commits it to the pull request as a second commit, so it can be reviewed
   next to the CSV change.

Two things to expect:

- The checks do not run again on the commit the workflow adds, so the pull request shows no
  check result for that last commit. The result that matters is the one on your own commit
  just before it, which is where the XML was generated and validated.
- For a pull request from a fork, the workflow cannot add a commit, and the check fails
  until the pull request includes the regenerated XML. Either run the conversion yourself
  (see below) and commit the XML, or ask for write access and open the pull request from a
  branch in this repository.

Do not edit the XML files by hand. They are regenerated from the CSV every time, so a manual
change is overwritten.

Only `cryo` is converted at the moment. `lcls.csv` and `lcls.xml` are in the repository but are
not part of this process yet.

## Running the checks yourself

This is optional, since the pull request runs the same steps.

```sh
pip install -r dev-requirements.txt
python tools/validate_csv_for_phoebus.py alarm-config/cryo.csv
python tools/alarm_csv2xml.py -i alarm-config/cryo.csv -c CRYO
python tools/validate_xml_for_phoebus.py
./tools/lint_xml.sh cryo
```

The last step needs `xmllint`, which is in the `libxml2-utils` package on Debian and Ubuntu.
The conversion rewrites `alarm-config/cryo.xml`. For a pull request from a branch in this
repository you can commit that along with the CSV or discard it, the result is the same.

## Review and merging

A pull request needs one approval from someone other than its author before it can be merged.
Any person with write access can approve. Before approving, check that:

- the checks passed on the author's commit, and the workflow's XML commit follows it;
- the CSV change is what was intended, and the XML change matches it;
- now is an acceptable time for the alarm server to reload (see the next section).

Once it is approved, the author can merge it.

## What happens when a change is merged

Merging changes the XML on `main`. A sidecar container next to the alarm server checks `main`
every two minutes, copies the new XML into place and tells the alarm server to reload. The
reload only happens if the XML actually changed.

During a reload:

- The alarm server stops monitoring its PVs for a short time. This was about 20 seconds for
  the CRYO configuration.
- An alarm that comes and goes entirely within that time is not seen.
- Acknowledged alarms stay acknowledged.
- Alarms that were not acknowledged are evaluated again from the current state of each PV.
  One that is still active is raised again. One that had latched but has since returned to
  normal is cleared.
- The Slack channel normally does not repeat alarms that were already reported. It can repeat
  one whose severity is now different from what was last reported, for example an alarm that
  latched as MAJOR and is currently MINOR.

Because of this, merge alarm configuration changes at a time when a brief gap in monitoring
is acceptable.
