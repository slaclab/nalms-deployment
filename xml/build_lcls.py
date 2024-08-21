from os.path import isfile

SUBSYSTEMS = ["BCS", "EVNT", "GADC", "MC", "MGNT", "MPS", "NTWK", "ODM", "PPS", "RF", "TEMP", "UTIL", "VAC"]

def main():

    lcls_filepath = "lcls.csv"
    if isfile(lcls_filepath):
        pass
    else:
        #Create lcls.csv if it doesn't exist already
        open("lcls.csv", "x")

    print("Building LCLS")
    with open("lcls.csv", "w") as lcls:
        count = 0
        for subsystem in SUBSYSTEMS:
            #Convert subsystem name to lowercase and create name of its CSV file
            system = subsystem.lower()
            csv_name = "xml/subsystems/{}_converted".format(system)

            sub_csv = open(csv_name, "r")

            if count == 0:
                pass
            else:
                next(sub_csv)
            
            lcls.write(sub_csv.read())
            count+=1
        
        lcls.close()
    
    print("LCLS Built")

if __name__=="__main__":
    main()
