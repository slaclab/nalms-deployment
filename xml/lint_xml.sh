# Run validation against the listed xml files using xmllint. Print any errors,
# with a non-zero exit code representing the number of failed files

exit_code=0
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Only cryo for now, add lcls once the LCLS config is stable
CONFIGS="cryo"

for CONFIG in $CONFIGS; do
  xmllint --noout --schema "$SCRIPT_DIR/phoebus-alarm-server.xsd" "$SCRIPT_DIR/$CONFIG.xml" || ((exit_code++))
done
exit $exit_code
