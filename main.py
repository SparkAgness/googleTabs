import sheets_transfer
import petrol_private
import corp

def main():
    rl = corp.corporatePetrol()        
    rl.searchingValues()
    print(len(rl.getRegionsList()))
    pp = petrol_private.privatePetrol()
    transfer = sheets_transfer.toSheets()
    transfer.insertData()

if __name__ == "__main__":
    main()