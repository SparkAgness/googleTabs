import sheets_transfer
import petrol_private
import corp
import time
import datetime

def main():
    while (True):
        nowTime = datetime.datetime.now()        
        if nowTime.hour == 10:
            print("The program is beginning")
            rl = corp.corporatePetrol()        
            rl.searchingValues()
            print(len(rl.getRegionsList()))
            pp = petrol_private.privatePetrol()
            transfer = sheets_transfer.toSheets()
            transfer.insertData()
            time.sleep(3600)
        else:
            print("It is too early to start program, so waiting 1 a.m")
            time.sleep(3600)

if __name__ == "__main__":
    main()