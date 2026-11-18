from os.path import abspath, dirname, isfile, join

# Directory holding the alarm config csv files, next to the directory this script is in
CONFIG_DIR = join(dirname(dirname(abspath(__file__))), "alarm-config")

SUBSYSTEMS = ["BCS", "EVNT", "GADC", "MC", "MGNT", "MPS", "NTWK", "ODM", "PPS", "RF", "TEMP", "UTIL", "VAC"]

def main():

    lcls_filepath = join(CONFIG_DIR, "lcls.csv")
    if isfile(lcls_filepath):
        pass
    else:
        #Create lcls.csv if it doesn't exist already
        open(lcls_filepath, "x")

    print("Building LCLS")
    with open(lcls_filepath, "w") as lcls:
        count = 0
        for subsystem in SUBSYSTEMS:
            #Convert subsystem name to lowercase and create name of its CSV file
            system = subsystem.lower()
            csv_name = join(CONFIG_DIR, "lcls-subsystems", "{}_converted".format(system))

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
