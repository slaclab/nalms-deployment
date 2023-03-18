# Run validation against all xml files using xmllint. Print any errors,
# with a non-zero exit code representing the number of failed files

exit_code=0
for FILE in *.xml; do
  xmllint --noout --schema phoebus-alarm-server.xsd $FILE || ((exit_code++));
done

exit $exit_code
