# Run validation against all xml files using xmllint. Print any errors,
# with a non-zero exit code representing the number of failed files

exit_code=0
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
#for FILE in $SCRIPT_DIR/*.xml; do
#  xmllint --noout --schema $SCRIPT_DIR/phoebus-alarm-server.xsd $FILE || ((exit_code++));
#done

# Temporarily run on lcls only, restore once alarm server restart is more stable
FILE="$SCRIPT_DIR/lcls.xml"
xmllint --noout --schema "$SCRIPT_DIR/phoebus-alarm-server.xsd" "$FILE" || ((exit_code++))
exit $exit_code
